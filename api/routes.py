# api/routes.py

# Fast API router for handling incoming API requests related to the AI companion system :
from fastapi import APIRouter , Depends, HTTPException
from pydantic import BaseModel

# auth 
from core.auth import verify_api_key

# Importing the Orchestrator and its dependencies :
from services.llm_services import LLMService
from core.orchestrator import Orchestrator
from core.planner import Planner
from core.executor import Executor  
from core.confirmation_manager import ConfirmationManager
from core.tools_registry import bulid_tools_registry
from core.config import LM_STUDIO_URL, PLANNER_MODEL, CRITIC_MODEL



# Repositories for handling database interactions related to agent runs and outcomes :
from repositories.agent_outcomes_repository import AgentOutcomesRepository
from repositories.agent_feedback_repository import AgentFeedbackRepository

from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from services.critic_service import CriticService



# Creating a router instance (this groups related endpoints) :

router = APIRouter(tags=["chat"])    # This tag is used for documentation purposes; it groups the endpoints under the 'chat' section in the API docs


# Initializing the LLM services for the planner and critic using the configuration variables defined in core/config.py :

planner_llm  = LLMService(LM_STUDIO_URL, PLANNER_MODEL)  # LLM service instance for the planner
critic_llm = LLMService(LM_STUDIO_URL, CRITIC_MODEL)

critic_service = CriticService(critic_llm) # Critic service instance that uses the critic LLM for evaluating plans and actions
planner = Planner(planner_llm)  # Planner instance that uses the planner LLM service

confirmation_manager = ConfirmationManager()


# This defines what input structure FastAPI expects :
class ChatRequest(BaseModel) :
    ''' this will accept user_id and message as string '''
    user_id : str
    message : str 

# Main chat endpoint :

"""This is the main chat endpoint.
 It receives a user message, passes it to the agent core, 
and returns the agent's response.
 The agent core will handle the logic of interacting with the LLM."""

@router.post("/chat") 
async def chat(
    request : ChatRequest,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    """ This is the main chat endpoint. It receives a user message, passes it to the agent core,
      and returns the agent's response. """
    
    # Building the tools registry , we are passing the memory to the tools registry so that the tools can use it .
    tools_registry = bulid_tools_registry(db)

    # Executor instance :
    executor = Executor(tools_registry, critic_service)

    # Orchestrator instance :
    orchestrator = Orchestrator(
        planner , executor , confirmation_manager)
    
    # Handling the incoming message through the orchestrator :
    response = await orchestrator.handle_message(
        request.user_id,
        request.message,
        db
    )

    if isinstance(response, dict) and "run_id" in response:
        return {
            "response" : response["response"],
            "run_id" : response["run_id"],}
    return {
        "response" : response,
        "run_id" : None,
    }

class FeedbackRequest(BaseModel) :
    ''' this will accept run_id and feedback as string '''
    run_id : int
    user_id : str
    was_correct : bool
    correction : str | None = None


@router.post("/feedback")
async def record_feedback(
    request : FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
) :
    ''' This endpoint will receive feedback from the user regarding a specific agent run, and it will record that feedback in the database. '''
    
    outcomes_repo = AgentOutcomesRepository(db)
    outcome = await outcomes_repo.get_by_run(request.run_id, request.user_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")

    # Update the canonical per-run outcome first.
    updated = await outcomes_repo.apply_feedback(
        run_id = request.run_id,
        user_id = request.user_id,
        was_correct = request.was_correct,
        correction = request.correction
    )

    if not updated:
        raise HTTPException(status_code=409, detail="Unable to apply feedback for this run")

    # Persist the human feedback event so confidence remains feedback-driven.
    feedback_repo = AgentFeedbackRepository(db)
    await feedback_repo.record_feedback(
        user_id=request.user_id,
        run_id=request.run_id,
        domain=outcome.domain,
        task_type=outcome.task_type,
        was_correct=request.was_correct,
        correction=request.correction,
    )

    return {"status" : "feedback recorded successfully"}









"""@router.get("/debug/projects")
async def create_projects(memory: MemoryManager = Depends(get_memory)):
projects = await memory.list_projects("rahul")
return projects
# temp endpoint to test create_confirmation :
@router.post("/debug/confirmations")
async def create_confirmation(user_id: str, action: str, parameters: dict, memory: MemoryManager = Depends(get_memory)):
await memory.create_confirmation(user_id, action, parameters)
return {"status": "confirmation created"}

# temp endpoint to test logging expenses :
@router.post("/debug/log_expense")
async def log_expense(user_id: str, amount: float, category: str, note: str | None = None, memory: MemoryManager = Depends(get_memory)):
expense_id = await memory.log_expense(user_id, amount, category, note)
return {"status": "expense logged", "expense_id": expense_i# temp endpoint to test analyzing expenses :
@router.get("/debug/analyze_expenses")
async def analyze_expenses(user_id: str, period: str | None = None, category: str | None = None, memory: MemoryManager = Depends(get_memory)):
total = await memory.get_total_expenses(user_id, period, category)
return {"total_expenses": total}"""