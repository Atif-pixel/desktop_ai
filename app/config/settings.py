"""Settings model.

Step 2B defines a simple settings structure; loading from env/files is deferred.
"""

from __future__ import annotations

from dataclasses import dataclass

from .constants import DEFAULT_LANGUAGE, DEFAULT_WAKEWORD


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the assistant."""

    language: str = DEFAULT_LANGUAGE
    wakeword: str = DEFAULT_WAKEWORD
