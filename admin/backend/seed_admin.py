"""
Seed script to create the default admin user for testing.

Usage: python seed_admin.py
"""
import asyncio
import uuid
from datetime import datetime

import bcrypt
from sqlalchemy import select

from app.database import async_session_factory
from app.models.admin_user import AdminUser


async def seed_admin():
    """Create the default admin user if it doesn't exist."""
    email = "admin@ecomm.com"
    password = "admin123"

    async with async_session_factory() as session:
        # Check if admin exists
        result = await session.execute(
            select(AdminUser).where(AdminUser.email == email)
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print(f"✅ Admin user already exists: {email}")
            return

        # Hash password
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        # Create admin user
        admin = AdminUser(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            role="super_admin",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        session.add(admin)
        await session.commit()

        print(f"✅ Created admin user: {email}")
        print(f"   Password: {password}")
        print(f"   Role: super_admin")


if __name__ == "__main__":
    asyncio.run(seed_admin())
