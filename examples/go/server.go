// Package main implements an MCP-Flow reference server in Go.
//
// This is a production-quality echo server demonstrating the MCP-Flow protocol.
//
// Usage:
//
//	go run server.go -cert cert.pem -key key.pem [-addr :4433]
package main

import (
	"context"
	"crypto/rand"
	"crypto/tls"
	"encoding/binary"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"math/big"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/quic-go/quic-go/http3"
	"github.com/quic-go/webtransport-go"
)

// =============================================================================
// Constants
// =============================================================================

const (
	mcpFlowVersion       = "0.1"
	protocolVersion      = "2024-11-05"
	serverName           = "mcp-flow-echo-go"
	serverVersion        = "1.0.0"
	maxFrameSize         = 16 * 1024 * 1024 // 16MB
	maxConcurrentStreams = 100
)

// jokes contains programming humor for the echo_joke tool.
var jokes = [...]string{
	"There are only 10 types of people: those who understand binary and those who don't.",
	"A SQL query walks into a bar, walks up to two tables and asks, 'Can I join you?'",
	"Why do programmers prefer dark mode? Because light attracts bugs.",
	"It works on my machine. ¯\\_(ツ)_/¯",
	"// TODO: fix this later — commit date: 3 years ago",
	"There's no place like 127.0.0.1",
	"I would tell you a UDP joke, but you might not get it.",
	"To understand recursion, you must first understand recursion.",
	"The best thing about a Boolean is that even if you're wrong, you're only off by a bit.",
	"Why do Java developers wear glasses? Because they can't C#.",
	"!false — It's funny because it's true.",
	"A programmer's wife says: 'Buy bread. If they have eggs, buy a dozen.' He returns with 12 loaves.",
	"There are only two hard things in CS: cache invalidation, naming things, and off-by-one errors.",
}

// =============================================================================
// JSON-RPC Types
// =============================================================================

// RequestID represents a JSON-RPC request identifier.
type RequestID interface{}

// RPCRequest represents an incoming JSON-RPC request or notification.
type RPCRequest struct {
	JSONRPC string                 `json:"jsonrpc"`
	ID      RequestID              `json:"id,omitempty"`
	Method  string                 `json:"method"`
	Params  map[string]interface{} `json:"params,omitempty"`
}

// RPCResponse represents an outgoing JSON-RPC response.
type RPCResponse struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      RequestID   `json:"id,omitempty"`
	Result  interface{} `json:"result,omitempty"`
	Error   *RPCError   `json:"error,omitempty"`
}

// RPCError represents a JSON-RPC error object.
type RPCError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// JSON-RPC error codes.
const (
	ErrCodeParseError     = -32700
	ErrCodeInvalidRequest = -32600
	ErrCodeMethodNotFound = -32601
	ErrCodeInvalidParams  = -32602
	ErrCodeInternalError  = -32603
)

// =============================================================================
// Frame Codec
// =============================================================================

// FrameCodec handles length-prefixed JSON frame encoding/decoding.
type FrameCodec struct {
	maxSize uint32
}

// NewFrameCodec creates a new codec with the specified maximum frame size.
func NewFrameCodec(maxSize uint32) *FrameCodec {
	return &FrameCodec{maxSize: maxSize}
}

// Encode serializes a value as a length-prefixed JSON frame.
func (c *FrameCodec) Encode(v interface{}) ([]byte, error) {
	body, err := json.Marshal(v)
	if err != nil {
		return nil, fmt.Errorf("marshal: %w", err)
	}

	if uint32(len(body)) > c.maxSize {
		return nil, fmt.Errorf("frame size %d exceeds maximum %d", len(body), c.maxSize)
	}

	frame := make([]byte, 4+len(body))
	binary.BigEndian.PutUint32(frame[:4], uint32(len(body)))
	copy(frame[4:], body)

	return frame, nil
}

// Decode reads a length-prefixed JSON frame from the reader.
func (c *FrameCodec) Decode(r io.Reader) (*RPCRequest, error) {
	lengthBuf := make([]byte, 4)
	if _, err := io.ReadFull(r, lengthBuf); err != nil {
		return nil, err
	}

	length := binary.BigEndian.Uint32(lengthBuf)
	if length > c.maxSize {
		return nil, fmt.Errorf("frame size %d exceeds maximum %d", length, c.maxSize)
	}

	body := make([]byte, length)
	if _, err := io.ReadFull(r, body); err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}

	var req RPCRequest
	if err := json.Unmarshal(body, &req); err != nil {
		return nil, fmt.Errorf("unmarshal: %w", err)
	}

	return &req, nil
}

// =============================================================================
// Tool Interface
// =============================================================================

// Tool defines the interface for MCP tools.
type Tool interface {
	Name() string
	Description() string
	InputSchema() map[string]interface{}
	Execute(args map[string]interface{}) (interface{}, error)
}

// =============================================================================
// Echo Joke Tool
// =============================================================================

type echoJokeTool struct{}

func (t *echoJokeTool) Name() string { return "echo_joke" }
func (t *echoJokeTool) Description() string {
	return "Returns a random programming joke. Guaranteed to pass a code review."
}
func (t *echoJokeTool) InputSchema() map[string]interface{} {
	return map[string]interface{}{
		"type":                 "object",
		"properties":           map[string]interface{}{},
		"additionalProperties": false,
	}
}

func (t *echoJokeTool) Execute(_ map[string]interface{}) (interface{}, error) {
	idx, err := rand.Int(rand.Reader, big.NewInt(int64(len(jokes))))
	if err != nil {
		return nil, err
	}

	joke := jokes[idx.Int64()]
	slog.Info("serving joke", "joke", joke)

	return map[string]interface{}{
		"content": []map[string]interface{}{
			{"type": "text", "text": joke},
		},
	}, nil
}

// =============================================================================
// RPC Handler
// =============================================================================

// Handler processes JSON-RPC requests for MCP-Flow.
type Handler struct {
	tools map[string]Tool
}

// NewHandler creates a new RPC handler with registered tools.
func NewHandler() *Handler {
	h := &Handler{
		tools: make(map[string]Tool),
	}

	jokeTool := &echoJokeTool{}
	h.tools[jokeTool.Name()] = jokeTool

	return h
}

// Handle processes a JSON-RPC request and returns a response.
// Returns nil for notifications (no response expected).
func (h *Handler) Handle(req *RPCRequest) *RPCResponse {
	switch req.Method {
	case "initialize":
		return h.handleInitialize(req)
	case "notifications/initialized":
		slog.Info("client initialized")
		return nil
	case "tools/list":
		return h.handleToolsList(req)
	case "tools/call":
		return h.handleToolsCall(req)
	case "ping":
		return &RPCResponse{JSONRPC: "2.0", ID: req.ID, Result: map[string]interface{}{}}
	case "$/shutdown":
		slog.Info("shutdown requested")
		return nil
	case "$/cancel":
		h.handleCancel(req)
		return nil
	default:
		if req.ID == nil {
			return nil // Unknown notification
		}
		return h.errorResponse(req.ID, ErrCodeMethodNotFound, "Method not found: "+req.Method)
	}
}

func (h *Handler) handleInitialize(req *RPCRequest) *RPCResponse {
	return &RPCResponse{
		JSONRPC: "2.0",
		ID:      req.ID,
		Result: map[string]interface{}{
			"protocolVersion": protocolVersion,
			"capabilities":    map[string]interface{}{"tools": map[string]interface{}{"listChanged": false}},
			"serverInfo":      map[string]interface{}{"name": serverName, "version": serverVersion},
			"transport": map[string]interface{}{
				"type":                 "mcp-flow",
				"version":              mcpFlowVersion,
				"encoding":             "json",
				"maxConcurrentStreams": maxConcurrentStreams,
				"datagramsSupported":   false,
			},
		},
	}
}

func (h *Handler) handleToolsList(req *RPCRequest) *RPCResponse {
	tools := make([]map[string]interface{}, 0, len(h.tools))
	for _, t := range h.tools {
		tools = append(tools, map[string]interface{}{
			"name":        t.Name(),
			"description": t.Description(),
			"inputSchema": t.InputSchema(),
		})
	}

	return &RPCResponse{
		JSONRPC: "2.0",
		ID:      req.ID,
		Result:  map[string]interface{}{"tools": tools},
	}
}

func (h *Handler) handleToolsCall(req *RPCRequest) *RPCResponse {
	toolName, _ := req.Params["name"].(string)
	args, _ := req.Params["arguments"].(map[string]interface{})
	if args == nil {
		args = make(map[string]interface{})
	}

	tool, ok := h.tools[toolName]
	if !ok {
		return &RPCResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result: map[string]interface{}{
				"content": []map[string]interface{}{{"type": "text", "text": "Unknown tool: " + toolName}},
				"isError": true,
			},
		}
	}

	result, err := tool.Execute(args)
	if err != nil {
		return &RPCResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result: map[string]interface{}{
				"content": []map[string]interface{}{{"type": "text", "text": "Tool error: " + err.Error()}},
				"isError": true,
			},
		}
	}

	return &RPCResponse{JSONRPC: "2.0", ID: req.ID, Result: result}
}

func (h *Handler) handleCancel(req *RPCRequest) {
	reqID := req.Params["requestId"]
	reason, _ := req.Params["reason"].(string)
	if reason == "" {
		reason = "no reason provided"
	}
	slog.Info("cancel requested", "requestId", reqID, "reason", reason)
}

func (h *Handler) errorResponse(id RequestID, code int, message string) *RPCResponse {
	return &RPCResponse{
		JSONRPC: "2.0",
		ID:      id,
		Error:   &RPCError{Code: code, Message: message},
	}
}

// =============================================================================
// Session Handler
// =============================================================================

// Session manages a single MCP-Flow WebTransport session.
type Session struct {
	codec   *FrameCodec
	handler *Handler
	logger  *slog.Logger
}

// NewSession creates a new session handler.
func NewSession(logger *slog.Logger) *Session {
	return &Session{
		codec:   NewFrameCodec(maxFrameSize),
		handler: NewHandler(),
		logger:  logger,
	}
}

// Run processes the WebTransport session until completion.
func (s *Session) Run(ctx context.Context, wt *webtransport.Session) error {
	stream, err := wt.AcceptStream(ctx)
	if err != nil {
		return fmt.Errorf("accept stream: %w", err)
	}
	defer stream.Close()

	s.logger.Info("control stream opened")

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		req, err := s.codec.Decode(stream)
		if err != nil {
			if errors.Is(err, io.EOF) {
				return nil
			}
			return fmt.Errorf("decode: %w", err)
		}

		s.logger.Debug("received", "method", req.Method, "id", req.ID)

		resp := s.handler.Handle(req)
		if resp == nil {
			continue
		}

		frame, err := s.codec.Encode(resp)
		if err != nil {
			s.logger.Error("encode failed", "error", err)
			continue
		}

		if _, err := stream.Write(frame); err != nil {
			return fmt.Errorf("write: %w", err)
		}

		s.logger.Debug("sent", "id", resp.ID, "hasError", resp.Error != nil)
	}
}

// =============================================================================
// Server
// =============================================================================

// Server is an MCP-Flow WebTransport server.
type Server struct {
	addr     string
	certFile string
	keyFile  string
	logger   *slog.Logger
}

// NewServer creates a new MCP-Flow server.
func NewServer(addr, certFile, keyFile string, logger *slog.Logger) *Server {
	return &Server{
		addr:     addr,
		certFile: certFile,
		keyFile:  keyFile,
		logger:   logger,
	}
}

// Run starts the server and blocks until shutdown.
func (s *Server) Run(ctx context.Context) error {
	cert, err := tls.LoadX509KeyPair(s.certFile, s.keyFile)
	if err != nil {
		return fmt.Errorf("load TLS cert: %w", err)
	}

	wtServer := &webtransport.Server{
		H3: http3.Server{
			Addr: s.addr,
			TLSConfig: &tls.Config{
				Certificates: []tls.Certificate{cert},
				MinVersion:   tls.VersionTLS13,
			},
		},
		CheckOrigin: func(r *http.Request) bool {
			origin := r.Header.Get("Origin")
			s.logger.Debug("origin check", "origin", origin)
			return true // Demo: allow all origins
		},
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/mcp-flow", func(w http.ResponseWriter, r *http.Request) {
		session, err := wtServer.Upgrade(w, r)
		if err != nil {
			s.logger.Error("upgrade failed", "error", err)
			http.Error(w, "WebTransport upgrade failed", http.StatusBadRequest)
			return
		}

		sessionLogger := s.logger.With("remote", r.RemoteAddr)
		sessionLogger.Info("session established")

		sess := NewSession(sessionLogger)
		go func() {
			if err := sess.Run(ctx, session); err != nil && !errors.Is(err, context.Canceled) {
				sessionLogger.Error("session error", "error", err)
			}
			sessionLogger.Info("session closed")
		}()
	})

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"name":     serverName,
			"version":  serverVersion,
			"protocol": "mcp-flow/" + mcpFlowVersion,
			"status":   "ready",
		})
	})

	wtServer.H3.Handler = mux

	s.logger.Info("server starting",
		"addr", s.addr,
		"protocol", "mcp-flow/"+mcpFlowVersion,
	)

	fmt.Fprintf(os.Stderr, `
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  MCP-Flow Echo Server — Go/quic-go                           ┃
┃                                                              ┃
┃  Endpoint:  https://localhost%s/mcp-flow
┃  Tool:      echo_joke                                        ┃
┃  Protocol:  MCP-Flow %s                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
`, s.addr, mcpFlowVersion)

	errCh := make(chan error, 1)
	go func() {
		errCh <- wtServer.ListenAndServe()
	}()

	select {
	case <-ctx.Done():
		s.logger.Info("shutting down")
		return wtServer.Close()
	case err := <-errCh:
		return err
	}
}

// =============================================================================
// Main
// =============================================================================

func main() {
	addr := flag.String("addr", ":4433", "Address to listen on")
	certFile := flag.String("cert", "cert.pem", "TLS certificate file")
	keyFile := flag.String("key", "key.pem", "TLS private key file")
	verbose := flag.Bool("v", false, "Enable debug logging")
	flag.Parse()

	// Configure logging
	logLevel := slog.LevelInfo
	if *verbose {
		logLevel = slog.LevelDebug
	}

	logger := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
		Level: logLevel,
	}))

	// Validate certificate files exist
	if _, err := os.Stat(*certFile); os.IsNotExist(err) {
		logger.Error("certificate file not found", "path", *certFile)
		fmt.Fprintln(os.Stderr, "\nGenerate certificates with:")
		fmt.Fprintln(os.Stderr, "  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj \"/CN=localhost\"")
		os.Exit(1)
	}
	if _, err := os.Stat(*keyFile); os.IsNotExist(err) {
		logger.Error("key file not found", "path", *keyFile)
		os.Exit(1)
	}

	// Setup graceful shutdown
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	server := NewServer(*addr, *certFile, *keyFile, logger)
	if err := server.Run(ctx); err != nil && !errors.Is(err, context.Canceled) {
		logger.Error("server error", "error", err)
		os.Exit(1)
	}
}
