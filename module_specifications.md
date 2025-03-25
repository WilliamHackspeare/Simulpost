# Simulpost - Module Specifications

This document outlines the specifications for the backend modules imported by the front-end Gradio interface. It reflects the current implementation, including security enhancements.

**Platforms:** ["X (Twitter)", "Threads", "Bluesky", "Mastodon", "LinkedIn"]

---

## 1. API Handlers Module (`api_handlers.py`)

**Purpose:** Handles API key validation, secure storage, and retrieval.

### Functions:

1.  `generate_secret_key() -> bytes`
    * **Description:** Generates or loads a secret key for encryption (used internally). Stored in `secret.key`.
    * **Returns:** The secret key as bytes.

2.  `encrypt_api_key(api_key: str) -> str`
    * **Description:** Encrypts a given string (e.g., API key, auth token).
    * **Parameters:** `api_key`: The string to encrypt.
    * **Returns:** Base64 encoded encrypted string.

3.  `decrypt_api_key(encrypted_api_key: str) -> str`
    * **Description:** Decrypts a string previously encrypted by `encrypt_api_key`.
    * **Parameters:** `encrypted_api_key`: The Base64 encoded encrypted string.
    * **Returns:** The original decrypted string.

4.  `validate_api_keys(api_keys: Dict[str, str]) -> Dict[str, bool]`
    * **Description:** Validates the API keys for each specified platform by attempting a basic API call.
    * **Parameters:** `api_keys`: Dictionary mapping platform names to their API keys/credentials string.
        * *X (Twitter) Format:* `"consumer_key,consumer_secret,access_token,access_token_secret"`
    * **Returns:** Dictionary mapping platform names to boolean values indicating if the key/credentials are valid.
    * **Note:** Currently only implements validation for X (Twitter). Other platforms default to `True` (placeholder).

5.  `save_api_keys(api_keys: Dict[str, str]) -> bool`
    * **Description:** Securely saves the *validated* API keys by encrypting them before writing to `api_keys.json`.
    * **Parameters:** `api_keys`: Dictionary mapping platform names to their API keys/credentials string.
    * **Returns:** Boolean indicating success or failure of saving.

6.  `load_api_keys() -> Dict[str, str]`
    * **Description:** Loads and decrypts API keys from `api_keys.json`.
    * **Returns:** Dictionary mapping platform names to their decrypted API keys/credentials string. Returns empty dict if file not found or on error.

---

## 2. Auth Handlers Module (`auth_handlers.py`)

**Purpose:** Handles platform authorization (e.g., OAuth), secure storage, and retrieval of authorization tokens.

### Functions:

1.  `authorize_platform(platform: str, api_key: str) -> Dict[str, Any]`
    * **Description:** Performs the authorization flow for a specific platform using its API key. For OAuth platforms, this might involve user interaction (handled externally or simulated).
    * **Parameters:**
        * `platform`: Name of the platform.
        * `api_key`: Decrypted API key/credentials string for the platform.
    * **Returns:** Dictionary containing:
        * `success` (bool): Authorization success status.
        * `auth_token` (str): The obtained authorization token (e.g., OAuth access token). *This token itself is NOT saved encrypted by this function.*
        * `expires_at` (Optional[int]): Unix timestamp of token expiry, if applicable.
        * `error` (Optional[str]): Error message on failure.
        * `user_info` (Optional[Dict]): Basic user info from the platform (if available).
    * **Note:** Currently only implements authorization for X (Twitter). Other platforms return mock success data.

2.  `save_auth_tokens(auth_tokens: Dict[str, Dict[str, Any]]) -> bool`
    * **Description:** Encrypts the `auth_token` within each platform's dictionary and saves the entire structure to `auth_tokens.json`.
    * **Parameters:** `auth_tokens`: Dictionary mapping platform names to their auth info (`{"auth_token": "...", "expires_at": ...}`).
    * **Returns:** Boolean indicating save success/failure.
    * **Security:** Uses `encrypt_api_key` from `api_handlers` to encrypt the `auth_token` field.

3.  `load_auth_tokens() -> Dict[str, Dict[str, Any]]`
    * **Description:** Loads auth info from `auth_tokens.json` and decrypts the `auth_token` for each platform.
    * **Returns:** Dictionary mapping platform names to their auth info with the `auth_token` decrypted. Handles decryption errors.

4.  `check_auth_status(platform: str) -> Dict[str, Any]`
    * **Description:** Checks if the authorization for a platform is currently valid by loading the (decrypted) token and checking expiry.
    * **Parameters:** `platform`: Name of the platform.
    * **Returns:** Dictionary containing:
        * `authorized` (bool): Current authorization status.
        * `needs_refresh` (bool): Indicates if authorization is needed or token expired.
        * `expires_at` (Optional[int]): Expiry timestamp.
        * `error` (Optional[str]): Error during loading/decryption.

5.  `refresh_auth(platform: str) -> Dict[str, Any]`
    * **Description:** Attempts to refresh the authorization for a platform, typically by re-running the authorization flow using the saved API key. Updates stored token upon success.
    * **Parameters:** `platform`: Name of the platform.
    * **Returns:** Result dictionary from `authorize_platform`, indicating success/failure of the refresh attempt.

6.  `authorize_all_platforms(selected_platforms: List[str]) -> Dict[str, Dict[str, Any]]`
    * **Description:** Iterates through selected platforms, checks current auth status, attempts authorization/refresh if needed using saved API keys, and saves the updated (encrypted) tokens.
    * **Parameters:** `selected_platforms`: List of platform names selected by the user.
    * **Returns:** Dictionary mapping platform names to their *authorization attempt* results for this run.

---

## 3. Post Handlers Module (`post_handlers.py`)

**Purpose:** Handles formatting, validation, and posting of content to authorized platforms, plus draft management.

### Functions:

1.  `format_post_for_platform(platform: str, post_text: str, max_length: Optional[int] = None) -> str`
    * **Description:** Formats post text for a specific platform, primarily by truncating if it exceeds the platform's character limit.
    * **Parameters:**
        * `platform`: Platform name.
        * `post_text`: Original text.
        * `max_length`: Optional override for character limit.
    * **Returns:** Formatted (potentially truncated) post text.
    * **Note:** Uses hardcoded limits except for Twitter. Needs updating as other platforms are implemented.

2.  `validate_post_length(platform: str, post_text: str) -> bool`
    * **Description:** Checks if the post text length is within the limit for the specified platform.
    * **Parameters:** `platform`, `post_text`.
    * **Returns:** Boolean indicating if length is valid.

3.  `post_to_platforms(platforms: List[str], post_text: str, media_files: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]`
    * **Description:** Posts content to a list of authorized platforms. Handles checking/refreshing auth, formatting text, and calling the specific platform's post function.
    * **Parameters:**
        * `platforms`: List of platform names to post to.
        * `post_text`: Text content.
        * `media_files`: List of file paths for media uploads.
    * **Returns:** Dictionary mapping platform names to result dictionaries from the platform's `post` function:
        * `success` (bool): Posting success status.
        * `post_id` (Optional[str]): ID of the created post.
        * `post_url` (Optional[str]): URL of the created post.
        * `error` (Optional[str]): Error message on failure.
    * **Note:** Currently only implements posting for X (Twitter). Other platforms return mock success data.

4.  `save_draft(post_text: str, media_files: Optional[List[str]] = None) -> Dict[str, Any]`
    * **Description:** Saves the post content as a JSON draft file in the `drafts/` directory.
    * **Parameters:** `post_text`, `media_files` (optional, currently saved but not used on load).
    * **Returns:** Dictionary indicating success/failure and the draft ID (timestamp).

5.  `load_drafts() -> List[Dict[str, Any]]`
    * **Description:** Loads all draft files from the `drafts/` directory.
    * **Returns:** List of draft dictionaries, sorted by creation time (newest first). Each dict includes `id`, `text`, `media_files`, `created_at`.

---

## 4. Platform-Specific Modules (`platforms/*.py`)

**Purpose:** Encapsulate all direct API interactions for a single platform.

**Required Functions (Example for `platforms/twitter.py`):**

1.  `validate_api_key(api_key: str) -> bool`
    * **Description:** Validate credentials string.
    * **Returns:** `True` if valid, `False` otherwise.

2.  `authorize(api_key: str) -> Dict[str, Any]`
    * **Description:** Perform authorization using credentials.
    * **Returns:** Dict with `success`, `auth_token`, `expires_at`, `error`, `user_info`.

3.  `post(auth_token: str, post_text: str, media_files: Optional[List[str]] = None) -> Dict[str, Any]`
    * **Description:** Publish a post using the authorization token.
    * **Returns:** Dict with `success`, `post_id`, `post_url`, `error`.

4.  `get_character_limit() -> int` (Optional helper)
    * **Description:** Returns the platform's character limit.

**Status:**
* `twitter.py`: Implemented.
* `threads.py`, `bluesky.py`, `mastodon.py`, `linkedin.py`: Placeholders, require implementation.

---

## 5. Utility Functions (Conceptual - currently integrated)

While `module_specifications.txt` mentioned a `utils.py`, the core encryption/decryption is currently within `api_handlers.py`. Post length validation is in `post_handlers.py`.