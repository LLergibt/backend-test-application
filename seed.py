import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine
from app.core.database import Base
from app.core.security import hash_password
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
import app.models  # noqa: F401



PERMISSIONS = [
    ("users:read_all",    "Read any user's profile"),
    ("users:read_own",    "Read own profile"),
    ("users:update_all",  "Update any user's profile"),
    ("users:update_own",  "Update own profile"),
    ("users:delete_all",  "Soft-delete any user"),
    ("users:delete_own",  "Soft-delete own account"),
]

ROLES = {
    "admin": {
        "description": "Full access to everything",
        "permissions": [
            "users:read_all", "users:read_own",
            "users:update_all", "users:update_own",
            "users:delete_all", "users:delete_own",
        ],
    },
    "moderator": {
        "description": "Can view all users, manage own account",
        "permissions": [
            "users:read_all", "users:read_own",
            "users:update_own", "users:delete_own",
        ],
    },
    "user": {
        "description": "Regular user — own profile only",
        "permissions": [
            "users:read_own", "users:update_own", "users:delete_own",
        ],
    },
}

TEST_USERS = [
    {
        "first_name": "Admin",
        "last_name": "User",
        "middle_name": None,
        "email": "admin@example.com",
        "password": "Admin1234",
        "role": "admin",
        "is_active": True,
    },
    {
        "first_name": "Moderator",
        "last_name": "User",
        "middle_name": None,
        "email": "moderator@example.com",
        "password": "Moder1234",
        "role": "moderator",
        "is_active": True,
    },
    {
        "first_name": "Alice",
        "last_name": "Smith",
        "middle_name": "Ivanovna",
        "email": "alice@example.com",
        "password": "Alice1234",
        "role": "user",
        "is_active": True,
    },
    {
        "first_name": "Bob",
        "last_name": "Jones",
        "middle_name": None,
        "email": "bob@example.com",
        "password": "Bob12345",
        "role": "user",
        "is_active": False,
    },
]


async def seed(db: AsyncSession) -> None:
    perm_map: dict[str, Permission] = {}
    for name, desc in PERMISSIONS:
        result = await db.execute(select(Permission).where(Permission.name == name))
        perm = result.scalar_one_or_none()
        if not perm:
            perm = Permission(name=name, description=desc)
            db.add(perm)
        perm_map[name] = perm

    await db.flush()

    role_map: dict[str, Role] = {}
    for role_name, role_data in ROLES.items():
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if not role:
            role = Role(name=role_name, description=role_data["description"])
            db.add(role)
            await db.flush()

        role_map[role_name] = role

        for perm_name in role_data["permissions"]:
            perm = perm_map[perm_name]
            result = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id,
                )
            )
            if not result.scalar_one_or_none():
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    await db.flush()

    for u_data in TEST_USERS:
        result = await db.execute(select(User).where(User.email == u_data["email"]))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                first_name=u_data["first_name"],
                last_name=u_data["last_name"],
                middle_name=u_data["middle_name"],
                email=u_data["email"],
                hashed_password=hash_password(u_data["password"]),
                is_active=u_data["is_active"],
            )
            db.add(user)
            await db.flush()

        role = role_map[u_data["role"]]
        result = await db.execute(
            select(UserRole).where(
                UserRole.user_id == user.id, UserRole.role_id == role.id
            )
        )
        if not result.scalar_one_or_none():
            db.add(UserRole(user_id=user.id, role_id=role.id))

    await db.commit()
    print("Seed complete.")


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
