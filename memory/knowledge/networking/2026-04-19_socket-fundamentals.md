# Socket Fundamentals — OS Abstraction to Distributed Systems

> Source: TheCodingGopher "99% of Devs Don't Get Sockets" (525K views, 2026-04-19 extraction)
> Confidence: 7 — solid explainer, no novel claims; well-known CS concepts
> Signal: MEDIUM | Jarvis relevance: LOW-MEDIUM

## What Is a Socket

Socket = OS abstraction enabling communication between processes, same machine or over network.

Endpoint = `protocol (TCP/UDP) + IP address + port number`

The OS routes messages via this combination. On Unix, sockets are file descriptors — integers representing OS-managed resources (same system calls as files: `read`, `write`).

**OSI layer placement**: Layer 4 (transport). App layer (L7) calls socket API → socket wraps data into TCP/UDP segments → network layer (L3) handles IP routing. Shields app logic from packet fragmentation, retransmission, routing.

## TCP vs UDP

| Property | TCP | UDP |
|----------|-----|-----|
| Connection | Connection-oriented (three-way handshake: SYN/ACK) | Connectionless |
| Reliability | Guaranteed delivery, ordering, error checking | Best-effort; no guarantees |
| Speed | Slower (overhead of handshake + ACKs) | Fast, lightweight |
| Use cases | HTTP, databases, file transfer | Video streaming, gaming, real-time apps |

## Socket Lifecycle

**Server side:**
1. Create listening socket → bind to IP:port
2. Accept connection → OS creates a **new dedicated socket per client**
3. Original socket continues listening (enables concurrency)
4. Communication → close socket (free resources)

**Client side:**
1. Create socket → connect to server IP:port
2. TCP: initiates three-way handshake
3. Read/write like a file (Unix FD model)

## Concurrency Models

**Multi-threading** (one thread per client): simple but doesn't scale — memory and context-switch overhead grows linearly.

**Event-driven / non-blocking IO**: single thread manages thousands of open sockets concurrently via OS notification:

| Syscall | OS | Notes |
|---------|----|-------|
| `epoll` | Linux | Notify only when socket is ready; foundation of Node.js, Nginx, asyncio |
| `kqueue` | BSD/macOS | Equivalent to epoll |
| `select`/`poll` | Portable | Older; poll all FDs each iteration — less efficient |

## Five-Tuple Uniqueness

Every socket connection uniquely identified by: `(protocol, src_IP, src_port, dst_IP, dst_port)`

OS assigns ephemeral source ports automatically. Result: hundreds of simultaneous connections to the same `example.com:443` — each differentiated by unique source port. Same mechanism enables agent connection pools to share a single Postgres host:port.

## Unix Domain Sockets (UDS)

IPC on the **same host only** — not a network socket.

- Address = file path (e.g., `/tmp/postgres.sock`) instead of IP:port
- Bypasses the network stack entirely — no IP routing, no protocol overhead
- Significantly faster than TCP loopback for local communication
- Used by: **PostgreSQL**, **Redis** as the default transport for local client-server connections
- Security: UDS access controlled by filesystem permissions; no network exposure

## TCP State Machine (Diagnostic Reference)

Key states for debugging connection/port issues:

| State | Meaning |
|-------|---------|
| `LISTEN` | Server waiting for connections |
| `SYN_SENT` | Client initiated handshake |
| `ESTABLISHED` | Active connection |
| `TIME_WAIT` | Waiting after close; ensures delayed packets from old connection not misread as new connection |
| `CLOSE_WAIT` | Remote closed; local close pending |

`TIME_WAIT` accumulation = symptom of port exhaustion on high-concurrency servers or connection pool misconfiguration.

## Security: Sockets Are Insecure by Default

Raw sockets transmit plaintext. TLS wraps the socket connection, encrypting + authenticating all data.

- **Local tools (stdio)**: no TLS needed — data stays in-process, no network exposure
- **Remote/cloud tools (HTTP+SSE)**: TLS mandatory; raw sockets vulnerable to MITM and packet sniffing
- Applies directly to MCP transport: local stdio MCP servers are safe without TLS; remote HTTP+SSE MCP servers must use TLS

## Jarvis-Specific Callouts

- **Postgres connection mode**: When Jarvis connects to Postgres on the same host, it likely uses UDS (`/var/run/postgresql/.s.PGSQL.5432`) — faster than TCP loopback, stays within filesystem permissions model
- **jarvis-app async backend**: If using FastAPI + asyncio, the epoll event loop model enables the single Python process to handle many concurrent WebSocket/HTTP connections without threading
- **Connection pool debugging**: `TIME_WAIT` buildup = connection pool not reusing connections; check for connection leak before increasing pool size
- **MCP security gate**: PostToolUse hook at Host layer + TLS at transport layer are complementary defenses — hooks catch semantic issues; TLS prevents eavesdropping on the wire

## Caveats

> LLM-flagged, unverified.
- [ASSUMPTION] PostgreSQL and Redis "default to UDS" — true for local installs; containerized deployments may default to TCP; connection string determines actual transport
- [ASSUMPTION] epoll as foundation of asyncio — directionally correct; CPython asyncio uses the OS event loop (epoll on Linux) but abstracted through `selectors` module
