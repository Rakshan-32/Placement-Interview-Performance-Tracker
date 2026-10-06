# Placement Interview Performance Tracker

## Database configuration

The application accesses SQLite through a SQLAlchemy engine. By default it uses
`database.db` in the project directory. Set `DATABASE_URL` to change the active
database connection later, for example:

```env
DATABASE_URL=sqlite:///./database.db
```

The current queries and schema migrations remain SQLite-specific. A future
Supabase/PostgreSQL migration should add a PostgreSQL-compatible adapter before
changing this value.

Application data access uses SQLAlchemy ORM models in `orm_models.py` and
session-based operations in `db.py`. The only remaining SQL is the startup
compatibility migration that adds missing columns to older SQLite databases.
