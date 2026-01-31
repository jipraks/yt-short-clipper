"""
AI API Settings Sub-Page - Card-based navigation to individual providers
"""

import customtkinter as ctk

from pages.settings.base_dialog import BaseSettingsSubPage


class AIAPISettingsSubPage(BaseSettingsSubPage):
    """Sub-page for AI API settings with card navigation"""
    
    def __init__(self, parent, config, on_save_callback, on_back_callback):
        self.config = config
        self.on_save_callback = on_save_callback
        self.main_back = on_back_callback
        self.container = parent
        
        super().__init__(parent, "AI API Settings", on_back_callback)
        
        self.create_content()
    
    def create_content(self):
        """Create page content with provider cards - NO Provider Type buttons here"""
        # AI Providers Section only
        providers_section = self.create_section("AI Providers")
        
        cards_frame = ctk.CTkFrame(providers_section, fg_color="transparent")
        cards_frame.pack(fill="x", padx=10, pady=(0, 12))
        cards_frame.grid_columnconfigure((0, 1), weight=1, uniform="provider")
        
        # Row 1
        self._create_provider_card(cards_frame, 0, 0, "Highlight Finder", 
            "Find viral moments", "highlight_finder")
        self._create_provider_card(cards_frame, 0, 1, "Caption Maker", 
            "Generate captions", "caption_maker")
        
        # Row 2
        self._create_provider_card(cards_frame, 1, 0, "Hook Maker", 
            "Create TTS hooks", "hook_maker")
        self._create_provider_card(cards_frame, 1, 1, "Title Generator", 
            "Generate titles", "youtube_title_maker")
    
    def _create_provider_card(self, parent, row, col, title, desc, key):
        """Create a clickable provider card"""
        card = ctk.CTkFrame(parent, fg_color=("gray85", "gray20"), corner_radius=8, cursor="hand2")
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        card.bind("<Button-1>", lambda e, k=key: self.navigate_to_provider(k))
        
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 5))
        header.bind("<Button-1>", lambda e, k=key: self.navigate_to_provider(k))
        
        ctk.CTkLabel(header, text=title, 
            font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        
        status = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=10))
        status.pack(side="right")
        setattr(self, f"{key}_status", status)
        
        d = ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=9), text_color="gray")
        d.pack(anchor="w", padx=12, pady=(0, 5))
        d.bind("<Button-1>", lambda e, k=key: self.navigate_to_provider(k))
        
        m = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=9), text_color="gray")
        m.pack(anchor="w", padx=12, pady=(0, 12))
        m.bind("<Button-1>", lambda e, k=key: self.navigate_to_provider(k))
        setattr(self, f"{key}_model", m)
        
        card.bind("<Enter>", lambda e: card.configure(fg_color=("gray75", "gray25")))
        card.bind("<Leave>", lambda e: card.configure(fg_color=("gray85", "gray20")))
        
        self._update_status(key)
    
    def _update_status(self, key):
        """Update provider card status"""
        p = self.config.get("ai_providers", {}).get(key, {})
        api_key, model = p.get("api_key", ""), p.get("model", "")
        
        s = getattr(self, f"{key}_status", None)
        m = getattr(self, f"{key}_model", None)
        
        if s:
            if api_key and model:
                s.configure(text="Configured", text_color="green")
            elif api_key:
                s.configure(text="No model", text_color="orange")
            else:
                s.configure(text="Not set", text_color="gray")
        
        if m:
            m.configure(text=f"Model: {model}" if model else "Model: Not set")
    
    def navigate_to_provider(self, key):
        """Navigate to provider settings page"""
        for w in self.container.winfo_children():
            w.destroy()
        
        if key == "highlight_finder":
            from pages.settings.ai_providers.highlight_finder import HighlightFinderSettingsPage
            HighlightFinderSettingsPage(self.container, self.config, self.on_save_callback, self._back)
        elif key == "caption_maker":
            from pages.settings.ai_providers.caption_maker import CaptionMakerSettingsPage
            CaptionMakerSettingsPage(self.container, self.config, self.on_save_callback, self._back)
        elif key == "hook_maker":
            from pages.settings.ai_providers.hook_maker import HookMakerSettingsPage
            HookMakerSettingsPage(self.container, self.config, self.on_save_callback, self._back)
        elif key == "youtube_title_maker":
            from pages.settings.ai_providers.title_generator import TitleGeneratorSettingsPage
            TitleGeneratorSettingsPage(self.container, self.config, self.on_save_callback, self._back)
    
    def _back(self):
        """Navigate back to AI API settings"""
        for w in self.container.winfo_children():
            w.destroy()
        AIAPISettingsSubPage(self.container, self.config, self.on_save_callback, self.main_back)
