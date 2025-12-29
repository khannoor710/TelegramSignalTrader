import sqlite3

conn = sqlite3.connect('trading_bot.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [t[0] for t in cursor.fetchall()]

print("="*60)
print("DATABASE STATUS")
print("="*60)

if not tables:
    print("❌ No tables found - Database exists but not initialized")
    print("\nAction needed: Start the backend server to initialize tables")
else:
    print(f"✅ Found {len(tables)} table(s):")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  - {table}: {count} rows")

# Check broker_config specifically
if 'broker_config' in tables:
    print("\n" + "="*60)
    print("BROKER CONFIGURATIONS")
    print("="*60)
    
    cursor.execute("""
        SELECT id, broker_name, client_id, 
               CASE WHEN LENGTH(auth_token) > 0 THEN LENGTH(auth_token) ELSE 0 END as token_len,
               is_active, session_expiry, last_login
        FROM broker_config 
        ORDER BY id DESC
    """)
    
    configs = cursor.fetchall()
    if configs:
        for config in configs:
            id, broker, client, token_len, active, expiry, last_login = config
            print(f"\nConfig #{id}:")
            print(f"  Broker: {broker}")
            print(f"  Client ID: {client}")
            print(f"  Auth Token: {'✅ Saved (' + str(token_len) + ' chars)' if token_len > 0 else '❌ Not saved'}")
            print(f"  Active: {'✅ Yes' if active else '❌ No'}")
            print(f"  Session Expiry: {expiry or 'Not set'}")
            print(f"  Last Login: {last_login or 'Never'}")
    else:
        print("\n❌ No broker configurations saved")
        print("Action: Complete broker setup in the web app")
else:
    print("\n❌ broker_config table doesn't exist")
    print("Action: Start backend to create tables, then complete setup")

# Check telegram_config
if 'telegram_config' in tables:
    print("\n" + "="*60)
    print("TELEGRAM CONFIGURATIONS")
    print("="*60)
    
    cursor.execute("""
        SELECT id, phone_number,
               CASE WHEN LENGTH(session_string) > 0 THEN LENGTH(session_string) ELSE 0 END as sess_len,
               is_active, monitored_chats
        FROM telegram_config 
        ORDER BY id DESC
    """)
    
    configs = cursor.fetchall()
    if configs:
        for config in configs:
            id, phone, sess_len, active, chats = config
            print(f"\nConfig #{id}:")
            print(f"  Phone: {phone}")
            print(f"  Session String: {'✅ Saved (' + str(sess_len) + ' chars)' if sess_len > 0 else '❌ Not saved'}")
            print(f"  Active: {'✅ Yes' if active else '❌ No'}")
            print(f"  Monitored Chats: {chats or 'None'}")
    else:
        print("\n❌ No telegram configurations saved")
        print("Action: Complete Telegram setup in the web app")
else:
    print("\n❌ telegram_config table doesn't exist")

conn.close()

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
if tables:
    print("✅ Database is initialized")
    has_broker = 'broker_config' in tables
    has_telegram = 'telegram_config' in tables
    
    if has_broker and has_telegram:
        print("✅ Both config tables exist")
        print("\nIf configurations show as 'Not saved', complete setup in web app")
    else:
        print("⚠️ Some tables missing - restart backend to create them")
else:
    print("❌ Database not initialized")
    print("\nStart the backend server:")
    print("  .\\start.ps1")
print("="*60)
