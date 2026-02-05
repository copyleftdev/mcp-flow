# Contributing to MCP-Flow

Thank you for your interest in contributing to MCP-Flow!

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Run `make build` to verify everything works

## Development

```bash
# Generate TLS certificates
make certs

# Build all examples
make build

# Run tests
make test

# Run individual servers
make run-go
make run-py
make run-ts
```

## Pull Request Process

1. **One feature per PR** — Keep changes focused
2. **Update documentation** — If you change behavior, update the docs
3. **Add tests** — New features should include tests
4. **Follow existing style** — Match the code style of each language

## Code Style

### Go
- Run `gofmt` before committing
- Use `slog` for structured logging
- Prefer explicit error handling

### Python
- Follow PEP 8
- Use type hints
- Use `dataclasses` where appropriate

### TypeScript
- Use strict mode
- Prefer `readonly` and `const`
- Use explicit return types

## Spec Changes

Changes to the protocol specification (`schema/`) require:

1. Update both `schema.ts` and `schema.json`
2. Update `IMPLEMENTATION.md` with wire format examples
3. Update at least one reference implementation
4. Add migration notes if breaking

## Questions?

Open an issue for discussion before starting large changes.
