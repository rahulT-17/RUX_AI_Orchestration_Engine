# api/routes.py

# Fast API router for handling incoming API requests related to the AI companion system :
from fastapi import APIRouter , Depends
from pydantic import BaseModel

# Importing the Orchestrator and its dependencies :
from services.llm_services import LLMService
from core.orchestrator import Orchestrator
from core.planner import Planner
from core.executor import Executor  
from core.confirmation_manager import ConfirmationManager
from core.tools_registry import bulid_tools_registry
from core.config import LM_STUDIO_URL

# memory manager and its dependency function to get the memory instance for each request :
from memory.memory_manager import MemoryManager, get_memory 



# Creating a router instance (this groups related endpoints) :

router = APIRouter(tags=["chat"])    # This tag is used for documentation purposes; it groups the endpoints under the 'chat' section in the API docs


# Creating a services instances (these are reusable objects) :
llm_service = LLMService(LM_STUDIO_URL)
planner = Planner(llm_service)
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
    memory : MemoryManager = Depends(get_memory) ):
    
    """ This is the main chat endpoint. It receives a user message, passes it to the agent core,
      and returns the agent's response. """
    
    # Building the tools registry , we are passing the memory to the tools registry so that the tools can use it .
    tools_registry = bulid_tools_registry(memory)

    # Executor instance :
    executator = Executor(tools_registry)

    # Orchestrator instance :
    orchestrator = Orchestrator(
        planner , executator , confirmation_manager)
    
    # Handling the incoming message through the orchestrator :
    response = await orchestrator.handle_message(
        request.user_id,
        request.message,
        memory 
    )

    return {"response" : response}

# == Debugging endpoints == these are temporary endpoints to test the functionality of the memory layer and the tools registry, they will be removed later once we confirm that everything is working fine.

# temporary endpoint to test if the API is working :

@router.get("/debug/projects")
async def list_projects(memory: MemoryManager = Depends(get_memory)):
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
    return {"status": "expense logged", "expense_id": expense_id}

# temp endpoint to test analyzing expenses :
@router.get("/debug/analyze_expenses")
async def analyze_expenses(user_id: str, period: str | None = None, category: str | None = None, memory: MemoryManager = Depends(get_memory)):
    total = await memory.get_total_expenses(user_id, period, category)
    return {"total_expenses": total}