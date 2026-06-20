# FixMate AI Architecture

FixMate AI is a local-first, read-only diagnostic application. Collection, deterministic detection, persistence, presentation, reporting, and optional model explanation are separate so each boundary can be tested and constrained.

## High-level architecture

```mermaid
flowchart LR
    OS["Windows or Ubuntu"] --> C["psutil collectors"]
    C --> D["Deterministic detectors"]
    D --> DB[("SQLite history")]
    DB --> UI["Streamlit pages"]
    DB --> API["FastAPI v1 services"]
    DB --> A["Read-only assistant tools"]
    A --> DA["Deterministic assistant"]
    DA --> UI
    DA --> API
    DB --> R["Privacy-safe report builder"]
    R --> E["CSV / JSON / HTML / PDF bytes"]
    KB["Local error knowledge base"] --> DA
    KB --> OCR["Local screenshot matcher"]
    OCR --> DB
```

## Diagnostic data flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit or API
    participant Collector
    participant Detector
    participant SQLite
    User->>UI: Run scan or diagnostic
    UI->>Collector: Collect bounded read-only metrics
    Collector-->>UI: Typed metric snapshot
    UI->>Detector: Evaluate explicit thresholds
    Detector-->>UI: Issues with evidence and guidance
    UI->>SQLite: Save scan and issues atomically
    SQLite-->>UI: Historical records
    UI-->>User: Current and historical evidence
```

Collectors do not require administrator privileges, inspect file contents, terminate processes, change settings, scan ports, or capture packets.

## Privacy flow

```mermaid
flowchart TD
    Input["Metrics, OCR text, questions, stored evidence"] --> U["Treat as untrusted data"]
    U --> Redact["Existing privacy redaction"]
    Redact --> Store["Store only allowed local fields"]
    Store --> Read["Read-only evidence tools"]
    Read --> RedactAgain["Display/report/provider redaction"]
    RedactAgain --> Local["Local UI or API response"]
    RedactAgain --> Consent{"External provider selected and consented?"}
    Consent -- No --> Stop["No external transmission"]
    Consent -- Yes --> Min["Minimized approved evidence only"]
```

Screenshot files are processed in memory and are not stored. OCR text is redacted before persistence. Reports are generated in memory. Conversation history remains in Streamlit session state unless explicitly selected for one report.

## Streamlit and FastAPI

Streamlit and FastAPI reuse the same service modules and SQLite schema. They are separate presentation surfaces rather than separate implementations.

- Streamlit provides interactive system/network dashboards, screenshot analysis, troubleshooting chat, and report downloads.
- FastAPI exposes versioned diagnostics, history, issues, screenshot metadata, assistant queries, and reports.
- API route handlers delegate to service classes instead of duplicating collectors or detection rules.
- Native FastAPI binds to `127.0.0.1`; Docker binds internally to `0.0.0.0` but publishes only on host loopback.

## Database overview

```mermaid
erDiagram
    SCANS ||--o{ ISSUES : contains
    NETWORK_DIAGNOSTICS ||--o{ NETWORK_ISSUES : contains
    SCANS {
      integer id PK
      text collected_at
      real cpu_percent
      real memory_percent
      real disk_free_percent
      integer health_score
      text top_processes_json
    }
    SCREENSHOT_ANALYSES {
      integer id PK
      text analyzed_at
      text extracted_text_redacted
      text matched_issue_id
      real confidence_score
    }
    SCHEMA_MIGRATIONS {
      text migration_id PK
      text applied_at
    }
```

Migrations are additive and preserve Phase 1–3 records. Assistant conversations and generated reports have no database tables.

## Assistant safety model

```mermaid
flowchart TD
    Q["Untrusted user question"] --> Intent["Deterministic intent routing"]
    Intent --> Tools["Nine allowlisted read-only tools"]
    Tools --> Answer["Authoritative deterministic answer"]
    Answer --> Mode{"AI enhancement enabled?"}
    Mode -- No --> Return["Return evidence-bound answer"]
    Mode -- Yes --> Consent{"External provider and consent valid?"}
    Consent -- No --> Return
    Consent -- Yes --> Agent["Bounded provider: max 4 tools / 2 calls"]
    Agent --> Validate["Schema, grounding, privacy, and safety validation"]
    Validate -- Valid --> Label["Labeled optional explanation"]
    Validate -- Invalid or failure --> Return
```

The model never receives database, filesystem, shell, process, repair, or unrestricted network access. It cannot replace deterministic evidence or claim a repair occurred.

## API request flow

```mermaid
sequenceDiagram
    participant Client
    participant Middleware
    participant Auth
    participant Router
    participant Service
    participant DB as SQLite
    Client->>Middleware: HTTP request
    Middleware->>Middleware: Request ID and body-size check
    Middleware->>Auth: Protected POST token and rate limit
    Auth->>Router: Valid request
    Router->>Service: Validated Pydantic input
    Service->>DB: Parameterized or read-only access
    DB-->>Service: Local records
    Service-->>Router: Privacy-safe result
    Router-->>Client: Versioned envelope + UTC timestamp
```

## Docker deployment

```mermaid
flowchart LR
    Browser -->|"127.0.0.1:8501"| S["Streamlit container"]
    Client -->|"127.0.0.1:8000"| F["FastAPI container"]
    S --> V[("fixmate_ai_data volume")]
    F --> V
    S -. "health before API startup" .-> F
```

Both services reuse one non-root Python 3.12 slim image. Container diagnostics describe container resources and networking, so native execution is required for actual host diagnostics.

