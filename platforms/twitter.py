"""
Twitter platform module for Simulpost.

This module provides functions for interacting with the Twitter (X) API.

The Twitter API key is expected to be in the format:
"consumer_key,consumer_secret,access_token,access_token_secret"
These four values are collected separately in the UI and combined into this format
before being passed to the functions in this module.
"""

import tweepy
from typing import Dict, Any, Optional, List
import os
import json

# Constants
TWITTER_CONFIG_FILE = "twitter_config.json"

def validate_api_key(api_key: str) -> bool:
    """
    Validate a Twitter API key by attempting to create a client and make a simple request.
    
    Args:
        api_key (str): The Twitter API key to validate. This should be in the format:
                      "consumer_key,consumer_secret,access_token,access_token_secret"
    
    Returns:
        bool: True if the API key is valid, False otherwise
    """
    try:
        # Parse the API key string
        keys = api_key.split(',')
        if len(keys) != 4:
            return False
        
        consumer_key, consumer_secret, access_token, access_token_secret = keys
        
        # Create a client
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Make a simple request to verify credentials
        client.get_me()
        
        return True
    except Exception as e:
        print(f"Error validating Twitter API key: {e}")
        return False

def authorize(api_key: str) -> Dict[str, Any]:
    """
    Authorize with Twitter using the provided API key.
    
    Args:
        api_key (str): The Twitter API key in the format:
                      "consumer_key,consumer_secret,access_token,access_token_secret"
    
    Returns:
        Dict[str, Any]: A dictionary containing authorization information:
            - success (bool): Whether authorization was successful
            - auth_token (str): The authorization token (if successful)
            - error (str): Error message (if unsuccessful)
            - user_info (Dict): Information about the authenticated user (if successful)
    """
    try:
        # Parse the API key string
        keys = api_key.split(',')
        if len(keys) != 4:
            return {
                "success": False,
                "error": "Invalid API key format. Expected: consumer_key,consumer_secret,access_token,access_token_secret"
            }
        
        consumer_key, consumer_secret, access_token, access_token_secret = keys
        
        # Create a client
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Get user information
        user = client.get_me(user_fields=["name", "username", "profile_image_url"])
        
        # Save the configuration
        config = {
            "consumer_key": consumer_key,
            "consumer_secret": consumer_secret,
            "access_token": access_token,
            "access_token_secret": access_token_secret,
            "user_id": user.data.id,
            "username": user.data.username,
            "name": user.data.name
        }
        
        try:
            with open(TWITTER_CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving Twitter configuration: {e}")
        
        return {
            "success": True,
            "auth_token": api_key,  # We're just returning the API key as the "auth token" for simplicity
            "user_info": {
                "id": user.data.id,
                "username": user.data.username,
                "name": user.data.name
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def post(auth_token: str, post_text: str, media_files: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Post a tweet to Twitter.
    
    Args:
        auth_token (str): The authorization token (API key)
        post_text (str): The text content of the tweet
        media_files (Optional[List[str]]): Optional list of paths to media files to include in the tweet
    
    Returns:
        Dict[str, Any]: A dictionary containing the result of the post:
            - success (bool): Whether posting was successful
            - post_id (str): ID of the tweet (if successful)
            - post_url (str): URL of the tweet (if successful)
            - error (str): Error message (if unsuccessful)
    """
    try:
        # Check if we have a saved configuration
        if os.path.exists(TWITTER_CONFIG_FILE):
            try:
                with open(TWITTER_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    consumer_key = config.get("consumer_key")
                    consumer_secret = config.get("consumer_secret")
                    access_token = config.get("access_token")
                    access_token_secret = config.get("access_token_secret")
                    username = config.get("username")
            except Exception as e:
                print(f"Error loading Twitter configuration: {e}")
                # Fall back to using the auth_token
                keys = auth_token.split(',')
                if len(keys) != 4:
                    return {
                        "success": False,
                        "error": "Invalid auth token format. Expected: consumer_key,consumer_secret,access_token,access_token_secret"
                    }
                consumer_key, consumer_secret, access_token, access_token_secret = keys
                username = None
        else:
            # Use the auth_token
            keys = auth_token.split(',')
            if len(keys) != 4:
                return {
                    "success": False,
                    "error": "Invalid auth token format. Expected: consumer_key,consumer_secret,access_token,access_token_secret"
                }
            consumer_key, consumer_secret, access_token, access_token_secret = keys
            username = None
        
        # Create a client
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Create a tweet
        media_ids = []
        
        # Handle media files if provided
        if media_files and len(media_files) > 0:
            # For media uploads, we need the v1 API
            auth = tweepy.OAuth1UserHandler(
                consumer_key, consumer_secret, access_token, access_token_secret
            )
            api = tweepy.API(auth)
            
            for media_file in media_files:
                media = api.media_upload(media_file)
                media_ids.append(media.media_id)
        
        # Post the tweet
        response = client.create_tweet(
            text=post_text,
            media_ids=media_ids if media_ids else None
        )
        
        tweet_id = response.data['id']
        
        # Construct the tweet URL
        tweet_url = f"https://twitter.com/{username}/status/{tweet_id}" if username else f"https://twitter.com/i/web/status/{tweet_id}"
        
        return {
            "success": True,
            "post_id": str(tweet_id),
            "post_url": tweet_url
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_character_limit() -> int:
    """
    Get the character limit for Twitter posts.
    
    Returns:
        int: The maximum number of characters allowed in a tweet
    """
    return 280
