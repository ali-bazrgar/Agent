# Phase 7: Tool System Specification

## Overview
The SuperAgent Tool System provides a provider-independent, secure, bounded, and deterministic execution layer that allows agents to invoke external capabilities (such as calculators, time queries, web search, and webpage fetching) without coupling business logic to specific third-party client SDKs or HTTP libraries.

## Architecture
- **Tool Domain Models (`src/superagent/tools/models.py`)**: Defines `ToolDefinition`, `ToolParameter`, `ToolCall`, `ToolExecutionContext`, `ToolExecutionStatus`, and `ToolResult`.
- **Tool Ports (`src/superagent/tools/ports.py`)**: Abstract interfaces (`ToolProvider`, `ToolRegistryPort`, `ToolExecutorPort`) enforcing Hexagonal Architecture.
- **Tool Registry (`src/superagent/tools/registry.py`)**: In-memory, case-insensitive, deterministic registry managing tool registration, lookup, and listing.
- **Tool Executor (`src/superagent/tools/executor.py`)**: Manages concurrent thread-pool execution with strict timeout enforcement, error isolation, secret scrubbing (redacting API keys and tokens), and execution duration logging.

## Core Tools
1. **Calculator Tool (`CalculatorTool`)**: Safe mathematical evaluation using Python's `ast` module (supporting arithmetic operators `+`, `-`, `*`, `/`, `%`, `**`, unary operators, and parentheses) while rejecting arbitrary code execution and malicious expressions.
2. **Current Time Tool (`TimeTool`)**: Returns current date, time, and UTC offset for any requested IANA timezone using Python's `zoneinfo`.
3. **Web Search Tool (`WebSearchTool`)**: Interfaces through `WebResearchProvider` to execute web searches and return normalized results.
4. **Web Fetch Tool (`WebFetchTool`)**: Fetches webpage text with robust **SSRF protection** (rejecting localhost, private IP ranges, loopback, and non-http/https schemes), content-type validation, payload size limits (1MB max), and HTML sanitization.

## Security & Safety
- **Secret Scrubbing**: Automatic regex-based redaction of API keys, Bearer tokens, and secrets from tool outputs and error logs.
- **SSRF Prevention**: IP address resolution check preventing requests to internal or private network interfaces.
- **Timeout Bounding**: Every tool call respects a strict execution timeout.
