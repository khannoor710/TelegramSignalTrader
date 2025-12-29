"""
Test script to verify Telegram and Broker session persistence
"""
import sqlite3
from pathlib import Path

def check_telegram_session():
    print("="*60)
    print("TELEGRAM SESSION PERSISTENCE TEST")
    print("="*60)
    
    # Database is in the backend folder (same level as this script)
    db_path = Path(__file__).parent / "trading_bot.db"
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if telegram_config table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='telegram_config'")
        if not cursor.fetchone():
            print("❌ telegram_config table doesn't exist yet")
            return
        
        # Get all configs
        cursor.execute("""
            SELECT id, phone_number, 
                   LENGTH(session_string) as session_len,
                   is_active,
                   monitored_chats,
                   created_at
            FROM telegram_config 
            ORDER BY id DESC
        """)
        
        configs = cursor.fetchall()
        
        if not configs:
            print("📝 No Telegram configurations found")
            print("   Action: Complete Telegram setup in the app")
            return
        
        print(f"\n📊 Found {len(configs)} configuration(s):\n")
        
        for config in configs:
            id, phone, sess_len, active, chats, created = config
            print(f"Config ID: {id}")
            print(f"  Phone: {phone}")
            print(f"  Session String: {'✅ Present (' + str(sess_len) + ' chars)' if sess_len else '❌ Missing'}")
            print(f"  Active: {'✅ Yes' if active else '❌ No'}")
            print(f"  Monitored Chats: {chats}")
            print(f"  Created: {created}")
            print()
        
        # Check for active config
        active_config = [c for c in configs if c[3]]  # is_active
        if active_config:
            _, _, sess_len, _, _, _ = active_config[0]
            if sess_len:
                print("✅ PASS: Active config has session string")
                print("   Session should persist across restarts")
            else:
                print("⚠️ WARNING: Active config missing session string")
                print("   Action: Complete phone verification in the app")
        else:
            print("⚠️ No active configuration")
    
    finally:
        conn.close()

def check_broker_session():
    print("\n" + "="*60)
    print("BROKER SESSION PERSISTENCE TEST")
    print("="*60)
    
    # Database is in the backend folder (same level as this script)
    db_path = Path(__file__).parent / "trading_bot.db"
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if broker_config table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='broker_config'")
        if not cursor.fetchone():
            print("❌ broker_config table doesn't exist yet")
            return
        
        # Check if new columns exist
        cursor.execute("PRAGMA table_info(broker_config)")
        columns = [row[1] for row in cursor.fetchall()]
        
        has_new_columns = all(col in columns for col in ['auth_token', 'refresh_token', 'feed_token', 'session_expiry'])
        
        if not has_new_columns:
            print("❌ Session persistence columns missing")
            print("   Action: Run: python backend\\migrate_broker_session.py")
            return
        
        print("✅ Session persistence columns exist\n")
        
        # Get all broker configs
        cursor.execute("""
            SELECT id, broker_name, client_id, 
                   LENGTH(auth_token) as token_len,
                   is_active,
                   session_expiry,
                   last_login
            FROM broker_config 
            ORDER BY id DESC
        """)
        
        configs = cursor.fetchall()
        
        if not configs:
            print("📝 No broker configurations found")
            print("   Action: Complete broker setup in the app")
            return
        
        print(f"📊 Found {len(configs)} configuration(s):\n")
        
        for config in configs:
            id, broker, client, token_len, active, expiry, last_login = config
            print(f"Config ID: {id}")
            print(f"  Broker: {broker}")
            print(f"  Client ID: {client}")
            print(f"  Auth Token: {'✅ Present (' + str(token_len) + ' chars)' if token_len else '❌ Missing'}")
            print(f"  Active: {'✅ Yes' if active else '❌ No'}")
            print(f"  Session Expiry: {expiry or 'Not set'}")
            print(f"  Last Login: {last_login or 'Never'}")
            print()
        
        # Check for active config with valid session
        active_with_token = [c for c in configs if c[4] and c[3]]  # active and has token
        if active_with_token:
            print("✅ PASS: Active config has auth token")
            print("   Session should persist across restarts")
        else:
            print("⚠️ WARNING: No active config with auth token")
            print("   Action: Login to broker in the app")
    
    finally:
        conn.close()

if __name__ == "__main__":
    check_telegram_session()
    check_broker_session()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("Both Telegram and Broker sessions should persist if:")
    print("1. ✅ Session string/auth token is present")
    print("2. ✅ Config is marked as active")
    print("3. ✅ Session hasn't expired (for broker)")
    print("\nIf either fails, complete the setup in the web app.")
    print("="*60)
