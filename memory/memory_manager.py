import aiosqlite

DB_PATH = "rux_memory.db"

class MemoryManager :
    async def init_db(self):

        # for creating tables in the memory db to remember imp features
        async with aiosqlite.connect(DB_PATH) as db :
            await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT
                )
                """)
            await db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                user_id TEXT,
                project_name TEXT,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE ) """ )
             
            await db.commit()
    async def get_user(self, user_id: str):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT name FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_user_name(self, user_id: str, name: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO users (user_id, name) VALUES (?, ?)",
                (user_id, name)
            )
            await db.commit()
            
            