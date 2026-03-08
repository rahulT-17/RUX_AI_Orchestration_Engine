# api / debug_routes.py : This file is used for defining debug routes for testing and debugging purposes.
# These routes are not meant for production use and should be used with caution.

from fastapi import APIRouter , Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from services.confidence_service import ConfidenceService

from database import get_db
from models import AgentRun, Agent_Outcomes



router = APIRouter(prefix="/debug", tags=["Observability"])    # This tag is used for documentation purposes; it groups the endpoints under the 'debug' section in the API docs

@router.get("/runs")
async def get_recent_runs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Endpoint to retrieve recent agent runs for debugging purposes.
        Here the query retrieves the most recent agent runs from the db, (20 by default) 
        and returns them as a list of AgentRun objects."""
    
    query = (
        select(AgentRun)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    runs = result.scalars().all() # scalars() is used to extract the AgentRun objects from the result set, and all() retrieves them as a list.

    return runs 

@router.get("/slow_runs")
async def get_slow_runs( db: AsyncSession = Depends(get_db)):
    """This Endpoint serves the purpose of debugging and monitoring slow running tools by returning the latency of the agents runs"""
    query = (
        select(AgentRun)
        .where(AgentRun.latency > 1)
        .order_by(AgentRun.latency.desc())
    )

    result = await db.execute(query)

    runs = result.scalars().all() # scalars() is used to extract the AgentRun objects from the result set, and all() retrieves them as a list.
    return runs

@router.get("/outcomes")
async def get_recent_outcomes(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Endpoint to retrieve recent agent outcomes for debugging purposes.
        Here the query retrieves the most recent agent outcomes from the db, (20 by default) 
        and returns them as a list of Agent_Outcomes objects."""
    
    query = (
        select(Agent_Outcomes)
        .order_by(Agent_Outcomes.created_at.desc())
        .limit(20)
    )

    result = await db.execute(query)
    outcomes = result.scalars().all() # scalars() is used to extract the Agent_Outcomes objects from the result set, and all() retrieves them as a list.

    return outcomes

@router.get("/confidence")
async def get_confidence(
    user_id: str, 
    domain: str,
    task_type: str, 
    db: AsyncSession = Depends(get_db)
    ):

    """Endpoint to retrieve confidence level for a specific user, domain, and task type.
        This endpoint uses the ConfidenceService to calculate and return the confidence level based on user feedback."""
    
    service = ConfidenceService(db)

    result = await service.get_confidence(user_id, domain, task_type)

    return result

