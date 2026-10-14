"""(22PC1IT202) Operating Systems — VNR VJIET B.Tech. AIML R22, V Semester."""

from __future__ import annotations

from skillforge.teacher.content._build import concept, lesson, question, subject, topic, unit

CPU_SCHEDULING = topic(
    "os-cpu-scheduling",
    "CPU Scheduling: Criteria, Algorithms and Evaluation",
    "Scheduling criteria, FCFS, SJF, priority and round robin, and computing waiting time.",
    lesson=lesson(
        "When several processes are ready, the CPU scheduler decides which one runs next. That choice "
        "shapes how responsive and efficient the whole system feels.",
        [
            "Scheduling criteria include CPU utilization, throughput, turnaround time (submission to "
            "completion), waiting time (time spent in the ready queue) and response time. First-Come, "
            "First-Served is simple but can suffer the convoy effect; Shortest-Job-First minimizes average "
            "waiting time; priority scheduling risks starvation unless priorities age; Round Robin gives each "
            "process a time quantum in turn.",
            "Algorithms are evaluated deterministically by working through a workload: draw the Gantt chart, "
            "compute each process's waiting time, and average.",
        ],
        [
            "Waiting time = time in the ready queue.",
            "SJF gives the minimum average waiting time.",
            "Round Robin with a huge quantum behaves like FCFS.",
        ],
    ),
    concepts={
        "criteria": concept(
            "Scheduling criteria",
            "Turnaround = completion − arrival; waiting = turnaround − burst; response = first run − "
            "arrival. Good schedulers trade these off.",
        ),
        "algorithms": concept(
            "Scheduling algorithms",
            "FCFS runs in arrival order; SJF picks the shortest next burst; priority picks the most urgent; "
            "Round Robin rotates with a fixed quantum.",
        ),
        "evaluation": concept(
            "Algorithm evaluation",
            "Draw the Gantt chart, read off when each process starts and finishes, and compute waiting time "
            "as start time minus arrival time for non-preemptive schedules.",
        ),
    },
    questions=[
        question(
            "os-cs-1", 1, "algorithms",
            "Which scheduling algorithm can cause the convoy effect, where short processes wait behind one "
            "long process?",
            ["Round Robin", "First-Come, First-Served", "Shortest-Job-First", "Priority with aging"], 1,
            "FCFS runs processes strictly in arrival order, so one long CPU-bound process delays everything "
            "queued behind it.",
        ),
        question(
            "os-cs-2", 1, "criteria",
            "What does turnaround time measure?",
            ["The interval from a process's submission to its completion",
             "The time until the process first gets the CPU",
             "The time a process spends waiting in the ready queue",
             "The length of one CPU burst"], 0,
            "Turnaround time covers the whole life of the process: waiting, executing and doing I/O.",
            {1: "That is response time.", 2: "That is waiting time."},
        ),
        question(
            "os-cs-3", 2, "algorithms",
            "For a set of processes all available at time 0, which algorithm gives the minimum average "
            "waiting time?",
            ["FCFS", "Round Robin", "Priority scheduling", "Shortest-Job-First"], 3,
            "Running shorter jobs first reduces the waiting time of short jobs more than it increases that of "
            "long ones, so SJF is provably optimal for average waiting time.",
        ),
        question(
            "os-cs-4", 2, "criteria",
            "What happens in Round Robin scheduling if the time quantum is made very large?",
            ["It behaves like FCFS",
             "It behaves like SJF",
             "The number of context switches increases",
             "Short processes are guaranteed to finish first"], 0,
            "If the quantum is longer than every burst, each process runs to completion in arrival order, "
            "which is exactly FCFS.",
            {2: "A larger quantum means fewer, not more, context switches."},
        ),
        question(
            "os-cs-5", 3, "evaluation",
            "Processes P1, P2 and P3 arrive at time 0 with CPU bursts of 24, 3 and 3 ms and run FCFS in that "
            "order. What is the average waiting time?",
            ["3 ms", "13 ms", "17 ms", "27 ms"], 2,
            "P1 waits 0, P2 waits 24 and P3 waits 27 ms. The average is (0 + 24 + 27) / 3 = 17 ms.",
        ),
        question(
            "os-cs-6", 3, "evaluation",
            "The same processes (bursts 24, 3 and 3 ms, all at time 0) are scheduled with non-preemptive SJF. "
            "What is the average waiting time?",
            ["17 ms", "3 ms", "6 ms", "9 ms"], 1,
            "SJF runs P2, P3, then P1, so the waits are 0, 3 and 6 ms. The average is 9 / 3 = 3 ms, far "
            "below FCFS's 17 ms.",
            {2: "6 ms is P1's waiting time alone, not the average."},
        ),
    ],
)

DEADLOCK = topic(
    "os-deadlock",
    "Deadlock: Characterization, Prevention, Avoidance, Detection and Recovery",
    "The four necessary conditions, how to prevent or avoid them, and how to detect and recover.",
    lesson=lesson(
        "A deadlock occurs when every process in a set is waiting for a resource held by another process in "
        "the same set, so none can proceed.",
        [
            "Four conditions must hold at once: mutual exclusion, hold and wait, no preemption, and circular "
            "wait. Deadlock prevention guarantees that at least one of them can never hold, for example by "
            "ordering resource types to rule out circular wait.",
            "Deadlock avoidance (the Banker's algorithm) grants a request only if the system stays in a safe "
            "state, one where some order lets every process finish. Detection lets deadlocks happen, finds "
            "them (for single-instance resources, a cycle in the wait-for graph), and recovers by "
            "terminating processes or preempting resources.",
        ],
        [
            "Mutual exclusion, hold and wait, no preemption, circular wait.",
            "Prevention breaks a condition; avoidance stays in safe states.",
            "Single-instance resources: a cycle means deadlock.",
        ],
    ),
    concepts={
        "conditions": concept(
            "Deadlock characterization",
            "All four conditions are necessary: mutual exclusion, hold and wait, no preemption and circular "
            "wait. Remove any one and deadlock is impossible.",
        ),
        "prevention-avoidance": concept(
            "Prevention and avoidance",
            "Prevention denies a condition outright (request everything at once, order resources). "
            "Avoidance checks each request and only grants it if a safe sequence still exists.",
        ),
        "detection": concept(
            "Detection and recovery",
            "With one instance per resource type, a cycle in the resource-allocation graph is a deadlock. "
            "Recovery aborts processes or preempts resources to break it.",
        ),
    },
    questions=[
        question(
            "os-dl-1", 1, "conditions",
            "Which of these is NOT one of the four necessary conditions for deadlock?",
            ["Mutual exclusion", "Hold and wait", "Circular wait", "Starvation"], 3,
            "The four conditions are mutual exclusion, hold and wait, no preemption and circular wait. "
            "Starvation is a different problem: a process waits indefinitely while others progress.",
        ),
        question(
            "os-dl-2", 1, "prevention-avoidance",
            "The Banker's algorithm is a technique for deadlock:",
            ["prevention", "avoidance", "detection", "recovery"], 1,
            "It examines each request and grants it only if the resulting state is safe, avoiding deadlock "
            "without denying any condition outright.",
        ),
        question(
            "os-dl-3", 2, "prevention-avoidance",
            "Requiring each process to request all of its resources before it starts prevents deadlock by "
            "eliminating which condition?",
            ["Mutual exclusion", "No preemption", "Hold and wait", "Circular wait"], 2,
            "A process can no longer hold some resources while waiting for others, so hold and wait cannot "
            "occur, at the cost of poor resource utilization.",
        ),
        question(
            "os-dl-4", 2, "detection",
            "In a resource-allocation graph where every resource type has a single instance, what does a "
            "cycle indicate?",
            ["A deadlock exists",
             "A deadlock may or may not exist",
             "The system is in a safe state",
             "Only starvation is possible"], 0,
            "With single instances, a cycle is both necessary and sufficient for deadlock. With multiple "
            "instances, a cycle only means deadlock is possible.",
            {1: "That is the multiple-instance case; with single instances a cycle guarantees deadlock."},
        ),
        question(
            "os-dl-5", 3, "prevention-avoidance",
            "Numbering resource types and requiring processes to request them only in increasing order "
            "prevents deadlock because it rules out:",
            ["mutual exclusion", "circular wait", "hold and wait", "preemption"], 1,
            "A cycle would need some process to hold a higher-numbered resource while requesting a "
            "lower-numbered one, which the ordering forbids.",
        ),
        question(
            "os-dl-6", 3, "prevention-avoidance",
            "A system has 12 tape drives. P0 holds 5 (maximum need 10), P1 holds 2 (maximum 4) and P2 holds 2 "
            "(maximum 9), so 3 are free. Is the state safe?",
            ["No, because no process can finish",
             "Yes: <P0, P1, P2> is a safe sequence",
             "Yes: <P1, P0, P2> is a safe sequence",
             "No, because P2 needs 7 more drives"], 2,
            "P1 needs 2 more (3 free), finishes and releases 4 drives → 5 free. P0 needs 5 → finishes → 10 "
            "free. P2 needs 7 → finishes. So <P1, P0, P2> is safe.",
            {1: "P0 needs 5 more drives but only 3 are free, so it cannot go first.",
             3: "P2 can wait until P1 and P0 release their drives; a safe sequence still exists."},
        ),
    ],
)

SUBJECT = subject(
    "operating-systems",
    "22PC1IT202",
    "Operating Systems",
    "OS",
    "theory",
    "Processes and threads, scheduling and synchronization, deadlock, memory and file management, mass "
    "storage, protection and security.",
    [
        unit(1, "Operating System Overview and Process Concept", [
            topic("os-overview", "Operating System Functions, Services and System Calls",
                  "What an operating system does and how programs request its services.", level="Beginner"),
            topic("os-process-concept", "Process Concept, Process States, Threads and Multithreading",
                  "Processes, their life cycle, and threads."),
        ]),
        unit(2, "Process Management and Process Synchronization", [
            CPU_SCHEDULING,
            topic("os-critical-section", "Critical-Section Problem, Peterson's Solution and Synchronization "
                  "Hardware", "Mutual exclusion in software and hardware."),
            topic("os-semaphores", "Semaphores and Classic Problems: Producer–Consumer, Dining Philosophers, "
                  "Readers–Writers", "Synchronization with semaphores and the classic problems."),
            topic("os-monitors", "Monitors and Synchronization Examples",
                  "Higher-level synchronization constructs."),
        ]),
        unit(3, "Inter Process Communication and Deadlock", [
            topic("os-ipc", "Inter Process Communication: Message Passing and Shared Memory",
                  "Two models for processes to exchange data."),
            DEADLOCK,
        ]),
        unit(4, "Memory Management and File System Interface", [
            topic("os-memory", "Swapping, Contiguous Memory Allocation, Paging, Page-Table Structure and "
                  "Segmentation", "How physical memory is shared among processes."),
            topic("os-virtual-memory", "Virtual Memory, Demand Paging, Page Replacement, Frame Allocation "
                  "and Thrashing", "Running programs larger than physical memory."),
            topic("os-file-system", "File Concepts, Access Methods, Directory Structure, Mounting, Sharing "
                  "and Protection", "The file-system interface."),
            topic("os-file-allocation", "Allocation Methods, Free-Space Management, Efficiency and "
                  "Performance", "How files are laid out on disk."),
        ]),
        unit(5, "Mass Storage, Protection and Security", [
            topic("os-mass-storage", "Disk Structure, Disk Attachment, Disk Scheduling, Swap-Space "
                  "Management and RAID", "Secondary storage and how it is scheduled."),
            topic("os-protection", "Protection: Goals, Principles, Domain of Protection and the Access "
                  "Matrix", "Controlling access to system resources."),
            topic("os-security", "Security: The Security Problem, Program Threats, System and Network "
                  "Threats", "Threats to operating systems."),
            topic("os-case-study", "Case Study: Windows and Linux Operating Systems",
                  "Two real operating systems."),
        ]),
    ],
)
