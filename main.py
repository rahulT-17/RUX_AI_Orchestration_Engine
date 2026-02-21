from fastapi import FastAPI
from api.routes import router

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

@app.get("/")
def root() :
 return {"message" : "AI compainon backend is running "}