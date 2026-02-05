# MCP-Flow Transport Schema v0.1

A WebTransport binding for the Model Context Protocol.

## Files

- **schema.ts** — TypeScript source of truth
- **schema.json** — JSON Schema (draft-07)

## Quick Reference

| Type | Purpose |
|------|---------|
| `ControlStreamFrame` | Length-prefixed RPC message framing (4-byte length + body) |
| `StreamHeader` | 8-byte header for Execution Streams (requestId + streamTag) |
| `StreamReference` | `ref/stream` content type for streamed payloads |
| `DatagramHeader` | 6-byte header for telemetry datagrams |
| `ClientTransportCapabilities` | Client's `transport` field in `initialize` |
| `ServerTransportCapabilities` | Server's `transport` field in `initialize` |
| `CancelNotification` | `$/cancel` — cancel in-flight request |
| `ShutdownNotification` | `$/shutdown` — graceful shutdown |
| `StreamErrorNotification` | `$/streamError` — report stream failure |

## Constants

| Name | Value | Description |
|------|-------|-------------|
| `MCP_FLOW_VERSION` | `"0.1"` | Protocol version |
| `RECOMMENDED_PATH` | `"/mcp-flow"` | Endpoint path |
| `ALPN` | `"h3"` | HTTP/3 ALPN identifier |
| `MIN_TLS_VERSION` | `"1.3"` | Minimum TLS version |
| `MAX_DATAGRAM_PAYLOAD_SIZE` | `1200` | Safe MTU for datagrams |

## Wire Encoding

Control Stream messages support `"json"` or `"cbor"` encoding, negotiated during `initialize`. The `initialize` request itself is always JSON.

## License

MIT
