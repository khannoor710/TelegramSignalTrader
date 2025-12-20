"""
Database migration script to add multi-broker support columns
"""
import sqlite3
from pathlib import Path

# Database path
db_path = Path(__file__).parent / "trading_bot.db"
print(f"Database path: {db_path}")

def migrate():
    """Add new columns for multi-broker support"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    migrations = []
    
    # Check and add api_secret column to broker_config
    try:
        cursor.execute("SELECT api_secret FROM broker_config LIMIT 1")
    except sqlite3.OperationalError:
        migrations.append(("broker_config", "api_secret", "ALTER TABLE broker_config ADD COLUMN api_secret VARCHAR"))
    
    # Check and add broker_type column to trades
    try:
        cursor.execute("SELECT broker_type FROM trades LIMIT 1")
    except sqlite3.OperationalError:
        migrations.append(("trades", "broker_type", "ALTER TABLE trades ADD COLUMN broker_type VARCHAR DEFAULT 'angel_one'"))
    
    # Check and add broker_type column to paper_trades
    try:
        cursor.execute("SELECT broker_type FROM paper_trades LIMIT 1")
    except sqlite3.OperationalError:
        migrations.append(("paper_trades", "broker_type", "ALTER TABLE paper_trades ADD COLUMN broker_type VARCHAR DEFAULT 'angel_one'"))
    
    # Check and add active_broker_type column to app_settings
    try:
        cursor.execute("SELECT active_broker_type FROM app_settings LIMIT 1")
    except sqlite3.OperationalError:
        migrations.append(("app_settings", "active_broker_type", "ALTER TABLE app_settings ADD COLUMN active_broker_type VARCHAR DEFAULT 'angel_one'"))
    
    # Execute migrations
    if migrations:
        print(f"Found {len(migrations)} columns to add:")
        for table, column, sql in migrations:
            print(f"  - Adding {table}.{column}")
            cursor.execute(sql)
        
        # Create indexes
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_broker_config_broker_name ON broker_config(broker_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_broker_type ON trades(broker_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_trades_broker_type ON paper_trades(broker_type)")
            print("  - Created indexes")
        except Exception as e:
            print(f"  - Index creation skipped: {e}")
        
        conn.commit()
        print("✅ Migration completed successfully!")
    else:
        print("✅ Database already up to date")
    
    conn.close()

if __name__ == "__main__":
    migrate()
