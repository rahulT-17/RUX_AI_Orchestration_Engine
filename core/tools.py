# CORE / tools.py => This is used for extracting tools related functions from agent_core.py to tools.py to make the code more modular and maintainable.

class Tool:
    def __init__(self, name , schema , function , requires_confirmation , risk) :
        self.name = name
        self.schema = schema 
        self.function = function
        self.requires_confirmation = requires_confirmation  
        self.risk = risk