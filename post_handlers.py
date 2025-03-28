"""
Post handlers module for Simulpost.

This module provides functions for posting content to multiple platforms.
"""

import os
import json
from typing import Dict, Any, List, Optional
import time

# Import platform modules
from platforms import twitter

# Import auth handlers for loading auth tokens
from auth_handlers import load_auth_tokens, check_auth_status, refresh_auth

# Constants
PLATFORM_CHARACTER_LIMITS = {
    "X (Twitter)": 280,
    "Threads": 500,
    "Bluesky": 300,
    "Mastodon": 500,
    "LinkedIn": 3000
}

def format_post_for_platform(platform: str, post_text: str, max_length: Optional[int] = None) -> str:
    """
    Format a post for a specific platform, considering character limits and platform-specific features.
    
    Args:
        platform (str): Name of the platform to format for
        post_text (str): Original text content of the post
        max_length (Optional[int]): Optional maximum length for the post
    
    Returns:
        str: Formatted post text
    """
    # Get the character limit for the platform
    if platform == "X (Twitter)":
        limit = twitter.get_character_limit()
    else:
        limit = PLATFORM_CHARACTER_LIMITS.get(platform, 500)
    
    # Override with provided max_length if specified
    if max_length is not None:
        limit = max_length
    
    # Truncate the post if it exceeds the limit
    if len(post_text) > limit:
        # Leave room for ellipsis
        truncated_text = post_text[:limit - 3] + "..."
        return truncated_text
    
    return post_text

def validate_post_length(platform: str, post_text: str) -> bool:
    """
    Validate if a post is within the character limit for a platform.
    
    Args:
        platform (str): Name of the platform
        post_text (str): Text content of the post
    
    Returns:
        bool: True if the post is within the limit, False otherwise
    """
    # Get the character limit for the platform
    if platform == "X (Twitter)":
        limit = twitter.get_character_limit()
    else:
        limit = PLATFORM_CHARACTER_LIMITS.get(platform, 500)
    
    return len(post_text) <= limit

def post_to_platform(platform: str, post_text: str, media_files: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Post content to a specific platform.
    
    Args:
        platform (str): Name of the platform to post to
        post_text (str): Text content of the post
        media_files (Optional[List[str]]): Optional list of paths to media files to include in the post
    
    Returns:
        Dict[str, Any]: Dictionary containing the result of the post
    """
    # Check if the platform is authorized
    auth_status = check_auth_status(platform)
    
    if not auth_status.get("authorized", False):
        if auth_status.get("needs_refresh", False):
            # Try to refresh the authorization
            refresh_result = refresh_auth(platform)
            if not refresh_result.get("success", False):
                return {
                    "success": False,
                    "error": f"Failed to refresh authorization for {platform}: {refresh_result.get('error', 'Unknown error')}"
                }
        else:
            return {
                "success": False,
                "error": f"{platform} is not authorized"
            }
    
    # Load auth tokens
    auth_tokens = load_auth_tokens()
    
    if platform not in auth_tokens:
        return {
            "success": False,
            "error": f"No authorization token found for {platform}"
        }
    
    auth_token = auth_tokens[platform].get("auth_token")
    
    # Format the post for the platform
    formatted_post = format_post_for_platform(platform, post_text)
    
    # Post to the platform
    if platform == "X (Twitter)":
        return twitter.post(auth_token, formatted_post, media_files)
    # Add posting for other platforms as they are implemented
    else:
        # For now, simulate successful posting for other platforms
        return {
            "success": True,
            "post_id": f"mock-id-{platform}-{int(time.time())}",
            "post_url": f"https://example.com/{platform.lower()}/post/{int(time.time())}"
        }

def post_to_platforms(platforms: List[str], post_text: str, media_files: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Post content to multiple platforms.
    
    Args:
        platforms (List[str]): List of platform names to post to
        post_text (str): Text content of the post
        media_files (Optional[List[str]]): Optional list of paths to media files to include in the post
    
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping platform names to result dictionaries
    """
    results = {}
    
    for platform in platforms:
        # Validate post length
        if not validate_post_length(platform, post_text):
            # Format the post to fit within the platform's character limit
            formatted_post = format_post_for_platform(platform, post_text)
            result = post_to_platform(platform, formatted_post, media_files)
        else:
            result = post_to_platform(platform, post_text, media_files)
        
        results[platform] = result
    
    return results

def save_draft(post_text: str, media_files: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Save a draft post for later.
    
    Args:
        post_text (str): Text content of the post
        media_files (Optional[List[str]]): Optional list of paths to media files to include in the post
    
    Returns:
        Dict[str, Any]: Dictionary containing the result of saving the draft
    """
    try:
        # Create drafts directory if it doesn't exist
        if not os.path.exists("drafts"):
            os.makedirs("drafts")
        
        # Generate a unique filename based on timestamp
        timestamp = int(time.time())
        filename = f"drafts/draft_{timestamp}.json"
        
        # Save the draft
        draft = {
            "text": post_text,
            "media_files": media_files,
            "created_at": timestamp
        }
        
        with open(filename, 'w') as f:
            json.dump(draft, f)
        
        return {
            "success": True,
            "draft_id": str(timestamp),
            "filename": filename
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def load_drafts() -> List[Dict[str, Any]]:
    """
    Load all saved drafts.
    
    Returns:
        List[Dict[str, Any]]: List of draft dictionaries
    """
    drafts = []
    
    if not os.path.exists("drafts"):
        return drafts
    
    try:
        for filename in os.listdir("drafts"):
            if filename.startswith("draft_") and filename.endswith(".json"):
                with open(f"drafts/{filename}", 'r') as f:
                    draft = json.load(f)
                    draft["id"] = filename.replace("draft_", "").replace(".json", "")
                    drafts.append(draft)
        
        # Sort drafts by creation time (newest first)
        drafts.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        
        return drafts
    except Exception as e:
        print(f"Error loading drafts: {e}")
        return []
