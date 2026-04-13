from core.tools import Tool
from core.tool_response import ToolResponse, ToolStatus
from domains.project.schemas import CreateProjectParams, DeleteProjectParams
from domains.project.service import ProjectService


# Tool adapters map validated planner params to service calls
# and normalize service outputs into ToolResponse.
async def create_project_tool(user_id: str, params: CreateProjectParams, db):
    service = ProjectService(db)
    result = await service.create_project(
        user_id=user_id,
        name=params.name,
        description=params.description,
    )

    if not isinstance(result, dict) or result.get("status") != "success":
        error = result.get("error", "Project creation failed") if isinstance(result, dict) else "Project creation failed"
        return ToolResponse(
            status=ToolStatus.FAILED,
            message=error,
            error=error,
        )

    return ToolResponse(
        status=ToolStatus.SUCCESS,
        message=result.get("message", "Project created successfully."),
        data={"project_id": result.get("project_id")},
    )


async def delete_project_tool(user_id: str, params: DeleteProjectParams, db):
    service = ProjectService(db)
    result = await service.delete_project(
        user_id=user_id,
        project_id=params.project_id,
        name=params.name,
    )

    if not isinstance(result, dict) or result.get("status") != "success":
        error = result.get("error", "Project deletion failed") if isinstance(result, dict) else "Project deletion failed"
        return ToolResponse(
            status=ToolStatus.FAILED,
            message=error,
            error=error,
        )

    return ToolResponse(
        status=ToolStatus.SUCCESS,
        message=result.get("message", "Project deleted successfully."),
        data={"project_id": result.get("project_id")},
    )

# Registers project tools with runtime metadata.
def build_project_tools():
    return {
        "create_project": Tool(
            name="create_project",
            function=create_project_tool,
            schema=CreateProjectParams,
            domain="project",
            task_type="create_project",
            risk="low",
            requires_confirmation=False,
        ),
        "delete_project": Tool(
            name="delete_project",
            function=delete_project_tool,
            schema=DeleteProjectParams,
            domain="project",
            task_type="delete_project",
            risk="high",
            requires_confirmation=True,
        ),
    }
