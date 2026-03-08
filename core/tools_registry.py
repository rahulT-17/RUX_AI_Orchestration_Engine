# core / tool registry.py :

""" This file defines the tools registry which is a central place to register all the tools that the agent can use to perform actions (create project, delete project, etc.)
 Each tool is defined with its function, input schema, risk level, and whether it requires confirmation before execution. The agent core will use this registry to look up and execute the appropriate tool based on the user message and the LLM response.
 The tools registry allows us to easily manage and organize the different actions that the agent can perform, and also to add new tools in the future without having to change the core logic of the agent. """

from turtle import st

from pydantic import BaseModel, Field
from typing import Callable, Dict , Any , Optional , Literal
from core.tools import Tool
from datetime import date

# Domain specified tools :
from services.expense_service import ExpenseService


# Repositories :
from repositories.project_repositories import ProjectRepository
from repositories.expense_repository import ExpenseRepository
from repositories.budget_repository import BudgetRepository

# schemas for the input parameters of the tools (these will be used for validation before executing the tool functions) :

class CreateProjectParams(BaseModel) :
    name : str
    description : str | None = None

    class Config :
        extra = "forbid"

class DeleteProjectParams(BaseModel) :
    project_id : int | None = None
    name : str | None = None

    class Config :
        extra = "forbid" # this will forbid any extra parameters other than project_id and name to be passed to the delete_project tool, this is important for validation and security reasons, we dont want the agent to pass any extra parameters that are not defined in the schema.

class ExpenseManagerParams(BaseModel) :
    action : Literal["log","analyze","set_budget","get_budget"]

    amount : Optional[float] = Field(None, gt=0)
    category : Optional[str] = None
    note : Optional[str] = None

    start_date : Optional[date] = None
    end_date : Optional[date] = None

    period : Optional[str] = None
    budget : Optional[float] = Field(None, gt=0)

    mode : Literal["hard","soft"] = "soft" # Default value here 

    class Config :
        extra = "forbid"

## Tools Resgistry == this will hold all the tools that the agent can use to perform actions (create project, delete project, etc.)

def bulid_tools_registry(db) :
    """ Passing memory as instance to the tools registry so that the tools 
    can use it to perform actions on the database (create project, delete project, etc.) """

    async def create_project_tool(user_id: str, params : CreateProjectParams, db) :

        """telling the memory layer to create a project for the user with the given name 
        and description, and return the project id"""
        
        repo = ProjectRepository(db)

        project_id = await repo.create_project(user_id = user_id, name = params.name, 
                                                 description = params.description)
        
        return f"Project '{params.name}' created successfully with ID: {project_id}"
    
    
    async def delete_project_tool(user_id: str, params : DeleteProjectParams, db) :

        repo = ProjectRepository(db)

        """Telling the memory layer to delete a project for the user with the given project_id/name
           deleting the projects by multiple cases to make it more flexible for the user, 
           they can provide either project_id or name to delete a project,
             if both are provided project_id will be used for deletion"""
           
        # Case 1 : if project_id is provided and is an integer, delete by project_id
        try :
           if params.project_id :
            success = await repo.delete_project(project_id = params.project_id)
            
            if not success : 
               return {"error" : f"No project found with ID {params.project_id}"}
            
            return f"Project with ID {params.project_id} deleted successfully"
        except ValueError :
            return {"error" : f"Invalid project_id {params.project_id}. It should be an integer."}
        
        # Case 2 : Delete by project name (if project_id is not provided or is invalid)
        try :
           if params.name :
              
            project = await repo.get_project(user_id = user_id, name = params.name)

            if not project :
                return {"error" : f"No project found with name '{params.name}' for the user."}
            
            success = await repo.delete_project(project.project_id)

            return f"Project '{params.name}' deleted successfully"
           
        except Exception as e :
            return {"error" : f"An error occurred while trying to delete the project: {str(e)}"}
        
    
    # Creating the Expense_Manager_tool :
    

    async def expense_manager_tool(user_id:str, params: ExpenseManagerParams, db) :

        expense_service = ExpenseService(db)
        result = None
         
        # SET BUDGET : 
        if params.action == "set_budget" :
           
           if params.budget is None or params.start_date is None or params.end_date is None or params.category is None :
              return "Budget, start_date, end_date and category are required."
           
           result = await expense_service.set_budget(
                user_id = user_id,
                category = params.category, # default category is general if not provided
                amount = params.budget,
                start_date = params.start_date,
                end_date = params.end_date
            )
           
        # GET BUDGET :
        elif params.action == "get_budget" :
            result = await expense_service.get_budget(user_id)
            
        
        # LOG EXPENSE : 
        elif params.action == "log" :
            if params.amount is None or params.category is None :
                return "amount and category required for log action"
            
            result = await expense_service.log_expense (
                user_id = user_id,
                amount = params.amount,
                category = params.category,
                note = params.note,
                mode = params.mode
            )

        # ANALYZE : 
        elif params.action == "analyze" :
            result = await expense_service.analyze_expense(
                user_id = user_id,
                period = params.period,
                category=params.category
            )
            
            if result["status"] == "success":
                total = result["total"]
                period = result.get("period") or "selected period"
                category = result.get("category")

                if category and period:
                    return f"Total expense for {category} in {period}: {total}"

                if category:
                    return f"Total expense for {category}: {total}"

                if period:
                    return f"Total expense in {period}: {total}"

                return f"Total expense: {total}"

            return "Unable to analyze expenses."
            
        
        else :
            return f"Invalid expense action : {params.action}"
        
        print("DEBUG RESULT:" , result)
        

        if not isinstance(result,dict) : 
           return f"Unexpected result format: {result}"
        
        status = result.get("status")

        if status == "logged":
          return f"Expense logged successfully."

        if status == "logged_with_warning":
          return (
            f"Expense logged but budget exceeded.\n"
            f"Current: {result['attempted_total']} / Budget: {result['budget']}")
        
        if status == "rejected":
          return (
            f"Expense rejected. Budget exceeded.\n"
            f"Current: {result['current_total']} / Budget: {result['budget']}")
        
        if status == "success":
          return result.get("message", "Success.")
        
        if status == "failed" :
           return result.get("reason" , "operation failed.")

        if status == "none":
          return result.get("message", "No data.")

        return f"Unhandled status: {status}"
            
         
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