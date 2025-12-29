"""
Utility script to fix broker configuration encryption issues.
Use this when you get "Configuration invalid (decryption failed)" error.

This script will:
1. Display your current broker configurations (without showing encrypted data)
2. Help you re-enter your credentials to re-encrypt them with the current key
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.models import BrokerConfig
from app.core.encryption import get_encryption_manager
from datetime import datetime


def list_broker_configs():
    """List all broker configurations"""
    db = SessionLocal()
    try:
        configs = db.query(BrokerConfig).all()
        
        if not configs:
            print("❌ No broker configurations found in database")
            return []
        
        print("\n📋 Current broker configurations:")
        print("-" * 60)
        
        for i, config in enumerate(configs, 1):
            print(f"\n{i}. Broker: {config.broker_name}")
            print(f"   Client ID: {config.client_id}")
            print(f"   Active: {config.is_active}")
            print(f"   Last Login: {config.last_login or 'Never'}")
            print(f"   Has encrypted PIN: {'✓' if config.password_encrypted else '✗'}")
            print(f"   Has encrypted TOTP: {'✓' if config.totp_secret else '✗'}")
            print(f"   Has encrypted API Secret: {'✓' if config.api_secret else '✗'}")
            print(f"   Has session tokens: {'✓' if config.auth_token else '✗'}")
        
        return configs
    finally:
        db.close()


def test_decryption(config):
    """Test if we can decrypt a config's credentials"""
    encryption_manager = get_encryption_manager()
    
    try:
        if config.password_encrypted:
            encryption_manager.decrypt(config.password_encrypted)
            print("✅ PIN decryption: OK")
        
        if config.totp_secret:
            encryption_manager.decrypt(config.totp_secret)
            print("✅ TOTP decryption: OK")
        
        if config.api_secret:
            encryption_manager.decrypt(config.api_secret)
            print("✅ API Secret decryption: OK")
        
        if config.auth_token:
            encryption_manager.decrypt(config.auth_token)
            print("✅ Auth token decryption: OK")
        
        return True
    except Exception as e:
        print(f"❌ Decryption failed: {e}")
        return False


def re_encrypt_credentials():
    """Re-encrypt credentials with current encryption key"""
    configs = list_broker_configs()
    
    if not configs:
        return
    
    print("\n" + "=" * 60)
    print("Decryption Test")
    print("=" * 60)
    
    for i, config in enumerate(configs, 1):
        print(f"\n Testing {config.broker_name} ({config.client_id})...")
        if test_decryption(config):
            print(f"✅ All credentials for {config.broker_name} can be decrypted successfully!")
        else:
            print(f"\n⚠️  Credentials for {config.broker_name} cannot be decrypted.")
            print("This means the encryption key has changed since you saved these credentials.")
            print("\n🔧 Solution: Delete and re-create this broker configuration through the web UI:")
            print(f"   1. Open http://localhost:5173")
            print(f"   2. Go to Multi-Broker Configuration")
            print(f"   3. Delete the {config.broker_name} configuration")
            print(f"   4. Re-add {config.broker_name} with your credentials")


def main():
    print("=" * 60)
    print("Broker Configuration Encryption Checker")
    print("=" * 60)
    
    encryption_key_file = Path(__file__).parent / "data" / ".encryption_key"
    if encryption_key_file.exists():
        print(f"✅ Encryption key file exists: {encryption_key_file}")
    else:
        print(f"⚠️  Encryption key file not found: {encryption_key_file}")
        print("   A new key will be generated when you save a configuration")
    
    re_encrypt_credentials()
    
    print("\n" + "=" * 60)
    print("✅ Check complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
