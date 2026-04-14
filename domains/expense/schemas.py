# domains / expense / schemas.py : This file is responsible for defining the schemas for the expense manager tool.

from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, Literal
from datetime import date


# Schema for the input parameters of the expense manager tool :
class ExpenseManagerParams(BaseModel) :
    action : Literal["log","analyze","set_budget","get_budget"]

    amount : Optional[float] = Field(None, gt=0)
    category : Optional[str] = None
    note : Optional[str] = None

    start_date : Optional[date] = None
    end_date : Optional[date] = None

    period : Optional[str] = None
    budget : Optional[float] = Field(None, gt=0)

    mode : Literal["hard","soft"] = "soft" # Default value here 

    model_config = ConfigDict(
        extra="forbid")

    @model_validator(mode="after")
    def validate_by_action(self):
        if self.action == "set_budget":
            missing = []
            if not self.category or not self.category.strip():
                missing.append("category")
            if self.budget is None:
                missing.append("budget")
            if self.start_date is None:
                missing.append("start_date")
            if self.end_date is None:
                missing.append("end_date")

            if missing:
                raise ValueError(
                    f"Missing required fields for set_budget: {', '.join(missing)}"
                )

        if self.action == "get_budget":
            missing = []
            if not self.category or not self.category.strip():
                missing.append("category")

            forbidden = []
            if self.budget is not None:
                forbidden.append("budget")
            if self.start_date is not None:
                forbidden.append("start_date")
            if self.end_date is not None:
                forbidden.append("end_date")
            if self.amount is not None:
                forbidden.append("amount")

            if missing:
                raise ValueError(
                    f"Missing required fields for get_budget: {', '.join(missing)}"
                )

            if forbidden:
                raise ValueError(
                    f"Fields not allowed for get_budget: {', '.join(forbidden)}"
                )

        return self