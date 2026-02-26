# services/llm_services.py => defines the LLMService class which is responsible for interacting with the language model (LM Studio in this case). It has a method to generate responses based on a system prompt and user message. 
# This service layer isolates the LM logic from the API routes, making it easier to swap out the model provider or test the agent core without relying on the actual LM """

import httpx


## Service layer isolates LM logic from API routes.
# Makes model provider swappable and easier to test.
class LLMService :
    def __init__(self, base_url:str):
          self.base_url = base_url
    
    async def generate(self,system_prompt:str , user_message:str) -> str :
      payload = {
        "model" : "local-model",
        "messages" : [
            {"role" : "system", "content": system_prompt},
            {"role" : "user", "content":user_message}
        ],
        "temperature" : 0.4,
        "max_tokens" : 300
    }
      async with httpx.AsyncClient(timeout=120.0) as client :
        response = await client.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()