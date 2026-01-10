"""
Add IMEI column to broker_config table for SHOONYA broker support
"""
import sqlite3
import sys
from pathlib import Path

# Database path
db_path = Path(__file__).parent / "data" / "trading_bot.db"

def migrate():
    """Add imei column to broker_config table"""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(broker_config)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'imei' in columns:
            print("✅ Column 'imei' already exists in broker_config table")
            conn.close()
            return True
        
        # Add the imei column
        print("Adding 'imei' column to broker_config table...")
        cursor.execute("ALTER TABLE broker_config ADD COLUMN imei VARCHAR")
        conn.commit()
        
        print("✅ Successfully added 'imei' column to broker_config table")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        sys.exit(1)
    
    success = migrate()
    sys.exit(0 if success else 1)
