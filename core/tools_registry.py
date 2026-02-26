# core / tool registry.py :

""" This file defines the tools registry which is a central place to register all the tools that the agent can use to perform actions (create project, delete project, etc.)
 Each tool is defined with its function, input schema, risk level, and whether it requires confirmation before execution. The agent core will use this registry to look up and execute the appropriate tool based on the user message and the LLM response.
 The tools registry allows us to easily manage and organize the different actions that the agent can perform, and also to add new tools in the future without having to change the core logic of the agent. """

from pydantic import BaseModel, Field
from typing import Callable, Dict , Any , Optional , Literal
from core.tools import Tool

# Domain specified tools :
from services.expense_service import ExpenseService


# schemas for the input parameters of the tools (these will be used for validation before executing the tool functions) :

class CreateProjectParams(BaseModel) :
    name : str
    description : str | None = None

class DeleteProjectParams(BaseModel) :
    project_id : int | None = None
    project_name : str | None = None

    class Config :
        extra = "forbid" # this will forbid any extra parameters other than project_id and project_name to be passed to the delete_project tool, this is important for validation and security reasons, we dont want the agent to pass any extra parameters that are not defined in the schema.

class ExpenseManagerParams(BaseModel) :
    action : Literal["log","analyze"]
    amount : Optional[float] = Field(None, gt=0)
    category : Optional[str] = None
    note : Optional[str] = None
    period : Optional[str] = None

    class Config :
        extra = "forbid"

## Tools Resgistry == this will hold all the tools that the agent can use to perform actions (create project, delete project, etc.)

def bulid_tools_registry(memory) :
    """ Passing memory as instance to the tools registry so that the tools 
    can use it to perform actions on the database (create project, delete project, etc.) """

    async def create_project_tool(user_id: str, params : CreateProjectParams) :

        """telling the memory layer to create a project for the user with the given name 
        and description, and return the project id"""

        project_id = await memory.create_project(user_id = user_id, name = params.name, 
                                                 description = params.description)
        
        return f"Project '{params.name}' created successfully with ID: {project_id}"
    
    
    async def delete_project_tool(user_id: str, params : DeleteProjectParams) :

        """Telling the memory layer to delete a project for the user with the given project_id/name
           deleting the projects by multiple cases to make it more flexible for the user, 
           they can provide either project_id or project_name to delete a project,
             if both are provided project_id will be used for deletion"""
           
        # Case 1 : if project_id is provided and is an integer, delete by project_id
        try :
           if params.project_id :
            success = await memory.delete_project(project_id = params.project_id)
            
            if not success : 
               return {"error" : f"No project found with ID {params.project_id}"}
            
            return f"Project with ID {params.project_id} deleted successfully"
        except ValueError :
            return {"error" : f"Invalid project_id {params.project_id}. It should be an integer."}
        
        # Case 2 : Delete by project name (if project_id is not provided or is invalid)
        try :
           if params.project_name :
              
              project = await memory.get_project_by_name(user_id = user_id, project_name = params.project_name)

              if not project :
                 return {"error" : f"No project found with name '{params.project_name}' for the user."}
              
              success = await memory.delete_project(project["project_id"])

              return f"Project '{params.project_name}' deleted successfully"
           
        except Exception as e :
            return {"error" : f"An error occurred while trying to delete the project: {str(e)}"}
        
    
    # Creating the Expense_Manager_tool :
    expense_service = ExpenseService(memory)

    async def expense_manager_tool(user_id:str, params: ExpenseManagerParams) :
        if params.action == 'log' :
            if not params.action or not params.category:
                raise ValueError ("amount and category required for log action")
            
            expense_id = await expense_service.log_expense (
                user_id,
                params.amount,
                params.category,
                params.note
            )

            return f"Expense logged succesfully with ID : {expense_id}"
        
        elif params.action == "analyze" :
            total = await expense_service.analyze_expense(
                user_id,
                params.period,
                params.category
            )
            
            return f"Total expense : {total}"
            
        
        
         
    # This block is where we register all the tools that the agent can use, we define the function to execute, the input schema for validation, 
    # the risk level of the tool, and whether it requires confirmation before execution or not. The agent core will use this registry to look up and execute the appropriate tool based on the user message and the LLM response.
    
    return {

        "create_project" : Tool(
            name="create_project",
            function=create_project_tool,
            schema=CreateProjectParams,     # this is the schema for the input parameters of the create_project tool
            risk="low", # this is a low risk tool because it only creates a project and doesnt perform any destructive action
            requires_confirmation=False, # this tool doesnt require confirmation before execution because it is a low risk
        ),

        "delete_project" : Tool(
            name="delete_project",
            function=delete_project_tool,   
            schema=DeleteProjectParams,   # this is the schema for the input parameters of the delete_project tool.
            risk="high", # this is a high risk tool because it deletes a project and can cause data loss if used incorrectly.
            requires_confirmation=True, # this tool requires confirmation before execution because it is a high risk.
        ),

        "expense_manager" : Tool(
            name="expense_manager",
            function=expense_manager_tool,
            schema=ExpenseManagerParams,   # this is the schema for the input parameters of the expensemanager tool.
            risk="low", # this is a low risk tool because it only logs an expense and doesnt perform any destructive action.
            requires_confirmation=False, # this tool doesnt require confirmation before execution because it is a low risk.
        ),

    }