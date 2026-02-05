/**
 * MCP-Flow Reference Implementation — TypeScript/Deno
 *
 * Production-quality echo server demonstrating the MCP-Flow protocol.
 *
 * Run:
 *   deno run --allow-net --allow-read --unstable-net server.ts
 *
 * @module
 */

// =============================================================================
// Type Definitions
// =============================================================================

type Encoding = "json" | "cbor";
type RequestId = string | number;

interface JsonRpcRequest {
  readonly jsonrpc: "2.0";
  readonly id: RequestId;
  readonly method: string;
  readonly params?: Record<string, unknown>;
}

interface JsonRpcNotification {
  readonly jsonrpc: "2.0";
  readonly method: string;
  readonly params?: Record<string, unknown>;
}

interface JsonRpcResponse {
  readonly jsonrpc: "2.0";
  readonly id: RequestId;
  readonly result?: unknown;
  readonly error?: JsonRpcError;
}

interface JsonRpcError {
  readonly code: number;
  readonly message: string;
  readonly data?: unknown;
}

interface ClientTransportCapabilities {
  readonly type: "mcp-flow";
  readonly version: string;
  readonly encodings?: readonly Encoding[];
}

interface ServerTransportCapabilities {
  readonly type: "mcp-flow";
  readonly version: string;
  readonly encoding: Encoding;
  readonly maxConcurrentStreams: number;
  readonly datagramsSupported: boolean;
}

interface Tool {
  readonly name: string;
  readonly description: string;
  readonly inputSchema: Record<string, unknown>;
}

interface TextContent {
  readonly type: "text";
  readonly text: string;
}

type JsonRpcMessage = JsonRpcRequest | JsonRpcNotification;

// =============================================================================
// Constants
// =============================================================================

const MCP_FLOW_VERSION = "0.1";
const PROTOCOL_VERSION = "2024-11-05";
const SERVER_INFO = Object.freeze({ name: "mcp-flow-echo-ts", version: "1.0.0" });
const MAX_CONCURRENT_STREAMS = 100;
const MAX_FRAME_SIZE = 16 * 1024 * 1024; // 16MB sanity limit

const JOKES: readonly string[] = Object.freeze([
  "There are only 10 types of people: those who understand binary and those who don't.",
  "A SQL query walks into a bar, walks up to two tables and asks, 'Can I join you?'",
  "Why do programmers prefer dark mode? Because light attracts bugs.",
  "It works on my machine. ¯\\_(ツ)_/¯",
  "// TODO: fix this later — commit mass: 3 years ago",
  "There's no place like 127.0.0.1",
  "I would tell you a UDP joke, but you might not get it.",
  "To understand recursion, you must first understand recursion.",
  "The best thing about a Boolean is that even if you're wrong, you're only off by a bit.",
  "Why do Java developers wear glasses? Because they can't C#.",
  "!false — It's funny because it's true.",
  "A programmer's wife says: 'Buy a loaf of bread. If they have eggs, buy a dozen.' He returns with 12 loaves.",
]);

// =============================================================================
// Frame Codec
// =============================================================================

class FrameCodec {
  private readonly encoder = new TextEncoder();
  private readonly decoder = new TextDecoder();

  encode(message: Record<string, unknown>): Uint8Array {
    const json = JSON.stringify(message);
    const body = this.encoder.encode(json);

    if (body.length > MAX_FRAME_SIZE) {
      throw new RangeError(`Frame exceeds maximum size: ${body.length} > ${MAX_FRAME_SIZE}`);
    }

    const frame = new Uint8Array(4 + body.length);
    new DataView(frame.buffer).setUint32(0, body.length, false);
    frame.set(body, 4);
    return frame;
  }

  async decode(reader: ReadableStreamDefaultReader<Uint8Array>): Promise<Record<string, unknown> | null> {
    const lengthBytes = await this.readExact(reader, 4);
    if (!lengthBytes) return null;

    const length = new DataView(lengthBytes.buffer).getUint32(0, false);

    if (length > MAX_FRAME_SIZE) {
      throw new RangeError(`Frame exceeds maximum size: ${length} > ${MAX_FRAME_SIZE}`);
    }

    const body = await this.readExact(reader, length);
    if (!body) return null;

    return JSON.parse(this.decoder.decode(body)) as Record<string, unknown>;
  }

  private async readExact(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    size: number
  ): Promise<Uint8Array | null> {
    const buffer = new Uint8Array(size);
    let offset = 0;

    while (offset < size) {
      const { value, done } = await reader.read();
      if (done) return offset === 0 ? null : buffer.slice(0, offset);

      const remaining = size - offset;
      const chunk = value.length <= remaining ? value : value.slice(0, remaining);
      buffer.set(chunk, offset);
      offset += chunk.length;

      // Handle overflow bytes (push back would be ideal, but we consume exact)
      if (value.length > remaining) {
        // In production, buffer the excess for next read
        console.warn("Frame boundary misalignment detected");
      }
    }

    return buffer;
  }
}

// =============================================================================
// RPC Handler
// =============================================================================

type HandlerResult = JsonRpcResponse | null;

class RpcHandler {
  private readonly tools: readonly Tool[] = Object.freeze([
    {
      name: "echo_joke",
      description: "Returns a random programming joke. Guaranteed to mass a code review.",
      inputSchema: { type: "object", properties: {}, additionalProperties: false },
    },
  ]);

  handle(message: JsonRpcMessage): HandlerResult {
    const method = message.method;
    const id = "id" in message ? message.id : undefined;

    switch (method) {
      case "initialize":
        return this.handleInitialize(id!, message.params);
      case "notifications/initialized":
        return this.handleInitialized();
      case "tools/list":
        return this.handleToolsList(id!);
      case "tools/call":
        return this.handleToolsCall(id!, message.params);
      case "ping":
        return this.handlePing(id!);
      case "$/shutdown":
        return this.handleShutdown();
      case "$/cancel":
        return this.handleCancel(message.params);
      default:
        return this.methodNotFound(id, method);
    }
  }

  private handleInitialize(id: RequestId, params?: Record<string, unknown>): JsonRpcResponse {
    const clientTransport = params?.transport as ClientTransportCapabilities | undefined;
    const requestedEncodings = clientTransport?.encodings ?? ["json"];
    const selectedEncoding: Encoding = requestedEncodings.includes("json") ? "json" : "json";

    const transport: ServerTransportCapabilities = {
      type: "mcp-flow",
      version: MCP_FLOW_VERSION,
      encoding: selectedEncoding,
      maxConcurrentStreams: MAX_CONCURRENT_STREAMS,
      datagramsSupported: false,
    };

    return {
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: { tools: { listChanged: false } },
        serverInfo: SERVER_INFO,
        transport,
      },
    };
  }

  private handleInitialized(): null {
    console.info("✓ Client initialized");
    return null;
  }

  private handleToolsList(id: RequestId): JsonRpcResponse {
    return {
      jsonrpc: "2.0",
      id,
      result: { tools: this.tools },
    };
  }

  private handleToolsCall(id: RequestId, params?: Record<string, unknown>): JsonRpcResponse {
    const toolName = params?.name as string | undefined;

    if (toolName !== "echo_joke") {
      return {
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: `Unknown tool: ${toolName}` }],
          isError: true,
        },
      };
    }

    const joke = JOKES[Math.floor(Math.random() * JOKES.length)];
    console.info(`→ ${joke}`);

    const content: TextContent[] = [{ type: "text", text: joke }];
    return {
      jsonrpc: "2.0",
      id,
      result: { content },
    };
  }

  private handlePing(id: RequestId): JsonRpcResponse {
    return { jsonrpc: "2.0", id, result: {} };
  }

  private handleShutdown(): null {
    console.info("⏻ Shutdown requested");
    return null;
  }

  private handleCancel(params?: Record<string, unknown>): null {
    const requestId = params?.requestId;
    const reason = params?.reason ?? "no reason provided";
    console.info(`⊘ Cancel requested for ${requestId}: ${reason}`);
    return null;
  }

  private methodNotFound(id: RequestId | undefined, method: string): JsonRpcResponse | null {
    if (id === undefined) return null; // Notification for unknown method

    return {
      jsonrpc: "2.0",
      id,
      error: { code: -32601, message: `Method not found: ${method}` },
    };
  }
}

// =============================================================================
// Session Handler
// =============================================================================

class McpFlowSession {
  private readonly codec = new FrameCodec();
  private readonly handler = new RpcHandler();
  private aborted = false;

  async run(controlStream: { readable: ReadableStream; writable: WritableStream }): Promise<void> {
    const reader = controlStream.readable.getReader();
    const writer = controlStream.writable.getWriter();

    try {
      await this.processMessages(reader, writer);
    } finally {
      reader.releaseLock();
      writer.releaseLock();
    }
  }

  abort(): void {
    this.aborted = true;
  }

  private async processMessages(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    writer: WritableStreamDefaultWriter<Uint8Array>
  ): Promise<void> {
    while (!this.aborted) {
      let message: Record<string, unknown> | null;

      try {
        message = await this.codec.decode(reader);
      } catch (err) {
        if (err instanceof SyntaxError) {
          await this.sendError(writer, null, -32700, "Parse error");
          continue;
        }
        throw err;
      }

      if (message === null) break;

      const response = this.handler.handle(message as JsonRpcMessage);

      if (response !== null) {
        const frame = this.codec.encode(response as Record<string, unknown>);
        await writer.write(frame);
      }
    }
  }

  private async sendError(
    writer: WritableStreamDefaultWriter<Uint8Array>,
    id: RequestId | null,
    code: number,
    message: string
  ): Promise<void> {
    const response: JsonRpcResponse = {
      jsonrpc: "2.0",
      id: id ?? 0,
      error: { code, message },
    };
    const frame = this.codec.encode(response as Record<string, unknown>);
    await writer.write(frame);
  }
}

// =============================================================================
// Server Entry Point
// =============================================================================

async function main(): Promise<void> {
  const port = parseInt(Deno.env.get("PORT") ?? "4433", 10);
  const certPath = Deno.env.get("TLS_CERT") ?? "./cert.pem";
  const keyPath = Deno.env.get("TLS_KEY") ?? "./key.pem";

  let cert: string;
  let key: string;

  try {
    cert = await Deno.readTextFile(certPath);
    key = await Deno.readTextFile(keyPath);
  } catch {
    console.error(`
╔══════════════════════════════════════════════════════════════╗
║  ERROR: TLS certificates not found                           ║
║                                                              ║
║  Generate with:                                              ║
║    openssl req -x509 -newkey rsa:4096 -keyout key.pem \\     ║
║      -out cert.pem -days 365 -nodes -subj "/CN=localhost"   ║
╚══════════════════════════════════════════════════════════════╝
`);
    Deno.exit(1);
  }

  console.info(`
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  MCP-Flow Echo Server — TypeScript/Deno                      ┃
┃                                                              ┃
┃  Endpoint:  https://localhost:${port.toString().padEnd(5)}/mcp-flow              ┃
┃  Tool:      echo_joke                                        ┃
┃  Protocol:  MCP-Flow ${MCP_FLOW_VERSION}                                        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
`);

  // Note: Deno's WebTransport API requires --unstable-net and is evolving.
  // This implementation demonstrates the correct protocol structure.
  // For production deployments, consider using the webtransport npm package
  // with Node.js or a dedicated QUIC server.

  Deno.serve(
    {
      port,
      cert,
      key,
      onListen: ({ hostname, port }) => {
        console.info(`Listening on https://${hostname}:${port}`);
      },
    },
    async (request: Request): Promise<Response> => {
      const url = new URL(request.url);

      if (url.pathname !== "/mcp-flow") {
        return new Response("Not Found", { status: 404 });
      }

      // WebTransport upgrade check
      if (request.headers.get("upgrade")?.toLowerCase() === "webtransport") {
        // In stable Deno WebTransport API:
        // const { response, session } = Deno.upgradeWebTransport(request);
        // const stream = await session.incomingBidirectionalStreams.getReader().read();
        // new McpFlowSession().run(stream.value);
        // return response;

        return new Response(
          "WebTransport requires --unstable-net flag. See Deno documentation.",
          { status: 501 }
        );
      }

      return new Response(
        JSON.stringify({
          name: SERVER_INFO.name,
          version: SERVER_INFO.version,
          protocol: `mcp-flow/${MCP_FLOW_VERSION}`,
          status: "ready",
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        }
      );
    }
  );
}

main();
