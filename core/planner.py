# CORE / planner.py => This is used for extracting planner from agent_core.py 
# Spilting LLM call , json parsing and sechma validation from agent_core.py to planner.py to make the code more modular and maintainable.

import json
from json import JSONDecodeError
from core.execution_state import ExecutionState

class Planner :
        
    def __init__(self,llm_service) :
        self.llm_service = llm_service
    """
        Main brain function.

        1. Call LLM
        2. Try parsing structured JSON
        3. If action → validate & execute
        4. Else → return normal reply
        """
    async def plan(self, state : "ExecutionState") :
        state.set_stage("PLANNING")
            
        # Building system prompt for the agent to know how to respond and when to use tools :

        system_prompt = """ You are RUX DevAgent.

        Your main goal is to assist the user in managing their projects and tasks efficiently, and to perform actions on their behalf when required. 
        You have access to a set of tools that allow you to create and delete projects for the user.

        Always analyze the user message carefully to determine if an action is required. If the user is asking to create a project or delete a project, you should respond with the appropriate action and parameters in a structured JSON format.

        If NO ACTION is required or the user is just asking a question, respond normally , act calm and helpful, and do NOT return any JSON structure.

        DO NOT INVENT AN ACTION, and DO NOT RETURN ANYTHING OTHER THAN THE JSON STRUCTURE IF AN ACTION IS REQUIRED.
        Always respond in the format specified below if an action is required.
        
        log_expense action is used to log an expense for the user, it takes amount, category and note as parameters and logs the expense in the memory, this action does not require confirmation before execution because it is a low risk action.

        These are the ALLOWED ACTIONS you can perform :
        - create_project 
        - delete_project
        - expense_manager ( If users wants to log expense you would correctly parse for example: ({
                                                                                                    "action": "expense_manager",
                                                                                                    "parameters": {
                                                                                                                    "action": "log",
                                                                                                                    "amount": 50,
                                                                                                                    "category": "food" }
                                                                                                                    }
                                                                                                }) )
   
        If the user message requires an action
        return ONLY valid JSON in this format:

        {
          "action": "<one of the allowed actions>",
          "parameters": { ... }
        }

        

        """
        # Calling the LLM to generate a response based on the user message and system prompt
        reply = await self.llm_service.generate(system_prompt, state.message)

        # Trying to parse the LLM response as JSON to check if it contains an action to execute
        try : 
            parsed = json.loads(reply)

            # if no action is required, return the normal reply
            if "action" not in parsed :
                return None,reply
            
            state.planner_output = parsed
            state.set_stage("PLANNING_COMPLETED")

            return parsed, None
        
        except JSONDecodeError :
         # if response is not a valid JSON , return None to indicate that no action is required and the response should be treated as a normal reply
            return None,reply
        