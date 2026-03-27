# Cloud SQL Setup

This backend uses SQLite for local development by default:

```env
DATABASE_URL=sqlite:///./pantry_to_plate.db
```

The intended production target is Google Cloud SQL for PostgreSQL. A typical SQLAlchemy connection string for Cloud SQL PostgreSQL looks like:

```env
DATABASE_URL=postgresql+psycopg2://DB_USER:DB_PASSWORD@DB_HOST:5432/DB_NAME
```

Examples:

- Local Cloud SQL Auth Proxy: `postgresql+psycopg2://app_user:secret@127.0.0.1:5432/pantry_to_plate`
- Private IP or VPC-connected instance: `postgresql+psycopg2://app_user:secret@10.x.x.x:5432/pantry_to_plate`

## Implemented in this repository

- SQLAlchemy ORM models under `app/models`
- PostgreSQL-compatible schema script at `db/schema.sql`
- Sample data script at `db/seed.sql`
- Validation query script at `db/validation_queries.sql`
- Environment file at `.env`

## Creating the schema in Cloud SQL

1. Create a PostgreSQL Cloud SQL instance and database.
2. Set `DATABASE_URL` in `.env` to the Cloud SQL PostgreSQL connection string.
3. Install the backend dependencies from `requirements.txt`.
4. Apply the schema manually in Cloud SQL using `db/schema.sql`.
5. Optionally load demo data with `db/seed.sql`.
6. Run `db/validation_queries.sql` to verify retrieval behavior.

Example with `psql` against a Cloud SQL Auth Proxy connection:

```bash
psql "postgresql://DB_USER:DB_PASSWORD@127.0.0.1:5432/pantry_to_plate" -f db/schema.sql
psql "postgresql://DB_USER:DB_PASSWORD@127.0.0.1:5432/pantry_to_plate" -f db/seed.sql
psql "postgresql://DB_USER:DB_PASSWORD@127.0.0.1:5432/pantry_to_plate" -f db/validation_queries.sql
```

The FastAPI app still supports local bootstrap via `Base.metadata.create_all(bind=engine)`, but Cloud SQL creation is currently a manual execution step. No Cloud SQL instance provisioning, credentials, or deployment automation is implemented in this repository.

## Project posture

- Local development target: SQLite
- Production target: Cloud SQL for PostgreSQL
- ORM schema owner: SQLAlchemy models under `app/models`
