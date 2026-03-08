# Introducing the ExecutionState class to manage the execution state of the agent.

""" Context Object Pattern : This pattern is useful for managing complex state and passing it through different stages of execution without having to pass 
   multiple parameters around.

   The ExecutionState class will hold all relevant information about the current execution instance, including the user message, the current stage of execution, 
   any outputs from the planner, validated parameters, tool results, and any errors that may occur."""

import uuid # for generating unique trace ids for each execution instance
from datetime import datetime 

class ExecutionState:
    def __init__(self, user_id: str , message : str):

        self.trace_id = str(uuid.uuid4())
        self.user_id = user_id
        self.message = message
        
        # filled by planner 
        self.action = None
        self.parameters = {}
        
        # filled by executor
        
        self.planner_output = None
        self.validated_params = None
        self.tool_result = None
        
        # Tracking
        self.stage = "INIT"
        self.error = None
        self.created_at = datetime.utcnow()
    
    def set_stage(self, stage: str): # this method is used to update the current stage of the execution, it can be used for logging and debugging purposes to track the flow of execution through different stages like "PLANNING", "VALIDATION", "EXECUTION" and "COMPLETED".
        self.stage = stage
        
    