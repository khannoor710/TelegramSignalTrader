"""
Fix script to restore Telegram session and clean up configs
"""
import sqlite3
from pathlib import Path

def fix_telegram_session():
    db_path = Path(__file__).parent / "trading_bot.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        print("=" * 60)
        print("FIXING TELEGRAM SESSION")
        print("=" * 60)
        
        # Get session from old config
        cur.execute("""
            SELECT id, session_string 
            FROM telegram_config 
            WHERE session_string IS NOT NULL AND LENGTH(session_string) > 0 
            LIMIT 1
        """)
        result = cur.fetchone()
        
        if result:
            source_id, session = result
            print(f"✅ Found session in config #{source_id} ({len(session)} chars)")
            
            # Update active config with the session
            cur.execute("""
                UPDATE telegram_config 
                SET session_string = ? 
                WHERE is_active = 1
            """, (session,))
            
            if cur.rowcount > 0:
                conn.commit()
                print(f"✅ Session restored to active config!")
            else:
                print("⚠️ No active config found to update")
        else:
            print("❌ No session found in any config")
            return False
        
        # Verify
        cur.execute("""
            SELECT id, is_active, LENGTH(session_string) as sess_len 
            FROM telegram_config 
            WHERE is_active = 1
        """)
        active = cur.fetchone()
        if active:
            print(f"\n📊 Active config #{active[0]}: session = {active[2]} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def clean_old_configs():
    db_path = Path(__file__).parent / "trading_bot.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        print("\n" + "=" * 60)
        print("CLEANING UP OLD CONFIGS")
        print("=" * 60)
        
        # Keep active config and one with session, delete rest
        cur.execute("""
            DELETE FROM telegram_config 
            WHERE is_active = 0 
            AND id NOT IN (
                SELECT id FROM telegram_config 
                WHERE session_string IS NOT NULL AND LENGTH(session_string) > 0 
                LIMIT 1
            )
        """)
        
        deleted = cur.rowcount
        if deleted > 0:
            conn.commit()
            print(f"✅ Deleted {deleted} old inactive configs")
        else:
            print("ℹ️ No configs to delete")
        
        # Show remaining
        cur.execute("SELECT COUNT(*) FROM telegram_config")
        remaining = cur.fetchone()[0]
        print(f"📊 Remaining Telegram configs: {remaining}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_telegram_session()
    clean_old_configs()
    print("\n✅ Done!")
