import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config import settings
from models.user import User
from models.home import Home
from models.booking import Booking
from models.pendingVerification import PendingVerification
from models.passwordReset import PasswordReset

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None

db = Database()

async def init_db():
    """Initialize MongoDB connection and Beanie ODM."""
    try:
        logger.info("Connecting to MongoDB Atlas...")
        db.client = AsyncIOMotorClient(settings.MONGODB_URI)
        database = db.client[settings.DATABASE_NAME]
        
        await init_beanie(
            database=database,
            document_models=[
                User,
                Home,
                Booking,
                PendingVerification,
                PasswordReset
            ]
        )
        logger.info("✅ MongoDB connected & Beanie ODM initialized successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
        raise e

async def close_db():
    """Close MongoDB connection on app shutdown."""
    if db.client:
        db.client.close()
        logger.info("MongoDB connection closed.")
