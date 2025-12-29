"""
Google Cloud TTS voice settings presets.

Voice Quality Tiers (best to basic):
1. Studio voices (en-US-Studio-*) - Professional, limited styles
2. Journey voices (en-US-Journey-*) - Conversational, natural
3. Neural2 voices (en-US-Neural2-*) - High quality, good range
4. Wavenet voices (en-US-Wavenet-*) - Good quality
5. Standard voices (en-US-Standard-*) - Basic quality

Recommended for video narration:
- en-US-Studio-O (female) - Professional, clear
- en-US-Studio-Q (male) - Professional, authoritative
- en-US-Journey-D (male) - Warm, conversational
- en-US-Journey-F (female) - Friendly, engaging
- en-US-Neural2-J (male) - Versatile, good for SSML
"""

from typing import TypedDict, Dict


class VoiceSettings(TypedDict):
	languageCode: str
	name: str
	ssmlGender: str


VOICE_CATALOG: Dict[str, str] = {
    "studio_female": "en-US-Studio-O",
    "studio_male": "en-US-Studio-Q",
    "journey_male": "en-US-Journey-D",
    "journey_female": "en-US-Journey-F",
    "neural2_male": "en-US-Neural2-J",
    "neural2_female": "en-US-Neural2-F",
    "casual_male": "en-US-Casual-K",
    "news_female": "en-US-News-K",
}

DEFAULT_VOICE = "en-US-Studio-O"

VOICE_PRESETS: Dict[str, VoiceSettings] = {
	"default": {
		"languageCode": "en-US",
		"name": DEFAULT_VOICE,
		"ssmlGender": "FEMALE"
	},
    "professional": {
        "languageCode": "en-US",
        "name": "en-US-Studio-O",
        "ssmlGender": "FEMALE"
    },
    "conversational": {
        "languageCode": "en-US",
        "name": "en-US-Journey-D",
        "ssmlGender": "MALE"
    },
    "news": {
        "languageCode": "en-US",
        "name": "en-US-News-K",
        "ssmlGender": "FEMALE"
    },
}


def get_voice_settings(emotion: str | None = None, preset: str = "default") -> VoiceSettings:
    """Get voice settings for a given emotion or preset."""
    return VOICE_PRESETS.get(preset, VOICE_PRESETS["default"])


def get_voice_by_name(name: str) -> VoiceSettings:
    """Get voice settings for a specific voice name."""
    gender = "FEMALE" if name.endswith(("O", "F", "K")) else "MALE"
    return {
        "languageCode": "en-US",
        "name": name,
        "ssmlGender": gender
    }
