# Generic API Ingestor Service

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

## Setup & Running Guide

This service can be run using either Docker Compose or direct local execution.

### Option A: Running with Docker Compose (Recommended)

Docker Compose automatically stands up the FastAPI application container, coordinates networking, and configures a PostgreSQL instance.

1. **Build and start the services:**
   Run this command in the project root:
   ```bash
   docker-compose up --build
   ```
2. **Access Swagger Interactive Documentation:**
   Open your browser and navigate to:
   `http://localhost:8000/docs`
3. **Verify running containers:**
   Ensure both the database and ingestion app are running:
   ```bash
   docker-compose ps
   ```

---

### Option B: Running Locally

If executing outside of Docker containers:

1. **Provision virtual environment:**
   Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
2. **Install project dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Database Connection Environment Variable:**
   Create a local PostgreSQL database (e.g., named `ingestion_db`) and export your connection URI:
   ```bash
   # On Windows (PowerShell):
   $env:DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/ingestion_db"
   
   # On macOS/Linux:
   export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/ingestion_db"
   ```
4. **Launch Development Server:**
   Start the FastAPI app via Uvicorn:
   ```bash
   uvicorn app.main:app --reload
   ```

---

### How to Trigger an Ingestion (User Instructions)

1. Open `http://localhost:8000/docs`.
2. Expand the `POST /api/v1/ingest` endpoint.
3. Click **Try it out**.
4. Copy and paste one of the JSON configurations from the `app/examples/` folder into the request body.
5. Provide real API secrets (like NewsAPI key or GitHub token) inside the `auth` structure if required.
6. Click **Execute**.
7. Query your local database dynamically using a PostgreSQL client to view the newly ingested table schema and raw data:
   ```sql
   SELECT * FROM your_configured_table_name LIMIT 10;
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

### 1. Schema Generation and Reflection
* **Dynamic Table Creation:** The service automatically infers types (`Integer`, `Float`, `Boolean`, `Text`) from the first batch of JSON records. This eliminates the need for predefined DDL schemas, allowing direct data ingestion from new APIs.
* **Schema Evolution Limitation:** Once a table is dynamically created and reflected in MetaData using `MetaData.reflect()`, columns are fixed. Future runs with schema changes (new API response fields) will ignore columns not in the reflected database table (`record_data = {k: v for k, v in record.items() if k in table.columns}`).

### 2. Storage Strategy & Upserts
* **On Conflict Upserts:** If a `primary_key` is provided in the configuration, the storage layer uses PostgreSQL-specific `on_conflict_do_update` syntax to execute incremental updates, avoiding duplicate entries.
* **Auto-increment Fallback:** If no primary key is specified in the configuration, an auto-incrementing `_id` column is generated to track ingested items uniquely.

### 3. Modular Pagination Framework
* **Decoupled State Engine:** `PaginationEngine` separates configuration parsed from JSON (`PaginationConfig`) from execution state tracking (`current_offset`, `current_page`, `next_url`).
* **Universal Interface:** The client handles various strategies (Offset, Limit-Offset, Cursor, Next URL, and RFC 5988 Link Headers) through a unified `get_request_params(base_params)` signature, returning either query parameter overrides or absolute URL overrides.

### 4. Normalization and Metadata Injection
* **Traceability:** Flat structures are generated via recursion to ensure standard tabular formatting. 
* **Ingestion Metadata:** Injected tracking attributes (`_ingestion_source`, `_ingestion_timestamp`, `_ingestion_request_id`, `_ingestion_endpoint`, `_raw_payload`) allow audit logging, tracking precisely when and from which source a database record was created.

---

## AI Usage Disclosure

### AI Mistake & Fix

**Mistake:** During initial test runner execution, global `pytest` command failed due to missing system path registration.  
**Fix:** Following user directive, instantiated clean Python virtual environment (`venv`), installed project dependencies in virtual environment, and executed test runner via explicit `.\venv\Scripts\python -m pytest tests/`.
