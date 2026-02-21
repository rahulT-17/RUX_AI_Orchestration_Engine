from fastapi import APIRouter
from pydantic import BaseModel
from services.llm_services import LLMService
from memory.memory_manager import MemoryManager
from core.config import LM_STUDIO_URL

# Creating a router instance (this groups related endpoints) :
router = APIRouter()

# Creating a services instances (these are reusable objects) :
llm_service = LLMService(LM_STUDIO_URL)
memory_manager = MemoryManager()

# This defines what input structure FastAPI expects :
class ChatRequest(BaseModel) :
    ''' this will accept user_id and message as string '''
    user_id : str
    message : str 

@router.post("/chat") 
async def chat(request: ChatRequest) :
    """ 
    
    This function runs when a POST request is sent to /chat
    
     """
    # 1. Making sure that the database table exists 
    await memory_manager.init_db()

    # 2. Get user name from database 
    name = await memory_manager.get_user(request.user_id)

    # 3. Building system_prompt :
    system_prompt =  f'''
                You are RUX DevAgent.
                The user's name is: {name}
                Be calm , helpful and technical.      
                '''
    # 4. Asking the LLM to generate response :
    reply = await llm_service.generate(system_prompt, request.message)

    # 5. Return response as JSON 
    return {"reply": reply}