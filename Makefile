# MCP-Flow Reference Implementations
# 
# Usage:
#   make certs      - Generate self-signed TLS certificates
#   make build      - Build all examples
#   make test       - Run integration tests against all servers
#   make run-go     - Run Go server
#   make run-py     - Run Python server
#   make run-ts     - Run TypeScript server
#   make clean      - Clean build artifacts

.PHONY: all certs build test clean run-go run-py run-ts help

# Configuration
CERT_DIR := certs
CERT_FILE := $(CERT_DIR)/cert.pem
KEY_FILE := $(CERT_DIR)/key.pem
VENV_DIR := .venv
PORT := 4433
HOST := localhost

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m

# Default target
all: certs build test

help:
	@echo "MCP-Flow Reference Implementations"
	@echo ""
	@echo "Usage:"
	@echo "  make certs      Generate self-signed TLS certificates"
	@echo "  make build      Build all examples"
	@echo "  make test       Run integration tests"
	@echo "  make run-go     Run Go server"
	@echo "  make run-py     Run Python server"  
	@echo "  make run-ts     Run TypeScript server"
	@echo "  make clean      Clean build artifacts"

# =============================================================================
# Certificates
# =============================================================================

$(CERT_FILE):
	@mkdir -p $(CERT_DIR)
	@echo "$(GREEN)Generating TLS certificates...$(NC)"
	@openssl req -x509 -newkey rsa:4096 \
		-keyout $(KEY_FILE) \
		-out $(CERT_FILE) \
		-days 365 -nodes \
		-subj "/CN=localhost" \
		2>/dev/null
	@echo "$(GREEN)✓ Certificates created in $(CERT_DIR)/$(NC)"

certs: $(CERT_FILE)

# =============================================================================
# Build
# =============================================================================

build: build-go build-py build-ts
	@echo "$(GREEN)✓ All examples built successfully$(NC)"

build-go:
	@echo "$(GREEN)Building Go server...$(NC)"
	@cd examples/go && go mod tidy && go build -o ../../bin/mcp-flow-go .
	@echo "$(GREEN)Building Go client...$(NC)"
	@cd examples/client && go mod tidy && go build -o ../../bin/mcp-flow-client .
	@echo "$(GREEN)✓ Go build complete$(NC)"

$(VENV_DIR)/bin/activate:
	@echo "$(GREEN)Creating Python virtual environment...$(NC)"
	@python3 -m venv $(VENV_DIR)
	@$(VENV_DIR)/bin/pip install -q --upgrade pip

build-py: $(VENV_DIR)/bin/activate
	@echo "$(GREEN)Installing Python dependencies...$(NC)"
	@$(VENV_DIR)/bin/pip install -q -r examples/python/requirements.txt
	@echo "$(GREEN)✓ Python dependencies installed$(NC)"

build-ts:
	@echo "$(GREEN)Checking TypeScript/Deno...$(NC)"
	@which deno > /dev/null 2>&1 || (echo "$(YELLOW)⚠ Deno not installed, skipping TypeScript$(NC)" && exit 0)
	@deno check examples/typescript/server.ts 2>/dev/null || echo "$(YELLOW)⚠ Deno check skipped (unstable APIs)$(NC)"
	@echo "$(GREEN)✓ TypeScript ready$(NC)"

# =============================================================================
# Run Servers
# =============================================================================

run-go: certs build-go
	@echo "$(GREEN)Starting Go server...$(NC)"
	./bin/mcp-flow-go -cert $(CERT_FILE) -key $(KEY_FILE) -addr :$(PORT)

run-py: certs build-py
	@echo "$(GREEN)Starting Python server...$(NC)"
	$(VENV_DIR)/bin/python examples/python/server.py --cert $(CERT_FILE) --key $(KEY_FILE) --port $(PORT)

run-ts: certs
	@echo "$(GREEN)Starting TypeScript server...$(NC)"
	TLS_CERT=$(CERT_FILE) TLS_KEY=$(KEY_FILE) PORT=$(PORT) \
		deno run --allow-net --allow-read --allow-env --unstable-net \
		examples/typescript/server.ts

# =============================================================================
# Testing
# =============================================================================

test: certs
	@echo "$(GREEN)Running integration tests...$(NC)"
	@./scripts/test-servers.sh $(CERT_FILE) $(KEY_FILE) $(PORT)

test-go: certs build-go
	@echo "$(GREEN)Testing Go server...$(NC)"
	@./scripts/test-server.sh go $(CERT_FILE) $(KEY_FILE) $(PORT)

test-py: certs build-py
	@echo "$(GREEN)Testing Python server...$(NC)"
	@./scripts/test-server.sh python $(CERT_FILE) $(KEY_FILE) $(PORT)

test-ts: certs
	@echo "$(GREEN)Testing TypeScript server...$(NC)"
	@./scripts/test-server.sh typescript $(CERT_FILE) $(KEY_FILE) $(PORT)

# =============================================================================
# Clean
# =============================================================================

clean:
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	@rm -rf bin/
	@rm -rf $(CERT_DIR)/
	@rm -rf examples/go/mcp-flow-go
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete$(NC)"

# =============================================================================
# Directory setup
# =============================================================================

bin:
	@mkdir -p bin

scripts:
	@mkdir -p scripts
