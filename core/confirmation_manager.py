# Core / confirmation_manager.py => defines the ConfirmationManager class which is responsible for handling the confirmation process for high-risk actions which is sent by the "Executator" when a tool that requires confirmation is about to be executed. 
# It manages the pending confirmations in the memory and processes the user's response to either confirm or reject the action.

class ConfirmationManager: 

    async def handle(self, state, memory , tools_registry) :
        pending = await memory.get_pending_confirmation(state.user_id)

        if not pending :
            return None 
        
        reply = state.message.strip().lower()

        if reply == "yes" :
            tool = tools_registry.get(pending["action"])    

            parameters = pending["parameters"]

            validated = tool.schema(**parameters)

            result = await tool.function(state.user_id, validated)

            await memory.mark_confirmation_executed(pending["confirmation_id"])

            return result
        
        elif reply == "no" :
            await memory.mark_confirmation_rejected(pending["confirmation_id"])
            return "Action cancelled as per your request."
        
        else :
            return "You have a pending confirmation. Please reply with 'yes' or 'no'."

 
    