import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

/*
 * Distributed Messaging Enterprise Architecture.
 *
 * Java 17
 *
 * Models:
 * - Message queues
 * - Partitioned event streams
 * - Consumer groups
 * - Delivery guarantees
 * - Acknowledgement policies
 * - Retry and dead-letter processing
 * - Idempotency
 * - Offset management
 * - Transactional processing boundaries
 * - Operational metrics
 */

public class DistributedMessaging {

    enum DeliveryGuarantee {
        AT_MOST_ONCE,
        AT_LEAST_ONCE,
        EXACTLY_ONCE
    }

    enum MessageStatus {
        PENDING,
        IN_FLIGHT,
        ACKNOWLEDGED,
        DEAD_LETTERED
    }

    enum ProcessingStatus {
        SUCCESS,
        DUPLICATE,
        FAILURE
    }

    static class MessagingException extends RuntimeException {
        MessagingException(String message) {
            super(message);
        }
    }

    static class ValidationException extends MessagingException {
        ValidationException(String message) {
            super(message);
        }
    }


    record Message(
        UUID id,
        String topic,
        String key,
        Map<String, String> payload,
        Instant timestamp
    ) {
        Message {
            Objects.requireNonNull(id);
            Objects.requireNonNull(timestamp);

            if (topic == null || topic.isBlank()) {
                throw new ValidationException("Topic is required");
            }

            if (key == null || key.isBlank()) {
                throw new ValidationException("Message key is required");
            }

            Objects.requireNonNull(payload);

            if (payload.size() > 100) {
                throw new ValidationException("Too many payload fields");
            }

            payload = Collections.unmodifiableMap(
                new HashMap<>(payload)
            );
        }

        static Message create(
            String topic,
            String key,
            Map<String, String> payload
        ) {
            return new Message(
                UUID.randomUUID(),
                topic,
                key,
                payload,
                Instant.now()
            );
        }
    }


    static final class Delivery {

        private final Message message;

        private int attempts;

        private MessageStatus status;

        private String lastError;

        Delivery(Message message) {
            this.message = Objects.requireNonNull(message);
            this.status = MessageStatus.PENDING;
        }

        Message message() {
            return message;
        }

        int attempts() {
            return attempts;
        }

        MessageStatus status() {
            return status;
        }

        void begin() {
            attempts++;
            status = MessageStatus.IN_FLIGHT;
        }

        void acknowledge() {
            status = MessageStatus.ACKNOWLEDGED;
        }

        void retry(String error) {
            status = MessageStatus.PENDING;
            lastError = error;
        }

        void deadLetter(String error) {
            status = MessageStatus.DEAD_LETTERED;
            lastError = error;
        }
    }


    record QueuePolicy(
        int maxRetries,
        int maxCapacity
    ) {
        QueuePolicy {
            if (maxRetries < 0 || maxCapacity < 1) {
                throw new ValidationException("Invalid queue policy");
            }
        }
    }


    static final class MessageQueue {

        private final String name;

        private final QueuePolicy policy;

        private final ArrayDeque<Delivery> pending =
            new ArrayDeque<>();

        private final Map<UUID, Delivery> inFlight =
            new HashMap<>();

        private final List<Delivery> deadLetters =
            new ArrayList<>();

        private long published;
        private long acknowledged;
        private long retried;

        MessageQueue(String name, QueuePolicy policy) {
            if (name == null || name.isBlank()) {
                throw new ValidationException("Queue name required");
            }

            this.name = name;
            this.policy = policy;
        }

        synchronized void publish(Message message) {
            Objects.requireNonNull(message);

            if (pending.size() + inFlight.size() >=
                policy.maxCapacity()) {
                throw new MessagingException("Queue capacity exceeded");
            }

            pending.addLast(new Delivery(message));
            published++;
        }

        synchronized Delivery receive() {
            Delivery delivery = pending.pollFirst();

            if (delivery == null) {
                return null;
            }

            delivery.begin();

            if (inFlight.containsKey(delivery.message().id())) {
                throw new MessagingException(
                    "Duplicate in-flight message"
                );
            }

            inFlight.put(delivery.message().id(), delivery);

            return delivery;
        }

        synchronized void acknowledge(UUID id) {
            Delivery delivery = inFlight.remove(id);

            if (delivery == null) {
                throw new MessagingException(
                    "Message is not in flight"
                );
            }

            delivery.acknowledge();
            acknowledged++;
        }

        synchronized void reject(UUID id, String error) {
            Delivery delivery = inFlight.remove(id);

            if (delivery == null) {
                throw new MessagingException("Unknown delivery");
            }

            if (delivery.attempts() <= policy.maxRetries()) {
                delivery.retry(error);
                pending.addLast(delivery);
                retried++;
            } else {
                delivery.deadLetter(error);
                deadLetters.add(delivery);
            }
        }

        synchronized int recoverInFlight() {
            int count = inFlight.size();

            List<Delivery> abandoned =
                new ArrayList<>(inFlight.values());

            inFlight.clear();

            for (int i = abandoned.size() - 1; i >= 0; i--) {
                Delivery delivery = abandoned.get(i);
                delivery.retry("Consumer recovery");
                pending.addFirst(delivery);
            }

            return count;
        }

        synchronized Map<String, Long> metrics() {
            Map<String, Long> result = new HashMap<>();

            result.put("published", published);
            result.put("acknowledged", acknowledged);
            result.put("retried", retried);
            result.put("pending", (long) pending.size());
            result.put("inFlight", (long) inFlight.size());
            result.put("deadLetters", (long) deadLetters.size());

            return Collections.unmodifiableMap(result);
        }

        synchronized List<Delivery> deadLetters() {
            return List.copyOf(deadLetters);
        }
    }


    record StreamPosition(
        int partition,
        long offset
    ) {}


    record StreamRecord(
        long offset,
        Message message
    ) {}


    static final class ConsumerGroup {

        private final String name;

        private final long[] committedOffsets;

        ConsumerGroup(String name, int partitions) {
            this.name = name;
            this.committedOffsets = new long[partitions];
        }

        synchronized long offset(int partition) {
            return committedOffsets[partition];
        }

        synchronized void commit(
            int partition,
            long nextOffset,
            long maximum
        ) {
            long current = committedOffsets[partition];

            if (
                nextOffset < current ||
                nextOffset > maximum
            ) {
                throw new MessagingException(
                    "Invalid offset transition"
                );
            }

            committedOffsets[partition] = nextOffset;
        }

        synchronized void seek(int partition, long offset, long maximum) {
            if (offset < 0 || offset > maximum) {
                throw new MessagingException("Invalid replay offset");
            }

            committedOffsets[partition] = offset;
        }

        synchronized List<Long> offsets() {
            List<Long> result = new ArrayList<>();

            for (long offset : committedOffsets) {
                result.add(offset);
            }

            return List.copyOf(result);
        }
    }


    static final class EventStream {

        private final String name;

        private final List<List<StreamRecord>> partitions =
            new ArrayList<>();

        private final Map<String, ConsumerGroup> groups =
            new HashMap<>();

        EventStream(String name, int partitionCount) {
            if (
                name == null ||
                name.isBlank() ||
                partitionCount < 1
            ) {
                throw new ValidationException(
                    "Invalid stream configuration"
                );
            }

            this.name = name;

            for (int i = 0; i < partitionCount; i++) {
                partitions.add(new ArrayList<>());
            }
        }

        private int partitionFor(String key) {
            return Math.floorMod(
                key.hashCode(),
                partitions.size()
            );
        }

        synchronized StreamPosition append(Message message) {
            int partitionId = partitionFor(message.key());

            List<StreamRecord> partition =
                partitions.get(partitionId);

            long offset = partition.size();

            partition.add(new StreamRecord(offset, message));

            return new StreamPosition(partitionId, offset);
        }

        synchronized void registerGroup(String groupName) {
            if (groupName == null || groupName.isBlank()) {
                throw new ValidationException("Group name required");
            }

            groups.computeIfAbsent(
                groupName,
                name -> new ConsumerGroup(name, partitions.size())
            );
        }

        synchronized List<StreamRecord> poll(
            String groupName,
            int partition,
            int batchSize
        ) {
            ConsumerGroup group = groups.get(groupName);

            if (group == null) {
                throw new MessagingException("Unknown consumer group");
            }

            if (
                partition < 0 ||
                partition >= partitions.size() ||
                batchSize < 1
            ) {
                throw new ValidationException("Invalid poll request");
            }

            List<StreamRecord> records =
                partitions.get(partition);

            int start = Math.toIntExact(group.offset(partition));

            int end = Math.min(
                start + batchSize,
                records.size()
            );

            return List.copyOf(records.subList(start, end));
        }

        synchronized void commit(
            String groupName,
            int partition,
            long nextOffset
        ) {
            ConsumerGroup group = groups.get(groupName);

            if (group == null) {
                throw new MessagingException("Unknown group");
            }

            group.commit(
                partition,
                nextOffset,
                partitions.get(partition).size()
            );
        }

        synchronized void replay(
            String groupName,
            int partition,
            long offset
        ) {
            ConsumerGroup group = groups.get(groupName);

            if (group == null) {
                throw new MessagingException("Unknown group");
            }

            group.seek(
                partition,
                offset,
                partitions.get(partition).size()
            );
        }

        synchronized List<Long> offsets(String groupName) {
            ConsumerGroup group = groups.get(groupName);

            if (group == null) {
                throw new MessagingException("Unknown group");
            }

            return group.offsets();
        }
    }


    static final class IdempotencyService {

        private final Set<UUID> processed = new HashSet<>();

        private final Map<String, Long> accountBalances =
            new HashMap<>();

        synchronized ProcessingStatus processPayment(
            Message message
        ) {
            if (processed.contains(message.id())) {
                return ProcessingStatus.DUPLICATE;
            }

            String account = message.payload().get("account");
            String amountText = message.payload().get("amount");

            if (account == null || account.isBlank()) {
                throw new ValidationException("Invalid account");
            }

            long amount;

            try {
                amount = Long.parseLong(amountText);
            } catch (RuntimeException exception) {
                throw new ValidationException("Invalid amount");
            }

            if (amount <= 0) {
                throw new ValidationException(
                    "Amount must be positive"
                );
            }

            // The balance update and idempotency record share one
            // synchronized transaction boundary in this demonstration.
            accountBalances.merge(
                account,
                amount,
                Math::addExact
            );

            processed.add(message.id());

            return ProcessingStatus.SUCCESS;
        }

        synchronized long balance(String account) {
            return accountBalances.getOrDefault(account, 0L);
        }
    }


    static final class ConsumerService {

        private final String consumerName;

        private final MessageQueue queue;

        private final Consumer<Message> handler;

        private final DeliveryGuarantee guarantee;

        private final AtomicBoolean running =
            new AtomicBoolean(false);

        ConsumerService(
            String consumerName,
            MessageQueue queue,
            Consumer<Message> handler,
            DeliveryGuarantee guarantee
        ) {
            this.consumerName = consumerName;
            this.queue = queue;
            this.handler = handler;
            this.guarantee = guarantee;
        }

        boolean processOne() {
            Delivery delivery = queue.receive();

            if (delivery == null) {
                return false;
            }

            UUID id = delivery.message().id();

            try {
                if (guarantee == DeliveryGuarantee.AT_MOST_ONCE) {
                    queue.acknowledge(id);
                    handler.accept(delivery.message());

                } else if (
                    guarantee == DeliveryGuarantee.AT_LEAST_ONCE ||
                    guarantee == DeliveryGuarantee.EXACTLY_ONCE
                ) {
                    handler.accept(delivery.message());
                    queue.acknowledge(id);
                }

                return true;

            } catch (RuntimeException exception) {
                queue.reject(id, exception.getMessage());
                throw exception;
            }
        }

        void start(int maximumMessages) {
            if (!running.compareAndSet(false, true)) {
                throw new MessagingException("Consumer already running");
            }

            try {
                for (
                    int i = 0;
                    i < maximumMessages && running.get();
                    i++
                ) {
                    if (!processOne()) {
                        break;
                    }
                }
            } finally {
                running.set(false);
            }
        }

        void stop() {
            running.set(false);
        }
    }


    static Message paymentMessage(String account, long amount) {
        return Message.create(
            "payments",
            account,
            Map.of(
                "account", account,
                "amount", Long.toString(amount)
            )
        );
    }


    static void queueDemonstration() {
        System.out.println("\n=== ENTERPRISE PAYMENT QUEUE ===");

        MessageQueue queue = new MessageQueue(
            "payment-queue",
            new QueuePolicy(3, 1000)
        );

        IdempotencyService idempotency =
            new IdempotencyService();

        Message payment = paymentMessage("ACC-100", 2500);

        queue.publish(payment);

        ConsumerService consumer = new ConsumerService(
            "payment-worker-1",
            queue,
            message -> idempotency.processPayment(message),
            DeliveryGuarantee.AT_LEAST_ONCE
        );

        consumer.processOne();

        ProcessingStatus duplicate =
            idempotency.processPayment(payment);

        System.out.println("Duplicate processing: " + duplicate);
        System.out.println(
            "Account balance: " + idempotency.balance("ACC-100")
        );

        System.out.println("Metrics: " + queue.metrics());
    }


    static void streamDemonstration() {
        System.out.println("\n=== EVENT STREAM ===");

        EventStream stream = new EventStream("orders", 3);

        stream.registerGroup("analytics");
        stream.registerGroup("billing");

        for (int i = 1; i <= 8; i++) {
            Message event = Message.create(
                "orders",
                "customer-" + (i % 2),
                Map.of(
                    "orderId", Integer.toString(i),
                    "amount", Integer.toString(i * 100)
                )
            );

            StreamPosition position = stream.append(event);

            System.out.printf(
                "Order %d -> partition %d, offset %d%n",
                i,
                position.partition(),
                position.offset()
            );
        }

        for (int partition = 0; partition < 3; partition++) {
            List<StreamRecord> records = stream.poll(
                "analytics",
                partition,
                100
            );

            for (StreamRecord record : records) {
                System.out.println(
                    "Analytics consumed: " +
                    record.message().payload().get("orderId")
                );
            }

            long nextOffset =
                stream.offsets("analytics").get(partition)
                + records.size();

            stream.commit(partition == -1 ? "" : "analytics",
                partition,
                nextOffset);
        }

        System.out.println(
            "Analytics offsets: " + stream.offsets("analytics")
        );

        System.out.println(
            "Billing offsets: " + stream.offsets("billing")
        );
    }


    static void retryDemonstration() {
        System.out.println("\n=== RETRY AND DEAD-LETTER PROCESSING ===");

        MessageQueue queue = new MessageQueue(
            "email-queue",
            new QueuePolicy(2, 100)
        );

        queue.publish(
            Message.create(
                "email",
                "customer-100",
                Map.of("recipient", "customer@example.com")
            )
        );

        for (int i = 0; i < 4; i++) {
            Delivery delivery = queue.receive();

            if (delivery == null) {
                break;
            }

            System.out.println(
                "Attempt " + delivery.attempts()
            );

            queue.reject(
                delivery.message().id(),
                "Simulated SMTP failure"
            );
        }

        System.out.println("Metrics: " + queue.metrics());
    }


    public static void main(String[] args) {
        try {
            queueDemonstration();
            streamDemonstration();
            retryDemonstration();

            System.out.println(
                "\nDistributed messaging execution completed."
            );

        } catch (RuntimeException exception) {
            System.err.println(
                "Messaging failure: " + exception.getMessage()
            );

            System.exit(1);
        }
    }
}
