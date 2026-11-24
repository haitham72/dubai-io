"""Local readers for desktop imports initiated by the user.

The caller obtains consent and passes the approved session roots or browser
profile. Browser preview returns only counts for the selected profile.
"""

from .agent_sessions import agent_session_records
from .browser import BrowserProfileError, browser_records, preview

__all__ = ["BrowserProfileError", "agent_session_records", "browser_records", "preview"]
