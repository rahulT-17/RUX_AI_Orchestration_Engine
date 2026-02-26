from fastapi import APIRouter, Depends
from memory.memory_manager import MemoryManager , get_memory

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/")
async def create_project(user_id: str, name: str, description: str | None = None, 
                         memory: MemoryManager = Depends(get_memory) ):
    
    project_id = await memory.create_project(user_id, name, description)
    return {"project_id": project_id} 

@router.get("/")
async def list_projects(user_id: str, memory: MemoryManager = Depends(get_memory) ):
    
    projects = await memory.list_projects(user_id,)
    return [dict(p) for p in projects]


@router.delete("/{project_id}")
async def delete_projects(
    project_id: int,
    memory: MemoryManager = Depends(get_memory)
):
    await memory.delete_project(project_id)
    return {"deleted": project_id}