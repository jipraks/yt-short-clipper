"""
Title Generator Settings Page
"""

import customtkinter as ctk

from pages.settings.ai_providers.base_provider import BaseProviderSettingsPage


class TitleGeneratorSettingsPage(BaseProviderSettingsPage):
    """Settings page for Title Generator AI provider"""
    
    # Load models from API (no fixed list)
    FIXED_MODELS = None
    
    def __init__(self, parent, config, on_save_callback, on_back_callback):
        super().__init__(
            parent=parent,
            title="Title Generator",
            provider_key="youtube_title_maker",
            config=config,
            on_save_callback=on_save_callback,
            on_back_callback=on_back_callback
        )
    
    def create_provider_content(self):
        """Create provider settings content with additional info"""
        # Info box
        info_frame = ctk.CTkFrame(self.content, fg_color=("gray85", "gray20"), corner_radius=8)
        info_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(info_frame, text="📺 About Title Generator", 
            font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(10, 5))
        ctk.CTkLabel(info_frame, 
            text="Uses GPT models to generate SEO-optimized titles,\ndescriptions, and tags for YouTube uploads.", 
            font=ctk.CTkFont(size=10), text_color="gray", justify="left").pack(anchor="w", padx=12, pady=(0, 10))
        
        # Call parent to create standard fields
        super().create_provider_content()
