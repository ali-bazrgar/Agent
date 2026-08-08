# Phase 9: Security Hardening Specification

## Security Protections
- **SSRF Prevention**: Strict URL validation blocking access to loopback (127.0.0.1, localhost), private IPv4/IPv6 blocks, and cloud metadata services.
- **Calculator Sandbox**: AST-safe expression evaluation preventing arbitrary code execution and injection attacks.
- **Payload Limits**: Maximum size validation on web fetches and tool responses (1MB limit).
- **Error Sanitization**: Production API responses omit internal stack traces and present standardized error envelopes.
