# CORE / executor.py => This file is responsible for executing the tools based on the planner's output and managing the execution flow, including handling confirmations for high-risk actions.

class Executor:
    def __init__(self ,tools_registry) :
        self.tools_registry = tools_registry
    
    async def execute(self, state , memory) :
        state.set_stage("EXECUTING")
   
        action_name = state.planner_output["action"]
        parameters = state.planner_output.get("parameters", {})

        tool = self.tools_registry.get(action_name)

        # Adding validation and confirmation logic block for tools that require confirmation before execution :
        if not tool :
            state.error = f"Error: Action '{action_name}' is not recognized."
            return state.error
        
        # try and except for validating the parameters using the tool's schema, if validation fails, we will return an error message and not execute the tool function.
        try :
            validated = tool.schema(**parameters)
            state.validated_params = validated
        
        except Exception as e :
            state.error = f"Error: Invalid parameters for action '{action_name}'. Details: {str(e)}"

        # If the tool requires confirmation before execution, we will save the pending confirmation in the memory and return a message to the user asking for confirmation.
        if tool.requires_confirmation :
            await memory.create_confirmation (
                user_id = state.user_id,
                action = action_name,
                parameters = parameters,
            )
            return f"Confirmation required for '{action_name}' action. Reply (yes/no)"
        
        result = await tool.function(state.user_id, validated)
        state.tool_result = result  
        state.set_stage("EXECUTION_COMPLETED")

        return result
    

        

        