# Purpose : To boot the system:

from fastapi import FastAPI
from api.routes import router
from api.projects_routes import router as project_router
from memory.memory_manager import get_memory

## APP CONFIGURATION :
''' upgrading the RUX to a devagent (02/2026,110 days) changing the
 whole architecture to router-based
'''

app = FastAPI(
    title="RUX DevAgent",
    version="2.0"
)

# connecting the app to api router :

app.include_router(router)
app.include_router(project_router)

@app.on_event("startup")
async def startup() :
    async for memory in get_memory() :
       await memory.init_db()

@app.get("/")
def root() :
 return {"message" : "RUX DevAgent backend is running "}