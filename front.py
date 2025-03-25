import gradio as gr
import os
import json
from typing import Dict, List, Optional, Any
import time
# Import the modules we've implemented
from api_handlers import validate_api_keys, save_api_keys, load_api_keys
from auth_handlers import authorize_platform, authorize_all_platforms, check_auth_status
from post_handlers import post_to_platforms, format_post_for_platform, save_draft, load_drafts

# Constants
PLATFORMS = ["X (Twitter)", "Threads", "Bluesky", "Mastodon", "LinkedIn"]
CONFIG_FILE = "user_config.json"
DRAFTS_DIR = "drafts" # Define drafts directory constant

class SimulpostApp:
    def __init__(self):
        """Initialize the Simulpost application with default state."""
        self.selected_platforms = {platform: False for platform in PLATFORMS}
        self.api_keys = {platform: "" for platform in PLATFORMS}
        self.authorized_platforms = {platform: False for platform in PLATFORMS}

        # Ensure drafts directory exists
        if not os.path.exists(DRAFTS_DIR):
            os.makedirs(DRAFTS_DIR)

        # Load saved configuration if it exists
        self.load_config()

        # Load saved API keys (decrypted)
        saved_api_keys = load_api_keys()
        for platform, api_key in saved_api_keys.items():
            if platform in self.api_keys:
                self.api_keys[platform] = api_key

        # Check authorization status for each platform (uses load_auth_tokens internally)
        for platform in PLATFORMS:
            auth_status = check_auth_status(platform)
            self.authorized_platforms[platform] = auth_status.get("authorized", False)

    def load_config(self):
        """Load user configuration from file if it exists."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.selected_platforms = config.get('selected_platforms', self.selected_platforms)
                    # We don't load API keys from config for security
                    self.authorized_platforms = config.get('authorized_platforms', self.authorized_platforms)
            except Exception as e:
                print(f"Error loading configuration: {e}")

    def save_config(self):
        """Save user configuration to file."""
        config = {
            'selected_platforms': self.selected_platforms,
            'authorized_platforms': self.authorized_platforms
            # We don't save API keys to config for security
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving configuration: {e}")

    def update_platform_selection(self, *args):
        """Update the selected platforms based on checkbox inputs."""
        # args correspond to checkbox values in PLATFORMS order
        updated_selection = {}
        visibility_updates = []
        for i, platform in enumerate(PLATFORMS):
             is_selected = args[i]
             self.selected_platforms[platform] = is_selected
             updated_selection[platform] = is_selected
             # Determine visibility update for the corresponding API key input group/textbox
             visibility_updates.append(gr.update(visible=is_selected))

        # The function needs to return updates for all visibility-controlled components
        return visibility_updates


    def update_api_keys(self, **kwargs):
        """Update API keys for selected platforms."""
        # This function might not be strictly needed if submit_api_keys reads directly
        # but can be useful for intermediate state updates if required later.
        for platform in PLATFORMS:
            if platform in kwargs and kwargs[platform]:
                self.api_keys[platform] = kwargs[platform]
        # Return value isn't used directly here, maybe remove or adapt if state needs updating.
        # return self.api_keys

    def submit_api_keys(self, *args):
        """Handle API key submission and validation.

        Args:
            *args: API key inputs flattened for all platforms. Order matters!

        Returns:
            Dict: Status and information for the next screen
        """
        current_keys = {}
        arg_index = 0

        # Process inputs for each platform based on PLATFORMS order
        for platform in PLATFORMS:
            if self.selected_platforms[platform]:
                if platform == "X (Twitter)":
                     # Expect 4 inputs if Twitter is selected
                    if arg_index + 4 > len(args):
                         return {"success": False, "message": "Internal error: Mismatched argument count for Twitter."}
                    api_key = args[arg_index]
                    api_secret = args[arg_index + 1]
                    access_token = args[arg_index + 2]
                    access_secret = args[arg_index + 3]

                    # Check if all required fields are provided (only if selected)
                    if not (api_key and api_secret and access_token and access_secret):
                        return {
                            "success": False,
                            "message": f"Please provide all four credentials for {platform}"
                        }
                    current_keys[platform] = f"{api_key},{api_secret},{access_token},{access_secret}"
                    arg_index += 4
                else:
                     # Expect 1 input for other selected platforms
                    if arg_index >= len(args):
                        return {"success": False, "message": "Internal error: Mismatched argument count."}
                    api_key_input = args[arg_index]
                    if not api_key_input:
                         return {
                            "success": False,
                            "message": f"Please provide the API key for {platform}"
                        }
                    current_keys[platform] = api_key_input
                    arg_index += 1
            # else: # If platform not selected, skip its potential args (logic depends on how inputs are structured)
            # This assumes inputs are *only* passed if the platform is selected, which needs careful handling in UI binding.
            # A safer approach is to always pass all inputs and ignore them here if not selected. Let's refine the input gathering.

        # Re-filter based on current selection state, *after* parsing args
        selected_api_keys = {
            platform: current_keys[platform]
            for platform in PLATFORMS
            if self.selected_platforms[platform] and platform in current_keys
        }


        if not selected_api_keys:
            return {
                "success": False,
                "message": "Please select at least one platform and provide its API key(s)"
            }

        # Validate API keys
        print(f"Validating keys for: {list(selected_api_keys.keys())}")
        validation_results = validate_api_keys(selected_api_keys)
        print(f"Validation results: {validation_results}")


        # Check if any keys are invalid
        invalid_platforms = [
            platform for platform, is_valid in validation_results.items()
            if not is_valid
        ]

        if invalid_platforms:
             # Attempt to provide more specific feedback if possible (requires validate_api_keys to return reasons)
            return {
                "success": False,
                "message": f"Invalid API key(s) provided for: {', '.join(invalid_platforms)}. Please check and try again."
            }

        # Save API keys securely (only the valid, selected ones)
        if not save_api_keys(selected_api_keys):
             return {
                "success": False,
                "message": "Error saving API keys. Please check logs."
            }

        # Update internal state after successful save
        self.api_keys.update(selected_api_keys)


        # Return information for the next screen
        selected_platforms_list = list(selected_api_keys.keys())

        return {
            "success": True,
            "message": f"API keys verified and saved for {', '.join(selected_platforms_list)}",
            "platforms": selected_platforms_list
        }

    def authorize_platforms(self):
        """Authorize the user for selected platforms using saved API keys."""
        # Get list of selected platforms *that have keys saved*
        saved_keys = load_api_keys()
        platforms_to_authorize = [
             p for p in PLATFORMS
             if self.selected_platforms[p] and p in saved_keys
        ]

        if not platforms_to_authorize:
             # Check if platforms are selected but keys are missing
             selected_but_no_keys = [p for p in PLATFORMS if self.selected_platforms[p] and p not in saved_keys]
             if selected_but_no_keys:
                 return {
                    "success": False,
                    "message": f"API Keys not found for selected platforms: {', '.join(selected_but_no_keys)}. Please go back and add them."
                 }
             else:
                return {
                    "success": False,
                    "message": "No platforms selected or API keys missing. Please select platforms and add keys first."
                }

        # Authorize all selected platforms
        print(f"Authorizing platforms: {platforms_to_authorize}")
        results = authorize_all_platforms(platforms_to_authorize) # This now uses saved keys and handles saving tokens
        print(f"Authorization results: {results}")


        # Update authorized platforms status based on results
        successful_auths = []
        failed_auths = []
        for platform, result in results.items():
             # Use check_auth_status *after* authorize_all_platforms which saves tokens
             # This ensures we read the latest state, including successful authorizations
            final_status = check_auth_status(platform)
            self.authorized_platforms[platform] = final_status.get("authorized", False)
            if self.authorized_platforms[platform]:
                successful_auths.append(platform)
            elif platform in platforms_to_authorize: # Only report failure if we attempted to authorize it
                 # Provide more detail if possible
                 error_msg = result.get("error", "Unknown reason")
                 if "Already authorized" in result.get("message", ""): # Don't count this as a failure
                     if platform not in successful_auths: successful_auths.append(platform) # Ensure it's counted as success
                 else:
                    failed_auths.append(f"{platform} ({error_msg})")


        # Save the updated configuration (selected platforms and final auth status)
        self.save_config()

        # Return information for the next screen
        if not successful_auths:
            return {
                "success": False,
                "message": f"Failed to authorize any platforms. Failures: {', '.join(failed_auths) if failed_auths else 'None attempted or all failed.'}"
            }

        message = f"Successfully authorized: {', '.join(successful_auths)}."
        if failed_auths:
            message += f" Failed or skipped: {', '.join(failed_auths)}."


        return {
            "success": True,
            "message": message,
            "platforms": successful_auths # Only list successfully authorized ones
        }

    def submit_post(self, post_text: str, media_files: Optional[List[gr.File]]):
        """Submit a post to all authorized platforms.

        Args:
            post_text (str): The text content of the post.
            media_files (Optional[List[gr.File]]): List of uploaded file objects from Gradio.

        Returns:
            Dict: Status of the posting operation.
        """
        if not post_text.strip():
            return {
                "success": False,
                "message": "Post text cannot be empty"
            }

        # Get list of platforms that are currently authorized
        platforms_to_post = [p for p in PLATFORMS if self.authorized_platforms[p]]

        if not platforms_to_post:
            return {
                "success": False,
                "message": "No authorized platforms to post to. Please authorize platforms first."
            }

        # Extract file paths from Gradio File objects
        media_file_paths = [file.name for file in media_files] if media_files else None
        print(f"Submitting post to: {platforms_to_post} with media: {media_file_paths}")


        # Post to all authorized platforms
        results = post_to_platforms(platforms_to_post, post_text, media_file_paths)
        print(f"Posting results: {results}")


        # Check results
        successful_posts = [p for p, res in results.items() if res.get("success")]
        failed_posts = [f"{p} ({res.get('error', 'Unknown error')})" for p, res in results.items() if not res.get("success")]


        if not successful_posts:
             return {
                "success": False,
                "message": f"Failed to post to all platforms. Errors: {', '.join(failed_posts)}",
                "results": results
            }

        message = f"Posted successfully to: {', '.join(successful_posts)}."
        if failed_posts:
            message += f" Failed on: {', '.join(failed_posts)}."


        return {
            "success": True,
            "message": message,
            "results": results
        }

    def get_drafts_list(self):
        """Get list of drafts for the dropdown."""
        drafts = load_drafts()
        # Format for dropdown: list of tuples (display_name, id) or just list of ids
        # Let's use a more descriptive name if possible
        choices = [(f"Draft {d['id']} ({time.strftime('%Y-%m-%d %H:%M', time.localtime(d.get('created_at', 0)))})", d['id']) for d in drafts]
        # Update the dropdown choices
        return gr.update(choices=choices)


    def load_selected_draft(self, draft_id: str):
        """Load the content of the selected draft."""
        if not draft_id:
            return "" # No draft selected

        drafts = load_drafts()
        selected_draft = next((d for d in drafts if d['id'] == draft_id), None)

        if selected_draft:
            # Update the post text area
            return gr.update(value=selected_draft.get('text', ''))
        else:
            # Handle case where draft ID is not found (e.g., deleted)
            return gr.update(value="") # Clear text area


    def handle_save_draft(self, post_text: str):
        """Handle saving a draft and update the drafts list."""
        if not post_text.strip():
             return gr.update(value={"success": False, "error": "Cannot save empty draft."}), gr.update() # No change to dropdown

        result = save_draft(post_text) # Assuming save_draft only needs text for now

        # Refresh the drafts dropdown after saving
        new_drafts_list = self.get_drafts_list()

        return gr.update(value=result), new_drafts_list # Return update for status and dropdown


    def build_interface(self):
        """Build the complete Gradio interface."""
        with gr.Blocks(title="Simulpost", theme=gr.themes.Soft()) as interface:
            gr.Markdown("# Simulpost")
            gr.Markdown("Post simultaneously to multiple social media platforms.")

            # State variables
            state = gr.State({"current_screen": "api_form"})
            api_key_inputs_flat = [] # To store all input components for API keys

            # --- Screen 1: API Form ---
            with gr.Group(visible=True) as api_form:
                gr.Markdown("## Step 1: Select Platforms & Enter API Keys")
                platform_checkboxes = {}
                platform_input_groups = {} # To control visibility

                for platform in PLATFORMS:
                    with gr.Row():
                        with gr.Column(scale=1, min_width=150):
                            platform_checkboxes[platform] = gr.Checkbox(
                                label=platform,
                                value=self.selected_platforms[platform],
                                elem_id=f"{platform}_checkbox"
                            )
                        with gr.Column(scale=3):
                             # Group for API inputs - visibility controlled by checkbox
                             with gr.Group(visible=self.selected_platforms[platform]) as input_group:
                                platform_input_groups[platform] = input_group
                                if platform == "X (Twitter)":
                                    api_key = gr.Textbox(label="API Key", type="password", placeholder="Enter Twitter API Key")
                                    api_secret = gr.Textbox(label="API Key Secret", type="password", placeholder="Enter Twitter API Key Secret")
                                    access_token = gr.Textbox(label="Access Token", type="password", placeholder="Enter Twitter Access Token")
                                    access_secret = gr.Textbox(label="Access Token Secret", type="password", placeholder="Enter Twitter Access Token Secret")
                                    api_key_inputs_flat.extend([api_key, api_secret, access_token, access_secret])
                                else:
                                    # Single API key input for others
                                    api_key = gr.Textbox(
                                        label=f"API Key / Credentials", # Generic label
                                        type="password",
                                        placeholder=f"Enter {platform} API Key or necessary credentials"
                                    )
                                    api_key_inputs_flat.append(api_key)


                # Link checkboxes to visibility of input groups
                for platform in PLATFORMS:
                     platform_checkboxes[platform].change(
                         fn=lambda x: gr.update(visible=x),
                         inputs=[platform_checkboxes[platform]],
                         outputs=[platform_input_groups[platform]],
                         queue=False # Faster UI update
                     )


                gr.Markdown(
                    """
                    **Note on API Keys**:
                    - **X (Twitter)**: Provide all four credentials (API Key, Secret, Access Token, Secret) from your Twitter Developer App settings.
                    - **Other Platforms**: Enter the required API key or credentials as specified by the platform. Implementations for platforms other than Twitter are pending.
                    *(Keys are stored encrypted)*
                    """
                )

                api_submit_btn = gr.Button("Verify and Save Keys")
                api_status = gr.JSON(label="API Key Status", visible=False) # Initially hidden

                # Collect checkbox components for the update function
                checkbox_inputs = [platform_checkboxes[p] for p in PLATFORMS]


                 # Update internal selection state when checkboxes change
                # This is tricky because change triggers visibility *and* we need the state updated for submit
                # Let's bind the checkbox values directly to the submit function instead of relying on intermediate state update.


            # --- Screen 2: Auth Form ---
            with gr.Group(visible=False) as auth_form:
                gr.Markdown("## Step 2: Authorize Platforms")
                auth_platforms_md = gr.Markdown("Checking authorization status...")
                auth_btn = gr.Button("Authorize Selected Platforms")
                auth_status = gr.JSON(label="Authorization Status", visible=False) # Initially hidden

            # --- Screen 3: Post Form ---
            with gr.Group(visible=False) as post_form:
                gr.Markdown("## Step 3: Create & Publish Post")
                post_platforms_md = gr.Markdown("Authorized platforms will appear here.")

                # Draft Management
                with gr.Row():
                    drafts_dropdown = gr.Dropdown(label="Load Draft", choices=[], interactive=True)
                    load_draft_btn = gr.Button("Load", size="sm")

                post_text = gr.Textbox(label="Post Content", placeholder="What's happening?", lines=8, interactive=True)
                char_counter = gr.Markdown("0 characters")
                media_upload = gr.File(label="Upload Media (Optional)", file_count="multiple", type="filepath", interactive=True) # Use filepath

                with gr.Row():
                    post_btn = gr.Button("Post to Authorized Platforms", variant="primary")
                    save_draft_btn = gr.Button("Save Draft")

                post_status = gr.JSON(label="Posting Status", visible=False) # Initially hidden
                draft_status = gr.JSON(label="Draft Status", visible=False) # Initially hidden

                # Back button
                restart_btn = gr.Button("Start Over / Manage Keys")


                # --- Post Form Logic ---
                post_text.change(fn=lambda x: f"{len(x)} characters", inputs=[post_text], outputs=[char_counter], queue=False)

                # Draft loading
                load_draft_btn.click(
                    fn=self.load_selected_draft,
                    inputs=[drafts_dropdown],
                    outputs=[post_text]
                )

                # Save draft and refresh dropdown
                save_draft_btn.click(
                    fn=self.handle_save_draft,
                    inputs=[post_text],
                    outputs=[draft_status, drafts_dropdown] # Update status and dropdown list
                ).then(lambda: gr.update(visible=True), outputs=[draft_status]) # Show status


            # --- Screen Transition Logic ---

            # API Submit -> Auth Screen
            api_submit_btn.click(
                fn=self.submit_api_keys,
                inputs=checkbox_inputs + api_key_inputs_flat, # Pass checkboxes first, then all API fields
                outputs=[api_status]
            ).then(
                 fn=lambda result: (
                     gr.update(visible=True), # Show status message
                     # Switch screen visibility based on success
                     gr.update(visible=not result.get("success", False)), # Hide API form if success
                     gr.update(visible=result.get("success", False)), # Show Auth form if success
                     # Update markdown in Auth screen
                     gr.update(value=f"Ready to authorize:\n- " + "\n- ".join(result.get("platforms",))) if result.get("success", False) else ""
                 ),
                 inputs=[api_status],
                 outputs=[api_status, api_form, auth_form, auth_platforms_md]
            )


            # Auth Submit -> Post Screen
            auth_btn.click(
                fn=self.authorize_platforms,
                inputs=[],
                outputs=[auth_status]
            ).then(
                fn=lambda result: (
                    gr.update(visible=True), # Show status
                    # Switch screen visibility
                    gr.update(visible=not result.get("success", False)), # Hide Auth form if success
                    gr.update(visible=result.get("success", False)), # Show Post form if success
                    # Update markdown in Post screen
                     gr.update(value=f"Posting to:\n- " + "\n- ".join(result.get("platforms",))) if result.get("success", False) else "No platforms authorized."
                ),
                inputs=[auth_status],
                outputs=[auth_status, auth_form, post_form, post_platforms_md]
            ).then( # Chain another .then to refresh drafts when entering post screen
                fn=self.get_drafts_list,
                inputs=[],
                outputs=[drafts_dropdown]
            )


            # Post Submit
            post_btn.click(
                fn=self.submit_post,
                inputs=[post_text, media_upload],
                outputs=[post_status]
            ).then(lambda: gr.update(visible=True), outputs=[post_status]) # Show status


            # Restart Button -> API Screen
            restart_btn.click(
                fn=lambda: (gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), # Show API, hide Auth, hide Post
                           gr.update(value=None), gr.update(value=None), gr.update(value=None)), # Clear statuses
                outputs=[api_form, auth_form, post_form, api_status, auth_status, post_status]
            )


            return interface

    def launch(self):
        """Launch the Gradio interface."""
        interface = self.build_interface()
        interface.launch()

if __name__ == "__main__":
    app = SimulpostApp()
    app.launch()