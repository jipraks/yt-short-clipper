"""
About Settings Sub-Page
"""

import webbrowser
import customtkinter as ctk

from pages.settings.base_dialog import BaseSettingsSubPage
from version import __version__


class AboutSettingsSubPage(BaseSettingsSubPage):
    """Sub-page showing app information and updates"""
    
    def __init__(self, parent, config, check_update_callback, on_back_callback):
        self.config = config
        self.check_update = check_update_callback
        
        super().__init__(parent, "About", on_back_callback)
        
        self.create_content()
    
    def create_content(self):
        """Create page content"""
        # App info section
        info_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        info_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(info_frame, text="YT Short Clipper", 
            font=ctk.CTkFont(size=20, weight="bold")).pack()
        ctk.CTkLabel(info_frame, text=f"v{__version__}", 
            font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(5, 0))
        
        # Check for updates button
        if self.check_update:
            ctk.CTkButton(info_frame, text="Check for Updates", height=35, width=150,
                fg_color="gray", hover_color=("gray70", "gray30"),
                command=self.check_update).pack(pady=(10, 0))
        
        # Description
        desc_frame = ctk.CTkFrame(self.content, fg_color=("gray90", "gray17"), corner_radius=10)
        desc_frame.pack(fill="x", pady=(0, 15))
        
        desc_text = """Automated YouTube to Short-Form Content Pipeline

Transform long-form YouTube videos into engaging 
short-form content for TikTok, Instagram Reels, 
and YouTube Shorts."""
        
        ctk.CTkLabel(desc_frame, text=desc_text, justify="center", 
            font=ctk.CTkFont(size=11), wraplength=380).pack(padx=15, pady=15)
        
        # Credits
        credits_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        credits_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(credits_frame, text="Made with coffee by", 
            font=ctk.CTkFont(size=11), text_color="gray").pack()
        ctk.CTkLabel(credits_frame, text="Aji Prakoso", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(5, 0))
        
        # Links
        links_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        links_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkButton(links_frame, text="GitHub Repository", height=40,
            fg_color=("#24292e", "#0d1117"), hover_color=("#2c3136", "#161b22"),
            command=lambda: webbrowser.open("https://github.com/jipraks/yt-short-clipper")).pack(fill="x", pady=2)
        
        ctk.CTkButton(links_frame, text="@jipraks on Instagram", height=40,
            fg_color=("#E4405F", "#C13584"), hover_color=("#F56040", "#E1306C"),
            command=lambda: webbrowser.open("https://instagram.com/jipraks")).pack(fill="x", pady=2)
        
        ctk.CTkButton(links_frame, text="YouTube Channel", height=40,
            fg_color=("#c4302b", "#FF0000"), hover_color=("#ff0000", "#CC0000"),
            command=lambda: webbrowser.open("https://youtube.com/@jipraks")).pack(fill="x", pady=2)
        
        # Footer
        footer_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", pady=(10, 0))
        
        ctk.CTkLabel(footer_frame, text="Open Source - MIT License", 
            font=ctk.CTkFont(size=10), text_color="gray").pack()
