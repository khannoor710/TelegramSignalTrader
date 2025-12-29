"""
Centralized encryption utility for secure credential storage.
Ensures consistent encryption/decryption across the application.
"""
from cryptography.fernet import Fernet
from pathlib import Path
import os


class EncryptionManager:
    """Manages encryption key and provides encrypt/decrypt methods"""
    
    _instance = None
    _cipher = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._cipher is None:
            self._cipher = self._get_cipher()
    
    def _get_encryption_key(self):
        """Get or create a stable encryption key"""
        # Path to encryption key file
        key_file = Path(__file__).parent.parent.parent / "data" / ".encryption_key"
        
        # Check environment variable first
        env_key = os.getenv("ENCRYPTION_KEY")
        if env_key:
            if isinstance(env_key, str) and len(env_key) == 44:
                return env_key.encode()
            if isinstance(env_key, bytes) and len(env_key) == 44:
                return env_key
            # Invalid env key, fall through to file-based key
            print(f"⚠️ ENCRYPTION_KEY environment variable is invalid (must be 44 chars), using file-based key")
        
        # Load from file for persistence across restarts
        try:
            key_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Failed to create data directory: {e}")
        
        if key_file.exists():
            try:
                key_data = key_file.read_bytes()
                if len(key_data) == 44:  # Valid Fernet key length
                    return key_data
                else:
                    print(f"⚠️ Invalid encryption key in file (wrong length), generating new one")
            except Exception as e:
                print(f"⚠️ Failed to read encryption key: {e}, generating new one")
        
        # Generate new key and save it
        new_key = Fernet.generate_key()
        try:
            key_file.write_bytes(new_key)
            print(f"🔐 Generated and saved new encryption key at {key_file}")
        except Exception as e:
            print(f"⚠️ Failed to save encryption key: {e}")
            print(f"⚠️ Using in-memory key (will not persist across restarts)")
        
        return new_key
    
    def _get_cipher(self):
        """Get Fernet cipher instance"""
        try:
            key = self._get_encryption_key()
            return Fernet(key)
        except Exception as e:
            print(f"❌ Failed to initialize encryption: {e}")
            # Generate a fallback in-memory key as last resort
            print("⚠️ Using fallback in-memory encryption key (data will not decrypt after restart)")
            return Fernet(Fernet.generate_key())
    
    def encrypt(self, data: str) -> str:
        """Encrypt a string and return base64-encoded encrypted data"""
        if not data:
            return None
        return self._cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64-encoded encrypted data and return original string"""
        if not encrypted_data:
            return None
        return self._cipher.decrypt(encrypted_data.encode()).decode()


# Global singleton instance
encryption_manager = EncryptionManager()


def get_encryption_manager() -> EncryptionManager:
    """Get the global encryption manager instance"""
    return encryption_manager
