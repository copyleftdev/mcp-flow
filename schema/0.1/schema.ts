/**
 * MCP-Flow Transport Schema
 * Version: 0.1
 * 
 * This schema defines transport-layer types for MCP-Flow,
 * a WebTransport binding for the Model Context Protocol.
 */

export const MCP_FLOW_VERSION = "0.1";

/* ============================================================================
 * Connection Establishment
 * ============================================================================ */

/**
 * Recommended URL path for MCP-Flow endpoints.
 */
export const RECOMMENDED_PATH = "/mcp-flow";

/**
 * Required ALPN identifier for HTTP/3.
 */
export const ALPN = "h3";

/**
 * Minimum required TLS version.
 */
export const MIN_TLS_VERSION = "1.3";

/* ============================================================================
 * Wire Encoding
 * ============================================================================ */

/**
 * Supported wire encodings for Control Stream messages.
 */
export type Encoding = "json" | "cbor";

/* ============================================================================
 * Control Stream Message Framing
 * ============================================================================ */

/**
 * Length-prefixed message frame for the Control Stream.
 * 
 * All messages on the Control Stream MUST be wrapped in this frame.
 * The length field is a 4-byte big-endian unsigned integer.
 */
export interface ControlStreamFrame {
  /**
   * Message length in bytes (big-endian Uint32).
   * Maximum value: 2^32 - 1 (4,294,967,295 bytes).
   */
  length: number;

  /**
   * The JSON or CBOR encoded RPC message body.
   */
  body: Uint8Array;
}

/* ============================================================================
 * Execution Stream Types
 * ============================================================================ */

/**
 * Header that MUST appear at the start of every Execution Stream.
 * Total size: 8 bytes.
 */
export interface StreamHeader {
  /**
   * The JSON-RPC request `id` this stream is associated with.
   * Encoded as big-endian Uint32 (bytes 0-3).
   */
  requestId: number;

  /**
   * Application-assigned tag for multi-stream responses.
   * Encoded as big-endian Uint32 (bytes 4-7).
   */
  streamTag: number;
}

/**
 * Reference to data delivered via an Execution Stream.
 * Used in JSON-RPC response `content` arrays.
 */
export interface StreamReference {
  /**
   * Discriminator for stream references.
   */
  type: "ref/stream";

  /**
   * The stream tag from the Execution Stream header.
   * Correlates with StreamHeader.streamTag.
   */
  streamTag: number;

  /**
   * MIME type of the streamed content.
   */
  mimeType: string;
}

/* ============================================================================
 * Datagram (Telemetry Plane) Types
 * ============================================================================ */

/**
 * Channel identifiers for datagram multiplexing.
 */
export type DatagramChannelId =
  | 0x00  // Reserved
  | 0x01  // Progress
  | 0x02  // Audio
  | 0x03; // Log

export const DATAGRAM_CHANNEL_RESERVED = 0x00;
export const DATAGRAM_CHANNEL_PROGRESS = 0x01;
export const DATAGRAM_CHANNEL_AUDIO = 0x02;
export const DATAGRAM_CHANNEL_LOG = 0x03;

/**
 * Header that MUST appear at the start of every datagram.
 * Total size: 6 bytes.
 */
export interface DatagramHeader {
  /**
   * Channel identifier (byte 0).
   */
  channelId: DatagramChannelId;

  /**
   * Reserved flags for future use (byte 1). MUST be 0x00.
   */
  flags: 0x00;

  /**
   * The JSON-RPC request `id` this datagram relates to (bytes 2-5).
   * Use 0 for session-global datagrams.
   */
  requestId: number;
}

/**
 * Maximum recommended datagram payload size to avoid fragmentation.
 * Based on conservative QUIC MTU assumptions.
 */
export const MAX_DATAGRAM_PAYLOAD_SIZE = 1200;

/* ============================================================================
 * Transport Capability Negotiation
 * ============================================================================ */

/**
 * Transport metadata sent by the client in the `initialize` request.
 */
export interface ClientTransportCapabilities {
  /**
   * Transport type identifier.
   */
  type: "mcp-flow";

  /**
   * MCP-Flow protocol version.
   */
  version: string;

  /**
   * Supported encodings, ordered by preference.
   * If omitted, server defaults to "json".
   */
  encodings?: Encoding[];
}

/**
 * Transport metadata sent by the server in the `initialize` response.
 */
export interface ServerTransportCapabilities {
  /**
   * Transport type identifier.
   */
  type: "mcp-flow";

  /**
   * MCP-Flow protocol version.
   */
  version: string;

  /**
   * The encoding selected by the server.
   * All subsequent Control Stream messages use this encoding.
   */
  encoding: Encoding;

  /**
   * Maximum number of concurrent Execution Streams allowed.
   */
  maxConcurrentStreams: number;

  /**
   * Whether the server supports WebTransport datagrams.
   */
  datagramsSupported: boolean;
}

/* ============================================================================
 * Error Handling
 * ============================================================================ */

/**
 * Notification sent when an Execution Stream encounters an error.
 */
export interface StreamErrorNotification {
  jsonrpc: "2.0";
  method: "$/streamError";
  params: {
    /**
     * The request ID of the failed stream.
     */
    requestId: number;

    /**
     * The stream tag of the failed stream.
     */
    streamTag: number;

    /**
     * Human-readable error description.
     */
    error: string;
  };
}

/**
 * Notification sent to initiate graceful shutdown.
 */
export interface ShutdownNotification {
  jsonrpc: "2.0";
  method: "$/shutdown";
}

/**
 * Notification sent to cancel an in-flight request.
 * 
 * The request SHOULD still be in-flight, but due to communication latency,
 * this notification MAY arrive after the request has already finished.
 */
export interface CancelNotification {
  jsonrpc: "2.0";
  method: "$/cancel";
  params: {
    /**
     * The ID of the request to cancel.
     * MUST correspond to the ID of a request previously issued.
     */
    requestId: number;

    /**
     * Optional reason for the cancellation.
     * MAY be logged or presented to the user.
     */
    reason?: string;
  };
}

/* ============================================================================
 * Composite Types
 * ============================================================================ */

/**
 * Union of all MCP-Flow specific notifications.
 */
export type McpFlowNotification =
  | StreamErrorNotification
  | ShutdownNotification
  | CancelNotification;
