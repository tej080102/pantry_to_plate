from sqlalchemy import text

from app.core.database import engine


def test_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database connection ok")


if __name__ == "__main__":
    test_connection()
