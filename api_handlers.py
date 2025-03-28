"""
API Handlers module for Simulpost.

Handles API key validation, secure storage (encryption/decryption),
and retrieval. Also manages the encryption secret key.
"""

import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Any

# Import platform-specific validation if needed (example for Twitter)
try:
    from platforms import twitter as twitter_platform
except ImportError:
    # Handle case where platform modules might not exist yet
    print("Warning: Could not import platform modules in api_handlers.py")
    twitter_platform = None


# Constants
API_KEYS_FILE = "api_keys.json"
SECRET_KEY_FILE = "secret.key"
# Use a simple, less secure default password for key derivation if needed,
# but strongly recommend setting a secure environment variable.
SECRET_PASSWORD = os.environ.get("SIMULPOST_SECRET_PASSWORD", "default-simulpost-password").encode('utf-8')
SECRET_SALT = b'simulpost_salt_' # Basic salt, better if unique per install

# --- Encryption Key Management ---

def generate_derived_key(password: bytes, salt: bytes) -> bytes:
    """Derives a cryptographic key from a password and salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32, # Fernet key size
        salt=salt,
        iterations=100000, # Adjust iterations as needed for security/performance balance
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key

def load_or_generate_fernet() -> Fernet:
    """Loads or generates the Fernet instance using a derived key."""
    derived_key = generate_derived_key(SECRET_PASSWORD, SECRET_SALT)
    return Fernet(derived_key)

# Initialize Fernet instance globally on module load
try:
    fernet = load_or_generate_fernet()
except Exception as e:
    print(f"FATAL: Could not initialize encryption system: {e}")
    # In a real app, might exit or raise a critical error
    fernet = None # Ensure fernet is None if initialization fails

# --- Encryption/Decryption Functions ---

def encrypt_api_key(api_key: str) -> str:
    """Encrypts a given string (API key, token, etc.)."""
    if not fernet:
        raise ValueError("Encryption system not initialized.")
    if not isinstance(api_key, str):
         # Ensure input is string before encoding
        api_key = str(api_key)
    encrypted_data = fernet.encrypt(api_key.encode('utf-8'))
    return base64.urlsafe_b64encode(encrypted_data).decode('utf-8') # Return as base64 string

def decrypt_api_key(encrypted_api_key_b64: str) -> str:
    """Decrypts a base64 encoded string encrypted by encrypt_api_key."""
    if not fernet:
        raise ValueError("Encryption system not initialized.")
    try:
        # Decode from base64 first
        encrypted_data = base64.urlsafe_b64decode(encrypted_api_key_b64.encode('utf-8'))
        decrypted_data = fernet.decrypt(encrypted_data)
        return decrypted_data.decode('utf-8')
    except Exception as e:
        print(f"Decryption failed: {e}")
        # Handle specific exceptions (e.g., InvalidToken) if needed
        raise ValueError("Decryption failed, invalid token or key.") from e


# --- API Key Validation ---

def validate_api_keys(api_keys: Dict[str, str]) -> Dict[str, bool]:
    """
    Validates the API keys for each specified platform.

    Args:
        api_keys (Dict[str, str]): Dictionary mapping platform names to their
                                    API keys/credentials string.
                                    X (Twitter) Format: "key,secret,token,token_secret"

    Returns:
        Dict[str, bool]: Dictionary mapping platform names to boolean validation status.
    """
    validation_results = {}
    for platform, key_string in api_keys.items():
        is_valid = False # Default to False
        try:
            if platform == "X (Twitter)":
                 if twitter_platform:
                    is_valid = twitter_platform.validate_api_key(key_string)
                 else:
                     print(f"Warning: Twitter platform module not available for validation.")
                     is_valid = False # Cannot validate if module is missing
            # Add validation logic for other platforms here
            # elif platform == "Bluesky":
            #     is_valid = bluesky_platform.validate_api_key(key_string)
            # elif platform == "Mastodon":
            #     is_valid = mastodon_platform.validate_api_key(key_string)
            # ... etc.
            else:
                # Placeholder: Assume valid if not implemented, or require implementation
                print(f"Warning: Validation not implemented for {platform}. Assuming invalid.")
                is_valid = False # Safer to assume invalid if not implemented
        except Exception as e:
            print(f"Error validating key for {platform}: {e}")
            is_valid = False # Treat errors during validation as invalid

        validation_results[platform] = is_valid

    return validation_results


# --- API Key Storage ---

def save_api_keys(api_keys: Dict[str, str]) -> bool:
    """
    Encrypts and saves the API keys to a JSON file.

    Args:
        api_keys (Dict[str, str]): Dictionary mapping platform names to their
                                    API keys/credentials string.

    Returns:
        bool: True if saving was successful, False otherwise.
    """
    if not fernet:
        print("Error: Encryption system not available for saving API keys.")
        return False
    try:
        encrypted_keys = {}
        for platform, key_string in api_keys.items():
            if key_string: # Only save if key_string is not empty
                encrypted_keys[platform] = encrypt_api_key(key_string)

        with open(API_KEYS_FILE, 'w') as f:
            json.dump(encrypted_keys, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving API keys: {e}")
        return False

def load_api_keys() -> Dict[str, str]:
    """
    Loads and decrypts API keys from the JSON file.

    Returns:
        Dict[str, str]: Dictionary mapping platform names to their decrypted
                        API keys/credentials string. Returns empty dict if file
                        not found or on error.
    """
    if not fernet:
        print("Error: Encryption system not available for loading API keys.")
        return {}
    if not os.path.exists(API_KEYS_FILE):
        return {}

    try:
        with open(API_KEYS_FILE, 'r') as f:
            encrypted_keys = json.load(f)

        decrypted_keys = {}
        for platform, encrypted_key_b64 in encrypted_keys.items():
            try:
                decrypted_keys[platform] = decrypt_api_key(encrypted_key_b64)
            except ValueError as dec_e: # Catch decryption errors specifically
                 print(f"Error decrypting API key for {platform}: {dec_e} - Skipping.")
                 # Optionally store an error state or None for this key
                 decrypted_keys[platform] = None # Indicate decryption failure

        # Filter out None values if desired, or handle them upstream
        return {k: v for k, v in decrypted_keys.items() if v is not None}

    except Exception as e:
        print(f"Error loading API keys: {e}")
        return {}