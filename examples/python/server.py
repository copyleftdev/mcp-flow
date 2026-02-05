#!/usr/bin/env python3
"""
MCP-Flow Reference Implementation — Python/aioquic

Production-quality echo server demonstrating the MCP-Flow protocol.

Usage:
    python server.py --cert cert.pem --key key.pem [--host 0.0.0.0] [--port 4433]

Requirements:
    pip install aioquic>=0.9.25
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import secrets
import struct
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, Final, Protocol, TypeAlias

from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import H3Event, HeadersReceived, WebTransportStreamDataReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ProtocolNegotiated, QuicEvent

# =============================================================================
# Type Aliases
# =============================================================================

RequestId: TypeAlias = str | int
JsonObject: TypeAlias = dict[str, Any]

# =============================================================================
# Constants
# =============================================================================

MCP_FLOW_VERSION: Final[str] = "0.1"
PROTOCOL_VERSION: Final[str] = "2024-11-05"
MAX_FRAME_SIZE: Final[int] = 16 * 1024 * 1024  # 16MB
MAX_CONCURRENT_STREAMS: Final[int] = 100

SERVER_INFO: Final[JsonObject] = {
    "name": "mcp-flow-echo-py",
    "version": "1.0.0",
}

JOKES: Final[tuple[str, ...]] = (
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
    "A programmer's wife says: 'Buy bread. If they have eggs, buy a dozen.' He returns with 12 loaves.",
    "There are only two hard things in CS: cache invalidation, naming things, and off-by-one errors.",
)

# =============================================================================
# Logging
# =============================================================================

logger = logging.getLogger("mcp-flow")


# =============================================================================
# JSON-RPC Error Codes
# =============================================================================


class JsonRpcErrorCode(IntEnum):
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # MCP-Flow specific
    STREAM_LIMIT_EXCEEDED = -32000
    INVALID_STREAM_REF = -32001
    STREAM_INJECTION = -32002
    ENCODING_MISMATCH = -32003


# =============================================================================
# Frame Codec
# =============================================================================


class FrameCodecError(Exception):
    """Raised when frame encoding/decoding fails."""


@dataclass(slots=True)
class FrameCodec:
    """Length-prefixed JSON frame codec for MCP-Flow Control Stream."""

    _buffer: bytearray = field(default_factory=bytearray)

    def encode(self, message: JsonObject) -> bytes:
        """Encode a message as a length-prefixed JSON frame."""
        body = json.dumps(message, separators=(",", ":")).encode("utf-8")

        if len(body) > MAX_FRAME_SIZE:
            raise FrameCodecError(f"Frame exceeds maximum size: {len(body)} > {MAX_FRAME_SIZE}")

        return struct.pack(">I", len(body)) + body

    def feed(self, data: bytes) -> None:
        """Feed incoming bytes into the decode buffer."""
        self._buffer.extend(data)

    def decode_next(self) -> JsonObject | None:
        """
        Attempt to decode the next complete frame from the buffer.
        Returns None if insufficient data is available.
        """
        if len(self._buffer) < 4:
            return None

        length = struct.unpack(">I", self._buffer[:4])[0]

        if length > MAX_FRAME_SIZE:
            raise FrameCodecError(f"Frame exceeds maximum size: {length} > {MAX_FRAME_SIZE}")

        if len(self._buffer) < 4 + length:
            return None

        body = self._buffer[4 : 4 + length]
        del self._buffer[: 4 + length]

        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise FrameCodecError(f"Invalid JSON in frame: {e}") from e


# =============================================================================
# Tool Registry
# =============================================================================


class Tool(Protocol):
    """Protocol for MCP tools."""

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def input_schema(self) -> JsonObject: ...

    def execute(self, arguments: JsonObject) -> JsonObject: ...


@dataclass(frozen=True, slots=True)
class EchoJokeTool:
    """Returns a random programming joke."""

    name: str = "echo_joke"
    description: str = "Returns a random programming joke. Guaranteed to mass a code review."
    input_schema: JsonObject = field(
        default_factory=lambda: {"type": "object", "properties": {}, "additionalProperties": False}
    )

    def execute(self, arguments: JsonObject) -> JsonObject:
        joke = secrets.choice(JOKES)
        logger.info("→ %s", joke)
        return {"content": [{"type": "text", "text": joke}]}


# =============================================================================
# RPC Handler
# =============================================================================


@dataclass(slots=True)
class RpcHandler:
    """Handles JSON-RPC 2.0 messages for MCP-Flow."""

    tools: dict[str, Tool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        joke_tool = EchoJokeTool()
        self.tools[joke_tool.name] = joke_tool

    def handle(self, message: JsonObject) -> JsonObject | None:
        """
        Process a JSON-RPC message and return a response.
        Returns None for notifications (no response expected).
        """
        method = message.get("method", "")
        request_id = message.get("id")
        params = message.get("params", {})

        # Dispatch by method
        handler = getattr(self, f"_handle_{method.replace('/', '_').replace('$', '_')}", None)

        if handler is not None:
            return handler(request_id, params)

        # Unknown method
        if request_id is not None:
            return self._error_response(request_id, JsonRpcErrorCode.METHOD_NOT_FOUND, f"Method not found: {method}")

        return None

    def _handle_initialize(self, request_id: RequestId, params: JsonObject) -> JsonObject:
        """Handle initialize request."""
        client_transport = params.get("transport", {})
        requested_encodings = client_transport.get("encodings", ["json"])

        # Select encoding (currently only JSON supported)
        selected_encoding = "json" if "json" in requested_encodings else "json"

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "transport": {
                    "type": "mcp-flow",
                    "version": MCP_FLOW_VERSION,
                    "encoding": selected_encoding,
                    "maxConcurrentStreams": MAX_CONCURRENT_STREAMS,
                    "datagramsSupported": False,
                },
            },
        }

    def _handle_notifications_initialized(self, request_id: RequestId | None, params: JsonObject) -> None:
        """Handle initialized notification."""
        logger.info("✓ Client initialized")
        return None

    def _handle_tools_list(self, request_id: RequestId, params: JsonObject) -> JsonObject:
        """Handle tools/list request."""
        tools_list = [
            {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
            for t in self.tools.values()
        ]
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools_list}}

    def _handle_tools_call(self, request_id: RequestId, params: JsonObject) -> JsonObject:
        """Handle tools/call request."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        tool = self.tools.get(tool_name)
        if tool is None:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True},
            }

        try:
            result = tool.execute(arguments)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as e:
            logger.exception("Tool execution failed")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": f"Tool error: {e}"}], "isError": True},
            }

    def _handle_ping(self, request_id: RequestId, params: JsonObject) -> JsonObject:
        """Handle ping request."""
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    def _handle___shutdown(self, request_id: RequestId | None, params: JsonObject) -> None:
        """Handle $/shutdown notification."""
        logger.info("⏻ Shutdown requested")
        return None

    def _handle___cancel(self, request_id: RequestId | None, params: JsonObject) -> None:
        """Handle $/cancel notification."""
        cancel_id = params.get("requestId")
        reason = params.get("reason", "no reason provided")
        logger.info("⊘ Cancel requested for %s: %s", cancel_id, reason)
        return None

    @staticmethod
    def _error_response(request_id: RequestId, code: JsonRpcErrorCode, message: str) -> JsonObject:
        """Create a JSON-RPC error response."""
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


# =============================================================================
# WebTransport Protocol Handler
# =============================================================================


class McpFlowProtocol(QuicConnectionProtocol):
    """WebTransport server protocol implementing MCP-Flow."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._http: H3Connection | None = None
        self._session_id: int | None = None
        self._control_stream_id: int | None = None
        self._codec = FrameCodec()
        self._handler = RpcHandler()

    def quic_event_received(self, event: QuicEvent) -> None:
        """Handle QUIC events."""
        if isinstance(event, ProtocolNegotiated):
            self._http = H3Connection(self._quic, enable_webtransport=True)

        if self._http is not None:
            for h3_event in self._http.handle_event(event):
                self._handle_h3_event(h3_event)

    def _handle_h3_event(self, event: H3Event) -> None:
        """Handle HTTP/3 events."""
        if isinstance(event, HeadersReceived):
            self._handle_headers(event)
        elif isinstance(event, WebTransportStreamDataReceived):
            self._handle_stream_data(event)

    def _handle_headers(self, event: HeadersReceived) -> None:
        """Handle incoming HTTP headers (WebTransport upgrade)."""
        headers = dict(event.headers)

        if headers.get(b":method") == b"CONNECT" and headers.get(b":protocol") == b"webtransport":
            self._session_id = event.stream_id
            logger.info("WebTransport session established (stream %d)", self._session_id)

            self._http.send_headers(stream_id=event.stream_id, headers=[(b":status", b"200")])
            self.transmit()

    def _handle_stream_data(self, event: WebTransportStreamDataReceived) -> None:
        """Handle incoming stream data."""
        # First stream becomes the control stream
        if self._control_stream_id is None:
            self._control_stream_id = event.stream_id
            logger.info("Control stream opened (stream %d)", self._control_stream_id)

        if event.stream_id != self._control_stream_id:
            # Execution streams would be handled here
            return

        self._process_control_data(event.data, event.stream_ended)

    def _process_control_data(self, data: bytes, stream_ended: bool) -> None:
        """Process incoming control stream data."""
        self._codec.feed(data)

        while True:
            try:
                message = self._codec.decode_next()
            except FrameCodecError as e:
                logger.error("Frame decode error: %s", e)
                self._send_error(None, JsonRpcErrorCode.PARSE_ERROR, str(e))
                break

            if message is None:
                break

            logger.debug("← %s", json.dumps(message)[:80])

            response = self._handler.handle(message)

            if response is not None:
                self._send_response(response)

        if stream_ended:
            logger.info("Control stream ended")

    def _send_response(self, response: JsonObject) -> None:
        """Send a JSON-RPC response on the control stream."""
        if self._control_stream_id is None or self._http is None:
            return

        frame = self._codec.encode(response)
        self._http.send_data(stream_id=self._control_stream_id, data=frame, end_stream=False)
        self.transmit()
        logger.debug("→ %s", json.dumps(response)[:80])

    def _send_error(self, request_id: RequestId | None, code: JsonRpcErrorCode, message: str) -> None:
        """Send a JSON-RPC error response."""
        response = {"jsonrpc": "2.0", "id": request_id or 0, "error": {"code": code, "message": message}}
        self._send_response(response)


# =============================================================================
# Server Entry Point
# =============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP-Flow Echo Server — Python/aioquic",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=4433, help="Port to bind")
    parser.add_argument("--cert", required=True, type=Path, help="TLS certificate file")
    parser.add_argument("--key", required=True, type=Path, help="TLS private key file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    return parser.parse_args()


async def run_server(args: argparse.Namespace) -> None:
    """Run the MCP-Flow server."""
    # Validate certificate files
    if not args.cert.exists():
        logger.error("Certificate file not found: %s", args.cert)
        sys.exit(1)
    if not args.key.exists():
        logger.error("Key file not found: %s", args.key)
        sys.exit(1)

    # Configure QUIC
    config = QuicConfiguration(
        alpn_protocols=H3_ALPN,
        is_client=False,
        max_datagram_frame_size=65536,
    )
    config.load_cert_chain(str(args.cert), str(args.key))

    logger.info(
        """
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  MCP-Flow Echo Server — Python/aioquic                       ┃
┃                                                              ┃
┃  Endpoint:  https://%s:%d/mcp-flow
┃  Tool:      echo_joke                                        ┃
┃  Protocol:  MCP-Flow %s                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
""",
        args.host,
        args.port,
        MCP_FLOW_VERSION,
    )

    await serve(
        host=args.host,
        port=args.port,
        configuration=config,
        create_protocol=McpFlowProtocol,
    )

    # Run forever
    await asyncio.Event().wait()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        asyncio.run(run_server(args))
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
