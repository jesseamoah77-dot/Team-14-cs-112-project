# Design Diagrams

All diagrams are Mermaid, so GitHub renders them inline. Sources are the diagrams —
edit here, not in an image editor.

## 1. GridCare-Lite

### 1.1 Entity-relationship diagram

```mermaid
erDiagram
    USERS {
        int user_id PK
        text username UK
        text password_hash
        text full_name
        text role "admin | engineer | technician | customer_service"
    }
    SUBSTATIONS {
        int substation_id PK
        text name
        text region
        int voltage_kv
        real capacity_mva
        text status
    }
    LINES {
        int line_id PK
        int source_substation_id FK
        int destination_substation_id FK
        int voltage_kv
        real length_km
        text status
    }
    OUTAGES {
        int outage_id PK
        int substation_id FK
        int reported_by FK
        text severity "Low | Medium | High | Critical"
        text status "Open | In Progress | Resolved"
        text reported_at
        text resolved_at
    }
    WORK_ORDERS {
        int work_order_id PK
        int outage_id FK
        int created_by FK
        int assigned_technician FK
        text scheduled_date
        text status "Pending | Scheduled | Completed"
        text work_notes
    }
    COMPLAINTS {
        int complaint_id PK
        int logged_by FK
        text customer_name
        int outage_id FK "nullable"
    }
    STATUS_HISTORY {
        int history_id PK
        text entity_type "outage | work_order"
        int entity_id
        text old_status
        text new_status
        int changed_by FK
    }

    SUBSTATIONS ||--o{ LINES : "source / destination"
    SUBSTATIONS ||--o{ OUTAGES : "suffers"
    USERS ||--o{ OUTAGES : "reports"
    OUTAGES ||--o{ WORK_ORDERS : "repaired by"
    USERS ||--o{ WORK_ORDERS : "assigned to"
    OUTAGES ||--o{ COMPLAINTS : "linked from"
    USERS ||--o{ COMPLAINTS : "logs"
    USERS ||--o{ STATUS_HISTORY : "changes"
```

### 1.2 Outage / work-order state machines

```mermaid
stateDiagram-v2
    direction LR
    state Outage {
        [*] --> Open : engineer logs outage
        Open --> InProgress : technician starts work
        InProgress --> Resolved : work order completed
        Resolved --> [*]
    }
    state WorkOrder {
        [*] --> Pending : admin creates
        Pending --> Scheduled : admin assigns technician + date
        Scheduled --> Completed : technician records work done
        Completed --> [*]
    }
```

Completing a work order resolves its outage in the same operation, so the two
records can never disagree. Both machines are enforced in `services.py` on every
transition; `status_history` records each change with who and when.

### 1.3 Role → permitted operations

```mermaid
flowchart LR
    subgraph Roles
        A[admin]
        E[engineer]
        T[technician]
        C[customer_service]
    end
    subgraph Operations
        O1[log outage]
        O2[create work order]
        O3[assign technician + date]
        O4[start work]
        O5[complete work + resolve]
        O6[log / link complaint]
        O7[view reports]
    end
    E --> O1
    A --> O1
    A --> O2
    A --> O3
    T --> O4
    T --> O5
    A --> O4
    A --> O5
    C --> O6
    A --> O6
    A --> O7
    E --> O7
    C --> O7
    T --> O7
```

Every operation re-checks the caller's role inside `services.py` — hiding a button
is presentation, the service check is the control. Technicians additionally may only
act on work orders assigned to them.

## 2. ClinicCare-Lite

### 2.1 Use-case diagram

```mermaid
flowchart TB
    CL((Clinician))
    PA((Patient))
    SYS((System / scheduler))

    subgraph ClinicCare-Lite
        U1[Register / log in]
        U2[Create + assign health task]
        U3[Submit task file]
        U4[Automated completeness check]
        U5[Review submission - categorical outcome]
        U6[Send / read messages]
        U7[Publish announcement]
        U8[Book appointment + mark attendance]
        U9[View operational analytics]
        U10[View private engagement + own history]
        U11[Send notifications + emails]
        U12[24h appointment reminders]
    end

    CL --> U1
    PA --> U1
    CL --> U2
    PA --> U3
    U3 -.includes.-> U4
    CL --> U5
    CL --> U6
    PA --> U6
    CL --> U7
    CL --> U8
    CL --> U9
    PA --> U10
    U2 -.triggers.-> U11
    U5 -.triggers.-> U11
    SYS --> U12
```

### 2.2 Class diagram (entities and their managers)

```mermaid
classDiagram
    class User {
        +user_id: str  "8 digits"
        +name: str
        +email: str
        +role: clinician|patient
        +theme: dark|colorful
        -password_hash: bcrypt
        +engagement: dict "patients only, private"
        +save()
    }
    class Clinic {
        +clinic_id: str
        +name: str
        +clinician_id: str
        +patient_ids: list
    }
    class HealthTask {
        +task_id: str
        +clinic_id: str
        +title / description
        +due_date
        +assigned_patient_ids: list
        +expected_fields: list
    }
    class TaskSubmission {
        +key: "patientID_taskID"
        +file_path
        +submitted_at
        +completeness: dict
        +review: outcome, reviewer, notes, notified
    }
    class Message {
        +sender_id / recipient_id
        +content / timestamp / read
        +kind: message|notification
    }
    class Appointment {
        +clinic_id / patient_id
        +when / purpose
        +status: Scheduled|Attended|No-show|Cancelled
        +reminder_sent: bool
    }
    class Announcement {
        +clinic_id
        +title / body
        +publish_date / expiry_date
        +urgent: bool
    }
    class Store {
        <<persistence>>
        +load(name)
        +save(name, data) "atomic replace"
        +update(name, mutate) "locked"
    }

    Clinic "1" o-- "many" User : registers patients
    Clinic "1" o-- "many" HealthTask
    HealthTask "1" o-- "many" TaskSubmission
    User "1" o-- "many" TaskSubmission : submits
    User "1" o-- "many" Message : sends / receives
    Clinic "1" o-- "many" Appointment
    Clinic "1" o-- "many" Announcement
    Store <.. User
    Store <.. Clinic
    Store <.. HealthTask
    Store <.. TaskSubmission
    Store <.. Message
    Store <.. Appointment
    Store <.. Announcement
```

### 2.3 System architecture

```mermaid
flowchart TB
    subgraph Browser
        B1[Bootstrap templates]
        B2[scripts.js - client-side validation, 5s message polling]
    end
    subgraph Flask
        R1[routes/auth.py]
        R2[routes/clinician.py]
        R3[routes/patient.py]
        G[routes/guards.py<br/>role decorators + ownership helpers]
    end
    subgraph Domain
        M[models/*  entities]
        U1[utils/validators]
        U2[utils/file_handler]
        U3[utils/completeness]
        U4[utils/engagement]
        U5[utils/analytics]
        U6[utils/email_handler]
    end
    subgraph Storage
        S1[(data/*.json<br/>atomic writes via store.py)]
        S2[(submissions/clinic/patient/<br/>uploaded files)]
        S3[(data/outbox.json<br/>dry-run email)]
    end

    Browser --> R1 & R2 & R3
    R2 & R3 --> G
    G --> M
    R1 & R2 & R3 --> U1
    R3 --> U2 --> S2
    R3 --> U3
    R2 & R3 --> U4 & U5
    R2 & R3 --> U6 --> S3
    M --> S1
```

### 2.4 Data-flow: submission → review → notification

```mermaid
sequenceDiagram
    actor P as Patient
    participant F as Flask route
    participant CC as completeness check
    participant FH as file_handler
    participant ST as store (JSON)
    participant EM as email (dry-run/SMTP)
    actor C as Clinician

    P->>F: POST /patient/tasks/T001/submit (file)
    F->>CC: check(raw bytes, expected fields)
    alt incomplete
        CC-->>F: problems list
        F-->>P: 400 + named problems, nothing stored
    else complete
        F->>FH: validate ext/size, rename, store under clinic/patient/
        F->>ST: record submission (Pending)
        F->>ST: notify patient (inbox) + engagement points
        F->>EM: email clinician
        F-->>P: confirmation
    end
    C->>F: POST /clinician/submissions/key/review (outcome + notes)
    F->>ST: record outcome, reviewer, timestamp
    F->>ST: notify patient (inbox)
    F->>EM: email patient
    F-->>C: confirmation
    P->>F: GET /patient/ (dashboard shows outcome + notes)
```

## 3. Grid analysis pipeline

```mermaid
flowchart LR
    GEN[generate_grid_data.py<br/>seed 42] --> RAW[(utilities / substations / lines CSVs)]
    RAW --> CLEAN[griddata.clean + validate]
    CLEAN --> MASTER[build_master<br/>lines + both ends + utility]
    CLEAN --> GRAPH[build_graph<br/>44 nodes incl. 2 isolates]
    MASTER --> NB3[notebook 03: merged questions]
    GRAPH --> NB4[notebook 04: centrality, communities,<br/>bridges, N-1 contingency]
    CLEAN --> NB2[notebook 02: EDA]
    MASTER --> NB5[notebook 05: geographic + Folium map]
    NB4 --> EXPORTS[(network_metrics.csv<br/>n1_contingency.csv)]
    EXPORTS --> DASH[Streamlit dashboard]
    MASTER --> DASH
    CLEAN --> GC[GridCare-Lite import_grid_data.py]
```
