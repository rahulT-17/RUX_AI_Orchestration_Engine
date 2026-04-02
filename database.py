# MEMORY / database.py : This file handles , engine creation , session creation , dependecy injection 

import os 
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:your_password@localhost:5432/rux_db")

# creating a connection pool to PostgreSQL :
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # shows sql queries in terminal 
)

# Creating session factory : 
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False 
)

Base = declarative_base()

# DEPENDENCY :
async def get_db() :
    async with AsyncSessionLocal() as session :
        yield session