import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "magic_ball.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            zodiac_sign TEXT NOT NULL,
            user_question TEXT NOT NULL,
            bot_answer TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_conversation(user_id: int, zodiac_sign: str, question: str, answer: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO conversations (user_id, zodiac_sign, user_question, bot_answer)
            VALUES (?, ?, ?, ?)
        """, (user_id, zodiac_sign, question, answer))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Ошибка при сохранении в БД: {e}")


def get_user_conversations(user_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT zodiac_sign, user_question, bot_answer, timestamp
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC
        """, (user_id,))

        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Ошибка при получении истории: {e}")
        return []


def get_all_conversations():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, zodiac_sign, user_question, bot_answer, timestamp
            FROM conversations
            ORDER BY timestamp DESC
        """)

        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Ошибка при получении всех разговоров: {e}")
        return []

