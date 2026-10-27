
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


## Order Authorization and Access Control

The project implements customer-level order ownership checks
to reduce the risk of unauthorized order access (IDOR).

### Authorization Flow

1. The Agent receives the customer's request.
2. A trusted application context supplies authenticated_customer_id.
3. The LLM selects a tool and provides the order_id.
4. The Tool Registry checks whether authentication is required.
5. The business tool queries PostgreSQL using both order_id and customer_id.
6. Unauthorized requests are denied without returning private order data.

### Protected Tools

- `get_order`: Requires an authenticated customer context.
- `get_shipping_status`: Requires an authenticated customer context.
- `search_refund_policy`: Does not require customer authentication
  because it retrieves fictional public demonstration policy information.

### Security Rules

- Customer identity must not be supplied or overridden by the LLM.
- Missing authentication returns `authentication_required`.
- Unauthorized or nonexistent orders return `order_not_found`.
- Pydantic rejects unexpected tool arguments.
- Order ownership is checked before accessing shipping details.
- Both single-round and multi-round Agent execution paths
  pass the trusted customer context to the Tool Registry.

### Authorization Testing

Tests cover:

- Missing customer authentication
- Access to a customer's own order
- Unauthorized access to another customer's order
- Unauthorized access to shipping information
- Rejection of LLM-provided customer identity overrides

32 automated tests currently pass.

### Current Limitations

The project currently simulates authenticated customer identity
for development and testing.

Real login, session validation, JWT verification, and trusted
HTTP authentication middleware have not yet been implemented.

The current authorization logic must not be considered
production-ready authentication.

## JWT Authentication and Secure Agent API

### Overview

The AI Customer Support Agent provides a FastAPI endpoint protected by JSON Web Token (JWT) authentication.

The system validates the client's JWT before passing the authenticated customer identity to the Agent. Order and shipping tools then verify order ownership before returning private information.

### API Endpoints

| Method | Endpoint | Description | Authentication |
|---|---|---|---|
| GET | `/health` | Health check | Not required |
| POST | `/agent/chat` | Run the customer support Agent | Bearer JWT required |

### Authentication Flow

1. The client sends an HTTP request containing a Bearer JWT.
2. FastAPI extracts the token using `HTTPBearer`.
3. PyJWT validates the signature and required claims.
4. The verified `sub` claim identifies the authenticated customer.
5. FastAPI passes this customer ID to the Agent.
6. The Tool Registry validates tool arguments and authentication requirements.
7. Order and shipping tools enforce customer ownership before accessing private order details.

The system does not trust customer IDs supplied by the LLM or the user's message.

### JWT Security

JWT verification uses the HS256 algorithm and validates:

- `sub`: Authenticated customer identity
- `exp`: Token expiration time
- `iat`: Token issuance time
- `iss`: Expected token issuer
- `aud`: Expected token audience
- JWT digital signature

Missing, expired, incorrectly signed, or otherwise invalid tokens are rejected with HTTP `401 Unauthorized`.

### Environment Configuration

Add the following variable to the local `.env` file:

```dotenv
JWT_SECRET_KEY=your_secure_random_secret
```

Generate a cryptographically secure random key for local development. Never commit the real secret or an active JWT to GitHub.

The `.env.example` file contains only a placeholder value.

### Running the API

Start the FastAPI server:

```bash
python -m uvicorn app.main:app --reload --port 8001
```

Open the interactive Swagger documentation:

http://127.0.0.1:8001/docs

The RAG Knowledge Platform uses port 8000, while the Customer Support Agent API uses port 8001.

### Example Chat Request

**Endpoint:** `POST /agent/chat`

**Authorization header:**

```http
Authorization: Bearer <valid_jwt>
```

**Request body:**

```json
{
  "message": "Please check the status of order ORD-1001."
}
```

A valid JWT is required. Private order information is returned only when the authenticated customer owns the requested order.

### Automated Tests

Run all tests:

```bash
python -m pytest -q
```

Run JWT authentication tests:

```bash
python -m pytest tests/test_auth_api.py -v
```

The authentication tests cover:

- Missing JWT
- Valid JWT and authenticated customer identity propagation
- Different customer identities
- Invalid JWT signature
- Expired JWT
- Incorrect issuer
- Incorrect audience
- Missing subject claim

**Day 23 test results:** 40 tests passed, including 8 JWT authentication tests.

### Security and Current Limitations

- JWTs are generated locally for development and testing.
- A real user registration and login system has not yet been implemented.
- The current authentication implementation is intended for development and demonstration, not production deployment.
- Order ownership is enforced in the application business logic.
- Historical Olist order data is used for development and demonstration.
- Refund policy documents are fictional examples and must not be treated as official policies for Olist customers.
- Real refunds, production payment operations, and complete human approval workflows have not yet been implemented.


## Customer Support Ticket System

### Overview

The Ticket System enables authenticated customers to create and track customer support requests.

Supported ticket types:

- `refund_request`
- `shipping_issue`
- `general_inquiry`

New tickets are created with the status `pending_review`. Creating a refund request does not execute an actual refund.

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/tickets` | Create a customer support ticket |
| GET | `/tickets/{ticket_id}` | Retrieve an existing ticket |

Both endpoints require JWT Bearer authentication.

### Create a Ticket

**Endpoint:** `POST /tickets`

Required headers:

```http
Authorization: Bearer <valid_jwt>
Idempotency-Key: <unique_request_key>
```

Example request:

```json
{
  "order_id": "ORD-1001",
  "ticket_type": "refund_request",
  "description": "Item arrived damaged. I would like to request a refund.",
  "confirmed": true
}
```

The authenticated customer identity is extracted from the verified JWT.

Before creating a ticket, the Repository verifies that the referenced order belongs to the authenticated customer.

The `confirmed: true` field is required for submission. It is an API-level confirmation flag, not a complete human approval mechanism.

### Idempotency

Ticket creation uses an `Idempotency-Key` HTTP header.

A PostgreSQL unique index on `(customer_id, idempotency_key)` prevents duplicate records for the same customer and request key.

- Same key and identical request: return the existing ticket.
- Same key and different request: reject with HTTP `409 Conflict`.
- Unauthorized order: reject with HTTP `404 Not Found`.

### Ticket Status

Supported ticket statuses:

- `pending_review`
- `approved`
- `rejected`
- `closed`

The current implementation creates tickets in `pending_review`. Human approval workflows and controlled status transitions are planned for later development.

### Database

The Ticket System uses PostgreSQL and SQLAlchemy.

Main database table: `tickets`.

A development migration script is provided for adding the idempotency column and unique index to an existing tickets table:

```bash
python -m scripts.add_ticket_idempotency
```

This script expects the `tickets` table to already exist. Database schema versioning with Alembic has not yet been implemented.

### Testing

Run all tests:

```bash
python -m pytest -q
```

Run the PostgreSQL smoke test:

```bash
python -m scripts.smoke_test_tickets
```

The smoke test creates temporary test data and cleans it up after execution.

**Day 24 results:** 53 automated tests passed. The PostgreSQL smoke test also verified ticket persistence, ownership restrictions, and sequential idempotency behavior.

### Current Limitations

- Ticket creation is exposed through a JWT-protected API, not directly as an autonomous LLM write tool.
- The Agent can look up existing tickets using `get_ticket`.
- Human-in-the-loop approval and LangGraph workflow orchestration have not yet been implemented.
- Creating a refund ticket does not issue a payment refund.
- PostgreSQL concurrency behavior still requires dedicated integration testing.
## Human-in-the-loop Ticket Review

### Overview

The AI Customer Support Agent supports a human review workflow for customer support tickets.

Customers can submit refund requests through the Ticket API. These requests are initially stored with the status `pending_review`.

Authorized reviewers can approve or reject pending tickets through a separate, JWT-protected review endpoint.

**Approval does not execute an actual refund or payment transaction.**

### Review API

**Endpoint:** `POST /reviews/{ticket_id}`

Authentication requires a reviewer JWT rather than a customer JWT.

Example request:

```json
{
  "decision": "approved",
  "reason": "The request has been reviewed and approved."
}
```

Supported decisions:

- `approved`
- `rejected`

Only tickets with the status `pending_review` can be reviewed.

### Reviewer Authentication

Reviewer authentication is implemented separately from customer authentication.

The reviewer API validates:

- JWT signature using a dedicated reviewer secret
- Token expiration
- Issuer and audience
- Required JWT claims
- Reviewer role

The reviewer identity is derived from the verified JWT and is not accepted from user-supplied request fields.

Reviewer tokens are currently generated for development and testing. A production login system, reviewer account management and permission revocation are not yet implemented.

### Atomic Review Transactions

The review process uses SQLAlchemy and PostgreSQL transactions.

The workflow:

1. Lock the selected ticket using `SELECT ... FOR UPDATE`.
2. Verify that the ticket status is `pending_review`.
3. Update the ticket status to `approved` or `rejected`.
4. Insert an audit record into `ticket_reviews`.
5. Commit both changes in the same transaction.

If an operation fails, the transaction is rolled back.

A unique database constraint ensures that each ticket has at most one final review record.

### Audit Records

The `ticket_reviews` table stores:

- Review ID
- Ticket ID
- Reviewer ID
- Decision
- Review reason
- Review timestamp

These records provide a basic audit trail for human decisions.

### Testing

Run all automated tests:

```bash
python -m pytest -q
```

Run PostgreSQL review smoke tests:

```bash
python -m scripts.smoke_test_reviews
python -m scripts.smoke_test_review_concurrency
python -m scripts.smoke_test_review_rollback
```

**Day 25 result: 62 automated tests passed.**

Additional PostgreSQL smoke tests verified:

- Successful approval
- Audit record persistence
- Duplicate review rejection
- Concurrent review conflict handling
- Transaction rollback after a simulated failure

### Current Limitations

- Reviewer tokens are development credentials, not production user accounts.
- Reviewer permissions are based on verified JWT claims; production account and permission lifecycle management is not yet implemented.
- Human decisions are submitted through the review API.
- LangGraph-based workflow interruption and resumption have not yet been implemented.
- The system does not execute real refunds or payment transactions.