# MCP-Flow Implementation Guide

This guide provides everything needed to implement MCP-Flow from scratch.

## 1. Connection State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────┐    WebTransport    ┌──────────────┐              │
│  │          │    CONNECT ok      │              │              │
│  │  CLOSED  │ ─────────────────► │  CONNECTED   │              │
│  │          │                    │              │              │
│  └──────────┘                    └──────┬───────┘              │
│       ▲                                 │                       │
│       │                                 │ createBidirectionalStream()
│       │                                 ▼                       │
│       │                          ┌──────────────┐              │
│       │                          │   CONTROL    │              │
│       │                          │   STREAM     │              │
│       │                          │   OPENED     │              │
│       │                          └──────┬───────┘              │
│       │                                 │                       │
│       │                                 │ send initialize (JSON)
│       │                                 ▼                       │
│       │                          ┌──────────────┐              │
│       │                          │  INITIALIZING │              │
│       │                          └──────┬───────┘              │
│       │                                 │                       │
│       │                                 │ recv initialize result
│       │                                 │ (encoding negotiated)
│       │                                 ▼                       │
│       │                          ┌──────────────┐              │
│       │         $/shutdown       │              │              │
│       └────────────────────────  │    READY     │              │
│                                  │              │              │
│                                  └──────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### State Transitions

| From | Event | To | Action |
|------|-------|-----|--------|
| CLOSED | WebTransport session established | CONNECTED | — |
| CONNECTED | Client opens bidirectional stream | CONTROL_STREAM_OPENED | — |
| CONTROL_STREAM_OPENED | Client sends `initialize` | INITIALIZING | Must be JSON encoded |
| INITIALIZING | Server sends `initialize` result | READY | Switch to negotiated encoding |
| READY | Either party sends `$/shutdown` | CLOSED | Drain streams, close session |
| Any | Transport error | CLOSED | — |

## 2. Wire Format Examples

All multi-byte integers are **big-endian**.

### 2.1 Control Stream Frame

```
┌─────────────┬─────────────────────────────────────┐
│ Length (4B) │ Message Body (N bytes)              │
└─────────────┴─────────────────────────────────────┘
```

**Example: `initialize` request (JSON)**

JSON payload (78 bytes):
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"},"transport":{"type":"mcp-flow","version":"0.1","encodings":["cbor","json"]}}}
```

Wire format (simplified, 222 bytes total):
```
Offset  Hex                                         ASCII
------  ------------------------------------------  -----
0000    00 00 00 DA                                 .... (Length = 218)
0004    7B 22 6A 73 6F 6E 72 70 63 22 3A 22 32 2E  {"jsonrpc":"2.
0012    30 22 2C 22 69 64 22 3A 31 2C 22 6D 65 74  0","id":1,"met
...     (rest of JSON body)
```

### 2.2 Execution Stream Header

```
┌───────────────────┬───────────────────┐
│ Request ID (4B)   │ Stream Tag (4B)   │
└───────────────────┴───────────────────┘
```

**Example: Stream for request ID 42, tag 1**

```
Offset  Hex                   Decimal
------  --------------------  -------
0000    00 00 00 2A           42 (Request ID)
0004    00 00 00 01           1  (Stream Tag)
0008    [payload bytes...]
```

### 2.3 Datagram Header

```
┌────────────┬────────────┬───────────────────┐
│ Channel(1B)│ Flags (1B) │ Request ID (4B)   │
└────────────┴────────────┴───────────────────┘
```

**Example: Progress update for request ID 42**

```
Offset  Hex                   Meaning
------  --------------------  -------
0000    01                    Channel = Progress (0x01)
0001    00                    Flags = 0x00 (reserved)
0002    00 00 00 2A           Request ID = 42
0006    [payload bytes...]    Progress data (JSON/Protobuf/etc.)
```

**Channel IDs:**
| Value | Channel |
|-------|---------|
| 0x00 | Reserved |
| 0x01 | Progress |
| 0x02 | Audio |
| 0x03 | Log |

## 3. Encoding Negotiation Flow

```
Client                                          Server
  │                                               │
  │  [Control Stream: JSON frame]                 │
  │  initialize {encodings: ["cbor", "json"]}     │
  │ ─────────────────────────────────────────────►│
  │                                               │
  │  [Control Stream: JSON frame]                 │
  │  initialize result {encoding: "cbor"}         │
  │ ◄─────────────────────────────────────────────│
  │                                               │
  │  ═══════ ALL SUBSEQUENT MESSAGES: CBOR ═══════│
  │                                               │
  │  [Control Stream: CBOR frame]                 │
  │  tools/list {}                                │
  │ ─────────────────────────────────────────────►│
  │                                               │
```

**Rules:**
1. `initialize` request: MUST be JSON
2. `initialize` response: MUST be JSON
3. All messages after `initialize` response: Use negotiated encoding
4. If client omits `encodings`: Server defaults to `"json"`

## 4. Error Codes

### 4.1 Standard JSON-RPC Errors

| Code | Name | When to Use |
|------|------|-------------|
| -32700 | Parse Error | Malformed JSON/CBOR |
| -32600 | Invalid Request | Missing required fields, unknown transport type |
| -32601 | Method Not Found | Unknown method |
| -32602 | Invalid Params | Bad parameter types/values |
| -32603 | Internal Error | Server-side failure |

### 4.2 MCP-Flow Specific Errors

| Code | Name | When to Use |
|------|------|-------------|
| -32000 | Stream Limit Exceeded | Too many concurrent execution streams |
| -32001 | Invalid Stream Reference | `streamTag` doesn't match any open stream |
| -32002 | Stream Injection | Request ID in stream header doesn't match in-flight request |
| -32003 | Encoding Mismatch | Message not in negotiated encoding |
| -32004 | Datagram Not Supported | Server indicated `datagramsSupported: false` |

### 4.3 Stream Error Notification

When an execution stream fails mid-transfer:

```json
{
  "jsonrpc": "2.0",
  "method": "$/streamError",
  "params": {
    "requestId": 42,
    "streamTag": 1,
    "error": "Connection reset by peer"
  }
}
```

## 5. Parallel File Download (Complete Example)

```
Client                                          Server
  │                                               │
  │  [Control Stream]                             │
  │  {"jsonrpc":"2.0","id":42,                    │
  │   "method":"tools/call",                      │
  │   "params":{"name":"read_file",               │
  │             "arguments":{"path":"/big.log"}}} │
  │ ─────────────────────────────────────────────►│
  │                                               │
  │                        [Server opens unidirectional stream]
  │                        [Writes header: requestId=42, streamTag=1]
  │                                               │
  │  [Control Stream]                             │
  │  {"jsonrpc":"2.0","id":42,                    │
  │   "result":{"content":[                       │
  │     {"type":"ref/stream",                     │
  │      "streamTag":1,                           │
  │      "mimeType":"text/plain"}]}}              │
  │ ◄─────────────────────────────────────────────│
  │                                               │
  │  [Execution Stream 1]                         │
  │  <10GB of file data>                          │
  │ ◄━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
  │                                               │
  │  [Control Stream - unblocked!]                │
  │  {"jsonrpc":"2.0","id":43,"method":"ping"}    │
  │ ─────────────────────────────────────────────►│
  │                                               │
  │  [Control Stream]                             │
  │  {"jsonrpc":"2.0","id":43,"result":{}}        │
  │ ◄─────────────────────────────────────────────│
  │                                               │
```

## 6. Cancellation Example

```
Client                                          Server
  │                                               │
  │  [Control Stream]                             │
  │  {"jsonrpc":"2.0","id":99,                    │
  │   "method":"tools/call",                      │
  │   "params":{"name":"analyze","arguments":{}}} │
  │ ─────────────────────────────────────────────►│
  │                                               │
  │           (Server starts long-running task)   │
  │                                               │
  │  [Control Stream]                             │
  │  {"jsonrpc":"2.0",                            │
  │   "method":"$/cancel",                        │
  │   "params":{"requestId":99,                   │
  │             "reason":"User pressed Escape"}}  │
  │ ─────────────────────────────────────────────►│
  │                                               │
  │           (Server aborts task)                │
  │                                               │
  │  [Control Stream]                             │
  │  {"jsonrpc":"2.0","id":99,                    │
  │   "error":{"code":-32000,                     │
  │            "message":"Cancelled"}}            │
  │ ◄─────────────────────────────────────────────│
  │                                               │
```

## 7. Graceful Shutdown

```
Client                                          Server
  │                                               │
  │  [Control Stream]                             │
  │  {"jsonrpc":"2.0","method":"$/shutdown"}      │
  │ ─────────────────────────────────────────────►│
  │                                               │
  │        (Both stop opening new streams)        │
  │        (Wait for in-flight streams to drain)  │
  │                                               │
  │  [WebTransport session close]                 │
  │ ◄────────────────────────────────────────────►│
  │                                               │
```

## 8. Implementation Checklist

### Client
- [ ] Establish WebTransport session over HTTPS + TLS 1.3
- [ ] Open bidirectional control stream immediately
- [ ] Send `initialize` as length-prefixed JSON
- [ ] Parse `initialize` response, extract `encoding`
- [ ] Switch to negotiated encoding for all subsequent messages
- [ ] Track in-flight request IDs for stream correlation
- [ ] Handle `$/streamError` notifications
- [ ] Implement `$/cancel` for user-initiated abort
- [ ] Implement `$/shutdown` for graceful close

### Server
- [ ] Accept WebTransport connections, validate `Origin`
- [ ] Accept control stream, parse length-prefixed frames
- [ ] Handle `initialize`, select encoding from client preferences
- [ ] Respond with `ServerTransportCapabilities`
- [ ] Open execution streams for large payloads
- [ ] Write 8-byte header before stream payload
- [ ] Enforce `maxConcurrentStreams` limit
- [ ] Send `$/streamError` on stream failures
- [ ] Handle `$/cancel`, abort in-flight work
- [ ] Handle `$/shutdown`, drain and close

## 9. Security Checklist

- [ ] TLS 1.3 minimum
- [ ] Validate `Origin` header (CSRF protection)
- [ ] Enforce stream limits (DoS protection)
- [ ] Validate request IDs in stream headers (injection protection)
- [ ] Throttle datagrams on high packet loss
- [ ] Set reasonable message size limits
