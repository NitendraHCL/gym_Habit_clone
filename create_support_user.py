"""
Create support team user (Facilitator role)
Run this to create a test support user
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import config
from auth import hash_password
from datetime import datetime

async def create_support_user():
    client = AsyncIOMotorClient(config.MONGODB_URL)
    db = client[config.MONGODB_DB_NAME]

    try:
        # Check if user exists
        existing = await db.users.find_one({'email': 'support@habithealth.com'})
        if existing:
            print('[INFO] Support user already exists: support@habithealth.com')
            return

        user = {
            'email': 'support@habithealth.com',
            'password_hash': hash_password('Support@2025'),
            'name': 'Support Team User',
            'role': 'facilitator',  # ← Support team role
            'is_active': True,
            'created_at': datetime.utcnow(),
            'login_count': 0
        }

        result = await db.users.insert_one(user)
        print('=' * 60)
        print('SUPPORT USER CREATED SUCCESSFULLY!')
        print('=' * 60)
        print(f'Email:    support@habithealth.com')
        print(f'Password: Support@2025')
        print(f'Role:     facilitator (Support Team)')
        print(f'User ID:  {result.inserted_id}')
        print()
        print('Login URL: http://localhost:8000/admin')
        print('=' * 60)

    except Exception as e:
        print(f'[ERROR] Failed to create user: {e}')
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(create_support_user())
