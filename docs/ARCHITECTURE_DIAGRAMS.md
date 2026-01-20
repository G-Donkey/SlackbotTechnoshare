# Architecture Flow Diagrams

These diagrams can be rendered using [Mermaid](https://mermaid.js.org/) or pasted into tools like [Mermaid Live Editor](https://mermaid.live/).

---

## Sequence Diagram: End-to-End Flow

```mermaid
sequenceDiagram
    actor User
    participant Slack as Slack Cloud
    participant Listener as Socket Listener<br/>(main_socket.py)
    participant DB as SQLite Queue
    participant Worker as Job Worker<br/>(main_worker.py)
    participant Pipeline as 5-Stage Pipeline
    participant LLM as GPT-4o API
    
    User->>Slack: Posts message with URL
    Slack->>Listener: WebSocket event push
    
    Note over Listener: Fast Path (< 3s)
    Listener->>Listener: 1. Validate channel
    Listener->>Listener: 2. Check not bot
    Listener->>Listener: 3. Extract URLs
    Listener->>DB: 4. INSERT job (idempotent)
    Listener->>Slack: 5. ACK event ✓
    
    Note over Worker,Pipeline: Slow Path (5-10s)
    loop Every 5s
        Worker->>DB: Poll for pending jobs
    end
    
    Worker->>DB: Claim job (UPDATE status='processing')
    Worker->>Pipeline: process_job(job_id, ...)
    
    Pipeline->>Pipeline: Stage 1: Extract URLs
    Pipeline->>Pipeline: Stage 2: HTTP GET + trafilatura
    Pipeline->>LLM: Stage 3: Analyze (with context)
    LLM-->>Pipeline: JSON response
    Pipeline->>Pipeline: Stage 4: Quality gates
    Pipeline->>Slack: Stage 5: Post Block Kit reply
    
    Pipeline->>DB: UPDATE status='done'
    Slack->>User: Shows threaded reply
```

---

## Flowchart: Pipeline Decision Logic

```mermaid
flowchart TD
    Start([Slack Message Received]) --> CheckChannel{Correct<br/>Channel?}
    CheckChannel -->|No| Ignore1[Ignore]
    CheckChannel -->|Yes| CheckBot{Bot<br/>Message?}
    
    CheckBot -->|Yes| Ignore2[Ignore]
    CheckBot -->|No| CheckURL{Contains<br/>URL?}
    
    CheckURL -->|No| Ignore3[Ignore]
    CheckURL -->|Yes| ExtractURL[Extract URLs]
    
    ExtractURL --> CheckDupe{Already<br/>Processed?}
    CheckDupe -->|Yes| Ignore4[Skip Duplicate]
    CheckDupe -->|No| QueueJob[Write to SQLite Queue]
    
    QueueJob --> ACK[ACK to Slack]
    ACK --> WaitWorker[Wait for Worker Poll]
    
    WaitWorker --> WorkerClaim[Worker Claims Job]
    WorkerClaim --> Stage1[Stage 1: URL Extraction]
    Stage1 --> Stage2[Stage 2: Fetch + Extract Content]
    
    Stage2 --> FetchOK{Fetch<br/>Success?}
    FetchOK -->|No| MarkFailed1[Mark job 'failed']
    FetchOK -->|Yes| Stage3[Stage 3: LLM Analysis]
    
    Stage3 --> LLMOK{LLM<br/>Success?}
    LLMOK -->|No| MarkFailed2[Mark job 'failed']
    LLMOK -->|Yes| Stage4[Stage 4: Quality Gates]
    
    Stage4 --> GatesOK{Validation<br/>Pass?}
    GatesOK -->|No| MarkFailed3[Mark job 'failed']
    GatesOK -->|Yes| Stage5[Stage 5: Post to Slack]
    
    Stage5 --> PostOK{Post<br/>Success?}
    PostOK -->|No| MarkFailed4[Mark job 'failed']
    PostOK -->|Yes| MarkDone[Mark job 'done']
    
    MarkDone --> End([Reply Visible in Thread])
    MarkFailed1 --> End2([Error Logged])
    MarkFailed2 --> End2
    MarkFailed3 --> End2
    MarkFailed4 --> End2
    
    Ignore1 --> End3([No Action])
    Ignore2 --> End3
    Ignore3 --> End3
    Ignore4 --> End3
    
    style Stage1 fill:#e1f5ff
    style Stage2 fill:#e1f5ff
    style Stage3 fill:#fff4e1
    style Stage4 fill:#e1f5ff
    style Stage5 fill:#e1f5ff
    style MarkDone fill:#e8f5e9
    style MarkFailed1 fill:#ffebee
    style MarkFailed2 fill:#ffebee
    style MarkFailed3 fill:#ffebee
    style MarkFailed4 fill:#ffebee
```

---

## Component Architecture Diagram

```mermaid
graph TB
    subgraph Slack["☁️ Slack Cloud"]
        Event[Message Event]
        Reply[Threaded Reply]
    end
    
    subgraph Process1["🔌 Process 1: Socket Listener"]
        SocketMode[Socket Mode Handler]
        Validator[Event Validator]
        URLExtractor[URL Extractor]
    end
    
    subgraph Database["🗄️ SQLite Database"]
        JobsTable[(jobs table)]
    end
    
    subgraph Process2["⚙️ Process 2: Job Worker"]
        Poller[Job Poller]
        PipelineRunner[Pipeline Runner]
    end
    
    subgraph Pipeline["📦 5-Stage Pipeline"]
        S1[Stage 1: URL Extraction]
        S2[Stage 2: Content Retrieval<br/>httpx + trafilatura]
        S3[Stage 3: LLM Analysis<br/>GPT-4o]
        S4[Stage 4: Quality Gates<br/>Pydantic validation]
        S5[Stage 5: Slack Posting<br/>Block Kit]
    end
    
    subgraph External["🌐 External Services"]
        OpenAI[OpenAI API]
        Web[Web Content]
    end
    
    Event -->|WebSocket| SocketMode
    SocketMode --> Validator
    Validator --> URLExtractor
    URLExtractor -->|INSERT| JobsTable
    
    JobsTable -->|Poll every 5s| Poller
    Poller -->|Claim job| PipelineRunner
    
    PipelineRunner --> S1
    S1 --> S2
    S2 -.->|HTTP GET| Web
    S2 --> S3
    S3 -.->|API Call| OpenAI
    S3 --> S4
    S4 --> S5
    S5 -->|POST| Reply
    
    S5 -->|UPDATE status| JobsTable
    
    style Process1 fill:#e3f2fd
    style Process2 fill:#f3e5f5
    style Pipeline fill:#fff3e0
    style Database fill:#e8f5e9
    style Slack fill:#fce4ec
    style External fill:#f5f5f5
```

---

## Data Flow: Stage 2 Content Retrieval

```mermaid
flowchart LR
    URL[URL Input<br/>https://example.com/article] --> Fetch
    
    subgraph Fetch[HTTP Fetch - httpx]
        GET[GET Request]
        Retry[Retry Logic<br/>3 attempts, 2s delay]
        HTML[Raw HTML<br/>50KB with ads, nav, etc.]
        GET --> Retry
        Retry --> HTML
    end
    
    HTML --> Extract
    
    subgraph Extract[Content Extraction - trafilatura]
        Parse[Parse HTML]
        Strip[Strip boilerplate<br/>ads, nav, footer]
        Clean[Clean Text<br/>5KB article content]
        Parse --> Strip
        Strip --> Clean
    end
    
    Clean --> Structure
    
    subgraph Structure[Snippet Creation]
        Split[Split into paragraphs]
        Truncate[Truncate to 500 chars]
        Format[Format as JSON]
        Split --> Truncate
        Truncate --> Format
    end
    
    Format --> Output[Evidence Pack<br/>sources + snippets]
    
    style Fetch fill:#e1f5ff
    style Extract fill:#fff4e1
    style Structure fill:#e8f5e9
```

---

## State Machine: Job Lifecycle

```mermaid
stateDiagram-v2
    [*] --> pending: Message received<br/>Job created
    
    pending --> processing: Worker claims job
    
    processing --> done: Pipeline succeeds
    processing --> failed: Any stage fails
    
    failed --> [*]: Error logged
    done --> [*]: Reply posted
    
    note right of pending
        Job sits in queue
        waiting for worker
    end note
    
    note right of processing
        5-stage pipeline
        executing
    end note
    
    note right of done
        Idempotent:
        Won't reprocess
    end note
    
    note right of failed
        Logged for debugging
        Manual intervention
    end note
```

---

## Usage

### For Google Slides:
1. Copy any Mermaid diagram above
2. Use [Mermaid Live Editor](https://mermaid.live/) to render as PNG/SVG
3. Download and insert into slides

### For Markdown Presentations (reveal.js, Marp):
Just paste the Mermaid code blocks directly - they'll auto-render

### For Documentation:
GitHub, GitLab, and many tools render Mermaid natively
