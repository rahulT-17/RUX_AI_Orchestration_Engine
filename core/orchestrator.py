# CORE / orchestrator.py => New Agent_core the Orchestrator class which is responsible for managing the overall flow of the AI companion system. 
# It coordinates between different components like the state manager, memory manager, and confirmation manager.

from core.execution_state import ExecutionState

# repositries and models :
from repositories.user_repository import UserRepository

class Orchestrator:
    def __init__(self , planner , executor , confirmation_manager )   :
        self.planner = planner
        self.executor = executor
        self.confirmation_manager = confirmation_manager

    async def handle_message(self, user_id , message , db ) :

        # Ensure the user exists in the database, if not create a new user. This is important because we want to have a record of all users interacting with the system for future reference and to associate their actions and confirmations with their user ID.
        user_repo = UserRepository(db)
        await user_repo.get_or_create(user_id)
        
        # Step 1 : Create a new execution state for the incoming message :
        state = ExecutionState(user_id , message)
        
        # Confirmation handling logic : Check if there is a pending confirmation for the user, if yes, we will handle the confirmation response and return the result without going through the planning and execution stages.
        confirm_result = await self.confirmation_manager.handle(
            state , db , self.executor.tools_registry)
        
        if confirm_result :            # if there was a pending confirmation and we handled it, we will return the result of the confirmation handling (either the tool execution result or a cancellation message) without proceeding to planning and execution stages.
            return {
                "response": confirm_result,
                "run_id": None,
                "action": "confirmation"
            }
        
        # Step 2 : Planning stage : Call the planner to analyze the user message and determine if any action is required, the planner will return the parsed action and parameters if an action is required, or None if no action is required and the message should be treated as a normal reply.
        state , normal_reply = await self.planner.plan(state)

        if normal_reply :
            return {
                "response": normal_reply,
                "run_id": None,
                "action": "conversational"
            }                               # if no action is required, we will return the original message as a normal reply.
        
        
        # Step 3 : Execution stage : If the planner returned an action to execute, we will call the executor to execute the action using the tools registry and return the result.

        result = await self.executor.execute(state , db)

        return {
            "response": result,
            "action": state.action
        }

        
