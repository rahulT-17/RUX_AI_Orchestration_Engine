# MEMORY / models.py : This file is used for defining tables using orm : (for now mitigrating users table first)

import datetime

import enum
from sqlalchemy import CheckConstraint, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, DateTime, Date, JSON , Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from database import Base 


class ConfirmationStatus(enum.Enum) :
    pending = "pending"
    executed = "executed"
    rejected = "rejected"


class User(Base) :
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)

    name = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Project(Base) :
    __tablename__ = "projects"

    project_id = Column(Integer,primary_key=True,index=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    name =Column(String,nullable=False)
    description =Column(Text,nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User" , backref="projects")

class Confirmation(Base) :

    __tablename__ = "confirmations"

    confirmation_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    action = Column(String, nullable=False)
    parameters = Column(JSONB, nullable=True) # Store parameters as JSON string

    status = Column(SAEnum(ConfirmationStatus), nullable=False, default=ConfirmationStatus.pending) 
    #         ^ only "pending", "executed", "rejected" allowed — DB rejects anything else

    created_at = Column(DateTime(timezone=True), server_default=func.now()) # Store the creation time of the confirmation request

    user = relationship("User" , backref="confirmations")

class Expense(Base) :
    __tablename__ = "expenses"
    
    __table_args__ = (
        CheckConstraint('amount >= 0', name='expense_amount_positive'), # Ensure that the amount is non-negative
    )
    expense_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    amount = Column(Float, nullable=False)
    note = Column(Text, nullable=True)
    category = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User" , backref="expenses")

class Budget(Base) :
    __tablename__ = "budgets"

    __table_args__ = (
        CheckConstraint('amount > 0', name='budget_amount_positive'),
        #                ^ a budget of 0 or negative makes no sense
        CheckConstraint('end_date > start_date', name='valid_budget_period'),
        #                ^ prevents start_date=March, end_date=January
    )


    budget_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User" , backref="budgets") 

class AgentRun(Base) :
    __tablename__ = "agent_runs"

    __table_args__ = (
        CheckConstraint('latency >= 0', name='agent_run_latency_non_negative'),
        #                ^ latency can't be negative
    )

    run_id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    message = Column(Text, nullable=False) # Store the original message from the user that triggered the agent run
    action = Column(String, nullable=False) # Store the action name that the agent decided to execute

    parameters = Column(JSON) # Store the parameters for the action as JSON 

    result = Column(Text) # Store the result of the action execution as JSON
    latency = Column(Float) # Store the latency of the action execution

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="agent_runs")
    outcomes = relationship("Agent_Outcomes", backref="run", cascade="all, delete-orphan")

class Agent_Outcomes(Base):
    __tablename__ = "agent_outcomes"

    outcome_id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    domain = Column(String, nullable=False)
    #                        ^ confidence engine breaks without domain
    task_type = Column(String, nullable=False)
    #                           ^ confidence engine breaks without task_type
    was_correct = Column(Boolean, nullable=False)
    #                              ^ can't calculate avg confidence if this is null
    correction = Column(Text, nullable=True)
    corrected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="agent_outcomes")

class AgentFeedback(Base) :

    __tablename__ = "agent_feedback"

    feedback_id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    domain = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    was_correct = Column(Boolean, nullable=False)
    correction = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="agent_feedback")
    run = relationship("AgentRun", backref="feedback")