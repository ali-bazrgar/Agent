# LLM-Driven Tool Architecture

## Decision

SuperAgent does not use language-specific keyword rules as its primary intent router. The model is the semantic decision-maker. Python provides capabilities, schemas, validation, permissions, execution, and persistence.

## Runtime contract

```text
User message
  -> Context Engine
  -> LLM + tool schemas
  -> model-selected tool call (or direct answer)
  -> ToolExecutor
  -> tool observation
  -> LLM
  -> final answer
```

The loop is bounded. Tool arguments are validated by the tool implementation and execution is subject to the existing executor limits and timeouts.

## Memory

Memory is exposed as capabilities:

- `memory.write`
- `memory.search`

The model decides whether either capability is relevant. There are no hard-coded Persian/English trigger phrases in this path.

For a request such as `این اطلاعات را نگه دار: من پایتون را دوست دارم`, the intended model action is a `memory.write` call whose `content` is the information itself. The system does not depend on matching `نگه دار`, `ذخیره کن`, `remember`, or equivalent phrases.

## Deterministic responsibilities

The model must not control security-sensitive behavior. The runtime remains responsible for:

- tool registry and schemas
- argument validation
- permissions and policy
- timeouts and call limits
- database transactions
- error reporting
- secret scrubbing
- persistence confirmation

An assistant response may claim that a memory was saved only after the tool returns a successful persistence result.

## Provider compatibility

The provider contract now supports OpenAI-compatible tool schemas and normalized tool calls. The llama.cpp provider forwards `tools` and `tool_choice` and normalizes returned tool calls. `AgenticLLMProvider` supplies the bounded execution loop independently of the concrete model provider.

If a local model does not support native tool calling, it must not silently be treated as tool-capable. A future compatibility adapter may implement structured-output tool selection, but that adapter must preserve the same tool contract and validation boundary.
