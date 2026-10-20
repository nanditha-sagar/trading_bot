import os
import json
import hashlib
import secrets

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """Create and return a MySQL database connection."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "order_bot"),
    )


# ---------------- PASSWORD HELPERS ----------------

def hash_password(password: str, salt: str = None) -> tuple:
    """Hash a password using the existing salt-based format."""
    if not salt:
        salt = secrets.token_hex(16)

    hashed = hashlib.sha256(
        (salt + password).encode("utf-8")
    ).hexdigest()

    return hashed, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verify a password against its stored hash."""
    test_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(test_hash, password_hash)


# ---------------- TRADE HISTORY ----------------

def save_trade_order(
    response, symbol, side, order_type, quantity,
    price=None, user_id=None
):
    """Save an accepted Testnet order for its authenticated user."""
    if user_id is None:
        raise ValueError("user_id is required to save an order.")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        sql = """
            INSERT INTO trade_history (
                user_id,
                exchange_order_id,
                symbol,
                side,
                order_type,
                quantity,
                price,
                executed_quantity,
                status,
                client_order_id,
                exchange_response
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                executed_quantity = VALUES(executed_quantity),
                exchange_response = VALUES(exchange_response)
        """

        cursor.execute(sql, (
            user_id,
            response.get("orderId"),
            response.get("symbol", symbol.upper()),
            response.get("side", side.upper()),
            response.get("type", order_type.upper()),
            response.get("origQty", quantity),
            response.get("price") or price,
            response.get("executedQty", 0),
            response.get("status", "UNKNOWN"),
            response.get("clientOrderId"),
            json.dumps(response),
        ))

        conn.commit()
        return response.get("orderId")

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def get_trade_history(user_id, limit=50):
    """Return only Testnet orders owned by the specified user."""
    if user_id is None:
        raise ValueError("A valid user ID is required.")

    limit = max(1, min(int(limit), 500))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        sql = """
            SELECT
                id,
                exchange_order_id,
                symbol,
                side,
                order_type,
                quantity,
                price,
                executed_quantity,
                status,
                client_order_id,
                created_at
            FROM trade_history
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
        """

        cursor.execute(sql, (user_id, limit))
        rows = cursor.fetchall()

        for row in rows:
            if row["created_at"] is not None:
                row["created_at"] = row["created_at"].isoformat()

        return rows

    finally:
        cursor.close()
        conn.close()


# ---------------- DATABASE INITIALIZATION ----------------

def init_db():
    """Create tables and safely add missing trade-history ownership fields."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(32) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                exchange_order_id BIGINT UNIQUE,
                symbol VARCHAR(30) NOT NULL,
                side VARCHAR(10) NOT NULL,
                order_type VARCHAR(20) NOT NULL,
                quantity DECIMAL(30, 10) NOT NULL,
                price DECIMAL(30, 10) NULL,
                executed_quantity DECIMAL(30, 10) DEFAULT 0,
                status VARCHAR(30) NOT NULL,
                client_order_id VARCHAR(100) NULL,
                exchange_response TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_trade_history_user_id (user_id),
                CONSTRAINT fk_trade_history_user
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # CREATE TABLE IF NOT EXISTS does not update existing tables.
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'trade_history'
              AND COLUMN_NAME = 'user_id'
        """)

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE trade_history
                ADD COLUMN user_id INT NULL
            """)

        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'trade_history'
              AND INDEX_NAME = 'idx_trade_history_user_id'
        """)

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                CREATE INDEX idx_trade_history_user_id
                ON trade_history(user_id)
            """)

        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.REFERENTIAL_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = DATABASE()
              AND TABLE_NAME = 'trade_history'
              AND CONSTRAINT_NAME = 'fk_trade_history_user'
        """)

        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE trade_history
                ADD CONSTRAINT fk_trade_history_user
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE SET NULL
            """)

        conn.commit()
        print("Database initialization successful.")

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# ---------------- USER MANAGEMENT ----------------

def register_user(username: str, email: str, password: str) -> dict:
    """Register a user and return their public profile."""
    username = username.strip()
    email = email.strip().lower()

    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")

    if not email or "@" not in email:
        raise ValueError("A valid email address is required.")

    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    password_hash, salt = hash_password(password)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id FROM users WHERE username = %s OR email = %s",
            (username, email),
        )

        if cursor.fetchone():
            raise ValueError("Username or email already exists.")

        cursor.execute("""
            INSERT INTO users (username, email, password_hash, salt)
            VALUES (%s, %s, %s, %s)
        """, (username, email, password_hash, salt))

        conn.commit()

        return {
            "id": cursor.lastrowid,
            "username": username,
            "email": email,
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def authenticate_user(identifier: str, password: str):
    """Authenticate using a username or email."""
    identifier = identifier.strip()

    if not identifier or not password:
        return None

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, username, email, password_hash, salt
            FROM users
            WHERE username = %s OR email = %s
            LIMIT 1
        """, (identifier, identifier.lower()))

        user = cursor.fetchone()

        if not user:
            return None

        if not verify_password(
            password, user["password_hash"], user["salt"]
        ):
            return None

        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
        }

    finally:
        cursor.close()
        conn.close()


def get_user_by_id(user_id: int):
    """Retrieve a user's public profile by database ID."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, username, email
            FROM users
            WHERE id = %s
            LIMIT 1
        """, (user_id,))

        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    try:
        init_db()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT DATABASE()")
        print("MySQL connected. Database:", cursor.fetchone()[0])

        cursor.execute("SHOW TABLES")
        print("Tables:", [row[0] for row in cursor.fetchall()])

        cursor.close()
        conn.close()

    except Exception as exc:
        print("Database check failed:", exc)
