# CORE / executor.py => This file is responsible for executing the tools based on the planner's output and managing the execution flow, including handling confirmations for high-risk actions.


import time

# Repositories:
from repositories.confirmation_repository import ConfirmationRepository
from repositories.agent_run_repository import AgentRunRepository
from repositories.agent_outcomes_repository import AgentOutcomesRepository

# services :
from services.confidence_service import ConfidenceService
from services.decision_engine import DecisionEngine


class Executor:
    def __init__(self ,tools_registry, critic_service) :
        self.tools_registry = tools_registry
        self.critic_service = critic_service
    
    async def execute(self, state , db) :
        state.set_stage("EXECUTING")
        
        if not state.planner_output:
            return "Nothing to execute"
        
        action_name = state.planner_output["action"]
        parameters = state.planner_output.get("parameters", {})

        

        tool = self.tools_registry.get(action_name)

        print("DEBUG PLANNER OUTPUT:", state.planner_output)  # Debugging line to check the planner output before execution
          
        # Adding validation and confirmation logic block for tools that require confirmation before execution :
        if not tool :
            state.error = f"Error: Action '{action_name}' is not recognized."
            return state.error

        # try and except for validating the parameters using the tool's schema, if validation fails, we will return an error message and not execute the tool function.
        try :
            validated = tool.schema(**parameters)
        
        except Exception as e :
            return f"Error: Invalid parameters for action '{action_name}'. Details: {str(e)}"

        # If the tool requires confirmation before execution, we will save the pending confirmation in the memory and return a message to the user asking for confirmation.
        if tool.requires_confirmation :
            repo = ConfirmationRepository(db)

            await repo.create(
                user_id = state.user_id,
                action = action_name,
                parameters = parameters
            )
            return f"Confirmation required for '{action_name}' action. Reply (yes/no)"
        
         # Tool Execution :
        start = time.time()
        
        try :
            # Execute the tool function :

            result = await tool.function(state.user_id, validated,db)
            
        except Exception as e :
            
            latency = time.time() - start
            error_message = f"Execution error : {str(e)}"
            
            # Observability - Log the failed agent run details in the database for monitoring and debugging purposes.
            agentrun_repo = AgentRunRepository(db)

            await agentrun_repo.log_run(
                user_id=state.user_id,
                message=state.message,
                action=action_name,
                parameters=parameters,
                result=error_message,
                latency=latency
            )

            return error_message
            
        latency = time.time() - start

        state.tool_result = result  
        state.set_stage("EXECUTION_COMPLETED")

        # domain + task detection 

        domain_map = {
            "expense_manager" : "expense",
            "create_project" : "project",
            "delete_project" : "project"
        }
        domain = domain_map.get(action_name, "general")
        
        task_type = parameters.get("action", action_name)  # Use specific task_type if provided, otherwise default to action_name

        # ------
        # Observability Logging  - Log the agent run details in the database for monitoring and debugging purposes 
        # ------

        agentrun_repo = AgentRunRepository(db)
        
        run_id = await agentrun_repo.log_run(
            user_id=state.user_id,
            message=state.message,
            action=action_name,
            parameters=parameters,
            result=result,
            latency=latency
        )
        
        # Outcome Recording for Feedback and Confidence Estimation :

        auto_correct = False

        if domain == "expense" and task_type in ["log", "set_budget", "anaylze"]: 
            auto_correct = True

        elif domain == "project" and task_type in ["create_project", "delete_project"] :
            auto_correct = True


        # 
        outcome_repo = AgentOutcomesRepository(db)

        await outcome_repo.record_outcome(
            run_id=run_id,
            user_id=state.user_id,
            domain = domain,
            task_type = task_type,
            was_correct = auto_correct)
        
        # Decision engine :

        decision_engine = DecisionEngine(db, self.critic_service)

        analysis = await decision_engine.evaluate(
            state.user_id,
            state.message,
            domain,
            task_type,
            result
        )
            

        # Confidence Engine :
        confidence_service = ConfidenceService(db)

        confidence = await confidence_service.get_confidence(
            state.user_id, 
            domain, 
            task_type
        
        )

        # response Builder :

        response = str(result)

        if analysis["system_analysis"] :
            response += f"\n\nObservation:\n{analysis['system_analysis']}"

        if analysis["critic_analysis"] :
            response += f"\n\nSecond Opinion:\n{analysis['critic_analysis']}"

        if confidence["confidence"] is None  :
            response += f"{result}\n\nConfidence: insufficient data ({confidence['samples']}samples)"
            
        else :

            response +=  f"\n\nConfidence: Confidence: {confidence['confidence']}%  (based on {confidence['samples']} runs)"
                
                
                
        return response
            
            
            
       
        
        
        