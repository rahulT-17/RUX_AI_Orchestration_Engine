# Decision Engine for evaluating and selecting the best course of action :

from core.tool_response import ToolResponse, ToolStatus

class DecisionEngine :

    def __init__ (self, critic_service) :
        self.critic_service = critic_service


    async def evaluate(self, user_id, message, domain, task_type, result: ToolResponse):
        """
        Generates system reasoning and LLM-based critique for the given
        user message, classified task, and normalized tool result.
        """
        
        # Deterministic reasoning runs first so we always have a local explanation path.
        system_analysis = await self.system_reasoning(domain, task_type, result)

        # Critic runs as a second opinion layer for important domains.
        critic_analysis = None

        # Only call critic for important domains
        if domain in ["expense", "project"] :
            critic_analysis = await self.critic_service.critique(
                message,
                domain,
                task_type,
                result.to_dict(),
            )
    
        return {
            "system_analysis" : system_analysis,
            "critic_analysis" : critic_analysis
        }
    
    async def system_reasoning(self, domain, task_type, result: ToolResponse) :

        """
        Deterministic reasoning based on normalized ToolResponse.
        This keeps rule-based explanations separate from LLM critique.
        """

        if domain == "expense" :
             
            if task_type == "log" :
                if result.status == ToolStatus.PARTIAL :
                    warning = None 
                    if result.metadata :
                        warning = result.metadata.get("warning")
                    return warning or result.message 
                
                if result.status == ToolStatus.FAILED:
                    return result.message
                return None
            
            elif task_type == "set_budget" :
                if result.status == ToolStatus.SUCCESS :
                    return "Budget set. Future expenses in this category will be validated against it."
                return result.message 
            
            elif task_type == "analyze" :
                if result.status == ToolStatus.SUCCESS and result.data :
                    category= result.data.get("category", "all categories")
                    period = result.data.get("period", "all time")
                    return f"Analysis complete for {category} over {period}."
                return None
            
            elif task_type == "get_budget" :
                return None 
            
        if domain == "project" :
            if task_type == "create_project":
                return None

            elif task_type == "delete_project":
                return "Project deletion is irreversible."

        return None
