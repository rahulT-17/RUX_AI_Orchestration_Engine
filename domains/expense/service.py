""" domains / expense / service.py : This file is responsible for implementing the business logic related to expenses and budgets,
 such as setting budgets, logging expenses, and analyzing spending patterns.
  It acts as an intermediary between the API endpoints and the database repos :"""

from datetime import date

from domains.expense.repository import ExpenseRepository, BudgetRepository

class ExpenseService :
    def __init__(self, db):
        self.expense_repo = ExpenseRepository(db)
        self.budget_repo = BudgetRepository(db)

    async def set_budget(self, user_id: str, category: str, amount: float, start_date: str, end_date: str ) :

        
        if category is None or not category.strip() :
            return {
                "status" : "failed",
                "reason" : "Category is required for budget."
        }
        
        category = category.strip().lower()

        # Required Fields check FIRST :
        if amount is None or  start_date is None or  end_date is None :
            return {
                "status": "failed",
                "reason": "budget, start_date and end_date are required."
        }
        
      
        try:
            start = start_date
            end = end_date

        except (ValueError,TypeError):
         return {
            "status": "failed",
            "reason": "Invalid date format. Use YYYY-MM-DD."
        }

        # Logical Ordering validation :

        if start > end:
         return {
           "status": "failed",
           "reason": "Start date cannot be after end date."
        } 
        
        # Now safe to persist :

        budget = await self.budget_repo.create_budget(
            user_id = user_id,
            category=category,
            amount=amount, 
            start_date=start,
            end_date=end
        )
       
        # If budget is None, it means there was an overlap and we should inform the user about it:
        
        if not budget :
            return {
                "status" : "failed",
                "reason" : "Oops, it seems like you got an overlapping budget already."
            }
        
        return {
            "status" : "success",
            "message" : "Budget created successfully",
            "amount" : amount,
            "start_date" : start.isoformat(),
            "end_date" : end.isoformat(),
        }

    # Get active budget for a user and category on a specific date (usually today):
    async def get_budget(self, user_id: str, category: str | None=None) :
        today = date.today()

        if not category :
            return {
                "status" : "failed",
                "reason" : "Category is required to check budget."
            }
        
        category = category.strip().lower()
        
        budget = await self.budget_repo.get_active_budget(
            user_id=user_id,
            category=category,
            today=today
        )

        if not budget :
            return {
                "status" : "none" ,
                "message" : "No active budget."
            }
        
        return {
            "status": "success",
            "message": f"Active budget: {budget.amount} from {budget.start_date} to {budget.end_date}",
            "amount": budget.amount,
            "start_date" : budget.start_date,
            "end_date" : budget.end_date
        }   

    async def log_expense(self, user_id, amount, category, note, mode="soft") :

        today = date.today()

        if not isinstance(amount,(int,float)) :
           return {
              "status" : "failed",
              "reason" : "Amount must be numeric."
           }
        if amount <= 0 :
           return {
              "status" : "failed",
              "reason" : "Amount must be greater than 0."
           }
        
        if not isinstance(category,str) :
           return {
              "status" : "failed" ,
              "reason" : "Category must be a string"
           }
        category = category.strip().lower()

        budget = await self.budget_repo.get_active_budget(
            user_id=user_id,
            category=category,
            today=today
        )
        # IF no active budget -> normal logging :
        if not budget :
            expense = await self.expense_repo.log_expense( 
                user_id=user_id,
                amount=amount,
                category=category, 
                note=note)
            return {
                "status" : "logged",
                "expense_id" :expense.expense_id,
                "message" : "Expense logged (no active budget)"
            }
        # IF budget exists => Enforce policy :
        start_date = budget.start_date
        end_date = budget.end_date 
        budget_amount = budget.amount

        current_total = await self.expense_repo.get_total_between(
            user_id=user_id,
            category=category,
            start_date=budget.start_date,
            end_date=budget.end_date
        )
        
        # Projected Total :
        projected_total = current_total + amount 
        
        # hard => reject if projected total exceeds budget
        # soft => log anyway but with a warning about budget breach
        try:  # hard 
            if projected_total > budget_amount:
                if mode == "hard":
                    return {
                        "status": "rejected",
                        "reason": "Budget exceeded.",
                        "current_total": current_total,
                        "budget": budget_amount,
                        "attempted_total": projected_total
                    }
                else:  # soft
                    expense = await self.expense_repo.log_expense(user_id=user_id, amount=amount, category=category, note=note)
                    return {
                        "status": "logged_with_warning",
                        "expense_id": expense.expense_id,
                        "reason": "Budget exceeded.",
                        "current_total": current_total,
                        "budget": budget_amount,
                        "attempted_total": projected_total
                    }

            elif projected_total == budget_amount:
                expense = await self.expense_repo.log_expense(
                    user_id=user_id, 
                    amount=amount, 
                    category=category, 
                    note=note)
                return {
                    "status": "logged_with_warning",
                    "expense_id": expense.expense_id,
                    "reason": "Budget exactly reached.",
                    "current_total": current_total,
                    "budget": budget_amount,
                    "attempted_total": projected_total
                }

            else:  # within budget
                expense = await self.expense_repo.log_expense(
                    user_id=user_id, 
                    amount=amount, 
                    category=category, 
                    note=note)
                return {
                    "status": "logged",
                    "expense_id": expense.expense_id,
                    "current_total": current_total,
                    "budget": budget_amount,
                    "attempted_total": projected_total
                }
            
        except Exception as e : 
            return {
            "status": "failed",
            "reason": f"Unexpected error during expense logging: {e}"
        }
                
    async def analyze_expense(self, user_id: str, period: str | None, category: str | None):
    
        # parse period into date range if provided
        today = date.today()
        start_date = None
        end_date = None

        if period == "this month":
            start_date = today.replace(day=1)
            end_date = today
        elif period == "this week":
            start_date = today.replace(day=today.day - today.weekday())
            end_date = today
        elif period == "today":
            start_date = today
            end_date = today

        total = await self.expense_repo.get_total_by_period(
            user_id=user_id,
            category=category,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "status": "success",
            "total": total,
            "period": period or "all time",
            "category": category or "all categories"
        }
        
        