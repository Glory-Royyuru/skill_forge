"""(22PC1IN202) Computer Networks — VNR VJIET B.Tech. AIML R22, V Semester."""

from __future__ import annotations

from skillforge.teacher.content._build import concept, lesson, question, subject, topic, unit

OSI_MODEL = topic(
    "cn-osi-model",
    "OSI Model",
    "The seven-layer reference model: what each layer does, how data is encapsulated, and which "
    "addresses each layer uses.",
    level="Beginner",
    lesson=lesson(
        "The OSI model divides network communication into seven layers. Each layer offers a service to "
        "the layer above it and relies on the layer below it.",
        [
            "From the bottom up the layers are Physical, Data Link, Network, Transport, Session, "
            "Presentation and Application. The physical layer moves bits; the data link layer delivers "
            "frames hop to hop; the network layer routes packets from source host to destination host; "
            "the transport layer delivers segments process to process.",
            "As data moves down the stack each layer adds its own header (the data link layer also adds a "
            "trailer). This is encapsulation. Each layer also has its own addressing: physical (MAC) "
            "addresses at the data link layer, logical (IP) addresses at the network layer and port numbers "
            "at the transport layer.",
        ],
        [
            "Network layer: host-to-host delivery and routing.",
            "Transport layer: process-to-process delivery.",
            "MAC addresses change hop by hop; the destination IP address does not.",
        ],
    ),
    concepts={
        "layers": concept(
            "Layer functions",
            "Match the job to the layer: bits on the medium (physical), frames between neighbours (data "
            "link), packets across networks (network), segments between processes (transport).",
        ),
        "encapsulation": concept(
            "Encapsulation and PDUs",
            "Each layer wraps what it receives from above in its own header. The data unit is a segment at "
            "the transport layer, a packet at the network layer and a frame at the data link layer.",
        ),
        "addressing": concept(
            "Addressing across layers",
            "Physical (MAC) addresses identify the next hop and are rewritten at every router. Logical (IP) "
            "addresses identify the end hosts and stay the same end to end.",
        ),
    },
    questions=[
        question(
            "cn-osi-1", 1, "layers",
            "Which OSI layer is responsible for routing packets between different networks?",
            ["Data link layer", "Transport layer", "Network layer", "Session layer"], 2,
            "Routing a packet from the source host to the destination host across networks is the network "
            "layer's job. The data link layer only moves frames between directly connected nodes.",
            {0: "The data link layer delivers frames hop to hop on one link; it does not choose routes "
                "across networks.",
             1: "The transport layer works end to end between processes; it relies on the network layer "
                "for routing."},
        ),
        question(
            "cn-osi-2", 1, "encapsulation",
            "What is the unit of data called at the data link layer?",
            ["Segment", "Frame", "Packet", "Message"], 1,
            "The data link layer encapsulates a network-layer packet into a frame by adding a header and a "
            "trailer.",
        ),
        question(
            "cn-osi-3", 2, "addressing",
            "A host sends data to a server on another network. Which address normally stays the same from "
            "end to end?",
            ["The source MAC address", "The MAC address of the next router",
             "The destination IP address", "The switch port number"], 2,
            "Logical (IP) addresses identify the end hosts, so the destination IP address is carried "
            "unchanged across the path. MAC addresses are rewritten at every hop.",
            {0: "MAC addresses are only meaningful on one link, so a router replaces them at every hop.",
             1: "The next-hop MAC address changes at every router along the path."},
        ),
        question(
            "cn-osi-4", 2, "layers",
            "Which layer is responsible for process-to-process delivery, including segmentation and "
            "reassembly of messages?",
            ["Network layer", "Presentation layer", "Session layer", "Transport layer"], 3,
            "The transport layer delivers a message from one process to another and splits it into "
            "segments that it reassembles at the receiver.",
        ),
        question(
            "cn-osi-5", 3, "encapsulation",
            "A 1,000-byte message passes down through the transport layer (20-byte header), the network "
            "layer (20-byte header) and the data link layer (18 bytes of header and trailer). How many bytes "
            "are placed on the link?",
            ["1,000", "1,040", "1,018", "1,058"], 3,
            "Every layer adds its overhead to what it receives: 1,000 + 20 + 20 + 18 = 1,058 bytes.",
            {1: "1,040 forgets the data link layer's header and trailer.",
             2: "1,018 counts only the data link layer and skips the transport and network headers."},
        ),
        question(
            "cn-osi-6", 3, "addressing",
            "A frame arrives at a router. Which header does the router use to choose where to forward the "
            "data, and which header does it replace for the next hop?",
            ["It reads the IP header and builds a new data link header",
             "It reads the MAC header and builds a new IP header",
             "It reads the port numbers and builds a new IP header",
             "It reads and forwards the frame unchanged"], 0,
            "A router forwards on the destination IP address. It removes the incoming frame and builds a new "
            "one addressed to the next hop's MAC address (it also decrements the IP TTL).",
        ),
    ],
)

ERROR_DETECTION = topic(
    "cn-error-detection",
    "Error Detection and Correction: Block Coding, Hamming Distance, CRC",
    "How redundancy bits let a receiver detect or correct transmission errors.",
    lesson=lesson(
        "Bits can be corrupted in transit. Error detection and correction work by adding redundant bits so "
        "the receiver can tell whether what arrived is a valid codeword.",
        [
            "In block coding, each k-bit dataword is mapped to an n-bit codeword; the r = n − k extra bits "
            "are redundancy. The Hamming distance between two words is the number of positions in which they "
            "differ. A code with minimum distance d_min can detect up to d_min − 1 errors and correct up to "
            "⌊(d_min − 1)/2⌋ errors.",
            "A cyclic redundancy check (CRC) treats the dataword as a polynomial. The sender appends r zeros, "
            "divides by the generator using modulo-2 (XOR) arithmetic, and appends the remainder. The "
            "receiver divides the codeword by the same generator; a non-zero remainder means an error.",
        ],
        [
            "Hamming distance = number of differing bits (XOR and count the 1s).",
            "Detect d_min − 1 errors; correct ⌊(d_min − 1)/2⌋.",
            "CRC: the remainder of modulo-2 division is appended to the dataword.",
        ],
    ),
    concepts={
        "block-coding": concept(
            "Block coding and redundancy",
            "Block coding turns k-bit datawords into n-bit codewords. Only some n-bit patterns are valid, so "
            "an invalid pattern at the receiver reveals an error.",
        ),
        "hamming": concept(
            "Hamming distance",
            "XOR the two words and count the 1s. A code's minimum distance decides its power: detect "
            "d_min − 1 errors, correct ⌊(d_min − 1)/2⌋.",
        ),
        "crc": concept(
            "Cyclic Redundancy Check",
            "Append r zeros (r = degree of the generator), divide by the generator with XOR, and send the "
            "dataword followed by the r-bit remainder.",
        ),
    },
    questions=[
        question(
            "cn-ed-1", 1, "hamming",
            "What is the Hamming distance between 10101 and 11110?",
            ["2", "3", "4", "5"], 1,
            "10101 XOR 11110 = 01011, which contains three 1s, so the words differ in 3 positions.",
        ),
        question(
            "cn-ed-2", 1, "block-coding",
            "In block coding, k-bit datawords become n-bit codewords. What are the r = n − k extra bits "
            "called?",
            ["Stuffed bits", "Redundant (check) bits", "Header bits", "Parity frames"], 1,
            "The extra bits carry no new data; they are redundancy that lets the receiver check whether the "
            "codeword is valid.",
            {0: "Stuffed bits are inserted for framing transparency, not for error checking."},
        ),
        question(
            "cn-ed-3", 2, "hamming",
            "A code has minimum Hamming distance d_min = 4. How many bit errors is it guaranteed to detect?",
            ["2", "4", "3", "1"], 2,
            "A code can detect up to d_min − 1 errors: with d_min = 4, any pattern of up to 3 errors cannot "
            "turn one valid codeword into another.",
            {1: "4 errors could change one valid codeword into another valid one, so they may go "
                "undetected."},
        ),
        question(
            "cn-ed-4", 2, "crc",
            "In CRC, what does the sender append to the dataword?",
            ["The quotient of dividing the dataword by the generator",
             "A single even-parity bit",
             "The remainder of modulo-2 division of the augmented dataword by the generator",
             "The arithmetic sum of all bytes"], 2,
            "The dataword is augmented with r zeros and divided by the generator using XOR; the r-bit "
            "remainder is appended, so the codeword is exactly divisible by the generator.",
            {3: "Adding up bytes is a checksum, a different technique from CRC."},
        ),
        question(
            "cn-ed-5", 3, "hamming",
            "To correct up to 2 bit errors in any codeword, what minimum Hamming distance does the code need?",
            ["3", "4", "6", "5"], 3,
            "To correct t errors, d_min must be at least 2t + 1. For t = 2 that is 5.",
            {0: "d_min = 3 corrects only one error.",
             1: "d_min = 4 corrects one error and detects three, but cannot correct two."},
        ),
        question(
            "cn-ed-6", 3, "crc",
            "The dataword 1001 is encoded with the generator 1011. What codeword is transmitted?",
            ["1001110", "1001011", "1001101", "1001000"], 0,
            "Append three zeros (1001000) and divide by 1011 using XOR: the remainder is 110. The codeword "
            "is the dataword followed by the remainder: 1001110.",
            {3: "1001000 is the augmented dataword before division; the zeros must be replaced by the "
                "remainder."},
        ),
    ],
)

TRANSPORT = topic(
    "cn-transport",
    "Process-to-Process Communication, UDP and TCP, QoS",
    "Port numbers, the different services of UDP and TCP, and traffic shaping with the leaky and token "
    "bucket algorithms.",
    lesson=lesson(
        "The network layer gets a packet to the right host; the transport layer gets the data to the right "
        "process on that host.",
        [
            "Processes are identified by port numbers. A connection is identified by the pair of sockets "
            "(IP address + port) at its two ends. UDP is connectionless and lightweight: no setup, no "
            "retransmission, no ordering. TCP is connection-oriented and reliable: it numbers bytes, "
            "acknowledges them, retransmits losses and controls congestion.",
            "Quality of service techniques shape traffic. A leaky bucket sends data out at a constant rate "
            "however bursty the input. A token bucket lets a host save tokens while idle, so it can send "
            "bursts up to the bucket size while keeping the long-term average rate.",
        ],
        [
            "Port numbers identify processes; sockets identify connections.",
            "UDP: fast and simple. TCP: reliable, ordered, congestion-controlled.",
            "Leaky bucket smooths output; token bucket permits bounded bursts.",
        ],
    ),
    concepts={
        "ports": concept(
            "Process-to-process delivery",
            "A host runs many processes. The transport layer tells them apart with port numbers, and tells "
            "connections apart by the full socket pair: source IP, source port, destination IP, destination "
            "port.",
        ),
        "tcp-udp": concept(
            "UDP and TCP services",
            "Choose UDP when speed and low overhead matter more than guaranteed delivery (DNS queries, live "
            "voice). Choose TCP when every byte must arrive in order (web pages, file transfer).",
        ),
        "congestion": concept(
            "Congestion control and QoS",
            "Leaky bucket: output leaves at a fixed rate. Token bucket: tokens accumulate at rate r up to "
            "capacity C; a burst can use all saved tokens, so up to C + r·t packets can be sent in t "
            "seconds.",
        ),
    },
    questions=[
        question(
            "cn-tl-1", 1, "ports",
            "At the transport layer, what identifies a particular process on a host?",
            ["Its MAC address", "Its port number", "Its domain name", "Its IP address"], 1,
            "The IP address gets data to the host; the port number gets it to the right process on that "
            "host.",
            {3: "The IP address identifies the host, but many processes share it."},
        ),
        question(
            "cn-tl-2", 1, "tcp-udp",
            "Which protocol provides connection-oriented, reliable, in-order byte-stream delivery?",
            ["UDP", "IP", "TCP", "ARP"], 2,
            "TCP sets up a connection, numbers and acknowledges bytes, retransmits losses and delivers data "
            "in order. UDP provides none of these guarantees.",
        ),
        question(
            "cn-tl-3", 2, "tcp-udp",
            "Why is UDP often chosen for DNS queries and real-time voice?",
            ["It guarantees delivery of every datagram",
             "It has low overhead and needs no connection setup",
             "It provides built-in congestion control",
             "It encrypts the payload"], 1,
            "A DNS query fits in one datagram and voice prefers a late packet lost to a stall, so avoiding "
            "connection setup and retransmission delays is worth more than reliability.",
            {0: "UDP makes no delivery guarantee; that is TCP's role.",
             2: "Congestion control is a TCP feature; UDP has none."},
        ),
        question(
            "cn-tl-4", 2, "congestion",
            "How does a leaky bucket shape traffic?",
            ["It sends packets out at a constant rate however bursty the input is",
             "It lets a host send bursts using tokens saved while idle",
             "It drops every packet that arrives in a burst",
             "It raises the output rate as the load grows"], 0,
            "Like water leaking from a hole, packets leave at a fixed rate; bursts are queued in the bucket "
            "(and dropped only if the bucket overflows).",
            {1: "Saving credit while idle to allow bursts describes the token bucket."},
        ),
        question(
            "cn-tl-5", 3, "congestion",
            "A token bucket holds at most 100 tokens and gains 10 tokens per second; each packet needs one "
            "token. The bucket is full when a long burst arrives. How many packets can be sent in the first 5 "
            "seconds?",
            ["50", "100", "500", "150"], 3,
            "The saved 100 tokens are spent at once, and 10 new tokens arrive each second: 100 + 10 × 5 = "
            "150 packets.",
            {0: "50 counts only newly generated tokens and ignores the 100 already saved.",
             1: "100 ignores the tokens generated during the 5 seconds."},
        ),
        question(
            "cn-tl-6", 3, "ports",
            "Two browser tabs on the same laptop open connections to the same web server on port 80. How "
            "does the laptop's transport layer keep the two connections apart?",
            ["They use different source (ephemeral) port numbers",
             "They use different destination IP addresses",
             "They use different MAC addresses",
             "It cannot; the second connection replaces the first"], 0,
            "A connection is identified by the full socket pair. Each tab's connection gets its own "
            "ephemeral source port, so the four-tuples differ even though the server side is the same.",
        ),
    ],
)

SUBJECT = subject(
    "computer-networks",
    "22PC1IN202",
    "Computer Networks",
    "CN",
    "theory",
    "Modern network architectures, the data link and network layers, QoS and congestion control, and "
    "application-layer services and security.",
    [
        unit(1, "Data Communication Components", [
            topic("cn-data-flow", "Representation of Data and its Flow",
                  "How data is represented and the simplex, half-duplex and full-duplex flow modes."),
            topic("cn-topologies", "Connection Topologies, Protocols and Standards",
                  "Mesh, star, bus and ring topologies, and the role of protocols and standards."),
            OSI_MODEL,
            topic("cn-transmission-media", "Transmission Media",
                  "Guided media (twisted pair, coaxial, fibre) and unguided (wireless) media."),
            topic("cn-lan", "Overview of LAN: Wired LAN, Wireless LANs, Connecting LAN and Virtual LAN",
                  "Ethernet, wireless LANs, connecting devices and VLANs."),
            topic("cn-bandwidth", "Bandwidth Utilization: Multiplexing and Spread Spectrum",
                  "Frequency-, time- and wave-division multiplexing, and the concepts of spread spectrum."),
        ]),
        unit(2, "Data Link Layer and Medium Access Sub Layer", [
            ERROR_DETECTION,
            topic("cn-flow-error-control", "Flow and Error Control: Stop and Wait, Go-Back-N ARQ, "
                  "Selective Repeat ARQ, Sliding Window, Piggybacking",
                  "Protocols that pace the sender and recover lost or damaged frames."),
            topic("cn-multiple-access", "Random Access: Pure ALOHA, Slotted ALOHA, CSMA/CD, CDMA/CA",
                  "How stations share a common medium."),
        ]),
        unit(3, "Network Layer", [
            topic("cn-switching", "Switching", "Circuit, packet and message switching."),
            topic("cn-ip-addressing", "Logical Addressing: IPv4 and IPv6",
                  "Address spaces, classful and classless addressing, and IPv6."),
            topic("cn-address-mapping", "Address Mapping: ARP, RARP, BOOTP and DHCP",
                  "Mapping between logical and physical addresses, and dynamic configuration."),
            topic("cn-routing", "Delivery, Forwarding and Unicast Routing Protocols",
                  "Forwarding tables and distance-vector and link-state routing."),
        ]),
        unit(4, "Transport Layer", [
            TRANSPORT,
            topic("cn-sctp-congestion", "SCTP and Congestion Control",
                  "The Stream Control Transmission Protocol and congestion control mechanisms."),
        ]),
        unit(5, "Application Layer", [
            topic("cn-dns", "Domain Name Space (DNS) and DDNS", "Name resolution and dynamic DNS."),
            topic("cn-remote-login-email", "TELNET and EMAIL", "Remote login and electronic mail."),
            topic("cn-ftp-www-http", "FTP, WWW and HTTP", "File transfer and the web."),
            topic("cn-snmp-firewalls", "SNMP and Firewalls", "Network management and firewalls."),
        ]),
    ],
)
