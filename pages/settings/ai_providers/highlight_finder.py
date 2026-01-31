"""
Highlight Finder Settings Page
"""

import customtkinter as ctk

from pages.settings.ai_providers.base_provider import BaseProviderSettingsPage


class HighlightFinderSettingsPage(BaseProviderSettingsPage):
    """Settings page for Highlight Finder AI provider"""
    
    # Load models from API (no fixed list)
    FIXED_MODELS = None
    
    def __init__(self, parent, config, on_save_callback, on_back_callback):
        super().__init__(
            parent=parent,
            title="Highlight Finder",
            provider_key="highlight_finder",
            config=config,
            on_save_callback=on_save_callback,
            on_back_callback=on_back_callback
        )
    
    def create_provider_content(self):
        """Create provider settings content with additional info"""
        # Info box
        info_frame = ctk.CTkFrame(self.content, fg_color=("gray85", "gray20"), corner_radius=8)
        info_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(info_frame, text="🎯 About Highlight Finder", 
            font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(10, 5))
        ctk.CTkLabel(info_frame, 
            text="Uses GPT models to analyze video transcripts and find\nthe most engaging moments for short-form content.", 
            font=ctk.CTkFont(size=10), text_color="gray", justify="left").pack(anchor="w", padx=12, pady=(0, 10))
        
        # Call parent to create standard fields
        super().create_provider_content()
