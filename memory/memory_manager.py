import aiosqlite
import json 
DB_PATH = "rux_memory.db"

class MemoryManager :
    def __init__(self,db):
            self.db = db

    async def init_db(self):
    
        # for creating tables in the memory db to remember imp features     
            await self.db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT
                )
                """)
            
            await self.db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
            project_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            project_name TEXT NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id)
            REFERENCES users(user_id)
            ON DELETE CASCADE
                                 ) """ )
             
             # adding confirmation tables for high risk actions that require confirmation before execution :
            await self.db.execute("""
             CREATE TABLE IF NOT EXISTS confirmations (
             confirmation_id INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id TEXT NOT NULL,
             action TEXT NOT NULL,
             parameters TEXT NOT NULL,
             status TEXT NOT NULL DEFAULT 'pending', -- pending
             created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
             FOREIGN KEY(user_id)
                REFERENCES users(user_id)
                ON DELETE CASCADE
                                 ) """ )
            

            # Adding Expense Table in memory for the agent to manage expenses for the user , when the user asks the agent to create an expense or list expenses, the agent will use this table to store and retrieve expenses data:
            await self.db.execute("""
             CREATE TABLE IF NOT EXISTS expenses (
             expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id TEXT NOT NULL,
             amount REAL NOT NULL,
             category TEXT NOT NULL,
             note TEXT,
             created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
             FOREIGN KEY(user_id)
                REFERENCES users(user_id)
                ON DELETE CASCADE
                                 ) """ )
            
            await self.db.commit()

            #---- USERS -----#
            
    async def get_user(self, user_id: str):
            cursor = await self.db.execute(
                "SELECT name FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_user_name(self, user_id: str, name: str):
            await self.db.execute(
                "INSERT OR REPLACE INTO users (user_id, name) VALUES (?, ?)",
                (user_id, name)
            )
            await self.db.commit()
            
            #---- For PROJects  ----#

    async def create_project(self, user_id: str, name: str, description: str | None = None):
        cursor = await self.db.execute(
            "INSERT INTO projects (user_id, project_name, description) VALUES (?, ?, ?)",
            (user_id, name, description)
        )
        await self.db.commit()
        return cursor.lastrowid

    async def get_project(self, project_id: int):
        cursor = await self.db.execute(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,)
        )
        return await cursor.fetchone()
    
    async def get_project_by_name(self, user_id: str, project_name: str):     
        cursor = await self.db.execute(
            "SELECT * FROM projects WHERE user_id = ? AND project_name = ?",
                (user_id, project_name)
        )
        return await cursor.fetchone()  

    async def list_projects(self, user_id: str):
        cursor = await self.db.execute(
            "SELECT * FROM projects WHERE user_id = ?",
            (user_id,)
        )
        return await cursor.fetchall()

    async def delete_project(self, project_id: int):
        await self.db.execute(
            "DELETE FROM projects WHERE project_id = ?",
            (project_id,)
        )
        await self.db.commit()

    #== confirmation table management for high risk actions ==#
    async def create_confirmation(self, user_id: str, action: str, parameters: dict):
        await self.db.execute(
            "INSERT INTO confirmations (user_id, action, parameters) VALUES (?, ?, ?)", 
            (user_id, action, json.dumps(parameters)) 
        )
        await self.db.commit() 
    
    # this function is used to get the most recent pending confirmation for a user, if there is any, to check if the user has confirmed a high risk action or not
    async def get_pending_confirmation(self, user_id: str):
        cursor = await self.db.execute(
            "SELECT * FROM confirmations WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        return await cursor.fetchone()
    
    # this function is used to mark a confirmation as confirmed after the user has confirmed the action and we have executed the action successfully
    async def mark_confirmation_executed(self, confirmation_id: int):
        await self.db.execute(
            """UPDATE confirmations 
            SET status = 'executed'
            WHERE confirmation_id = ?""",
            (confirmation_id,)
        )
        await self.db.commit()
    
    # this function is used to mark a confirmation as rejected if the user has rejected the confirmation and does not want to proceed with the high risk action
    async def mark_confirmation_rejected(self, confirmation_id: int):
        await self.db.execute(
            """UPDATE confirmations 
            SET status = 'rejected'
            WHERE confirmation_id = ?""",
            (confirmation_id,)
        )
        await self.db.commit()

    # function for logging expenses in the expenses table in memory when the user asks the agent to create an expense :
    async def log_expense(self, user_id: str, amount: float, category: str , note: str | None = None):
        cursor = await self.db.execute(
            "INSERT INTO expenses (user_id, amount, category, note) VALUES (?, ?, ?, ?)",
            (user_id, amount, category.lower(), note)  # normalizing category to lowercase for easier querying later
        )
        await self.db.commit()
        return cursor.lastrowid 
    
    # Function to get total expenses for a user in a given period or category, this can be used when the user asks the agent to analyze expenses or give insights about expenses:
    async def get_total_expenses(self, user_id: str, period: str | None = None, category: str | None = None):
        query = "SELECT SUM(amount) FROM expenses WHERE user_id = ?"
        params = [user_id]

        if period == "today":
             query += " AND DATE(created_at) = DATE('now')"

        elif period == "month":
             query += " AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')"
        
        if category : 
                query += " AND category = ?"
                params.append(category.lower())
        
        cursor = await self.db.execute(query, tuple(params)) # This LOC is used to execute the query with the dynamic parameters based on the filters provided (period and category) when fetching expenses data for analysis. The use of parameterized queries here also helps prevent SQL injection attacks.
        result = await cursor.fetchone()

        return result[0] if result[0] else 0.0   # this LOC will return 0.0 if there are no expenses logged for the given criteria instead of returning None
    
async def get_memory():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield MemoryManager(db)
    