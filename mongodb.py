"""
Gym Habit - MongoDB Database Connection
Async MongoDB client using Motor
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import config

class MongoDB:
    """MongoDB connection manager"""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB"""
        try:
            cls.client = AsyncIOMotorClient(config.MONGODB_URL)
            cls.db = cls.client[config.MONGODB_DB_NAME]

            # Test connection
            await cls.client.admin.command('ping')
            print(f"[MongoDB] [OK] Connected to MongoDB: {config.MONGODB_DB_NAME}")

            # Create indexes
            await cls.create_indexes()

        except Exception as e:
            print(f"[MongoDB] [ERROR] Failed to connect: {e}")
            raise

    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            print("[MongoDB] [OK] Disconnected from MongoDB")

    @classmethod
    async def create_indexes(cls):
        """Create all necessary indexes"""
        try:
            # Gyms collection indexes
            await cls.db.gyms.create_index("gym_id", unique=True)
            await cls.db.gyms.create_index("pincode")
            await cls.db.gyms.create_index("city")
            await cls.db.gyms.create_index("partner_name")
            await cls.db.gyms.create_index([("location", "2dsphere")])
            await cls.db.gyms.create_index("is_active")

            # Leads collection indexes
            await cls.db.leads.create_index("lead_id", unique=True)
            await cls.db.leads.create_index("email")
            await cls.db.leads.create_index("phone")
            await cls.db.leads.create_index([("created_at", -1)])
            await cls.db.leads.create_index("status")
            await cls.db.leads.create_index("payment.status")
            await cls.db.leads.create_index([("status", 1), ("payment.status", 1), ("created_at", -1)])

            # Users collection indexes
            await cls.db.users.create_index("email", unique=True)
            await cls.db.users.create_index("role")
            await cls.db.users.create_index("is_active")

            print("[MongoDB] [OK] Indexes created successfully")

        except Exception as e:
            print(f"[MongoDB] [WARNING] Index creation warning: {e}")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if cls.db is None:
            raise Exception("Database not connected. Call connect_db() first.")
        return cls.db


# Convenience function to get database
def get_database() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance"""
    return MongoDB.get_db()
