# Cloud SQL Setup

This backend uses SQLite for local development by default:

```env
DATABASE_URL=sqlite:///./sprout_recipe_developer.db
```

The intended production target is Google Cloud SQL for PostgreSQL. A typical SQLAlchemy connection string for Cloud SQL PostgreSQL looks like:

```env
DATABASE_URL=postgresql+psycopg2://DB_USER:DB_PASSWORD@DB_HOST:5432/DB_NAME
```

Examples:

- Local Cloud SQL Auth Proxy: `postgresql+psycopg2://app_user:secret@127.0.0.1:5432/sprout_recipe_developer`
- Private IP or VPC-connected instance: `postgresql+psycopg2://app_user:secret@10.x.x.x:5432/sprout_recipe_developer`

## Creating the schema in Cloud SQL

1. Create a PostgreSQL Cloud SQL instance and database.
2. Set `DATABASE_URL` to the Cloud SQL PostgreSQL connection string.
3. Install the backend dependencies from `requirements.txt`.
4. Run the application or a schema bootstrap step so SQLAlchemy executes `Base.metadata.create_all(bind=engine)`.

For this class project, `create_all()` is enough to stand up the schema quickly. In a more production-ready deployment, the next step would be introducing Alembic migrations and running those against the Cloud SQL database instead of relying on startup table creation.

## Project posture

- Local development target: SQLite
- Production target: Cloud SQL for PostgreSQL
- ORM schema owner: SQLAlchemy models under `app/models`
