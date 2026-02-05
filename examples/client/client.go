// Package main implements a simple MCP-Flow test client in Go.
//
// This client connects to an MCP-Flow server and demonstrates the protocol flow:
// 1. Establish WebTransport connection
// 2. Open control stream
// 3. Send initialize request
// 4. Call echo_joke tool
// 5. Display result
//
// Usage:
//
//	go run client.go [-addr localhost:4433] [-insecure]
package main

import (
	"context"
	"crypto/tls"
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"os"
	"time"

	"github.com/quic-go/quic-go/http3"
	"github.com/quic-go/webtransport-go"
)

const (
	mcpFlowVersion  = "0.1"
	protocolVersion = "2024-11-05"
)

// JSON-RPC types
type Request struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      int         `json:"id"`
	Method  string      `json:"method"`
	Params  interface{} `json:"params,omitempty"`
}

type Response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      int             `json:"id"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// Frame codec
func encodeFrame(req *Request) ([]byte, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	frame := make([]byte, 4+len(body))
	binary.BigEndian.PutUint32(frame[:4], uint32(len(body)))
	copy(frame[4:], body)
	return frame, nil
}

func decodeFrame(r io.Reader) (*Response, error) {
	lengthBuf := make([]byte, 4)
	if _, err := io.ReadFull(r, lengthBuf); err != nil {
		return nil, err
	}
	length := binary.BigEndian.Uint32(lengthBuf)

	body := make([]byte, length)
	if _, err := io.ReadFull(r, body); err != nil {
		return nil, err
	}

	var resp Response
	if err := json.Unmarshal(body, &resp); err != nil {
		return nil, err
	}
	return &resp, nil
}

func main() {
	addr := flag.String("addr", "localhost:4433", "Server address")
	insecure := flag.Bool("insecure", true, "Skip TLS verification (for self-signed certs)")
	flag.Parse()

	logger := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelInfo}))

	fmt.Println(`
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  MCP-Flow Test Client                                        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛`)

	// Create WebTransport dialer
	tlsConfig := &tls.Config{
		InsecureSkipVerify: *insecure,
		NextProtos:         []string{"h3"},
	}

	dialer := webtransport.Dialer{
		RoundTripper: &http3.RoundTripper{
			TLSClientConfig: tlsConfig,
		},
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Connect
	url := fmt.Sprintf("https://%s/mcp-flow", *addr)
	logger.Info("connecting", "url", url)

	_, session, err := dialer.Dial(ctx, url, nil)
	if err != nil {
		logger.Error("connection failed", "error", err)
		os.Exit(1)
	}
	defer session.CloseWithError(0, "done")

	logger.Info("connected")

	// Open control stream
	stream, err := session.OpenStreamSync(ctx)
	if err != nil {
		logger.Error("failed to open stream", "error", err)
		os.Exit(1)
	}
	defer stream.Close()

	logger.Info("control stream opened")

	// Helper to send request and receive response
	requestID := 0
	sendRequest := func(method string, params interface{}) (*Response, error) {
		requestID++
		req := &Request{
			JSONRPC: "2.0",
			ID:      requestID,
			Method:  method,
			Params:  params,
		}

		frame, err := encodeFrame(req)
		if err != nil {
			return nil, fmt.Errorf("encode: %w", err)
		}

		if _, err := stream.Write(frame); err != nil {
			return nil, fmt.Errorf("write: %w", err)
		}

		logger.Info("sent", "method", method, "id", requestID)

		resp, err := decodeFrame(stream)
		if err != nil {
			return nil, fmt.Errorf("decode: %w", err)
		}

		if resp.Error != nil {
			return nil, fmt.Errorf("rpc error %d: %s", resp.Error.Code, resp.Error.Message)
		}

		return resp, nil
	}

	// 1. Initialize
	fmt.Println("\n─── Step 1: Initialize ───")
	initParams := map[string]interface{}{
		"protocolVersion": protocolVersion,
		"capabilities":    map[string]interface{}{},
		"clientInfo": map[string]interface{}{
			"name":    "mcp-flow-test-client",
			"version": "1.0.0",
		},
		"transport": map[string]interface{}{
			"type":      "mcp-flow",
			"version":   mcpFlowVersion,
			"encodings": []string{"json"},
		},
	}

	resp, err := sendRequest("initialize", initParams)
	if err != nil {
		logger.Error("initialize failed", "error", err)
		os.Exit(1)
	}

	var initResult map[string]interface{}
	json.Unmarshal(resp.Result, &initResult)
	fmt.Printf("✓ Server: %v\n", initResult["serverInfo"])

	// Send initialized notification (no response expected)
	notifyFrame, _ := encodeFrame(&Request{JSONRPC: "2.0", Method: "notifications/initialized"})
	stream.Write(notifyFrame)

	// 2. List tools
	fmt.Println("\n─── Step 2: List Tools ───")
	resp, err = sendRequest("tools/list", map[string]interface{}{})
	if err != nil {
		logger.Error("tools/list failed", "error", err)
		os.Exit(1)
	}

	var toolsResult map[string]interface{}
	json.Unmarshal(resp.Result, &toolsResult)
	tools := toolsResult["tools"].([]interface{})
	for _, t := range tools {
		tool := t.(map[string]interface{})
		fmt.Printf("✓ Tool: %s - %s\n", tool["name"], tool["description"])
	}

	// 3. Call echo_joke
	fmt.Println("\n─── Step 3: Call echo_joke ───")
	resp, err = sendRequest("tools/call", map[string]interface{}{
		"name":      "echo_joke",
		"arguments": map[string]interface{}{},
	})
	if err != nil {
		logger.Error("tools/call failed", "error", err)
		os.Exit(1)
	}

	var callResult map[string]interface{}
	json.Unmarshal(resp.Result, &callResult)
	content := callResult["content"].([]interface{})
	for _, c := range content {
		item := c.(map[string]interface{})
		fmt.Printf("\n🎭 %s\n", item["text"])
	}

	// 4. Ping
	fmt.Println("\n─── Step 4: Ping ───")
	_, err = sendRequest("ping", nil)
	if err != nil {
		logger.Error("ping failed", "error", err)
		os.Exit(1)
	}
	fmt.Println("✓ Pong!")

	fmt.Println("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
	fmt.Println("✓ All tests passed! MCP-Flow protocol working correctly.")
	fmt.Println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
}
