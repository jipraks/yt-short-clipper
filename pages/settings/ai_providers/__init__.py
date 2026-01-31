"""
AI Provider settings pages
"""

from pages.settings.ai_providers.highlight_finder import HighlightFinderSettingsPage
from pages.settings.ai_providers.caption_maker import CaptionMakerSettingsPage
from pages.settings.ai_providers.hook_maker import HookMakerSettingsPage
from pages.settings.ai_providers.title_generator import TitleGeneratorSettingsPage

__all__ = [
    'HighlightFinderSettingsPage',
    'CaptionMakerSettingsPage',
    'HookMakerSettingsPage',
    'TitleGeneratorSettingsPage'
]
