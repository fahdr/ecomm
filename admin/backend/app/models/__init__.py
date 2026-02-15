"""
SQLAlchemy models for the Super Admin Dashboard.

For Developers:
    All admin models use the ``admin_`` table prefix to avoid collisions
    with other services sharing the same PostgreSQL database.

For QA Engineers:
    Models are created automatically on startup via ``Base.metadata.create_all``.
    Tables are isolated per service via prefix naming.

For Project Managers:
    The admin backend stores its own data (admin users, health snapshots)
    alongside the platform database, but in clearly separated tables.

For End Users:
    These models store internal platform management data and are not
    visible in any customer-facing interface.
"""
