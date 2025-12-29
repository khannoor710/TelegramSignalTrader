"""
Migration script to add session persistence fields to broker_config table
Run this after updating the models
"""
import sqlite3
from pathlib import Path

def migrate_database():
    db_path = Path(__file__).parent / "trading_bot.db"
    
    if not db_path.exists():
        print("❌ Database not found. Run the app first to create it.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(broker_config)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_columns = [
            ("auth_token", "TEXT"),
            ("refresh_token", "TEXT"),
            ("feed_token", "TEXT"),
            ("session_expiry", "DATETIME")
        ]
        
        added = []
        for col_name, col_type in new_columns:
            if col_name not in columns:
                cursor.execute(f"ALTER TABLE broker_config ADD COLUMN {col_name} {col_type}")
                added.append(col_name)
                print(f"✅ Added column: {col_name}")
        
        if added:
            conn.commit()
            print(f"\n✅ Migration complete! Added {len(added)} columns")
        else:
            print("✅ All columns already exist. No migration needed.")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
