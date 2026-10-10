# Rubber Duck Architecture & Design Document

Rubber Duck is an AI debugging companion created for the AWS Builder Center hackathon. Rather than generating answers that developers paste without understanding, it coaches developers Socratically by asking **exactly ONE question at a time** (under 60 words) until they uncover the bug themselves.

---

## 1. End-to-End System Architecture

```mermaid
flowchart TB
    subgraph Client ["Client (Desktop & Mobile Browser)"]
        UI["React 18 + Tailwind CSS + Framer Motion"]
        Mascot["Animated SVG Duck Mascot\n(idle, thinking, celebrating, napping)"]
        Store["Zustand Store\n(localStorage synced)"]
        StatsModal["Live Results & Metrics Modal\n(/stats)"]
    end

    subgraph CDN ["AWS Edge & Static Hosting"]
        CloudFront["Amazon CloudFront CDN\n(HTTPS Edge Caching)"]
        S3["Amazon S3 Static Bucket\n(Vite Production Build)"]
    end

    subgraph Serverless ["AWS Serverless Compute (arm64, Free Tier)"]
        FURL["Lambda Function URL\n(CORS enabled)"]
        Router["AWS Lambda (Python 3.12, arm64)\nFast, Zero-Dependency Handler"]
        Agent["Socratic Agent State Loop\n(<60 words, 1 question, 'hint', 'show me')"]
        EMF["CloudWatch Embedded Metric Format\n(Zero-latency Custom Metrics)"]
        SSM["AWS SSM Parameter Store\n(SecureString Gemini Key)"]
    end

    subgraph Data ["Amazon DynamoDB (On-Demand)"]
        SessionsTable[("RubberDuckSessions\n(session_id, history, streak, TTL: 7 days)")]
        StatsTable[("RubberDuckStats\n(Atomic Counters: sessions, solved, ratings)")]
    end

    subgraph LLM ["Google Gemini API (Free Tier)"]
        GeminiAdapter["LLM Provider Abstraction\n(Pure HTTPS urllib.request)"]
        GeminiFlash["gemini-2.5-flash / gemini-1.5-flash\n(Structured JSON Mode)"]
    end

    CloudFront --> S3
    Client -->|"Loads Web App"| CloudFront
    UI -->|"POST /chat, POST /rate, GET /stats"| FURL
    FURL --> Router
    Router --> Agent
    Agent --> GeminiAdapter
    GeminiAdapter --> GeminiFlash
    Router --> SessionsTable
    Router --> StatsTable
    Router --> EMF
    Router --> SSM
```

---

## 2. Interaction & State Machine Flow

```mermaid
stateDiagram-v2
    [*] --> Idle: User visits app / starts chat
    Idle --> Thinking: User pastes error or code
    Thinking --> Asking: Duck analyzes & formulates 1 question (<60 words)
    Asking --> Thinking: User answers question
    Asking --> Hint: User clicks "Hint" chip
    Hint --> Asking: Duck provides gentle nudge
    Asking --> Revealed: User clicks "Show me"
    Revealed --> [*]: Full explanation & fix shown
    Asking --> Celebrating: User solves bug ("I found it!")
    Celebrating --> Recap: Duck celebrates + provides 1-sentence lesson
    Recap --> [*]: Solved streak increments & session rated
```

---

## 3. Core Architectural Decisions

### Zero-Dependency arm64 Lambda Backend
- **Problem**: Traditional AI agent frameworks (LangChain, LlamaIndex, Strands) carry large package footprints (30–60 MB) and require binary wheel compilation for ARM64 targets, causing high cold start latencies (2–4 seconds).
- **Solution**: We built a lightweight agent loop in pure Python standard library (`urllib.request`, `json`, `re`) paired with AWS Lambda's pre-installed `boto3`.
- **Result**: The zipped Lambda artifact is **under 30 KB**, and cold starts on AWS Lambda Graviton2 (`arm64`) run in **under 180 ms**.

### Amazon CloudWatch Embedded Metric Format (EMF)
- Custom metrics (`SessionsStarted`, `BugsSolved`, `HintsUsed`, `ShowMeUsed`, `Ratings`) are emitted directly to `stdout` in EMF format:
```json
{
  "_aws": {
    "Timestamp": 1690000000000,
    "CloudWatchMetrics": [
      {
        "Namespace": "RubberDuck",
        "Dimensions": [["Environment"]],
        "Metrics": [
          { "Name": "BugsSolved", "Unit": "Count" },
          { "Name": "SolvedWithoutFix", "Unit": "Count" }
        ]
      }
    ]
  },
  "Environment": "Production",
  "BugsSolved": 1,
  "SolvedWithoutFix": 1
}
```
- CloudWatch extracts these asynchronously without consuming runtime compute or adding API latency.

### Amazon DynamoDB Single-Table + Atomic Counter Aggregations
- **Session Expiration**: Each session includes an automatic `ttl` attribute (7-day epoch timestamp). DynamoDB clears aged records with zero admin intervention.
- **Real-Time Hackathon Stats**: Rather than scanning the sessions table on every `/stats` call, global metrics are updated using atomic `ADD` expressions (`update_item`). The `/stats` endpoint executes in single-digit milliseconds.

### Custom SVG Framer Motion Duck Mascot
- Rather than static avatars or heavy raster GIFs, the mascot is a custom vector component with dynamic animations:
  - `idle`: Breathing scale and realistic eye-blink loop.
  - `thinking`: Curious head tilt, bobbing, and thought bubble dots.
  - `celebrating`: Hop animation, wing flap, and canvas-confetti burst.
  - `napping`: Head droop, closed eyes, and floating `zZz` particles for error states.

---

## 4. AWS Free Tier Cost Profile

| Service | Free Tier Allowance | Rubber Duck Consumption | Projected Cost |
| :--- | :--- | :--- | :--- |
| **AWS Lambda** | 1,000,000 requests / month + 3.2M sec compute | ~10,000 hackathon requests | **\$0.00** |
| **Amazon DynamoDB** | 25 GB storage + 25 WCU / 25 RCU | < 50 MB, on-demand pay-per-request | **\$0.00** |
| **CloudWatch Logs** | 5 GB ingestion / month | < 50 MB logs | **\$0.00** |
| **Amazon S3** | 5 GB standard storage | ~4 MB frontend assets | **\$0.00** |
| **Amazon CloudFront** | 1 TB data transfer out / month | < 5 GB | **\$0.00** |
| **Google Gemini API**| Free tier: 15 RPM, 1,500 RPD | Well within hackathon usage | **\$0.00** |
