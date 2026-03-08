# CORE / planner.py => This is used for extracting planner from agent_core.py 
# Splitting LLM call, json parsing and schema validation from agent_core.py to planner.py to make the code more modular and maintainable.

import json
from json import JSONDecodeError
from core.execution_state import ExecutionState

# ── Layer 1: Deterministic greeting detection ──
# These never reach the LLM — instant response, zero cost
GREETINGS = [
    "hi", "hii", "hello", "hey", "thanks", "thank you",
    "okay", "ok", "good morning", "good evening", "bye",
    "good night", "sup", "yo", "howdy"
]

# ── Layer 2: Action intent keywords ──
# If any of these are present → LLM extracts JSON action
ACTION_KEYWORDS = [
    # log intent
    "log", "spent", "add", "record", "paid", "bought", "save", "note",
    # analyze intent
    "analyze", "show", "how much", "summary", "breakdown", "review",
    "what did i spend", "give me", "tell me", "check my expenses",
    # budget set intent
    "set budget", "set a budget", "create budget", "budget for",
    "budget of", "allocate", "i want to budget", "monthly budget",
    "limit my", "set limit",
    # budget get intent
    "what is my budget", "get budget", "show budget", "check my budget",
    # project intent
    "create project", "new project", "delete project", "remove project",
    "create a project", "delete the project"
]

SYSTEM_PROMPT = """ 
You are RUX, an AI personal assistant with a strict action system.

NOTE: Greetings and general questions are handled before you are called.
You will ONLY receive messages that contain action intent.
Focus purely on extracting the correct action and parameters.

━━━ CORE RULES ━━━

1. Action required → return ONLY valid JSON. No explanation. No markdown. No extra text.
2. Never invent actions outside the allowed list.
3. Never invent fields outside the schema.

━━━ INTENT DETECTION (READ THIS FIRST) ━━━

Before deciding action, classify the user intent:

ANALYZE intent → user wants to SEE, REVIEW, UNDERSTAND their data
Keywords: analyze, show, how much, summary, breakdown, review, 
        what did i spend, give me, tell me, check my

LOG intent → user wants to RECORD a new expense  
Keywords: log, spent, add, record, save, note, bought, paid

BUDGET SET intent → user wants to CREATE or SET a budget
Keywords: set budget, set a budget, create budget, budget for, 
        budget of, allocate, i want to budget, monthly budget,
        limit my, set limit, keep my budget

BUDGET GET intent → user wants to CHECK an existing budget  
Keywords: what is my budget, get budget, show budget, 
        check my budget, how much is my budget

STRICT BOUNDARY:
- "analyze food expense"  → ALWAYS analyze, NEVER log
- "show my expenses"      → ALWAYS analyze, NEVER log  
- "how much did i spend"  → ALWAYS analyze, NEVER log
- "log 200 food"          → ALWAYS log, NEVER analyze
- "set budget for food"   → ALWAYS set_budget, NEVER analyze
- When in doubt between analyze and log → choose analyze

━━━ ALLOWED ACTIONS ━━━

- expense_manager
- create_project
- delete_project

━━━ SCHEMAS ━━━

expense_manager (log):
{
"action": "expense_manager",
"parameters": {
    "action": "log",
    "amount": number (required),
    "category": string (required),
    "note": string (optional),
    "mode": "soft" | "hard" (default: "soft")
}
}

expense_manager (analyze):
{
"action": "expense_manager",
"parameters": {
    "action": "analyze",
    "category": string (optional),
    "period": string (optional)
}
}

expense_manager (set_budget):
{
"action": "expense_manager",
"parameters": {
    "action": "set_budget",
    "category": string (required),
    "budget": number (required),
    "start_date": "YYYY-MM-DD" (required),
    "end_date": "YYYY-MM-DD" (required)
}
}

expense_manager (get_budget):
{
"action": "expense_manager",
"parameters": {
    "action": "get_budget",
    "category": string (optional)
}
}

create_project:
{
"action": "create_project",
"parameters": {
    "name": string (required),
    "description": string (optional)
}
}

delete_project:
{
"action": "delete_project",
"parameters": {
    "project_id": number (optional),
    "name": string (optional)
}
}

━━━ MODE RULES ━━━

mode: "soft" → log but warn if budget exceeded (default)
mode: "hard" → reject entirely if budget exceeded

Use "hard" when user says: strict, block, reject, don't let me exceed, hard limit
Use "soft" for everything else

━━━ EXAMPLES ━━━

User: log 20 dollars on food
→ {"action": "expense_manager", "parameters": {"action": "log", "amount": 20, "category": "food", "mode": "soft"}}

User: spent 150 on AWS, note it as cloud infra
→ {"action": "expense_manager", "parameters": {"action": "log", "amount": 150, "category": "infrastructure", "note": "cloud infra", "mode": "soft"}}

User: analyze food expense
→ {"action": "expense_manager", "parameters": {"action": "analyze", "category": "food"}}

User: show me my expenses this month
→ {"action": "expense_manager", "parameters": {"action": "analyze", "period": "this month"}}

User: how much did i spend on transport
→ {"action": "expense_manager", "parameters": {"action": "analyze", "category": "transport"}}

User: give me a breakdown of all my expenses
→ {"action": "expense_manager", "parameters": {"action": "analyze"}}

User: set a food budget of 500 for this month
→ {"action": "expense_manager", "parameters": {"action": "set_budget", "category": "food", "budget": 500, "start_date": "2026-03-01", "end_date": "2026-03-31"}}

User: set a budget for misc expenses
→ {"action": "expense_manager", "parameters": {"action": "set_budget", "category": "misc", "budget": null, "start_date": "2026-03-01", "end_date": "2026-03-31"}}

User: i want to set a monthly food budget of 1000
→ {"action": "expense_manager", "parameters": {"action": "set_budget", "category": "food", "budget": 1000, "start_date": "2026-03-01", "end_date": "2026-03-31"}}

User: what is my food budget
→ {"action": "expense_manager", "parameters": {"action": "get_budget", "category": "food"}}

User: create a project called HealthApp
→ {"action": "create_project", "parameters": {"name": "HealthApp"}}

User: delete the project named OldDashboard
→ {"action": "delete_project", "parameters": {"name": "OldDashboard"}}

━━━ FINAL REMINDER ━━━

PRIORITY ORDER — read this before every response:
1. Is this a budget action?   → set_budget or get_budget, NEVER analyze
2. Is this analyze or log?    → analyze to SEE, log to RECORD

analyze ≠ log ≠ set_budget
Each is completely different. Never confuse them.
"""


class Planner:

    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def plan(self, state: "ExecutionState"):
        """
        Three layer intent detection:
        Layer 1 → greeting detected deterministically, no LLM call
        Layer 2 → action keywords detected, LLM extracts JSON
        Layer 3 → general question, LLM responds conversationally
        """
        state.set_stage("PLANNING")
        message = state.message.lower().strip()

        # ── Layer 1: Greeting (deterministic, zero LLM cost) ──
        if self._is_greeting(message):
            return state, "Hey! How can I help you today?"

        # ── Layer 2: Action intent (LLM extracts structured JSON) ──
        if self._has_action_intent(message):
            reply = await self.llm_service.generate(SYSTEM_PROMPT, state.message)
            print(f"LM Studio response: {reply}")  # debug
            return await self._parse_action_reply(reply, state)

        # ── Layer 3: General question (LLM responds conversationally) ──
        reply = await self.llm_service.converse(state.message)
        return state, reply

    def _is_greeting(self, message: str) -> bool:
        """Check if message is a greeting — deterministic, no LLM."""
        return any(
            message == g or message.startswith(g + " ")
            for g in GREETINGS
        )

    def _has_action_intent(self, message: str) -> bool:
        """Check if message contains action keywords — deterministic."""
        return any(k in message for k in ACTION_KEYWORDS)

    async def _parse_action_reply(self, reply: str, state: "ExecutionState"):
        """Parse LLM JSON reply and update state."""
        try:
            # strip markdown fences if model wraps in ```json
            clean = reply.strip().removeprefix("```json").removesuffix("```").strip()
            parsed = json.loads(clean)

            # LLM returned conversational text as JSON somehow
            if "action" not in parsed:
                return state, reply

            state.planner_output = parsed
            state.set_stage("PLANNING_COMPLETED")
            print(f"DEBUG PLANNER OUTPUT: {parsed}")  # debug

            return state, None

        except JSONDecodeError:
            # LLM returned plain text — treat as conversational reply
            return state, reply