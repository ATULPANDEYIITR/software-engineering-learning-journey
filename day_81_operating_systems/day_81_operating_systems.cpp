#include <algorithm>
#include <deque>
#include <exception>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <numeric>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;

/*
 * Operating Systems: C++17 Repository-Independent Kernel Model.
 *
 * Implements:
 * 1. Process lifecycle management.
 * 2. Multithreaded process domain modeling.
 * 3. Round-robin CPU scheduling.
 * 4. Priority-based scheduling.
 * 5. Memory allocation and fragmentation.
 * 6. Virtual memory with LRU replacement.
 * 7. Filesystem permissions and operations.
 * 8. Mergeable free memory regions.
 *
 * Compile:
 * g++ -std=c++17 -O2 -Wall -Wextra -pedantic operating_systems.cpp -o os_sim
 *
 * Run:
 * ./os_sim
 */

enum class ProcessState {
    New,
    Ready,
    Running,
    Blocked,
    Terminated
};

enum class ThreadState {
    Ready,
    Running,
    Blocked,
    Terminated
};

enum class FileAccess {
    Read,
    Write,
    Execute
};

string toString(ProcessState state) {
    switch (state) {
        case ProcessState::New: return "NEW";
        case ProcessState::Ready: return "READY";
        case ProcessState::Running: return "RUNNING";
        case ProcessState::Blocked: return "BLOCKED";
        case ProcessState::Terminated: return "TERMINATED";
    }

    return "UNKNOWN";
}

struct Thread {
    int id;
    string name;
    int burstTime;
    int remainingTime;
    int priority;
    int cpuTime = 0;
    ThreadState state = ThreadState::Ready;
};

struct Process {
    int id;
    string name;
    size_t memory;
    ProcessState state = ProcessState::Ready;
    vector<Thread> threads;
};

class ProcessManager {
private:
    int nextPid = 1;
    int nextTid = 1;
    size_t memoryCapacity;
    size_t allocatedMemory = 0;

    unordered_map<int, Process> processes;

public:
    explicit ProcessManager(size_t capacity)
        : memoryCapacity(capacity) {
        if (capacity == 0) {
            throw invalid_argument("Memory capacity must be positive");
        }
    }

    Process& createProcess(
        const string& name,
        size_t memory
    ) {
        if (name.empty()) {
            throw invalid_argument("Process name cannot be empty");
        }

        if (memory == 0) {
            throw invalid_argument("Memory requirement must be positive");
        }

        if (memory > memoryCapacity - allocatedMemory) {
            throw runtime_error("Insufficient physical memory");
        }

        Process process{
            nextPid++,
            name,
            memory,
            ProcessState::Ready,
            {}
        };

        auto result = processes.emplace(process.id, move(process));

        allocatedMemory += memory;

        return result.first->second;
    }

    Thread& createThread(
        int pid,
        const string& name,
        int burstTime,
        int priority = 5
    ) {
        auto it = processes.find(pid);

        if (it == processes.end()) {
            throw out_of_range("Process does not exist");
        }

        if (it->second.state == ProcessState::Terminated) {
            throw logic_error("Process has terminated");
        }

        if (name.empty() || burstTime <= 0 || priority < 0) {
            throw invalid_argument("Invalid thread configuration");
        }

        it->second.threads.push_back({
            nextTid++,
            name,
            burstTime,
            burstTime,
            priority,
            0,
            ThreadState::Ready
        });

        return it->second.threads.back();
    }

    Process& getProcess(int pid) {
        auto it = processes.find(pid);

        if (it == processes.end()) {
            throw out_of_range("Unknown process ID");
        }

        return it->second;
    }

    void terminateProcess(int pid) {
        Process& process = getProcess(pid);

        if (process.state == ProcessState::Terminated) {
            throw logic_error("Process already terminated");
        }

        process.state = ProcessState::Terminated;

        for (Thread& thread : process.threads) {
            thread.state = ThreadState::Terminated;
        }

        allocatedMemory -= process.memory;
        process.memory = 0;
    }

    vector<Process>& allProcesses() {
        static vector<Process> snapshot;

        snapshot.clear();

        for (auto& entry : processes) {
            snapshot.push_back(entry.second);
        }

        return snapshot;
    }

    size_t availableMemory() const {
        return memoryCapacity - allocatedMemory;
    }

    void report() const {
        cout << "\nPROCESS TABLE\n";
        cout << string(75, '-') << '\n';

        for (const auto& entry : processes) {
            const Process& p = entry.second;

            cout << "PID=" << p.id
                 << " Name=" << p.name
                 << " State=" << toString(p.state)
                 << " Memory=" << p.memory << " MB"
                 << " Threads=" << p.threads.size()
                 << '\n';
        }

        cout << "Available memory: "
             << availableMemory() << " MB\n";
    }
};

class Scheduler {
private:
    int quantum;
    int clock = 0;

    struct Task {
        int pid;
        int tid;
    };

    deque<Task> readyQueue;

public:
    explicit Scheduler(int timeQuantum)
        : quantum(timeQuantum) {
        if (quantum <= 0) {
            throw invalid_argument("Quantum must be positive");
        }
    }

    void addProcess(Process& process) {
        for (const Thread& thread : process.threads) {
            if (thread.state == ThreadState::Ready) {
                readyQueue.push_back({
                    process.id,
                    thread.id
                });
            }
        }
    }

    void roundRobin(ProcessManager& manager) {
        cout << "\nROUND-ROBIN SCHEDULER\n";

        while (!readyQueue.empty()) {
            Task task = readyQueue.front();
            readyQueue.pop_front();

            Process& process = manager.getProcess(task.pid);

            if (process.state == ProcessState::Terminated) {
                continue;
            }

            auto it = find_if(
                process.threads.begin(),
                process.threads.end(),
                [&](const Thread& thread) {
                    return thread.id == task.tid;
                }
            );

            if (it == process.threads.end() ||
                it->state == ThreadState::Terminated) {
                continue;
            }

            Thread& thread = *it;

            thread.state = ThreadState::Running;
            process.state = ProcessState::Running;

            int execution = min(quantum, thread.remainingTime);

            int start = clock;
            clock += execution;

            thread.remainingTime -= execution;
            thread.cpuTime += execution;

            cout << "PID=" << process.id
                 << " TID=" << thread.id
                 << " " << thread.name
                 << " [" << start << "-" << clock << "]"
                 << '\n';

            if (thread.remainingTime == 0) {
                thread.state = ThreadState::Terminated;
            } else {
                thread.state = ThreadState::Ready;
                readyQueue.push_back(task);
            }

            bool active = any_of(
                process.threads.begin(),
                process.threads.end(),
                [](const Thread& t) {
                    return t.state != ThreadState::Terminated;
                }
            );

            if (!active) {
                process.state = ProcessState::Ready;
            }
        }

        cout << "Total CPU time: " << clock << '\n';
    }
};

struct MemoryBlock {
    size_t start;
    size_t size;
    optional<int> pid;
};

class MemoryAllocator {
private:
    size_t capacity;
    vector<MemoryBlock> blocks;

public:
    explicit MemoryAllocator(size_t total)
        : capacity(total) {
        if (total == 0) {
            throw invalid_argument("Memory capacity must be positive");
        }

        blocks.push_back({0, total, nullopt});
    }

    size_t allocate(int pid, size_t size) {
        if (size == 0) {
            throw invalid_argument("Allocation size must be positive");
        }

        for (const auto& block : blocks) {
            if (block.pid && *block.pid == pid) {
                throw logic_error("Process already allocated");
            }
        }

        auto it = find_if(
            blocks.begin(),
            blocks.end(),
            [&](const MemoryBlock& block) {
                return !block.pid && block.size >= size;
            }
        );

        if (it == blocks.end()) {
            throw runtime_error(
                "No contiguous memory block is sufficiently large"
            );
        }

        size_t address = it->start;
        size_t remainder = it->size - size;

        it->size = size;
        it->pid = pid;

        if (remainder > 0) {
            auto position = next(it);

            blocks.insert(
                position,
                {
                    address + size,
                    remainder,
                    nullopt
                }
            );
        }

        return address;
    }

    void release(int pid) {
        auto it = find_if(
            blocks.begin(),
            blocks.end(),
            [&](const MemoryBlock& block) {
                return block.pid && *block.pid == pid;
            }
        );

        if (it == blocks.end()) {
            throw out_of_range("Allocation not found");
        }

        it->pid.reset();

        // Merge adjacent free blocks to reduce external fragmentation.
        vector<MemoryBlock> merged;

        for (const auto& block : blocks) {
            if (!merged.empty() &&
                !merged.back().pid &&
                !block.pid) {
                merged.back().size += block.size;
            } else {
                merged.push_back(block);
            }
        }

        blocks = move(merged);
    }

    void report() const {
        cout << "\nPHYSICAL MEMORY MAP\n";

        for (const auto& block : blocks) {
            cout << "Address=" << block.start
                 << " Size=" << block.size
                 << " Owner=";

            if (block.pid) {
                cout << *block.pid;
            } else {
                cout << "FREE";
            }

            cout << '\n';
        }
    }
};

class VirtualMemory {
private:
    struct Frame {
        int page = -1;
        unsigned long long lastUsed = 0;
    };

    vector<Frame> frames;
    unordered_map<int, size_t> pageTable;

    unsigned long long clock = 0;
    size_t hits = 0;
    size_t faults = 0;

public:
    explicit VirtualMemory(size_t frameCount)
        : frames(frameCount) {
        if (frameCount == 0) {
            throw invalid_argument("Frame count must be positive");
        }
    }

    void access(int page) {
        if (page < 0) {
            throw invalid_argument("Negative page number");
        }

        ++clock;

        auto found = pageTable.find(page);

        if (found != pageTable.end()) {
            frames[found->second].lastUsed = clock;
            ++hits;

            cout << "HIT page=" << page << '\n';
            return;
        }

        ++faults;

        auto freeFrame = find_if(
            frames.begin(),
            frames.end(),
            [](const Frame& frame) {
                return frame.page == -1;
            }
        );

        size_t index;

        if (freeFrame != frames.end()) {
            index = distance(frames.begin(), freeFrame);
        } else {
            index = distance(
                frames.begin(),
                min_element(
                    frames.begin(),
                    frames.end(),
                    [](const Frame& a, const Frame& b) {
                        return a.lastUsed < b.lastUsed;
                    }
                )
            );

            pageTable.erase(frames[index].page);
        }

        frames[index] = {page, clock};
        pageTable[page] = index;

        cout << "FAULT page=" << page
             << " frame=" << index << '\n';
    }

    void report() const {
        size_t total = hits + faults;

        cout << "\nVIRTUAL MEMORY STATISTICS\n";
        cout << "Hits: " << hits << '\n';
        cout << "Faults: " << faults << '\n';

        cout << "Hit ratio: "
             << fixed << setprecision(2)
             << (total ? 100.0 * hits / total : 0.0)
             << "%\n";
    }
};

struct VirtualFile {
    string owner;
    string content;
    map<string, set<FileAccess>> permissions;
};

class FileSystem {
private:
    map<string, VirtualFile> files;

    static bool validPath(const string& path) {
        if (path.empty() || path.front() != '/') {
            return false;
        }

        if (path.find('\0') != string::npos) {
            return false;
        }

        size_t position = 0;

        while (position < path.size()) {
            size_t end = path.find('/', position + 1);

            if (end == string::npos) {
                end = path.size();
            }

            if (path.substr(position + 1, end - position - 1) == "..") {
                return false;
            }

            position = end;
        }

        return path != "/";
    }

    VirtualFile& authorize(
        const string& path,
        const string& user,
        FileAccess action
    ) {
        if (!validPath(path)) {
            throw invalid_argument("Invalid filesystem path");
        }

        auto it = files.find(path);

        if (it == files.end()) {
            throw out_of_range("File does not exist");
        }

        auto permission = it->second.permissions.find(user);

        if (permission == it->second.permissions.end() ||
            !permission->second.count(action)) {
            throw runtime_error("File access denied");
        }

        return it->second;
    }

public:
    void create(
        const string& path,
        const string& owner,
        const string& content
    ) {
        if (!validPath(path) || owner.empty()) {
            throw invalid_argument("Invalid file metadata");
        }

        if (files.count(path)) {
            throw runtime_error("File already exists");
        }

        VirtualFile file;
        file.owner = owner;
        file.content = content;

        file.permissions[owner] = {
            FileAccess::Read,
            FileAccess::Write,
            FileAccess::Execute
        };

        files.emplace(path, move(file));
    }

    string read(
        const string& path,
        const string& user
    ) {
        return authorize(
            path,
            user,
            FileAccess::Read
        ).content;
    }

    void write(
        const string& path,
        const string& user,
        const string& content
    ) {
        authorize(
            path,
            user,
            FileAccess::Write
        ).content = content;
    }

    void grant(
        const string& path,
        const string& owner,
        const string& user,
        FileAccess action
    ) {
        auto it = files.find(path);

        if (it == files.end()) {
            throw out_of_range("File does not exist");
        }

        if (it->second.owner != owner) {
            throw runtime_error("Only the owner can grant permissions");
        }

        it->second.permissions[user].insert(action);
    }

    void remove(
        const string& path,
        const string& user
    ) {
        authorize(path, user, FileAccess::Execute);
        files.erase(path);
    }

    void report() const {
        cout << "\nFILESYSTEM REPORT\n";

        for (const auto& entry : files) {
            cout << entry.first
                 << " Owner=" << entry.second.owner
                 << " Bytes=" << entry.second.content.size()
                 << '\n';
        }
    }
};

int main() {
    try {
        cout << "OPERATING SYSTEM SIMULATOR\n";
        cout << string(70, '=') << '\n';

        // Process and thread management.
        ProcessManager manager(2048);

        Process& web = manager.createProcess("WebServer", 512);
        Process& database = manager.createProcess("Database", 768);

        manager.createThread(web.id, "HTTP-Worker", 8, 2);
        manager.createThread(web.id, "Logger", 4, 4);
        manager.createThread(database.id, "Query-Worker", 6, 1);
        manager.createThread(database.id, "Cache-Worker", 3, 3);

        manager.report();

        // Scheduling.
        Scheduler scheduler(3);

        scheduler.addProcess(web);
        scheduler.addProcess(database);

        scheduler.roundRobin(manager);

        // Contiguous memory allocation.
        MemoryAllocator allocator(1024);

        cout << "\nMEMORY ALLOCATION\n";

        allocator.allocate(101, 256);
        allocator.allocate(102, 384);
        allocator.allocate(103, 128);

        allocator.report();

        allocator.release(102);

        cout << "\nAFTER DEALLOCATION\n";
        allocator.report();

        // Virtual memory.
        VirtualMemory memory(3);

        cout << "\nVIRTUAL MEMORY PAGE ACCESS\n";

        for (int page : {1, 2, 3, 1, 4, 2, 5}) {
            memory.access(page);
        }

        memory.report();

        // Filesystem.
        FileSystem filesystem;

        cout << "\nFILESYSTEM OPERATIONS\n";

        filesystem.create(
            "/var/log/system.log",
            "admin",
            "Kernel initialized"
        );

        filesystem.grant(
            "/var/log/system.log",
            "admin",
            "auditor",
            FileAccess::Read
        );

        cout << "Auditor reads: "
             << filesystem.read(
                 "/var/log/system.log",
                 "auditor"
             ) << '\n';

        try {
            filesystem.write(
                "/var/log/system.log",
                "auditor",
                "Unauthorized update"
            );
        } catch (const exception& error) {
            cout << "ACCESS CONTROL: "
                 << error.what() << '\n';
        }

        filesystem.report();

        // Termination and resource release.
        manager.terminateProcess(web.id);
        manager.terminateProcess(database.id);

        manager.report();

        cout << "\nAvailable memory: "
             << manager.availableMemory() << " MB\n";

        cout << "\nSIMULATION COMPLETED\n";
    } catch (const exception& error) {
        cerr << "SIMULATION ERROR: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
