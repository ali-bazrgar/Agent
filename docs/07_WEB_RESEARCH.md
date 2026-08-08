# Web Research Architecture

## Web research as a tool subsystem

Web research is treated as a separate provider/subsystem rather than as a direct extension of the LLM. It is responsible for finding evidence, extracting content, and returning structured results that can be evaluated before use.

## Responsibilities

- search for relevant URLs or web results
- fetch and normalize pages
- extract relevant content
- identify claims and source metadata
- preserve timestamps and citation information
- return structured evidence for later processing

## Evidence model

The subsystem must distinguish:

- raw web content
- extracted evidence
- claims
- source metadata
- timestamps
- citations
- confidence

## Storage policy

Web evidence should not automatically become permanent knowledge. It should be stored as evidence first and then promoted into durable knowledge only when the user or an explicit policy workflow requests that behavior.

## Security constraints

Web access must be governed by:

- allow/deny domain policies
- request timeout limits
- response size limits
- SSRF protections
- content sanitization

## Integration points

The research subsystem integrates with the orchestrator and the retrieval/context layers. It can provide evidence for synthesis, verification, or optional knowledge persistence.
