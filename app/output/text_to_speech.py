"""Text-to-speech interface.

Step 2B defines a tiny contract; implementation is deferred.
"""

from __future__ import annotations


class TextToSpeech:
    """Speak text to the user (placeholder)."""

    def speak(self, text: str) -> None:
        raise NotImplementedError
