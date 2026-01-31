"""
Settings page for YT Short Clipper - Card-based layout with sub-pages
"""

import customtkinter as ctk
from tkinter import messagebox

from version import __version__


class SettingsPage(ctk.CTkFrame):
    """Settings page with card-based navigation to sub-pages"""
    
    def __init__(self, parent, config, on_save_callback, on_back_callback, output_dir, check_update_callback=None):
        super().__init__(parent)
        self.config = config
        self.on_save = on_save_callback
        self.on_back = on_back_callback
        self.output_dir = output_dir
        self.check_update = check_update_callback
        
        # Container for switching between main and sub-pages
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        
        # Current sub-page
        self.current_subpage = None
        
        self.create_main_page()
    
    def create_main_page(self):
        """Create the main settings page with cards"""
        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()
        
        self.current_subpage = None
        
        # Main frame
        main_frame = ctk.CTkFrame(self.container, fg_color=("#1a1a1a", "#0a0a0a"))
        main_frame.pack(fill="both", expand=True)
        
        from components.page_layout import PageHeader, PageFooter
        
        # Header with back button
        header = PageHeader(main_frame, self, show_nav_buttons=False, show_back_button=True, page_title="Settings")
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        # Footer (pack first to stay at bottom)
        footer = PageFooter(main_frame, self)
        footer.pack(fill="x", padx=20, pady=(0, 15), side="bottom")
        
        # Scrollable main content
        main = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Settings cards container
        cards_section = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        cards_section.pack(fill="x", pady=(15, 10))
        
        ctk.CTkLabel(cards_section, text="Settings", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(12, 8))
        
        # Cards grid - 4 cards per row
        cards_frame = ctk.CTkFrame(cards_section, fg_color="transparent")
        cards_frame.pack(fill="x", padx=10, pady=(0, 12))
        cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="settings")
        
        # Row 1: AI API, Performance, Output, Watermark
        self._create_setting_card(cards_frame, 0, 0, "🤖", "AI API", "Configure AI providers", "ai_api")
        self._create_setting_card(cards_frame, 0, 1, "⚡", "Performance", "GPU & encoding", "performance")
        self._create_setting_card(cards_frame, 0, 2, "📁", "Output", "Output directory", "output")
        self._create_setting_card(cards_frame, 0, 3, "💧", "Watermark", "Video watermark", "watermark")
        
        # Row 2: Credit Watermark, Repliz, YouTube API, About
        self._create_setting_card(cards_frame, 1, 0, "📝", "Credit", "Channel name credit", "credit_watermark")
        self._create_setting_card(cards_frame, 1, 1, "🎬", "Repliz", "Repliz integration", "repliz")
        self._create_setting_card(cards_frame, 1, 2, "📺", "YouTube API", "YouTube OAuth", "youtube_api")
        self._create_setting_card(cards_frame, 1, 3, "ℹ️", "About", "App info & updates", "about")
    
    def _create_setting_card(self, parent, row, col, icon, title, description, page_key):
        """Create a clickable settings card"""
        card = ctk.CTkFrame(parent, fg_color=("gray85", "gray20"), corner_radius=8, cursor="hand2")
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        # Make entire card clickable
        card.bind("<Button-1>", lambda e, k=page_key: self.navigate_to_subpage(k))
        
        # Icon
        icon_label = ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=24))
        icon_label.pack(anchor="w", padx=12, pady=(12, 5))
        icon_label.bind("<Button-1>", lambda e, k=page_key: self.navigate_to_subpage(k))
        
        # Title
        title_label = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12, weight="bold"))
        title_label.pack(anchor="w", padx=12)
        title_label.bind("<Button-1>", lambda e, k=page_key: self.navigate_to_subpage(k))
        
        # Description
        desc_label = ctk.CTkLabel(card, text=description, font=ctk.CTkFont(size=9), text_color="gray")
        desc_label.pack(anchor="w", padx=12, pady=(2, 12))
        desc_label.bind("<Button-1>", lambda e, k=page_key: self.navigate_to_subpage(k))
        
        # Hover effect
        def on_enter(e):
            card.configure(fg_color=("gray75", "gray25"))
        def on_leave(e):
            card.configure(fg_color=("gray85", "gray20"))
        
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        
        return card
    
    def navigate_to_subpage(self, page_key):
        """Navigate to a settings sub-page"""
        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()
        
        self.current_subpage = page_key
        
        # Create sub-page based on key
        if page_key == "ai_api":
            from pages.settings.ai_api_settings import AIAPISettingsSubPage
            AIAPISettingsSubPage(self.container, self.config, self._on_settings_saved, self.create_main_page)
        elif page_key == "performance":
            from pages.settings.performance_settings import PerformanceSettingsSubPage
            PerformanceSettingsSubPage(self.container, self.config, self._on_settings_saved, self.create_main_page)
        elif page_key == "output":
            from pages.settings.output_settings import OutputSettingsSubPage
            OutputSettingsSubPage(self.container, self.config, self.output_dir, self._on_settings_saved, self.create_main_page)
        elif page_key == "watermark":
            from pages.settings.watermark_settings import WatermarkSettingsSubPage
            WatermarkSettingsSubPage(self.container, self.config, self._on_settings_saved, self.create_main_page)
        elif page_key == "credit_watermark":
            from pages.settings.credit_watermark_settings import CreditWatermarkSettingsSubPage
            CreditWatermarkSettingsSubPage(self.container, self.config, self._on_settings_saved, self.create_main_page)
        elif page_key == "repliz":
            from pages.settings.repliz_settings import ReplizSettingsSubPage
            ReplizSettingsSubPage(self.container, self.config, self._on_settings_saved, self.create_main_page)
        elif page_key == "youtube_api":
            from pages.settings.youtube_api_settings import YouTubeAPISettingsSubPage
            YouTubeAPISettingsSubPage(self.container, self.config, self._on_settings_saved, self.create_main_page)
        elif page_key == "about":
            from pages.settings.about_settings import AboutSettingsSubPage
            AboutSettingsSubPage(self.container, self.config, self.check_update, self.create_main_page)
    
    def _on_settings_saved(self, updated_config):
        """Handle settings saved from sub-page"""
        # ConfigManager uses .config dict internally
        if hasattr(self.config, 'config'):
            # Deep merge updated_config into config.config
            for key, value in updated_config.items():
                if isinstance(value, dict) and key in self.config.config and isinstance(self.config.config[key], dict):
                    self.config.config[key].update(value)
                else:
                    self.config.config[key] = value
            self.config.save()
            print(f"[DEBUG] Config saved to file: {self.config.config_file}")
        else:
            # Fallback for dict config
            self.config.update(updated_config)
        
        if self.on_save:
            self.on_save(updated_config)
    
    # ===== Helper Methods =====
    
    def open_github(self):
        """Open GitHub repository"""
        import webbrowser
        webbrowser.open("https://github.com/jipraks/yt-short-clipper")
    
    def open_discord(self):
        """Open Discord server"""
        import webbrowser
        webbrowser.open("https://s.id/ytsdiscord")
    
    def show_page(self, page_name):
        """Delegate to parent app's show_page method"""
        try:
            parent = self.master
            while parent and not hasattr(parent, 'show_page'):
                parent = parent.master
            if parent and hasattr(parent, 'show_page'):
                parent.show_page(page_name)
        except:
            pass
