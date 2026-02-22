import csv
import json
import os
import sqlite3
import tempfile

import pytest


@pytest.fixture
def sample_db():
    """Create a temporary SQLite database with sample data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            age INTEGER,
            active BOOLEAN DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            title TEXT,
            content TEXT,
            created_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        ("Alice", "alice@example.com", 30),
    )
    conn.execute(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        ("Bob", "bob@example.com", 25),
    )
    conn.execute(
        "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
        (1, "Hello World", "First post content"),
    )
    conn.commit()
    conn.close()

    yield db_path
    os.unlink(db_path)


@pytest.fixture
def sample_data_dir():
    """Create a temporary directory with sample data files."""
    with tempfile.TemporaryDirectory() as dir_path:
        # Create CSV file
        csv_path = os.path.join(dir_path, "products.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "price", "in_stock"])
            writer.writerow([1, "Widget", 9.99, "true"])
            writer.writerow([2, "Gadget", 24.99, "false"])
            writer.writerow([3, "Doohickey", 4.50, "true"])

        # Create JSON file
        json_path = os.path.join(dir_path, "config.json")
        with open(json_path, "w") as f:
            json.dump(
                [
                    {"key": "api_url", "value": "https://api.example.com"},
                    {"key": "timeout", "value": 30},
                ],
                f,
            )

        # Create text file
        txt_path = os.path.join(dir_path, "readme.txt")
        with open(txt_path, "w") as f:
            f.write("This is a readme file.")

        yield dir_path
