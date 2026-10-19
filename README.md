
# AI Customer Support & Operations Agent

An AI-powered e-commerce customer support agent built with Python, DeepSeek, and a custom tool-execution harness.

## Overview

This project explores how LLM agents can interact with business tools through a controlled execution layer.

The agent can interpret customer requests, select registered tools, validate tool arguments, execute business operations, and generate responses grounded in tool results.

## Current Features

- DeepSeek LLM Tool Calling
- Order lookup using PostgreSQL-backed demo data
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
Business Tools → Repositories → PostgreSQL
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
- PostgreSQL 17
- SQLAlchemy ORM
- psycopg

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

Planned features include Shopify sandbox integration,
customer authentication and authorization, policy RAG,
human approval workflows, refund operations, and agent evaluation.

No real payment or refund operations are performed.



## Multi-Tool Agent Workflow

The agent supports multiple business tools through a controlled execution harness.

### Available Tools

| Tool | Description |
|---|---|
| `get_order` | Retrieve order information |
| `get_shipping_status` | Retrieve shipping status, carrier, and tracking number |

Both tools currently query demonstration data stored in PostgreSQL.

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

Current test suite: 14 passing tests.

### Limitations

The system currently uses demonstration order and shipping data persisted in PostgreSQL.

Customer authentication, order ownership authorization,
and real payment operations have not yet been implemented.

The execution limits and duplicate detection are preliminary safeguards, not a complete production security system.



## PostgreSQL Persistence

The agent uses PostgreSQL to persist e-commerce order and shipping records.

### Database Tables

- `orders`: order ID, customer ID, order status, amount, currency
- `shipments`: order ID, shipping status, carrier, tracking number

The `shipments.order_id` column references `orders.order_id` through a foreign key.

### Data Access Architecture

Agent → Harness → Business Tools → Repositories → SQLAlchemy → PostgreSQL

### Database Setup

1. Install PostgreSQL and create a database named `ai_customer_support_db`.
2. Copy `.env.example` to `.env` and configure the PostgreSQL connection.
3. Initialize the tables:

```powershell
python -m app.core.init_db
```

4. Insert demonstration data:

```powershell
python -m app.core.seed_data
```

5. Run the Agent:

```powershell
python -m app.agent.agent_loop
```

### Testing

```powershell
python -m pytest -q
```

The unit tests use pytest fixtures and monkeypatch to isolate database access, so they do not require a running PostgreSQL server. Database environment configuration is still required by the current implementation.

### Current Limitations

- The database contains demonstration data, not real customer records.
- Shopify integration is not yet implemented.
- Customer authentication and order ownership authorization are not yet implemented.
- Refund operations and human approval workflows are planned for later development.


## Real E-Commerce Data Integration

The project supports the Olist Brazilian E-Commerce Public Dataset,
which contains anonymized historical e-commerce orders.

### ETL Pipeline

The ETL pipeline:

1. Reads order and payment CSV files.
2. Aggregates payment amounts by order ID using Decimal.
3. Maps raw Olist fields to the PostgreSQL orders schema.
4. Imports records in batches of 500.
5. Uses PostgreSQL ON CONFLICT DO NOTHING to avoid duplicate inserts.
6. Uses RETURNING to count successfully inserted records.

### Data Import

Download the Olist dataset and place the required CSV files in:

`data/olist/`

Required files:

- `olist_orders_dataset.csv`
- `olist_order_payments_dataset.csv`

Preview transformed records:

```powershell
python -m app.etl.preview_olist
```

Import 10 records for testing:

```powershell
python -m app.etl.import_olist --limit 10
```

Import all available orders:

```powershell
python -m app.etl.import_olist
```

### Verified Results

- 99,440 Olist orders imported into PostgreSQL
- 2 existing demonstration orders preserved
- Both legacy and 32-character Olist order IDs supported
- DeepSeek Agent successfully queried a real Olist order
- Both order and shipping tools executed successfully
- 20 automated tests passing

### Data Limitations

Olist is a historical public dataset, not a live e-commerce system.

The current ETL imports orders and payment totals. It does not
import independent shipment records, carrier names, or tracking numbers.

Duplicate orders are skipped rather than updated. Customer
authentication and order ownership authorization are not yet implemented.

The raw CSV files are excluded from Git.


## RAG-Powered Refund Policy Tool

The AI Customer Support Agent integrates with the separate
RAG Knowledge Platform through an HTTP API.

### Architecture

Customer Request
    → DeepSeek Agent
    → Tool Registry
    → search_refund_policy
    → HTTP POST /ask
    → RAG Knowledge Platform
    → Policy Answer and Sources
    → Agent Final Response

### Available Tools

- `get_order`: Query order information from PostgreSQL.
- `get_shipping_status`: Query shipping information.
- `search_refund_policy`: Retrieve return and refund policy
  information from the RAG knowledge base.

### Configuration

Add these settings to `.env`:

```dotenv
RAG_API_BASE_URL=http://127.0.0.1:8000
REFUND_POLICY_DOCUMENT_ID=your_uploaded_document_id
```

The RAG service must be running before executing policy
queries. The document ID is configured by the application,
not supplied by the LLM.

### Policy Tool Behavior

The policy tool returns structured statuses:

- `retrieved`: A policy answer and sources were returned.
- `insufficient_evidence`: No sufficient policy evidence.
- `service_error`: The RAG service request failed.
- `not_configured`: The policy document ID is missing.
- `invalid_question`: The question is empty or whitespace.

The Agent must inspect the tool's data status rather than
relying only on the Tool Registry's success flag.

### Safety Limitations

The current refund policy is fictional demonstration data.

It is NOT an official Olist policy or a real merchant policy.

The Agent must not use the demo policy to approve real refunds
or determine eligibility for real Olist orders.

Real refund execution, authentication, authorization,
and human approval workflows are not yet implemented.

### Testing

Policy tool tests cover successful retrieval,
insufficient evidence, service errors, and rejection
of unauthorized document ID overrides.

The current automated test suite contains 24 tests.
