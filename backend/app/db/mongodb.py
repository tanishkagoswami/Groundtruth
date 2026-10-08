from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_config = Database()

async def connect_to_mongo():
    """Triggered on FastAPI startup to initialize the connection pool."""
    print("Connecting to MongoDB...")
    db_config.client = AsyncIOMotorClient(settings.MONGODB_URI)
    db_config.db = db_config.client[settings.MONGO_DB_NAME]
    print("Successfully connected to MongoDB.")

async def close_mongo_connection():
    """Triggered on FastAPI shutdown to close connections cleanly."""
    if db_config.client:
        db_config.client.close()
        print("MongoDB connection closed.")

def get_database():
    return db_config.db