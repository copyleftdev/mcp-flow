# MCP-Flow

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go&logoColor=white)](examples/go/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](examples/python/)
[![TypeScript](https://img.shields.io/badge/TypeScript-Deno-3178C6?logo=deno&logoColor=white)](examples/typescript/)
[![Protocol](https://img.shields.io/badge/Protocol-v0.1-green)](schema/0.1/)
[![WebTransport](https://img.shields.io/badge/Transport-WebTransport%2FQUIC-orange)](https://developer.mozilla.org/en-US/docs/Web/API/WebTransport_API)

**WebTransport binding for the Model Context Protocol.**

MCP-Flow eliminates head-of-line blocking in MCP by leveraging QUIC streams and datagrams for parallel, mixed-reliability communication.

![Traditional MCP vs MCP-Flow](docs/comparison.gif)

## Why MCP-Flow?

| Traditional MCP | MCP-Flow |
|-----------------|----------|
| Single stream blocks all messages | Parallel streams for concurrent operations |
| Large responses freeze the connection | Bulk data flows on dedicated Execution Streams |
| No progress updates during transfers | Real-time datagrams for progress, audio, logs |

## Quick Start

```bash
# Build everything
make build

# Terminal 1: Start a server
make run-go

# Terminal 2: Run the test client
./bin/mcp-flow-client
```

## Project Structure

```
schema/0.1/
├── schema.ts            # TypeScript type definitions
├── schema.json          # JSON Schema for validation
└── IMPLEMENTATION.md    # Wire formats, state machine, examples

examples/
├── go/                  # Go server (quic-go)
├── python/              # Python server (aioquic)
├── typescript/          # TypeScript server (Deno)
└── client/              # Go test client
```

## Key Features

- **No head-of-line blocking** — Large responses stream independently
- **Mixed reliability** — Datagrams for progress/audio, streams for data
- **Encoding negotiation** — JSON or CBOR, negotiated at connection time
- **Backward compatible** — Standard MCP JSON-RPC messages, new transport

## Documentation

| Document | Description |
|----------|-------------|
| [Implementation Guide](schema/0.1/IMPLEMENTATION.md) | Wire formats, state machine, error codes |
| [Schema Reference](schema/0.1/README.md) | Type definitions and constants |
| [Examples README](examples/README.md) | Running the reference servers |
| [Contributing](CONTRIBUTING.md) | How to contribute |

## Status

**Version 0.1** — Reference implementations demonstrate the core Control Stream protocol. Execution Streams and Datagrams are specified but not yet implemented in examples.

## License

[MIT](LICENSE)
