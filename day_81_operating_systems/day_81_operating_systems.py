#!/usr/bin/env python3
"""
Operating Systems: Processes, Threads, Memory Management, and Filesystems.

A self-contained operating-system simulator demonstrating:
- Process creation and lifecycle management.
- Thread creation and scheduling.
- Round-robin CPU scheduling.
- Thread synchronization using locks.
- Virtual memory and page replacement using LRU.
- File creation, reading, writing, permissions, and deletion.
- Resource accounting, validation, and failure handling.

Run: python operating_systems.py
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from threading import Lock
from typing import Optional
import time


class OSErrorBase(Exception):
    """Base exception for simulated operating-system failures."""


class ResourceError(OSErrorBase):
    pass


class InvalidStateError(OSErrorBase):
    pass


class PermissionDeniedError(OSErrorBase):
    pass


class ProcessState(Enum):
    NEW = "new"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


class ThreadState(Enum):
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


@dataclass
class Thread:
    thread_id: int
    name: str
    burst_time: int
    remaining_time: int
    state: ThreadState = ThreadState.READY
    cpu_time: int = 0

    def __post_init__(self):
        if self.burst_time <= 0:
            raise ValueError("Thread burst time must be positive")


@dataclass
class Process:
    process_id: int
    name: str
    memory_required: int
    state: ProcessState = ProcessState.NEW
    threads: dict[int, Thread] = field(default_factory=dict)
    allocated_memory: int = 0
    exit_code: Optional[int] = None


class ProcessManager:
    """Manages process creation, state transitions, and resource accounting."""

    def __init__(self, memory_limit: int):
        if memory_limit <= 0:
            raise ValueError("Memory limit must be positive")

        self.memory_limit = memory_limit
        self.allocated_memory = 0
        self.processes: dict[int, Process] = {}
        self.next_process_id = 1
        self.next_thread_id = 1

    def create_process(self, name: str, memory_required: int) -> Process:
        if not name.strip():
            raise ValueError("Process name cannot be empty")

        if memory_required <= 0:
            raise ValueError("Memory requirement must be positive")

        if self.allocated_memory + memory_required > self.memory_limit:
            raise ResourceError("Insufficient physical memory")

        process = Process(
            process_id=self.next_process_id,
            name=name,
            memory_required=memory_required,
            state=ProcessState.READY,
            allocated_memory=memory_required,
        )

        self.next_process_id += 1
        self.allocated_memory += memory_required
        self.processes[process.process_id] = process

        return process

    def create_thread(
        self,
        process_id: int,
        name: str,
        burst_time: int
    ) -> Thread:
        process = self.get_process(process_id)

        if process.state == ProcessState.TERMINATED:
            raise InvalidStateError("Cannot add a thread to a terminated process")

        thread = Thread(
            thread_id=self.next_thread_id,
            name=name,
            burst_time=burst_time,
            remaining_time=burst_time,
        )

        self.next_thread_id += 1
        process.threads[thread.thread_id] = thread

        return thread

    def get_process(self, process_id: int) -> Process:
        try:
            return self.processes[process_id]
        except KeyError:
            raise ValueError(f"Unknown process ID: {process_id}")

    def terminate_process(self, process_id: int, exit_code: int = 0):
        process = self.get_process(process_id)

        if process.state == ProcessState.TERMINATED:
            raise InvalidStateError("Process is already terminated")

        process.state = ProcessState.TERMINATED
        process.exit_code = exit_code

        for thread in process.threads.values():
            thread.state = ThreadState.TERMINATED

        self.allocated_memory -= process.allocated_memory
        process.allocated_memory = 0

    def report(self):
        print("\nPROCESS TABLE")
        print("-" * 76)

        for process in self.processes.values():
            print(
                f"PID={process.process_id:<3} "
                f"Name={process.name:<18} "
                f"State={process.state.value:<12} "
                f"Memory={process.allocated_memory} MB "
                f"Threads={len(process.threads)}"
            )


class RoundRobinScheduler:
    """Preemptive round-robin scheduler operating on process threads."""

    def __init__(self, quantum: int):
        if quantum <= 0:
            raise ValueError("Time quantum must be positive")

        self.quantum = quantum
        self.ready_queue = deque()
        self.completed = []
        self.clock = 0

    def add_thread(self, process_id: int, thread: Thread):
        if thread.state != ThreadState.READY:
            raise InvalidStateError("Only ready threads can enter the queue")

        self.ready_queue.append((process_id, thread))

    def run(self):
        print("\nROUND-ROBIN SCHEDULING")
        print("-" * 76)

        while self.ready_queue:
            process_id, thread = self.ready_queue.popleft()

            if thread.state == ThreadState.TERMINATED:
                continue

            thread.state = ThreadState.RUNNING

            execution_time = min(
                self.quantum,
                thread.remaining_time
            )

            start = self.clock
            self.clock += execution_time

            thread.remaining_time -= execution_time
            thread.cpu_time += execution_time

            print(
                f"PID {process_id} | TID {thread.thread_id} | "
                f"{thread.name} | "
                f"{start}-{self.clock} | "
                f"Executed {execution_time}"
            )

            if thread.remaining_time == 0:
                thread.state = ThreadState.TERMINATED
                self.completed.append(thread)
            else:
                thread.state = ThreadState.READY
                self.ready_queue.append((process_id, thread))

        print(f"Total simulated CPU time: {self.clock}")


class ThreadSafeCounter:
    """Demonstrates mutual exclusion through a lock."""

    def __init__(self):
        self.value = 0
        self.lock = Lock()

    def increment(self, repetitions: int):
        if repetitions < 0:
            raise ValueError("Repetitions cannot be negative")

        for _ in range(repetitions):
            with self.lock:
                self.value += 1


@dataclass
class PageFrame:
    frame_number: int
    page_number: Optional[int] = None
    last_used: int = 0


class VirtualMemory:
    """
    Simulates virtual pages mapped to physical frames.

    LRU replaces the least recently used resident page.
    This is a simplified simulator, not a hardware MMU.
    """

    def __init__(self, frame_count: int):
        if frame_count <= 0:
            raise ValueError("Frame count must be positive")

        self.frames = [
            PageFrame(i) for i in range(frame_count)
        ]
        self.page_table: dict[int, int] = {}
        self.access_counter = 0
        self.page_faults = 0
        self.hits = 0

    def access(self, page_number: int) -> str:
        if page_number < 0:
            raise ValueError("Page number cannot be negative")

        self.access_counter += 1

        if page_number in self.page_table:
            frame_index = self.page_table[page_number]
            self.frames[frame_index].last_used = self.access_counter
            self.hits += 1
            return f"PAGE HIT: {page_number} in frame {frame_index}"

        self.page_faults += 1

        free_frame = next(
            (f for f in self.frames if f.page_number is None),
            None
        )

        if free_frame is not None:
            selected = free_frame
        else:
            selected = min(
                self.frames,
                key=lambda frame: frame.last_used
            )

            old_page = selected.page_number
            del self.page_table[old_page]

        selected.page_number = page_number
        selected.last_used = self.access_counter
        self.page_table[page_number] = selected.frame_number

        return (
            f"PAGE FAULT: {page_number} loaded "
            f"into frame {selected.frame_number}"
        )

    def report(self):
        total = self.hits + self.page_faults
        hit_ratio = self.hits / total if total else 0

        print("\nVIRTUAL MEMORY REPORT")
        print("-" * 50)

        for frame in self.frames:
            print(
                f"Frame {frame.frame_number}: "
                f"Page {frame.page_number}"
            )

        print(f"Page hits: {self.hits}")
        print(f"Page faults: {self.page_faults}")
        print(f"Hit ratio: {hit_ratio:.2%}")


class FilePermission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"


@dataclass
class VirtualFile:
    path: str
    owner: str
    content: str
    permissions: dict[str, set[FilePermission]]


class VirtualFileSystem:
    """
    In-memory hierarchical-path file model.

    It demonstrates ownership and permission checks.
    It does not implement an actual disk filesystem.
    """

    def __init__(self):
        self.files: dict[str, VirtualFile] = {}

    @staticmethod
    def validate_path(path: str) -> str:
        parsed = PurePosixPath(path)

        if not parsed.is_absolute():
            raise ValueError("File paths must be absolute")

        if ".." in parsed.parts:
            raise ValueError("Parent-directory traversal is prohibited")

        if str(parsed) == "/":
            raise ValueError("Root directory is not a file")

        if "\x00" in path:
            raise ValueError("Null bytes are prohibited")

        return str(parsed)

    def create_file(
        self,
        path: str,
        owner: str,
        content: str,
        permissions: Optional[dict[str, set[FilePermission]]] = None,
    ):
        path = self.validate_path(path)

        if path in self.files:
            raise FileExistsError(path)

        if not owner.strip():
            raise ValueError("Owner cannot be empty")

        if permissions is None:
            permissions = {
                owner: {
                    FilePermission.READ,
                    FilePermission.WRITE,
                    FilePermission.DELETE,
                }
            }

        self.files[path] = VirtualFile(
            path=path,
            owner=owner,
            content=content,
            permissions=permissions,
        )

    def check_permission(
        self,
        path: str,
        user: str,
        permission: FilePermission
    ):
        path = self.validate_path(path)

        if path not in self.files:
            raise FileNotFoundError(path)

        file = self.files[path]
        allowed = file.permissions.get(user, set())

        if permission not in allowed:
            raise PermissionDeniedError(
                f"{user} cannot {permission.value} {path}"
            )

    def read_file(self, path: str, user: str) -> str:
        self.check_permission(path, user, FilePermission.READ)
        return self.files[path].content

    def write_file(self, path: str, user: str, content: str):
        self.check_permission(path, user, FilePermission.WRITE)
        self.files[path].content = content

    def delete_file(self, path: str, user: str):
        self.check_permission(path, user, FilePermission.DELETE)
        del self.files[path]


def demonstrate():
    print("=" * 76)
    print("OPERATING SYSTEM SIMULATOR")
    print("=" * 76)

    # 1. Process management
    manager = ProcessManager(memory_limit=1024)

    editor = manager.create_process("TextEditor", 256)
    browser = manager.create_process("Browser", 384)
    database = manager.create_process("Database", 256)

    manager.create_thread(editor.process_id, "UI", 5)
    manager.create_thread(editor.process_id, "Autosave", 3)
    manager.create_thread(browser.process_id, "Renderer", 8)
    manager.create_thread(browser.process_id, "Network", 4)
    manager.create_thread(database.process_id, "QueryWorker", 6)

    manager.report()

    # 2. CPU scheduling
    scheduler = RoundRobinScheduler(quantum=2)

    for process in manager.processes.values():
        for thread in process.threads.values():
            scheduler.add_thread(process.process_id, thread)

    scheduler.run()

    # 3. Synchronization
    print("\nTHREAD SYNCHRONIZATION")
    print("-" * 50)

    counter = ThreadSafeCounter()

    import threading

    workers = [
        threading.Thread(
            target=counter.increment,
            args=(10000,)
        )
        for _ in range(4)
    ]

    for worker in workers:
        worker.start()

    for worker in workers:
        worker.join()

    assert counter.value == 40000
    print(f"Thread-safe counter: {counter.value}")

    # 4. Virtual memory
    memory = VirtualMemory(frame_count=3)

    reference_string = [1, 2, 3, 1, 4, 2, 5, 1, 2]

    print("\nPAGE ACCESS SEQUENCE")
    for page in reference_string:
        print(memory.access(page))

    memory.report()

    # 5. Filesystem
    filesystem = VirtualFileSystem()

    filesystem.create_file(
        "/home/atul/report.txt",
        owner="atul",
        content="Operating system laboratory report.",
        permissions={
            "atul": {
                FilePermission.READ,
                FilePermission.WRITE,
                FilePermission.DELETE,
            },
            "auditor": {
                FilePermission.READ,
            },
        },
    )

    print("\nFILESYSTEM OPERATIONS")
    print("-" * 50)

    print(filesystem.read_file(
        "/home/atul/report.txt",
        "auditor"
    ))

    filesystem.write_file(
        "/home/atul/report.txt",
        "atul",
        "Updated operating system report."
    )

    print(filesystem.read_file(
        "/home/atul/report.txt",
        "atul"
    ))

    try:
        filesystem.write_file(
            "/home/atul/report.txt",
            "auditor",
            "Unauthorized modification"
        )
    except PermissionDeniedError as error:
        print(f"SECURITY EVENT: {error}")

    try:
        filesystem.create_file(
            "/home/../etc/passwd",
            "atul",
            "malicious"
        )
    except ValueError as error:
        print(f"PATH VALIDATION: {error}")

    # 6. Process termination
    manager.terminate_process(browser.process_id)

    manager.report()

    print("\nSIMULATION COMPLETED")


if __name__ == "__main__":
    demonstrate()
