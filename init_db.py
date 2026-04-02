# Initilizing db and creating tables

import asyncio
from database import engine , Base
import models # imp so models can be registred

async def init_models():
    async with engine.begin() as conn :
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__" : 
    asyncio.run(init_models())