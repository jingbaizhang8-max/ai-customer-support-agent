
# AI Customer Support & Operations Agent

An AI-powered e-commerce customer support agent built with Python, DeepSeek, and a custom tool-execution harness.

## Overview

This project explores how LLM agents can interact with business tools through a controlled execution layer.

The agent can interpret customer requests, select registered tools, validate tool arguments, execute business operations, and generate responses grounded in tool results.

## Current Features

- DeepSeek LLM Tool Calling
- Order lookup using mock e-commerce data
- Tool Registry with an explicit allowlist
- Pydantic argument validation
- JSON parsing and error handling
- Tool call ID tracking
- Final response generation using tool results
- Automated unit tests with pytest

## Architecture

Customer Request
    ↓
DeepSeek Tool Calling
    ↓
Agent Runner
    ↓
Tool Registry + Pydantic Validation
    ↓
Order Tool (Mock Data)
    ↓
Tool Result
    ↓
DeepSeek Final Response

## Tech Stack

- Python 3.13
- DeepSeek API
- OpenAI Python SDK
- Pydantic
- pytest

## Quick Start

1. Create a Python virtual environment.
2. Install dependencies:

    python -m pip install -r requirements.txt

3. Copy `.env.example` to `.env` and configure your DeepSeek API key.
4. Run the example agent:

    python -m app.agent.agent_runner

## Testing

Run all automated tests:

    python -m pytest -q

## Development Status

This project is under active development.

The current implementation supports multiple tools and multi-round agent execution using mock business data.

Planned features include PostgreSQL, Shopify sandbox integration, multi-step agent workflows, policy RAG, human approval, audit logging, guardrails, and agent evaluation.

No real payment or refund operations are performed.



## Multi-Tool Agent Workflow

The agent supports multiple business tools through a controlled execution harness.

### Available Tools

| Tool | Description |
|---|---|
| `get_order` | Retrieve order information |
| `get_shipping_status` | Retrieve shipping status, carrier, and tracking number |

Both tools currently use mock e-commerce data.

### Multi-Step Agent Loop

The agent can perform multiple LLM decision rounds, execute registered tools, and pass tool results back to the LLM for further decisions.

The harness includes:

- Pydantic argument validation
- Tool allowlist enforcement
- Multi-round conversation history
- Multiple tool calls within a single decision round
- Maximum LLM decision rounds: 4
- Maximum tool requests per run: 6
- Duplicate tool call detection
- Structured tool execution results

Tool calls within the same round are currently executed sequentially.

### Example

Customer: "Check order ORD-1001. If it has shipped, find its tracking number."

The agent can use `get_order` and `get_shipping_status` to retrieve the necessary information before generating its response.

### Run the Agent Loop

```powershell
python -m app.agent.agent_loop
```

### Automated Tests

```powershell
python -m pytest -q
```

Current test suite: 11 passing tests.

### Limitations

The system currently uses mock order and shipping data.

Customer authentication, order ownership authorization, persistent business records, real payment operations, and human approval workflows have not yet been implemented.

The execution limits and duplicate detection are preliminary safeguards, not a complete production security system.
