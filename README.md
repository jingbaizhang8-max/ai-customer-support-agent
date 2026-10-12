
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

The current implementation uses mock order data and a single round of tool calling.

Planned features include PostgreSQL, Shopify sandbox integration, multi-step agent workflows, policy RAG, human approval, audit logging, guardrails, and agent evaluation.

No real payment or refund operations are performed.
