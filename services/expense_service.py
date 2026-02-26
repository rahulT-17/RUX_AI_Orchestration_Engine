# shifting to domain specified tools : Expense Service 

class ExpenseService :
    def __init__(self, memory):
        self.memory = memory 

    async def log_expense(self, user_id, amount, category, note) :
        return await self.memory.log_expense(
                user_id = user_id,
                amount = amount,
                category = category,
                note = note
        )
    
    async def analyze_expense(self, user_id, period=None, category= None) :
        return await self.memory.get_total_expenses(
            user_id = user_id,
            period = period,
            category = category
        )