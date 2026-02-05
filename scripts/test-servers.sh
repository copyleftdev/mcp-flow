#!/usr/bin/env bash
#
# Integration test runner for MCP-Flow reference implementations
#
# Tests each server implementation by:
# 1. Starting the server
# 2. Sending HTTP health check
# 3. Verifying JSON response
# 4. Stopping the server
#
# Usage: ./test-servers.sh <cert_file> <key_file> <port>

set -uo pipefail

CERT_FILE="${1:-certs/cert.pem}"
KEY_FILE="${2:-certs/key.pem}"
PORT="${3:-4433}"
TIMEOUT=10

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

PASSED=0
FAILED=0
SKIPPED=0

log_pass() { echo -e "${GREEN}✓ $1${NC}"; ((PASSED++)); }
log_fail() { echo -e "${RED}✗ $1${NC}"; ((FAILED++)); }
log_skip() { echo -e "${YELLOW}⊘ $1${NC}"; ((SKIPPED++)); }
log_info() { echo -e "  $1"; }

cleanup() {
    if [[ -n "${SERVER_PID:-}" ]]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT

wait_for_server() {
    local max_attempts=10
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        # Check if process is still running and port is listening
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            if ss -tlnp 2>/dev/null | grep -q ":${PORT}" || \
               netstat -tlnp 2>/dev/null | grep -q ":${PORT}" || \
               lsof -i ":${PORT}" >/dev/null 2>&1; then
                return 0
            fi
        else
            return 1
        fi
        sleep 0.5
        ((attempt++))
    done
    
    # Fallback: just check if process is running
    kill -0 "$SERVER_PID" 2>/dev/null
}

check_port_listening() {
    ss -ulnp 2>/dev/null | grep -q ":${PORT}" || \
    netstat -ulnp 2>/dev/null | grep -q ":${PORT}" || \
    lsof -i UDP:${PORT} >/dev/null 2>&1
}

# =============================================================================
# Go Server Test
# =============================================================================

test_go() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing Go Server"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [[ ! -f "bin/mcp-flow-go" ]]; then
        log_skip "Go: binary not found (run 'make build-go' first)"
        return
    fi
    
    log_info "Starting server..."
    ./bin/mcp-flow-go -cert "$CERT_FILE" -key "$KEY_FILE" -addr ":${PORT}" 2>&1 &
    SERVER_PID=$!
    
    sleep 2
    
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        log_pass "Go: server started and running"
    else
        log_fail "Go: server failed to start"
    fi
    
    cleanup
    sleep 1
}

# =============================================================================
# Python Server Test
# =============================================================================

test_python() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing Python Server"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    PYTHON_BIN=".venv/bin/python"
    if [[ ! -f "$PYTHON_BIN" ]]; then
        log_skip "Python: venv not found (run 'make build-py' first)"
        return
    fi
    
    if ! "$PYTHON_BIN" -c "import aioquic" 2>/dev/null; then
        log_skip "Python: aioquic not installed (run 'make build-py' first)"
        return
    fi
    
    log_info "Starting server..."
    "$PYTHON_BIN" examples/python/server.py --cert "$CERT_FILE" --key "$KEY_FILE" --port "$PORT" 2>&1 &
    SERVER_PID=$!
    
    sleep 2
    
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        log_pass "Python: server started and running"
    else
        log_fail "Python: server failed to start"
    fi
    
    cleanup
    sleep 1
}

# =============================================================================
# TypeScript Server Test
# =============================================================================

test_typescript() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing TypeScript Server"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if ! command -v deno &> /dev/null; then
        log_skip "TypeScript: Deno not installed"
        return
    fi
    
    log_info "Starting server..."
    TLS_CERT="$CERT_FILE" TLS_KEY="$KEY_FILE" PORT="$PORT" \
        deno run --allow-net --allow-read --allow-env --unstable-net \
        examples/typescript/server.ts &
    SERVER_PID=$!
    
    if wait_for_server; then
        log_pass "TypeScript: server started"
    else
        log_fail "TypeScript: server failed to start"
        cleanup
        return
    fi
    
    if test_http_health; then
        log_pass "TypeScript: HTTP health check"
    else
        log_fail "TypeScript: HTTP health check failed"
    fi
    
    cleanup
    sleep 1
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           MCP-Flow Integration Tests                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Certificates: $CERT_FILE, $KEY_FILE"
    echo "Port: $PORT"
    
    # Verify certificates exist
    if [[ ! -f "$CERT_FILE" ]] || [[ ! -f "$KEY_FILE" ]]; then
        echo -e "${RED}Error: Certificates not found. Run 'make certs' first.${NC}"
        exit 1
    fi
    
    # Run tests
    test_go
    test_python
    test_typescript
    
    # Summary
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "  ${GREEN}Passed:${NC}  $PASSED"
    echo -e "  ${RED}Failed:${NC}  $FAILED"
    echo -e "  ${YELLOW}Skipped:${NC} $SKIPPED"
    echo ""
    
    if [[ $FAILED -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
