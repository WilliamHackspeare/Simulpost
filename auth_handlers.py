"""
Authentication handlers module for Simulpost.

This module provides functions for authorizing platforms and managing authorization tokens.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional

# Import platform modules dynamically or handle potential ImportErrors
try:
    from platforms import twitter
    # Import other platform modules as needed
    # from platforms import bluesky, mastodon, ...
except ImportError as e:
    print(f"Warning: Could not import platform modules in auth_handlers.py: {e}")
    twitter = None
    # Set other imported platforms to None as well

# Import API handlers for loading API keys and encryption functions
try:
    from api_handlers import load_api_keys, encrypt_api_key, decrypt_api_key
except ImportError as e:
    print(f"FATAL: Could not import api_handlers in auth_handlers.py: {e}")
    # Define dummy functions or raise error if api_handlers are critical
    def load_api_keys(): return {}
    def encrypt_api_key(s): raise NotImplementedError("Encryption unavailable")
    def decrypt_api_key(s): raise NotImplementedError("Decryption unavailable")


# Constants
AUTH_TOKENS_FILE = "auth_tokens.json"

def authorize_platform(platform: str, api_key: str) -> Dict[str, Any]:
    """
    Handle the OAuth flow or other authorization methods for a specific platform.

    Args:
        platform (str): Name of the platform to authorize
        api_key (str): Decrypted API key/credentials string for the platform

    Returns:
        Dict[str, Any]: Dictionary containing authorization information
                        (e.g., success, auth_token, expires_at, error).
    """
    try:
        if platform == "X (Twitter)":
            if twitter:
                return twitter.authorize(api_key)
            else:
                return {"success": False, "error": "Twitter module not available"}
        # Add authorization calls for other platforms here
        # elif platform == "Bluesky":
        #     if bluesky:
        #         return bluesky.authorize(api_key) # Assuming Bluesky needs the App Password here
        #     else: ...
        # elif platform == "Mastodon":
        #     if mastodon:
        #         # Mastodon might need instance URL + API Key (access token)
        #         return mastodon.authorize(api_key)
        #     else: ...
        else:
            # Placeholder for unimplemented platforms
            print(f"Authorization not implemented for {platform}.")
            # Simulate successful authorization for testing UI flow if needed
            return {
                "success": True, # Change to False for stricter behavior
                "auth_token": f"mock-token-{platform}-{int(time.time())}",
                "expires_at": int(time.time()) + 3600, # Mock 1 hour expiry
                "message": "Authorization not implemented (mock success)."
            }
    except Exception as e:
        print(f"Error during authorization for {platform}: {e}")
        return {"success": False, "error": str(e)}


def save_auth_tokens(auth_tokens: Dict[str, Dict[str, Any]]) -> bool:
    """
    Save and encrypt authorization tokens to file.

    Args:
        auth_tokens (Dict[str, Dict[str, Any]]): Dictionary mapping platform names
                                                to their auth token info.
                                                'auth_token' will be encrypted.

    Returns:
        bool: True if saving was successful, False otherwise.
    """
    try:
        encrypted_auth_tokens = {}
        for platform, token_info in auth_tokens.items():
            encrypted_info = token_info.copy() # Avoid modifying the original dict in memory
            if "auth_token" in encrypted_info and encrypted_info["auth_token"]:
                try:
                    # Encrypt the auth_token using the function from api_handlers
                    encrypted_info["auth_token"] = encrypt_api_key(str(encrypted_info["auth_token"]))
                except Exception as enc_e:
                    print(f"Error encrypting token for {platform}: {enc_e}")
                    # Store None or handle error as appropriate (e.g., skip saving this token)
                    encrypted_info["auth_token"] = None # Indicate encryption failure
            encrypted_auth_tokens[platform] = encrypted_info

        with open(AUTH_TOKENS_FILE, 'w') as f:
            json.dump(encrypted_auth_tokens, f, indent=4)
        return True
    except NotImplementedError:
         print(f"Error saving auth tokens: Encryption unavailable.")
         return False
    except Exception as e:
        print(f"Error saving auth tokens: {e}")
        return False

def load_auth_tokens() -> Dict[str, Dict[str, Any]]:
    """
    Load and decrypt authorization tokens from file.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping platform names to their
                                   auth token info with 'auth_token' decrypted.
    """
    if not os.path.exists(AUTH_TOKENS_FILE):
        return {}

    try:
        with open(AUTH_TOKENS_FILE, 'r') as f:
            encrypted_tokens = json.load(f)

        decrypted_tokens = {}
        for platform, token_info in encrypted_tokens.items():
            decrypted_info = token_info.copy()
            if "auth_token" in decrypted_info and decrypted_info["auth_token"]:
                try:
                    # Decrypt the auth_token using the function from api_handlers
                    decrypted_info["auth_token"] = decrypt_api_key(decrypted_info["auth_token"])
                except (ValueError, NotImplementedError) as dec_e: # Catch specific decryption errors
                    print(f"Error decrypting token for {platform}: {dec_e}")
                    # If decryption fails, treat as unauthorized or store error state
                    decrypted_info["auth_token"] = None
                    decrypted_info["error"] = "Decryption failed or unavailable"
            decrypted_tokens[platform] = decrypted_info

        return decrypted_tokens
    except Exception as e:
        print(f"Error loading auth tokens: {e}")
        return {}

def check_auth_status(platform: str) -> Dict[str, Any]:
    """
    Check if the authorization for a platform is still valid.

    Args:
        platform (str): Name of the platform to check.

    Returns:
        Dict[str, Any]: Dictionary containing authorization status:
                        authorized (bool), needs_refresh (bool), expires_at (Optional[int]),
                        error (Optional[str]).
    """
    auth_tokens = load_auth_tokens() # Loads with decrypted tokens

    if platform not in auth_tokens or not auth_tokens[platform].get("auth_token"):
        # Consider unauthorized if platform missing, token is missing, or decryption failed
        return {
            "authorized": False,
            "needs_refresh": True,
            "error": auth_tokens.get(platform, {}).get("error") # Propagate decryption error
        }

    token_info = auth_tokens[platform]
    current_time = int(time.time())

    # Check if token has expired (if expiry info is available)
    expires_at = token_info.get("expires_at")
    if expires_at is not None and expires_at < current_time:
        return {
            "authorized": False,
            "needs_refresh": True,
            "expires_at": expires_at
        }

    # If token exists, hasn't failed decryption, and hasn't expired
    return {
        "authorized": True,
        "needs_refresh": False,
        "expires_at": expires_at
    }

def refresh_auth(platform: str) -> Dict[str, Any]:
    """
    Refresh the authorization token for a platform by re-running authorize.

    Args:
        platform (str): Name of the platform to refresh.

    Returns:
        Dict[str, Any]: Dictionary containing new authorization information
                        (result from authorize_platform).
    """
    # Load API keys (decrypted)
    api_keys = load_api_keys()

    if platform not in api_keys or not api_keys[platform]:
        return {
            "success": False,
            "error": f"No valid API key found for {platform} to refresh authorization."
        }

    print(f"Attempting to refresh authorization for {platform}...")
    # Re-authorize with the stored API key
    result = authorize_platform(platform, api_keys[platform])

    # If refresh/re-auth is successful, update the stored token
    if result.get("success", False):
        current_tokens = load_auth_tokens() # Load current state (decrypted tokens)
        current_tokens[platform] = {
            "auth_token": result.get("auth_token"),
            "expires_at": result.get("expires_at") # Use expiry from result if available
        }
        save_auth_tokens(current_tokens) # Save updated tokens (will re-encrypt)
        print(f"Authorization successfully refreshed and saved for {platform}.")
    else:
        print(f"Failed to refresh authorization for {platform}: {result.get('error', 'Unknown reason')}")


    return result


def authorize_all_platforms(selected_platforms: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Authorize all selected platforms that require it.

    Checks current status, attempts authorization/refresh if needed using saved
    API keys, and saves the updated (encrypted) tokens.

    Args:
        selected_platforms (List[str]): List of platform names to authorize.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping platform names to their
                                   authorization attempt results for this run.
    """
    results = {}
    auth_tokens_to_update = {} # Store tokens that need saving/resaving

    # Load API keys (decrypted) once
    api_keys = load_api_keys()
    # Load current auth tokens to check status and potentially merge later
    current_auth_tokens = load_auth_tokens()

    for platform in selected_platforms:
        if platform not in api_keys or not api_keys[platform]:
            results[platform] = {
                "success": False,
                "error": f"No API key found for {platform}. Cannot authorize."
            }
            continue

        # Check current status first
        status = check_auth_status(platform)
        if status["authorized"]:
             results[platform] = {
                 "success": True,
                 "message": "Already authorized and valid.",
                 "expires_at": status.get("expires_at")
             }
             # Ensure the current valid token info is preserved for saving
             if platform in current_auth_tokens:
                  auth_tokens_to_update[platform] = current_auth_tokens[platform]
             continue # Skip re-authorization if already valid

        # If not authorized or needs refresh, attempt authorization
        print(f"Attempting authorization/refresh for {platform}...")
        result = authorize_platform(platform, api_keys[platform])
        results[platform] = result # Store the result of the attempt

        # If authorization was successful, prepare the new token info for saving
        if result.get("success", False):
            auth_tokens_to_update[platform] = {
                "auth_token": result.get("auth_token"),
                "expires_at": result.get("expires_at")
            }
        elif platform in current_auth_tokens:
             # If auth failed, but we had an old (potentially invalid/decryption-failed) token entry,
             # keep it to avoid losing the entry entirely. The check_auth_status will still report it as not authorized.
             auth_tokens_to_update[platform] = current_auth_tokens[platform]


    # Save the updated tokens
    # Merge updates with existing tokens for platforms *not* processed in this run
    final_tokens_to_save = load_auth_tokens() # Load existing state again before merge
    final_tokens_to_save.update(auth_tokens_to_update) # Overwrite/add the processed platform tokens

    if final_tokens_to_save: # Only save if there's something to save
        if not save_auth_tokens(final_tokens_to_save):
            print("Error: Failed to save updated authorization tokens.")
            # Optionally update results to indicate save failure?

    return results