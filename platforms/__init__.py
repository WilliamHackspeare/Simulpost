"""
Platforms package for Simulpost.

This package contains modules for interacting with different social media platforms.
Each platform module provides functions for API key validation, authorization, and posting.
"""

from typing import List

# List of supported platforms
SUPPORTED_PLATFORMS = ["X (Twitter)", "Threads", "Bluesky", "Mastodon", "LinkedIn"]

# Import platform modules
from . import twitter
# These imports will be uncommented when the modules are implemented
# from . import threads
# from . import bluesky
# from . import mastodon
# from . import linkedin 