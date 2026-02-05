# MCP-Flow Reference Implementations

Simple echo servers demonstrating MCP-Flow protocol in three languages.

Each server exposes a single tool: `echo_joke` — returns a random programming joke.

## Prerequisites

All examples require TLS certificates. Generate self-signed certs for testing:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/CN=localhost"
```

## TypeScript (Deno)

```bash
cd typescript
deno run --unstable-net --allow-net --allow-read server.ts
```

**Note:** Deno's WebTransport server API is still evolving. Check latest docs.

## Python (aioquic)

```bash
cd python
pip install -r requirements.txt
python server.py --cert ../cert.pem --key ../key.pem
```

## Go (quic-go)

```bash
cd go
go mod tidy
go run server.go -cert ../cert.pem -key ../key.pem
```

## Testing

Connect using any WebTransport client to `https://localhost:4433/mcp-flow`

Example test flow:
1. Open bidirectional stream (Control Stream)
2. Send length-prefixed `initialize` request
3. Receive `initialize` response
4. Send `tools/list` request
5. Send `tools/call` with `name: "echo_joke"`
6. Receive a programming joke 🎭

## Protocol Summary

```
┌─────────────────────────────────────────────────────────────┐
│  Control Stream (length-prefixed JSON-RPC 2.0)              │
│                                                             │
│  Client                              Server                 │
│    │                                   │                    │
│    │─── initialize ──────────────────►│                    │
│    │◄── initialize result ────────────│                    │
│    │                                   │                    │
│    │─── tools/call {echo_joke} ──────►│                    │
│    │◄── "Why do programmers..." ──────│                    │
│    │                                   │                    │
└─────────────────────────────────────────────────────────────┘
```
