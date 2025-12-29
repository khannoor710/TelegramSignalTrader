
import sys
import os
from pathlib import Path

# Add backend to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.models import BrokerConfig
from app.services.broker_registry import broker_registry
from cryptography.fernet import Fernet

def test_login():
    print("🚀 Starting login debug...")
    
    # 1. Setup Encryption
    key_file = Path(__file__).parent / "data" / ".encryption_key"
    if not key_file.exists():
        print(f"❌ Encryption key not found at {key_file}")
        return
    encryption_key = key_file.read_bytes()
    cipher = Fernet(encryption_key)
    print("🔐 Encryption key loaded")
    
    # 2. Get Config
    db = SessionLocal()
    try:
        config = db.query(BrokerConfig).filter(BrokerConfig.broker_name == 'angel_one').first()
        if not config:
            print("❌ No Angel One config found")
            return
            
        print(f"📄 Found config for {config.client_id}")
        
        # 3. Decrypt credentials
        try:
            decrypted_pin = cipher.decrypt(config.password_encrypted.encode()).decode()
            decrypted_totp_secret = None
            if config.totp_secret:
                decrypted_totp_secret = cipher.decrypt(config.totp_secret.encode()).decode()
            
            print("🔓 Credentials decrypted successfully")
        except Exception as e:
            print(f"❌ Decryption failed: {e}")
            return

        # 4. Create Broker Instance
        print("🏭 Creating broker instance...")
        try:
            broker = broker_registry.create_broker('angel_one')
            print(f"✅ Broker instance created: {type(broker)}")
        except Exception as e:
            print(f"❌ Failed to create broker: {e}")
            return

        # 5. Attempt Login
        print("🔌 Attempting Login...")
        try:
            result = broker.login(
                api_key=config.api_key,
                client_id=config.client_id,
                password=decrypted_pin,
                totp_secret=decrypted_totp_secret
            )
            print("📬 Login returned:")
            import json
            print(json.dumps(result, indent=2, default=str))
            
        except Exception as e:
            print(f"❌ Login crashed: {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    test_login()
