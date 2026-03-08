# CORE / config.py => this file contains configuration variables for the application, such as the URL of the LM Studio service.

# This allows us to easily manage and change configurations in one place without having to search through the codebase.

LM_STUDIO_URL = "http://127.0.0.1:1234"

PLANNER_MODEL = "qwen/qwen3-vl-4b"  # This is the model used by the planner to generate plans. It can be changed to any compatible model as needed.

CRITIC_MODEL = "mistralai/mistral-7b-instruct-v0.3"  # This is the model used by the critic to evaluate plans and actions. It can also be changed to any compatible model as needed.