# RUX — AI Orchestration Engine

> A local AI agent that converts natural language into safe, persistent state changes — with deterministic enforcement, self-evaluation, and multi-model critique.


---

## STATUS 

This project is under active development.  
I am currently refactoring the system toward a modular domain-based architecture, so some parts of the codebase are still evolving.

## What RUX Is

Most AI agents work like this:

```
LLM → tool → response
```

No validation. No reliability measurement. No audit trail. If the LLM hallucinates an action name or inverts a parameter, the system fails silently.

RUX is built differently:

```
User
 ↓
Planner (LLM)          ← probabilistic intent extraction
 ↓
Executor               ← schema enforcement — the trust boundary
 ↓
Tool → Service         ← domain logic, business rules
 ↓
Repository → PostgreSQL ← persistence
 ↓
Observability Layer    ← every execution logged
 ↓
Outcome Tracker        ← correctness feedback per run
 ↓
Decision Engine        ← deterministic reasoning + Critic LLM
 ↓
Confidence Engine      ← real historical accuracy via SQL aggregation
 ↓
Final Response         ← result + observation + second opinion + confidence
```

The core idea: **the LLM is untrusted**. Everything before the Executor is probabilistic. Everything after is deterministic. The schema inside the Executor is the contract that separates the two worlds.

---

## Architecture

### Core Layers

| Layer | Responsibility |
|---|---|
| **Planner** | Converts natural language → structured JSON intent via LLM |
| **Executor** | Schema validation + action routing — rejects anything malformed |
| **Tool** | Thin adapter — translates validated params to service calls |
| **Service** | Domain logic and business rule enforcement |
| **Repository** | All DB read/write via SQLAlchemy async ORM |
| **PostgreSQL** | Durable persistence |

### Intelligence Layers

| Layer | Responsibility |
|---|---|
| **Observability** | Logs every execution — action, params, result, latency, timestamp |
| **Outcome Tracker** | Records correctness feedback per run per domain |
| **Confidence Engine** | Calculates real accuracy via SQL aggregation over outcome history |
| **Decision Engine** | Post-execution reasoning — deterministic rules + Critic LLM |
| **Critic LLM** | Separate model independently evaluates every decision |

### Project Structure

Refining and modulating domains 
```
rux/
├── core/
│   ├── orchestrator.py      # coordinates full execution flow
│   ├── planner.py           # three-layer intent detection + LLM
│   ├── executor.py          # schema validation + trust boundary
│   ├── confirmation_manager.py
│
├── tools/
│   ├── base_tool.py
│   ├── registry.py
│   ├── expense_manager.py
│
├── services/
│   ├── llm_service.py       # supports multiple models (planner + critic)
│   ├── expense_service.py   # budget enforcement, domain logic
│   ├── confidence_service.py
│   ├── critic_service.py
│   ├── decision_engine.py
│
├── repositories/
│   ├── expense_repository.py
│   ├── budget_repository.py
│   ├── user_repository.py
│   ├── agent_runs_repository.py
│   ├── agent_outcomes_repository.py
│
├── observability/
│   ├── tracer.py
│   ├── logger.py
│
├── api/
│   └── routes.py
│
└── main.py
```

---

## Key Design Decisions

### 1. The Trust Boundary

The Executor is where trust is established. LLM output is treated as untrusted input — it must pass schema validation with `extra="forbid"` before any tool is called. This catches hallucinated field names, invented action types, and malformed JSON before they reach domain logic.

```
LLM output         → untrusted — can hallucinate anything
Executor (schema)  → trust boundary
Tool onward        → deterministic, validated, safe
```

### 2. Why the Planner Doesn't Call Tools Directly

LLMs are probabilistic. Tools are deterministic, state-mutating, and potentially destructive. Mixing these responsibilities means you can't test planning logic in isolation, can't enforce business rules cleanly, and can't reason about failures.

```
Planner  → intent extraction only
Executor → structural validation
Tool     → domain gateway
Service  → business rules
Memory   → persistence
```

### 3. Three-Layer Planner

Not everything should reach the LLM.

```
Layer 1 → greeting keywords    → instant deterministic reply (zero LLM cost)
Layer 2 → action intent        → LLM extracts structured JSON
Layer 3 → open question        → LLM responds conversationally
```

This protects confidence score integrity — greetings incorrectly mapped to actions were corrupting outcome data before this was implemented.

### 4. Confidence from Data, Not from the LLM

Asking an LLM how confident it is produces meaningless output. RUX calculates confidence from real historical outcomes:

```sql
SELECT domain, task_type,
       COUNT(*)         AS samples,
       AVG(was_correct) AS accuracy
FROM agent_outcomes
WHERE user_id = :user_id
GROUP BY domain, task_type
```

Confidence only surfaces when `samples >= 5`. Before that the system returns `"Confidence: insufficient data"` rather than fabricating a number.

### 5. Critic Uses a Different Model

If the Planner and Critic use the same model, the Critic tends to agree with the Planner's reasoning — defeating the purpose of independent evaluation. Separate models are configured in the config layer. The Critic runs non-blocking via `asyncio.create_task()` so it never adds latency to the user-facing response.

---

## What a Response Looks Like

```
Expense logged successfully

Observation:
Expense logged. Monitor spending relative to budget.

Second Opinion:
Repeated spending in this category may exceed your monthly budget.
Consider reviewing your food expense trend.

Confidence: 85% (based on 12 runs)
```

---

## Domain — Expense & Budget Management

Current working domain with full enforcement logic:

- Log expenses with category tagging
- Set monthly budgets with hard or soft enforcement mode
  - **Hard mode** — rejects expenses that exceed budget
  - **Soft mode** — logs with a warning
- Analyse spending by category and time period
- Budget enforcement validates projected spend before logging

---

## Database Schema

```
users
projects
expenses          ← amount, category, note, timestamp
budgets           ← start_date, end_date, mode (hard/soft)
confirmations     ← pending action state
agent_runs        ← full execution log per message
agent_outcomes    ← correctness feedback per run
```

---

## Debug Endpoints

```
GET /debug/runs          → inspect agent execution logs
GET /debug/outcomes      → inspect correctness feedback
GET /debug/confidence    → live accuracy metrics by domain
```

---

## Tech Stack

- **Python 3.11+**
- **FastAPI** — async HTTP layer (ASGI)
- **SQLAlchemy** — async ORM with PostgreSQL
- **PostgreSQL** — primary persistence
- **LM Studio** — local LLM inference (`http://localhost:1234/v1`)
- **Pydantic v2** — schema validation with `extra="forbid"`

---

## Setup

```bash
# Clone
git clone https://github.com/rahulT-17/RUX-Orchestration-Engine.git
cd RUX-Orchestration-Engine

# Create and activate virtual environment
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt

# Initialize database tables
python init_db.py

# Start the app
python -m uvicorn main:app --reload

```

---

## What's Next

- [ ] Reflection layer — agent challenges past decisions using outcome history
- [ ] Hybrid memory — short-term + episodic + semantic in one system
- [ ] Knowledge Domain — capturing reusable facts and context and will be reasoning about it and more 
- [ ] Cloud deployment
- [ ] Confidence-triggered automatic second opinion (low accuracy → auto-critique)

---

## Why I Built This

I wanted to understand what actually breaks in AI agent systems — not from reading papers but from building something that fails in real ways and fixing it. Every architectural decision in RUX came from a real bug: the trust boundary from schema validation failures, the three-layer planner from greeting messages corrupting confidence scores, the separate Critic model from noticing single-model self-evaluation is meaningless.

The goal was never to build another chatbot wrapper. It was to build the layer underneath — the enforcement, evaluation, and reasoning infrastructure that makes an AI agent actually reliable.

---

*Built as a learning project. Active development.*

