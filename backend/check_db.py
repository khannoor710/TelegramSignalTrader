import sqlite3

conn = sqlite3.connect('trading_bot.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("Tables:", tables)

if 'broker_config' in tables:
    cursor.execute("PRAGMA table_info(broker_config)")
    columns = [row[1] for row in cursor.fetchall()]
    print("broker_config columns:", columns)

conn.close()
