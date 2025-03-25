# Simulpost

A web application using Gradio to create and publish posts simultaneously across multiple social media platforms including X (Twitter), Threads, Bluesky, Mastodon, and LinkedIn.

**Current Status:** Basic posting to X (Twitter) is functional. Support for other platforms, media uploads (UI), and advanced features are under development.

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher (due to Gradio/dependency requirements)
- Pip package manager

### Installation

1.  Clone the repository:
    ```bash
    git clone [https://github.com/WilliamHackspeare/simulpost.git](https://github.com/WilliamHackspeare/simulpost.git)
    cd simulpost
    ```
2.  Create and activate a virtual environment (recommended):
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate
    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

Run the Gradio interface:
```bash
python front.py
```

The application will typically be available at `http://127.0.0.1:7860` in your web browser.

## 🔑 API Keys & Authorization

Simulpost requires API credentials for each platform you wish to use.

1.  **Enter Credentials:** On the first screen, select the platforms and enter the required API keys/credentials.
    * **X (Twitter):** Requires API Key, API Secret, Access Token, and Access Token Secret from your app on the [Twitter Developer Portal](https://developer.twitter.com/). Ensure your app has the necessary permissions (e.g., Read and Write).
    * **Threads:** API is currently limited. Often uses Instagram Basic Display API or Instagram Graph API via [Meta for Developers](https://developers.facebook.com/). Specific implementation TBD.
    * **Bluesky:** Requires creating an "App Password" in your Bluesky account settings. Use your handle (e.g., `yourname.bsky.social`) and the App Password. Implementation TBD.
    * **Mastodon:** Create an application within your Mastodon instance's Preferences -> Development section to get an access token. You'll also need your instance URL (e.g., `https://mastodon.social`). Implementation TBD.
    * **LinkedIn:** Register an app on the [LinkedIn Developer Portal](https://www.linkedin.com/developers/) to get a Client ID and Client Secret. Authorization involves OAuth 2.0. Implementation TBD.

2.  **Authorize:** On the second screen, click "Authorize Platforms". This uses your saved credentials to obtain authorization tokens (like OAuth tokens) needed for posting. These tokens are stored securely.

## ✨ Features

### Current:
* **Frontend:** Gradio web interface for managing connections and creating posts.
* **Platform Support:**
    * X (Twitter): Full support for text and media posting.
* **Security:**
    * API keys are encrypted using `cryptography` before saving (`api_keys.json`).
    * Authorization tokens are encrypted before saving (`auth_tokens.json`).
    * A unique `secret.key` is generated for encryption.
* **Drafts:** Save post text as drafts (`drafts/` folder) and load them back into the composer via a dropdown.

### Implemented (Backend/Partial):
* Media upload handling for Twitter in the backend (`post_handlers.py`, `platforms/twitter.py`).
* Basic framework for adding other platforms (`platforms/` structure).

### To Be Implemented:
* **Full Platform Support:** Complete implementation for Threads, Bluesky, Mastodon, LinkedIn (validation, authorization, posting).
* **Frontend Media Upload:** UI component in Gradio to select and upload media files.
* **Frontend Draft Management:** UI for viewing, editing, and deleting drafts.
* Platform-Specific Post Customization (Phase 2).
* AI Content Adaptation (Phase 2).
* Post Scheduling (Phase 3).
* Analytics Dashboard (Phase 3).

## 🔒 Security Notes

* API keys and authorization tokens are stored encrypted in JSON files (`api_keys.json`, `auth_tokens.json`).
* Encryption relies on a `secret.key` file generated in the application directory.  Treat it like a password.

## 📝 License

This project is intended to be licensed under the MIT License (add a LICENSE file if one doesn't exist).
```