# OpsPilot

[中文版](README.zh-CN.md)

> An intelligent operations assistant built on RAG and MCP

OpsPilot is designed for enterprise operations scenarios. The goal is not to wrap an LLM in a chat UI, but to build a more complete Agent engineering loop across intent routing, retrieval, tool orchestration, diagnosis workflows, persistent state, and lightweight observability.

## Project Positioning

This project is best framed in resumes and interviews as:

- an Agent engineering project for enterprise operations scenarios
- an intelligent operations assistant with intent-based routing
- a practical system combining RAG, MCP, workflow orchestration, and persistent state

The positioning is intentionally honest and restrained:

- it does not claim to be a real production system
- it does not claim full integration with real ticketing platforms
- it does not claim complete production deployment of Prometheus/MySQL
- it does not market itself as a multi-agent platform
- it does not claim unverified cost or efficiency gains

One-line summary:

OpsPilot emphasizes complete execution flow, clear structure, and honest boundaries rather than exaggerated production claims.

## Why It Is More Than a Chatbot

The interesting part of OpsPilot is not “the model can answer questions.” The interesting part is how the system decides which execution path to take and how the result is persisted and made observable.

The current system provides six capability groups:

- intent routing across `smalltalk / simple_qa / knowledge_qa / aiops_diagnosis / unsupported`
- hybrid retrieval with Milvus dense recall, SQLite FTS5 sparse recall, RRF fusion, and lightweight reranking
- an AIOps diagnosis workflow based on `Plan-Execute-Replan`
- MCP-based tool integration for logs and monitoring-style tools
- persistent state for sessions, messages, workflow runs, and tool call logs
- lightweight observability for request volume, latency, retrieval timing, tool success rate, and workflow duration

This matters because:

- simple questions do not need a heavy Agent path
- document-centric questions have a retrieval engineering story
- diagnosis requests have a workflow orchestration story
- key execution steps can be replayed, audited, and explained clearly

## Overall Architecture

OpsPilot currently uses a layered structure: frontend interaction, API interfaces, orchestration services, retrieval and tooling, and persistence.

### 1. Frontend Interaction Layer

This layer turns the project into a usable demo with login state and session history.

- handles login state in the browser
- stores JWT locally
- syncs session history from the backend
- provides quick chat, streaming chat, and AIOps diagnosis entry points

### 2. API Interface Layer

This layer exposes the system through clear endpoints.

- `/api/auth/*` for login and current-user lookup
- `/api/chat*` for chat, streaming responses, and chat cleanup
- `/api/sessions*` for session history and details
- `/api/aiops` for streaming diagnosis
- `/api/upload` for document ingestion and indexing
- `/metrics` for lightweight metrics exposure

### 3. Orchestration Layer

This is the most important Agent-engineering layer.

- `chat_service` handles intent classification, routing, and message persistence
- `aiops_service` runs the `Plan-Execute-Replan` workflow
- `intent_service` performs rule-first routing with optional LLM fallback

### 4. Retrieval and Tool Layer

This layer organizes knowledge access and external capabilities.

- `retrieval_service` implements dense recall, sparse recall, RRF, and reranking
- `knowledge_tool` converts retrieval results into answer context
- `mcp_client` manages MCP tool loading, retries, and call logging

### 5. Persistence Layer

This layer ensures the system is no longer purely in-memory.

- `sessions` stores session metadata and `thread_id`
- `messages` stores user and assistant messages
- `workflow_runs` stores knowledge-QA and diagnosis workflow records
- `tool_call_logs` stores tool execution status and latency
- `document_chunks` and `document_chunks_fts` support sparse retrieval

Why this layering helps:

it lets you explain chat, retrieval, diagnosis, tools, and persistence separately while still presenting them as one coherent engineering loop.

## Core Query Flow

The most interview-worthy part of the project is how a single request flows through the system.

The current request path can be described in six steps:

### 1. The request enters the chat API

The user calls `/api/chat` or `/api/chat_stream`. The system first validates the JWT and resolves the current user.

This happens up front so that session access, diagnosis, and uploads all sit behind a minimal but explicit security boundary.

### 2. The request goes through the intent-routing layer

`chat_service` calls `intent_service.classify()`.

The routing strategy is:

- rules first
- lightweight LLM fallback only when needed

This is useful because:

- many operations-related request patterns are stable
- rules reduce unnecessary heavy-path traffic
- not every request needs a full Agent workflow

### 3. The system routes to the right execution path

The route space is fixed:

- `smalltalk`
- `simple_qa`
- `knowledge_qa`
- `aiops_diagnosis`
- `unsupported`

The current routing actions are:

- direct answers for smalltalk and simple QA
- hybrid retrieval for document and knowledge questions
- AIOps workflow execution for diagnosis requests
- explicit refusal for out-of-scope requests

### 4. Knowledge questions enter the hybrid retrieval path

`knowledge_qa` triggers `retrieval_service.hybrid_search()`.

That path has four internal stages:

1. dense recall with Milvus
2. sparse recall with SQLite FTS5
3. candidate fusion via RRF
4. lightweight reranking over the fused candidates

This structure gives the project a clear retrieval-engineering story:

- why dense-only retrieval is not enough
- why keyword-sensitive retrieval still matters for operations data
- why fusion and reranking improve credibility

### 5. Diagnosis questions enter the workflow path

`aiops_diagnosis` triggers the `Plan-Execute-Replan` workflow.

The point here is not “let the model think longer.” The point is to separate diagnosis into explicit stages:

- Planner creates the diagnosis plan
- Executor runs steps and calls tools
- Replanner decides whether to continue or to converge on a report

That makes the diagnosis path much easier to explain as orchestrated workflow logic rather than a single oversized prompt.

### 6. The system persists results and updates metrics

After execution, the system writes back:

- session metadata
- user messages
- assistant responses
- workflow run state
- tool execution logs
- request timing metrics

This step is critical because it makes the project replayable, inspectable, and explainable instead of being a one-shot demo.

One-line flow summary:

the core of OpsPilot is “route first, execute second, persist third, observe throughout.”

## Hybrid Retrieval Design

Hybrid retrieval is one of the strongest engineering talking points in the project.

The current design stays intentionally focused:

- Milvus for dense retrieval
- SQLite FTS5 for sparse retrieval
- RRF for candidate fusion
- lightweight overlap-based reranking

### Why hybrid retrieval matters here

Dense retrieval alone can be weak on:

- exact metric names
- error strings
- alert names
- operations-specific terminology

Sparse retrieval alone can be weak on:

- semantic paraphrases
- broader intent matching
- natural-language formulations

Combining both gives you a much stronger and more defensible retrieval story in interviews.

### What the retrieval trace now captures

The trace records:

- dense hit count
- sparse hit count
- fused hit count
- reranked hit count
- latency for dense, sparse, and rerank stages
- final source documents

That turns the project from “I used a vector database” into “I designed a retrieval path and can explain how it behaves.”

## Persistence and Session Management

The current version no longer treats `MemorySaver` as the primary state source. The backend database is the main source of truth.

This layer solves four practical problems:

- session recovery
- conversation history lookup
- workflow review
- tool-call traceability

### What is persisted today

- `sessions`: session title, timestamps, and `thread_id`
- `messages`: user and assistant messages plus intent and route metadata
- `workflow_runs`: execution type, status, start/end time, and duration
- `tool_call_logs`: tool name, success/failure, latency, and payload traces

### Why this matters

Many demo-style Agent projects break here:

- state disappears on refresh
- conversations cannot be resumed
- workflows cannot be audited
- tool failures leave no trace

OpsPilot now closes that gap with a minimal but coherent persistence model.

## Authentication and Security Boundary

OpsPilot does not implement a complex permission system, but it does include a minimal “enterprise-like” boundary.

The current setup includes:

- JWT-based login state
- three roles: `viewer / operator / admin`
- restricted access to upload and AIOps diagnosis for `operator / admin`

The point is not permission complexity. The point is that you can clearly explain:

- what a read-only user can do
- which operations are considered higher-risk
- why tool-driven diagnosis should not be completely open

## Observability and Testing

The goal here is not to overbuild a monitoring stack. The goal is to add enough engineering evidence to support resume and interview storytelling.

### Current metrics

The system records:

- request volume
- average HTTP request latency
- retrieval latency
- rerank latency
- MCP tool success/failure counts
- end-to-end AIOps workflow duration

### Current tests

The added tests cover:

- authentication service behavior
- rule-based intent routing
- retrieval fusion and reranking
- API authorization boundaries

The point of these tests is not a vanity coverage number. The point is to prove that the important execution paths are not just stitched together for a demo.

## Resume and Interview Framing

A stronger way to describe the project is:

### Short English version

OpsPilot is an Agent engineering project for enterprise operations scenarios. It combines intent routing, hybrid retrieval and reranking, a Plan-Execute-Replan diagnosis workflow, MCP tool orchestration, and persistent session/workflow state to build an end-to-end loop from issue identification to troubleshooting guidance.

### Expanded version

- the system first routes requests through a rule-first intent layer so that small talk, simple QA, knowledge QA, and diagnosis requests do not share the same execution path
- the knowledge path uses Milvus, SQLite FTS5, RRF, and reranking to form a hybrid retrieval pipeline
- the diagnosis path uses Plan-Execute-Replan to separate planning, tool execution, and convergence
- the engineering layer adds JWT auth, role boundaries, session persistence, tool-call logs, and metrics exposure so the project feels like a more complete system prototype instead of a one-off demo

## Current Boundaries

To keep the story honest, the current boundaries should also be explicit.

- monitoring and ticket data are better described as near-realistic samples or simulated data loops
- reranking is currently lightweight rather than a dedicated cross-encoder service
- MCP capabilities are integrated, but underlying data realism depends on local or simulated services
- tests cover key paths, but the project is not presented as a production-grade validation matrix

Final positioning sentence:

OpsPilot is best presented as a complete, structurally clear, and engineering-oriented intelligent operations Agent project with honest boundaries.
