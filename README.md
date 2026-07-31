# Intentwise AI Generic Data Ingestion Service

Generic, configuration-driven data ingestion service written in Python with FastAPI, SQLAlchemy, and PostgreSQL.

## Overview

Service connects to arbitrary REST APIs, handles authentication and pagination strategies, normalizes JSON payloads, and persists records into PostgreSQL without source-specific code.

---

## High-Level Architecture

```text
                User Request
                      │
                      ▼
               FastAPI Endpoint
                      │
                      ▼
              Ingestion Controller
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
 API Configuration            Validation
        │
        ▼
 Generic API Client
        │
        ▼
 Authentication Handler
        │
        ▼
 Pagination Engine
        │
        ▼
 Response Parser
        │
        ▼
 Data Normalizer
        │
        ▼
 Storage Interface
        │
        ▼
      PostgreSQL
```

---

## Project Structure

```text
generic-ingestion/
├── app/
│   ├── api/
│   │   └── endpoints.py
│   ├── clients/
│   │   ├── api_client.py
│   │   ├── auth.py
│   │   └── pagination.py
│   ├── database/
│   │   └── session.py
│   ├── examples/
│   │   ├── dummyjson.json
│   │   └── github.json
│   ├── schemas/
│   │   └── config.py
│   ├── services/
│   │   ├── ingestion.py
│   │   ├── normalizer.py
│   │   └── parser.py
│   ├── storage/
│   │   ├── base.py
│   │   └── postgres.py
│   └── main.py
├── tests/
│   └── test_ingestion.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Setup & Running

### Running with Docker Compose (Recommended)

```bash
docker-compose up --build
```

Access API documentation at: `http://localhost:8000/docs`

---

### Running Locally

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Ensure local PostgreSQL server running
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/ingestion_db"

uvicorn app.main:app --reload
```

---

## Running Unit Tests

```bash
.\venv\Scripts\python -m pytest tests/
```

---

## Demo

Working execution demonstration showing multi-source generic configuration support. Tested using different API configurations:

### Example 1: NewsAPI Ingestion (API Key Auth & Offset Pagination)

#### A. Source Configuration (JSON)
Custom NewsAPI source configuration specifying the endpoint, query arguments, api key credentials, offset pagination rules, and target storage:
![NewsAPI Configuration](assets/api_key_example.png)

#### B. Execution (FastAPI Docs Interface)
Triggering POST request on `/api/v1/ingest` with the NewsAPI configuration:
![NewsAPI Ingest Screen](assets/newsapi_ingest.png)

#### C. Ingestion Output
FastAPI returns success details on normalized record throughput and operational metrics:
![NewsAPI Ingest Response](assets/newsapi_response.png)

#### D. Server Logs & SQL Verification
Stdout splits showing container initialization, request execution, auto-generating columns, and checking record count in DB:
![NewsAPI Logs and SQL](assets/terminal_logs.png)


### Example 2: GitHub API Ingestion (Bearer Token & Link Header Pagination)

#### A. Source Configuration (JSON)
Multiple GitHub sources config using Bearer authentication and Link Header pagination structures:
![GitHub Configuration](assets/github_code.png)

#### B. Execution
Executing multi-source task via Swagger UI:
![GitHub Ingest Docs](assets/github_docs.png)

#### C. Ingestion Output
Ingestion result summarizing all successfully written batches:
![GitHub Ingest Response](assets/github_response.png)

#### D. Server Logs & SQL Verification
Stdout split demonstrating pagination request flow and verifying row count for Repos and Gists tables inside postgres container:
![GitHub Logs and SQL](assets/github_terminal.png)

---

## Example Usage

Send POST request to `http://localhost:8000/api/v1/ingest`:

### Example payload (DummyJSON Products):

```json
{
  "sources": [
    {
      "name": "DummyJSON Products",
      "base_url": "https://dummyjson.com",
      "endpoint": "/products",
      "method": "GET",
      "headers": {
        "User-Agent": "GenericIngestionService/1.0"
      },
      "auth": {
        "type": "none"
      },
      "params": {},
      "pagination": {
        "type": "offset",
        "page_param": "skip",
        "size_param": "limit",
        "page_size": 30,
        "max_pages": 3
      },
      "data_path": "products",
      "storage": {
        "table_name": "dummyjson_products",
        "primary_key": "id"
      }
    }
  ]
}
```

---

## Supported Features

- **Auth Mechanisms:** None, API Key (Header or Query), Bearer Token, Basic Auth.
- **Pagination Strategies:** Offset, Cursor, Next URL, Limit-Offset, Link Header.
- **Dynamic Normalization:** Flattens JSON objects, injects metadata (`_ingestion_source`, `_ingestion_timestamp`, `_ingestion_request_id`, `_ingestion_endpoint`, `_raw_payload`).
- **Dynamic PostgreSQL Persistence:** Automatically reflects/creates tables and schema columns dynamically on first run with primary key upsert support.

---

## Design Decisions & Trade-offs

1. **Config-Driven Architecture:** Decouples ingestion logic from API sources, allowing new sources to be onboarded via JSON/YAML without changing codebase.
2. **Abstract Storage Interface:** `BaseStorage` permits future plug-and-play implementations (S3, MongoDB, Elasticsearch).
3. **Dynamic PostgreSQL Schema Creation:** Ingests heterogeneous payloads directly without manual DDL migrations.

---

## AI Usage Disclosure

### AI Mistake & Fix

**Mistake:** During initial test runner execution, global `pytest` command failed due to missing system path registration.  
**Fix:** Following user directive, instantiated clean Python virtual environment (`venv`), installed project dependencies in virtual environment, and executed test runner via explicit `.\venv\Scripts\python -m pytest tests/`.
