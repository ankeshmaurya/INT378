import sqlite3
from pathlib import Path

import pytest
from flask_migrate import upgrade
from sqlalchemy import inspect

from app import create_app, db


MIGRATIONS = str(Path(__file__).parents[1] / "migrations")


@pytest.mark.parametrize("existing_schema", [False, True])
def test_task_metadata_migration_supports_fresh_and_existing_sqlite(tmp_path, existing_schema):
    database_path = tmp_path / "migration.db"
    if existing_schema:
        connection = sqlite3.connect(database_path)
        connection.executescript(
            """
            CREATE TABLE user (
                id INTEGER NOT NULL PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL
            );
            CREATE TABLE task (
                id INTEGER NOT NULL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                completed BOOLEAN NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                user_id INTEGER NOT NULL REFERENCES user (id)
            );
            INSERT INTO user (id, email, password_hash)
            VALUES (1, 'migration@example.com', 'hash');
            INSERT INTO task (
                id, title, description, completed, created_at, updated_at, user_id
            ) VALUES (
                1, 'Existing task', '', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1
            );
            """
        )
        connection.commit()
        connection.close()

    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        }
    )
    with application.app_context():
        upgrade(directory=MIGRATIONS)
        columns = {column["name"] for column in inspect(db.engine).get_columns("task")}
        assert {"priority", "category", "due_date"} <= columns
        if existing_schema:
            task = db.session.execute(db.text("SELECT priority, category FROM task WHERE id = 1")).one()
            assert task == ("medium", "Other")
