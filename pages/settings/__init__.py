"""
Settings sub-pages for YT Short Clipper
"""

from pages.settings.ai_api_settings import AIAPISettingsSubPage
from pages.settings.performance_settings import PerformanceSettingsSubPage
from pages.settings.output_settings import OutputSettingsSubPage
from pages.settings.watermark_settings import WatermarkSettingsSubPage
from pages.settings.repliz_settings import ReplizSettingsSubPage
from pages.settings.youtube_api_settings import YouTubeAPISettingsSubPage
from pages.settings.about_settings import AboutSettingsSubPage

__all__ = [
    'AIAPISettingsSubPage',
    'PerformanceSettingsSubPage', 
    'OutputSettingsSubPage',
    'WatermarkSettingsSubPage',
    'ReplizSettingsSubPage',
    'YouTubeAPISettingsSubPage',
    'AboutSettingsSubPage'
]
