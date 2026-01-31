"""
YT Short Clipper Desktop App
"""

import customtkinter as ctk
import threading
import json
import os
import sys
import subprocess
import re
import urllib.request
import io
from pathlib import Path
from tkinter import filedialog, messagebox
from openai import OpenAI
from PIL import Image, ImageTk

# Import version info
from version import __version__, UPDATE_CHECK_URL

# Import utilities
from utils.helpers import get_app_dir, get_bundle_dir, get_ffmpeg_path, get_ytdlp_path, extract_video_id
from utils.logger import debug_log, setup_error_logging, log_error, get_error_log_path
from config.config_manager import ConfigManager
from dialogs.model_selector import SearchableModelDropdown
from dialogs.youtube_upload import YouTubeUploadDialog
from components.progress_step import ProgressStep
from pages.settings_page import SettingsPage
from pages.browse_page import BrowsePage
from pages.results_page import ResultsPage
from pages.status_pages import APIStatusPage, LibStatusPage
from pages.processing_page import ProcessingPage
from pages.contact_page import ContactPage

# Fix for PyInstaller windowed mode (console=False)
# When built with console=False, sys.stdout and sys.stderr are None
# This causes 'NoneType' object has no attribute 'flush' errors
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

APP_DIR = get_app_dir()
BUNDLE_DIR = get_bundle_dir()

# Setup error logging to file (for production builds)
setup_error_logging(APP_DIR)

CONFIG_FILE = APP_DIR / "config.json"
OUTPUT_DIR = APP_DIR / "output"
ASSETS_DIR = BUNDLE_DIR / "assets"
ICON_PATH = ASSETS_DIR / "icon.png"
ICON_ICO_PATH = ASSETS_DIR / "icon.ico"
COOKIES_FILE = APP_DIR / "cookies.txt"  # NEW: Cookies file path


class YTShortClipperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.config = ConfigManager(CONFIG_FILE, OUTPUT_DIR)
        self.client = None
        self.current_thumbnail = None
        self.processing = False
        self.cancelled = False
        self.token_usage = {"gpt_input": 0, "gpt_output": 0, "whisper_seconds": 0, "tts_chars": 0}
        self.youtube_connected = False
        self.youtube_channel = None
        self.ytdlp_path = get_ytdlp_path()  # NEW: Store yt-dlp path for subtitle fetching
        self.cookies_path = COOKIES_FILE  # NEW: Store cookies path
        
        self.title("YT Short Clipper")
        self.geometry("780x620")
        self.resizable(False, False)
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Set app icon after window is created
        self.after(200, self.set_app_icon)
        
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        
        self.pages = {}
        self.create_home_page()
        self.create_processing_page()
        self.create_results_page()
        self.create_browse_page()
        self.create_settings_page()
        self.create_api_status_page()
        self.create_lib_status_page()
        self.create_contact_page()
        
        self.show_page("home")
        self.load_config()
        self.check_youtube_status()
        
        # Update start button state based on cookies
        self.update_start_button_state()
        
        # Check for updates on startup
        threading.Thread(target=self.check_update_silent, daemon=True).start()
    
    def set_app_icon(self):
        """Set window icon"""
        try:
            if sys.platform == "win32":
                # Use .ico file directly on Windows
                if ICON_ICO_PATH.exists():
                    self.iconbitmap(str(ICON_ICO_PATH))
                elif ICON_PATH.exists():
                    # Convert PNG to ICO if needed
                    img = Image.open(ICON_PATH)
                    ico_path = ASSETS_DIR / "icon.ico"
                    img.save(str(ico_path), format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
                    self.iconbitmap(str(ico_path))
            else:
                if ICON_PATH.exists():
                    icon_img = Image.open(ICON_PATH)
                    photo = ImageTk.PhotoImage(icon_img)
                    self.iconphoto(True, photo)
                    self._icon_photo = photo
        except Exception as e:
            print(f"Icon error: {e}")
    
    def show_page(self, name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        
        # Refresh browse list when showing browse page
        if name == "browse":
            self.pages["browse"].refresh_list()
        
        # Refresh API status when showing api_status page
        if name == "api_status":
            self.pages["api_status"].refresh_status()
        
        # Refresh lib status when showing lib_status page
        if name == "lib_status":
            self.pages["lib_status"].refresh_status()
        
        # Reset home page state when returning to home
        if name == "home":
            self.reset_home_page()
    
    def reset_home_page(self):
        """Reset home page to initial state"""
        # Clear URL input
        self.url_var.set("")
        
        # Reset thumbnail - recreate preview placeholder
        self.current_thumbnail = None
        self.create_preview_placeholder()
        
        # Reset subtitle state (keep visible but disabled)
        self.subtitle_loaded = False
        self.subtitle_loading.pack_forget()
        self.subtitle_dropdown.configure(state="disabled", values=["id - Indonesian"])
        self.subtitle_var.set("id - Indonesian")
        
        # Reset clips input to default
        self.clips_var.set("5")
        
        # Reset toggles to default (OFF)
        self.caption_var.set(False)
        self.hook_var.set(False)
        
        # Update switch texts
        self.caption_switch.configure(text="ON")
        self.hook_switch.configure(text="ON")
        
        # Update start button state
        self.update_start_button_state()

    def create_home_page(self):
        page = ctk.CTkFrame(self.container, fg_color=("#1a1a1a", "#0a0a0a"))
        self.pages["home"] = page
        
        # Import header and footer components
        from components.page_layout import PageHeader, PageFooter
        
        # Top header
        header = PageHeader(page, self, show_nav_buttons=True)
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        # Load icons for buttons
        try:
            play_img = Image.open(ASSETS_DIR / "play.png")
            play_img.thumbnail((20, 20), Image.Resampling.LANCZOS)
            self.play_icon = ctk.CTkImage(light_image=play_img, dark_image=play_img, size=(20, 20))
            
            refresh_img = Image.open(ASSETS_DIR / "refresh.png")
            refresh_img.thumbnail((20, 20), Image.Resampling.LANCZOS)
            self.refresh_icon = ctk.CTkImage(light_image=refresh_img, dark_image=refresh_img, size=(20, 20))
        except Exception as e:
            debug_log(f"Icon load error: {e}")
            self.play_icon = None
            self.refresh_icon = None
        
        # ===== TOP ROW: Left config + Right thumbnail =====
        top_row = ctk.CTkFrame(page, fg_color="transparent")
        top_row.pack(fill="x", padx=20, pady=(5, 10))
        
        # Left column - URL, Subtitle, Clip Count
        left_col = ctk.CTkFrame(top_row, fg_color="transparent")
        left_col.pack(side="left", fill="y", padx=(0, 20))
        
        # YouTube URL
        ctk.CTkLabel(left_col, text="YouTube URL", font=ctk.CTkFont(size=11, weight="bold"), 
            anchor="w").pack(fill="x", pady=(0, 3))
        
        url_input_container = ctk.CTkFrame(left_col, fg_color="transparent")
        url_input_container.pack(fill="x", pady=(0, 8))
        
        self.url_var = ctk.StringVar()
        self.url_var.trace("w", self.on_url_change)
        self.url_entry = ctk.CTkEntry(url_input_container, textvariable=self.url_var, 
            placeholder_text="Paste YouTube link...", width=220, height=32, border_width=1,
            border_color=("#3a3a3a", "#2a2a2a"), fg_color=("#1a1a1a", "#0a0a0a"))
        self.url_entry.pack(side="left", padx=(0, 5))
        
        self.paste_btn = ctk.CTkButton(url_input_container, text="📋 Paste", width=65, height=32,
            fg_color=("#3a3a3a", "#2a2a2a"), hover_color=("#4a4a4a", "#3a3a3a"),
            font=ctk.CTkFont(size=10), command=self.paste_url)
        self.paste_btn.pack(side="left")
        
        # Subtitle Language
        ctk.CTkLabel(left_col, text="Subtitle Language", font=ctk.CTkFont(size=11, weight="bold"), 
            anchor="w").pack(fill="x", pady=(3, 3))
        
        self.subtitle_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        self.subtitle_frame.pack(fill="x", pady=(0, 8))
        self.subtitle_loaded = False
        
        self.subtitle_var = ctk.StringVar(value="id - Indonesian")
        self.subtitle_dropdown = ctk.CTkOptionMenu(self.subtitle_frame, 
            variable=self.subtitle_var, values=["id - Indonesian"], width=290,
            height=32, fg_color=("#2b2b2b", "#1a1a1a"),
            button_color=("#3a3a3a", "#2a2a2a"), button_hover_color=("#4a4a4a", "#3a3a3a"),
            state="disabled")
        self.subtitle_dropdown.pack(anchor="w")
        
        self.subtitle_loading = ctk.CTkLabel(self.subtitle_frame, text="⏳ Loading...", 
            font=ctk.CTkFont(size=10), text_color="gray")
        
        # Clip Count
        ctk.CTkLabel(left_col, text="Clip Count", font=ctk.CTkFont(size=11, weight="bold"), 
            anchor="w").pack(fill="x", pady=(3, 3))
        
        clips_input_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        clips_input_frame.pack(fill="x", pady=(0, 5))
        
        self.clips_var = ctk.StringVar(value="5")
        clips_entry = ctk.CTkEntry(clips_input_frame, textvariable=self.clips_var, width=60, height=32,
            fg_color=("#2b2b2b", "#1a1a1a"), border_width=1, border_color=("#3a3a3a", "#2a2a2a"), justify="center")
        clips_entry.pack(side="left", padx=(0, 8))
        
        ctk.CTkLabel(clips_input_frame, text="(1-10)", font=ctk.CTkFont(size=10), 
            text_color="gray").pack(side="left")
        
        # Right column - Thumbnail 16:9
        right_col = ctk.CTkFrame(top_row, fg_color="transparent")
        right_col.pack(side="right", fill="y")
        
        # Video preview frame 16:9 (400x225)
        self.thumb_frame = ctk.CTkFrame(right_col, width=400, height=225, 
            fg_color=("#2b2b2b", "#1a1a1a"), corner_radius=8)
        self.thumb_frame.pack(anchor="ne")
        self.thumb_frame.pack_propagate(False)
        
        self.create_preview_placeholder()
        
        # ===== MIDDLE ROW: Cookies + Enhancements (full width 50:50) =====
        middle_row = ctk.CTkFrame(page, fg_color="transparent")
        middle_row.pack(fill="x", padx=20, pady=(0, 10))
        
        # YouTube Cookies card (left 50%)
        cookies_frame = ctk.CTkFrame(middle_row, fg_color=("#2b2b2b", "#1a1a1a"), corner_radius=8)
        cookies_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ctk.CTkLabel(cookies_frame, text="YouTube Cookies", font=ctk.CTkFont(size=11, weight="bold"), 
            anchor="w").pack(fill="x", padx=12, pady=(10, 5))
        
        self.cookies_status_label = ctk.CTkLabel(cookies_frame, text="🍪 No cookies", 
            font=ctk.CTkFont(size=10), anchor="w", text_color="gray")
        self.cookies_status_label.pack(fill="x", padx=12, pady=(0, 5))
        
        upload_cookies_btn = ctk.CTkButton(cookies_frame, text="📁 Upload", height=28,
            fg_color=("#3a3a3a", "#2a2a2a"), hover_color=("#4a4a4a", "#3a3a3a"),
            font=ctk.CTkFont(size=10), command=self.upload_cookies)
        upload_cookies_btn.pack(fill="x", padx=12, pady=(0, 10))
        
        # Enhancements card (right 50%)
        enhance_frame = ctk.CTkFrame(middle_row, fg_color=("#2b2b2b", "#1a1a1a"), corner_radius=8)
        enhance_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        ctk.CTkLabel(enhance_frame, text="Enhancements", font=ctk.CTkFont(size=11, weight="bold"), 
            anchor="w").pack(fill="x", padx=12, pady=(10, 5))
        
        # Captions toggle
        captions_row = ctk.CTkFrame(enhance_frame, fg_color="transparent")
        captions_row.pack(fill="x", padx=12, pady=(0, 3))
        
        ctk.CTkLabel(captions_row, text="💬 Captions", font=ctk.CTkFont(size=10), 
            anchor="w").pack(side="left")
        
        self.caption_var = ctk.BooleanVar(value=False)
        self.caption_switch = ctk.CTkSwitch(captions_row, text="", variable=self.caption_var, 
            width=36, height=18, command=self.update_caption_switch_text)
        self.caption_switch.pack(side="right")
        
        # Hook toggle
        hook_row = ctk.CTkFrame(enhance_frame, fg_color="transparent")
        hook_row.pack(fill="x", padx=12, pady=(0, 10))
        
        ctk.CTkLabel(hook_row, text="🪝 Hook Text", font=ctk.CTkFont(size=10), 
            anchor="w").pack(side="left")
        
        self.hook_var = ctk.BooleanVar(value=False)
        self.hook_switch = ctk.CTkSwitch(hook_row, text="", variable=self.hook_var, 
            width=36, height=18, command=self.update_hook_switch_text)
        self.hook_switch.pack(side="right")
        
        # ===== BOTTOM: Generate button + Browse =====
        bottom_section = ctk.CTkFrame(page, fg_color="transparent")
        bottom_section.pack(fill="x", padx=20, pady=(0, 5))
        
        self.start_btn = ctk.CTkButton(bottom_section, text="Generate Shorts", image=self.play_icon, 
            compound="left", font=ctk.CTkFont(size=13, weight="bold"),
            height=40, command=self.start_processing, state="disabled", 
            fg_color="gray", hover_color="gray", corner_radius=8)
        self.start_btn.pack(fill="x", pady=(0, 5))
        
        browse_link = ctk.CTkLabel(bottom_section, text="📂 Browse Videos", 
            font=ctk.CTkFont(size=10), text_color=("#3B8ED0", "#1F6AA5"), cursor="hand2")
        browse_link.pack()
        browse_link.bind("<Button-1>", lambda e: self.show_page("browse"))
        
        # ===== LIB STATUS =====
        self.lib_status_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.lib_status_frame.pack(fill="x", padx=20, pady=(5, 0))
        
        self.lib_status_label = ctk.CTkLabel(self.lib_status_frame, text="", 
            font=ctk.CTkFont(size=10), cursor="hand2")
        self.lib_status_label.pack()
        self.lib_status_label.bind("<Button-1>", lambda e: self.show_page("lib_status"))
        
        # Check and update lib status
        self.check_lib_status()
        
        # Check cookies status
        self.check_cookies_status()
        
        # Footer
        footer = PageFooter(page, self)
        footer.pack(fill="x", padx=20, pady=(5, 8), side="bottom")
    
    def create_preview_placeholder(self):
        """Create placeholder content for video preview"""
        # Clear existing content
        for widget in self.thumb_frame.winfo_children():
            widget.destroy()
        
        # Preview content container - centered
        preview_container = ctk.CTkFrame(self.thumb_frame, fg_color="transparent")
        preview_container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Placeholder text
        self.thumb_label = ctk.CTkLabel(preview_container, 
            text="📺 Video thumbnail will appear here", 
            font=ctk.CTkFont(size=12), text_color="gray", justify="center")
        self.thumb_label.pack()
    
    def paste_url(self):
        """Paste URL from clipboard"""
        try:
            # Get clipboard content
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                self.url_var.set(clipboard_text.strip())
        except Exception as e:
            debug_log(f"Paste error: {e}")
            # If clipboard is empty or error, do nothing
            pass
    
    def upload_cookies(self):
        """Upload cookies.txt file"""
        file_path = filedialog.askopenfilename(
            title="Select cookies.txt file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # Copy file to app directory
                import shutil
                shutil.copy(file_path, self.cookies_path)
                debug_log(f"Cookies uploaded: {file_path}")
                
                # Update status
                self.check_cookies_status()
                
                # Show success message
                messagebox.showinfo("Success", "cookies.txt uploaded successfully!")
                
            except Exception as e:
                debug_log(f"Upload cookies error: {e}")
                messagebox.showerror("Upload Failed", f"Failed to upload cookies.txt:\n{str(e)}")
    
    def check_cookies_status(self):
        """Check if cookies.txt exists and update UI"""
        if self.cookies_path.exists():
            self.cookies_status_label.configure(
                text="✅ cookies.txt loaded",
                text_color=("#27ae60", "#2ecc71")  # Green
            )
            # Update start button state when cookies status changes
            self.update_start_button_state()
            return True
        else:
            self.cookies_status_label.configure(
                text="🍪 No cookies.txt found",
                text_color="gray"
            )
            # Update start button state when cookies status changes
            self.update_start_button_state()
            return False
    
    def update_caption_switch_text(self):
        """Update caption switch text based on state"""
        # Check if trying to turn ON
        if self.caption_var.get():
            # Validate Caption Maker API in background
            self.caption_switch.configure(state="disabled")
            
            def validate_caption_api():
                try:
                    ai_providers = self.config.get("ai_providers", {})
                    cm_config = ai_providers.get("caption_maker", {})
                    api_key = cm_config.get("api_key", "").strip()
                    base_url = cm_config.get("base_url", "https://api.openai.com/v1").strip()
                    model = cm_config.get("model", "").strip()
                    
                    if not api_key or not model:
                        self.after(0, lambda: self._on_caption_validation_failed("API Key or Model not configured"))
                        return
                    
                    # Test API connection
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    
                    # Get available models
                    models_response = client.models.list()
                    available_models = [m.id for m in models_response.data]
                    
                    # Check if configured model is available
                    if model not in available_models:
                        self.after(0, lambda: self._on_caption_validation_failed(f"Model '{model}' not available"))
                        return
                    
                    # Validation successful
                    self.after(0, self._on_caption_validation_success)
                    
                except Exception as e:
                    error_msg = str(e)[:100]
                    self.after(0, lambda: self._on_caption_validation_failed(error_msg))
            
            threading.Thread(target=validate_caption_api, daemon=True).start()
            return
        
        # Update text when turning OFF
        self.caption_switch.configure(text="OFF", state="normal")
    
    def _on_caption_validation_success(self):
        """Handle successful caption API validation"""
        self.caption_switch.configure(text="ON", state="normal")
    
    def _on_caption_validation_failed(self, error_msg):
        """Handle failed caption API validation"""
        self.caption_var.set(False)
        self.caption_switch.configure(text="OFF", state="normal")
        messagebox.showerror("Caption Maker Validation Failed", 
            f"Caption Maker API validation failed!\n\n" +
            f"Error: {error_msg}\n\n" +
            "Please check your configuration in:\n" +
            "Settings → AI API Settings → Caption Maker")
    
    def update_hook_switch_text(self):
        """Update hook switch text based on state"""
        # Check if trying to turn ON
        if self.hook_var.get():
            # Validate Hook Maker API in background
            self.hook_switch.configure(state="disabled")
            
            def validate_hook_api():
                try:
                    ai_providers = self.config.get("ai_providers", {})
                    hm_config = ai_providers.get("hook_maker", {})
                    api_key = hm_config.get("api_key", "").strip()
                    base_url = hm_config.get("base_url", "https://api.openai.com/v1").strip()
                    model = hm_config.get("model", "").strip()
                    
                    if not api_key or not model:
                        self.after(0, lambda: self._on_hook_validation_failed("API Key or Model not configured"))
                        return
                    
                    # Test API connection
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    
                    # Get available models
                    models_response = client.models.list()
                    available_models = [m.id for m in models_response.data]
                    
                    # Check if configured model is available
                    if model not in available_models:
                        self.after(0, lambda: self._on_hook_validation_failed(f"Model '{model}' not available"))
                        return
                    
                    # Validation successful
                    self.after(0, self._on_hook_validation_success)
                    
                except Exception as e:
                    error_msg = str(e)[:100]
                    self.after(0, lambda: self._on_hook_validation_failed(error_msg))
            
            threading.Thread(target=validate_hook_api, daemon=True).start()
            return
        
        # Update text when turning OFF
        self.hook_switch.configure(text="OFF", state="normal")
    
    def _on_hook_validation_success(self):
        """Handle successful hook API validation"""
        self.hook_switch.configure(text="ON", state="normal")
    
    def _on_hook_validation_failed(self, error_msg):
        """Handle failed hook API validation"""
        self.hook_var.set(False)
        self.hook_switch.configure(text="OFF", state="normal")
        messagebox.showerror("Hook Maker Validation Failed", 
            f"Hook Maker API validation failed!\n\n" +
            f"Error: {error_msg}\n\n" +
            "Please check your configuration in:\n" +
            "Settings → AI API Settings → Hook Maker")

    def create_processing_page(self):
        """Create processing page as embedded frame"""
        self.pages["processing"] = ProcessingPage(
            self.container,
            self.cancel_processing,
            lambda: self.show_page("home"),
            self.open_output,
            self.show_browse_after_complete
        )
        # Keep reference to steps for update_progress
        self.steps = self.pages["processing"].steps
    
    def create_results_page(self):
        """Create results page as embedded frame"""
        self.pages["results"] = ResultsPage(
            self.container,
            self.config,
            self.client,
            lambda: self.show_page("processing"),
            lambda: self.show_page("home"),
            self.open_output,
            self.get_youtube_client
        )
    
    def create_settings_page(self):
        """Create settings page as embedded frame"""
        self.pages["settings"] = SettingsPage(
            self.container, 
            self.config, 
            self.on_settings_saved,
            lambda: self.show_page("home"),
            OUTPUT_DIR,
            self.check_update_manual
        )
    
    def create_api_status_page(self):
        """Create API status page as embedded frame"""
        self.pages["api_status"] = APIStatusPage(
            self.container,
            lambda: self.client,
            lambda: self.config,
            lambda: (self.youtube_connected, self.youtube_channel),
            lambda: self.show_page("home"),
            self.refresh_icon
        )
    
    def create_lib_status_page(self):
        """Create library status page as embedded frame"""
        self.pages["lib_status"] = LibStatusPage(
            self.container,
            lambda: self.show_page("home"),
            self.refresh_icon
        )
    
    def create_browse_page(self):
        """Create browse page as embedded frame"""
        self.pages["browse"] = BrowsePage(
            self.container,
            self.config,
            self.client,
            lambda: self.show_page("home"),
            self.refresh_icon,
            self.get_youtube_client
        )
    
    def create_contact_page(self):
        """Create contact page as embedded frame"""
        self.pages["contact"] = ContactPage(
            self.container,
            lambda: self.config.get("installation_id", "unknown"),
            lambda: self.show_page("home")
        )
    
    def load_config(self):
        api_key = self.config.get("api_key", "")
        base_url = self.config.get("base_url", "https://api.openai.com/v1")
        model = self.config.get("model", "")
        
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key, base_url=base_url)
                # Only update UI if widgets exist
                if hasattr(self, 'api_dot'):
                    self.api_dot.configure(text_color="#27ae60")  # Green
                    self.api_status_label.configure(text=model[:15] if model else "Connected")
            except:
                if hasattr(self, 'api_dot'):
                    self.api_dot.configure(text_color="#e74c3c")  # Red
                    self.api_status_label.configure(text="Invalid key")
        else:
            if hasattr(self, 'api_dot'):
                self.api_dot.configure(text_color="#e74c3c")  # Red
                self.api_status_label.configure(text="Not configured")
    
    def check_youtube_status(self):
        """Check YouTube connection status"""
        try:
            from youtube_uploader import YouTubeUploader
            uploader = YouTubeUploader()
            
            if uploader.is_authenticated():
                channel = uploader.get_channel_info()
                if channel:
                    self.youtube_connected = True
                    self.youtube_channel = channel
                    
                    # Only update UI if widgets exist
                    if hasattr(self, 'yt_dot'):
                        self.yt_dot.configure(text_color="#27ae60")  # Green
                        
                        # Show channel name
                        channel_name = channel['title']
                        self.yt_status_label_home.configure(text=f"{channel_name[:20]}")
                    return
            
            self.youtube_connected = False
            if hasattr(self, 'yt_dot'):
                self.yt_dot.configure(text_color="#e74c3c")  # Red
                self.yt_status_label_home.configure(text="Not connected")
        except:
            self.youtube_connected = False
            if hasattr(self, 'yt_dot'):
                self.yt_dot.configure(text_color="#e74c3c")  # Red
                self.yt_status_label_home.configure(text="Not available")
    
    def update_connection_status(self):
        """Update connection status cards (called after settings change)"""
        self.load_config()
        self.check_youtube_status()
    
    def on_settings_saved(self, updated_config):
        """Handle settings saved - accepts config dict"""
        # Update internal config
        if isinstance(updated_config, dict):
            self.config.config.update(updated_config)
            self.config.save()
            
            # Update OpenAI client if highlight_finder config changed
            ai_providers = updated_config.get("ai_providers", {})
            hf_config = ai_providers.get("highlight_finder", {})
            if hf_config.get("api_key"):
                self.client = OpenAI(
                    api_key=hf_config.get("api_key"),
                    base_url=hf_config.get("base_url", "https://api.openai.com/v1")
                )
    
    def get_youtube_client(self):
        """Get OpenAI client for YouTube title generation"""
        ai_providers = self.config.get("ai_providers", {})
        yt_config = ai_providers.get("youtube_title_maker", {})
        
        if yt_config.get("api_key"):
            return OpenAI(
                api_key=yt_config.get("api_key"),
                base_url=yt_config.get("base_url", "https://api.openai.com/v1")
            )
        else:
            # Fallback to main client for backward compatibility
            return self.client
    
    def on_url_change(self, *args):
        url = self.url_var.get().strip()
        video_id = extract_video_id(url)
        if video_id:
            # Reset subtitle loaded flag when URL changes
            self.subtitle_loaded = False
            self.load_thumbnail(video_id)
            self.load_subtitles(url)  # Fetch available subtitles
        else:
            self.current_thumbnail = None
            self.subtitle_loaded = False
            # Recreate placeholder
            self.create_preview_placeholder()
            # Reset subtitle dropdown to disabled state
            self.subtitle_loading.pack_forget()
            self.subtitle_dropdown.configure(state="disabled", values=["id - Indonesian"])
            self.subtitle_var.set("id - Indonesian")
            # Disable start button when URL is invalid or cookies missing
            self.update_start_button_state()
    
    def update_start_button_state(self):
        """Update start button state based on URL, cookies, and library validation"""
        has_cookies = self.cookies_path.exists()
        libs_ok = getattr(self, 'libs_installed', True)  # Default True if not checked yet
        
        # If no cookies, disable everything
        if not has_cookies:
            self.url_entry.configure(state="disabled")
            self.paste_btn.configure(state="disabled")
            self.start_btn.configure(state="disabled", fg_color="gray", hover_color="gray")
            return
        
        # Cookies exist - enable URL input
        self.url_entry.configure(state="normal")
        self.paste_btn.configure(state="normal")
        
        # Check if URL is valid, subtitle is loaded, and libs are installed
        url = self.url_var.get().strip()
        video_id = extract_video_id(url)
        
        if video_id and self.subtitle_loaded and libs_ok:
            self.start_btn.configure(state="normal", fg_color=("#1f538d", "#14375e"), 
                                    hover_color=("#144870", "#0d2a47"))
        else:
            self.start_btn.configure(state="disabled", fg_color="gray", hover_color="gray")
    
    def check_lib_status(self):
        """Check library installation status and update UI"""
        from utils.dependency_manager import check_dependency
        from utils.helpers import get_app_dir, is_ytdlp_module_available
        
        app_dir = get_app_dir()
        
        # Check each dependency
        ffmpeg_ok = check_dependency('ffmpeg', app_dir)
        deno_ok = check_dependency('deno', app_dir)
        ytdlp_ok = is_ytdlp_module_available()
        
        all_ok = ffmpeg_ok and deno_ok and ytdlp_ok
        self.libs_installed = all_ok
        
        if all_ok:
            # All installed - hide lib status
            self.lib_status_frame.pack_forget()
        else:
            # Clear existing widgets
            for widget in self.lib_status_frame.winfo_children():
                widget.destroy()
            
            # Create status row with colored indicators
            status_row = ctk.CTkFrame(self.lib_status_frame, fg_color="transparent")
            status_row.pack()
            
            ctk.CTkLabel(status_row, text="Lib Status:", font=ctk.CTkFont(size=10), 
                text_color="gray").pack(side="left", padx=(0, 5))
            
            # Deno
            deno_color = "#4ade80" if deno_ok else "#f87171"
            ctk.CTkLabel(status_row, text=f"Deno {'✓' if deno_ok else '✗'}", 
                font=ctk.CTkFont(size=10), text_color=deno_color).pack(side="left", padx=(0, 8))
            
            # YT-DLP
            ytdlp_color = "#4ade80" if ytdlp_ok else "#f87171"
            ctk.CTkLabel(status_row, text=f"YT-DLP {'✓' if ytdlp_ok else '✗'}", 
                font=ctk.CTkFont(size=10), text_color=ytdlp_color).pack(side="left", padx=(0, 8))
            
            # FFmpeg
            ffmpeg_color = "#4ade80" if ffmpeg_ok else "#f87171"
            ctk.CTkLabel(status_row, text=f"FFmpeg {'✓' if ffmpeg_ok else '✗'}", 
                font=ctk.CTkFont(size=10), text_color=ffmpeg_color).pack(side="left", padx=(0, 8))
            
            # Install link
            install_link = ctk.CTkLabel(status_row, text="(Install required libraries)", 
                font=ctk.CTkFont(size=10), text_color="#f87171", cursor="hand2")
            install_link.pack(side="left")
            install_link.bind("<Button-1>", lambda e: self.show_page("lib_status"))
            
            self.lib_status_frame.pack(fill="x", padx=20, pady=(5, 0))
        
        # Update start button state
        self.update_start_button_state()
    
    def load_subtitles(self, url: str):
        """Fetch available subtitles for the video"""
        def fetch():
            try:
                # Show loading state
                self.after(0, lambda: self.show_subtitle_loading())
                
                # Import here to avoid circular dependency
                from clipper_core import AutoClipperCore
                
                # Get available subtitles (pass cookies_path)
                debug_log(f"Fetching subtitles for: {url}")
                debug_log(f"Cookies path: {self.cookies_path}")
                debug_log(f"Cookies exists: {self.cookies_path.exists()}")
                
                cookies_str = str(self.cookies_path) if self.cookies_path.exists() else None
                debug_log(f"Passing cookies_path: {cookies_str}")
                
                result = AutoClipperCore.get_available_subtitles(
                    url, 
                    self.ytdlp_path, 
                    cookies_path=cookies_str
                )
                debug_log(f"Subtitle fetch result: {result}")
                
                if result.get("error"):
                    debug_log(f"Subtitle error: {result['error']}")
                    self.after(0, lambda: self.on_subtitle_error(result["error"]))
                    return
                
                # Combine manual and auto-generated subtitles
                all_subs = []
                
                # Prioritize manual subtitles
                for sub in result.get("subtitles", []):
                    all_subs.append({
                        "code": sub["code"],
                        "name": sub["name"],
                        "type": "manual"
                    })
                
                # Add auto-generated subtitles
                for sub in result.get("automatic_captions", []):
                    all_subs.append({
                        "code": sub["code"],
                        "name": f"{sub['name']} (auto)",
                        "type": "auto"
                    })
                
                debug_log(f"Total subtitles found: {len(all_subs)}")
                
                if not all_subs:
                    self.after(0, lambda: self.on_subtitle_error("No subtitles available"))
                    return
                
                self.after(0, lambda: self.show_subtitle_selector(all_subs))
                
            except Exception as e:
                debug_log(f"Exception in load_subtitles: {str(e)}")
                import traceback
                debug_log(traceback.format_exc())
                self.after(0, lambda: self.on_subtitle_error(str(e)))
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def show_subtitle_loading(self):
        """Show loading state for subtitle selector"""
        # Keep dropdown visible but show loading indicator
        self.subtitle_dropdown.configure(state="disabled")
        self.subtitle_loading.pack(fill="x", padx=(4, 8), pady=(4, 0))
    
    def on_subtitle_error(self, error: str):
        """Handle subtitle fetch error"""
        debug_log(f"Subtitle fetch error: {error}")
        self.subtitle_loaded = False
        # Hide loading, keep dropdown disabled
        self.subtitle_loading.pack_forget()
        self.subtitle_dropdown.configure(state="disabled")
        # Show error to user
        messagebox.showerror("Subtitle Error", f"Failed to fetch subtitles:\n\n{error}")
        # Update button state
        self.update_start_button_state()
    
    def show_subtitle_selector(self, subtitles: list):
        """Show subtitle selector with available options"""
        # Hide loading
        self.subtitle_loading.pack_forget()
        
        # Create dropdown options
        options = [f"{sub['code']} - {sub['name']}" for sub in subtitles]
        
        # Set default to Indonesian if available, otherwise first option
        default_value = options[0]
        for opt in options:
            if opt.startswith("id "):
                default_value = opt
                break
        
        self.subtitle_var.set(default_value)
        self.subtitle_dropdown.configure(values=options, state="normal")
        
        # Mark subtitles as loaded
        self.subtitle_loaded = True
        
        # Update start button state (subtitles loaded successfully)
        self.update_start_button_state()
    
    def load_thumbnail(self, video_id: str):
        def fetch():
            try:
                import ssl
                import certifi
                
                # Try with certifi first, fallback to unverified SSL
                ssl_context = None
                try:
                    ssl_context = ssl.create_default_context(cafile=certifi.where())
                except Exception:
                    pass
                
                if ssl_context is None:
                    # Fallback to unverified SSL (for PyInstaller builds)
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                
                img = None
                for quality in ["maxresdefault", "hqdefault", "mqdefault"]:
                    try:
                        url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
                        with urllib.request.urlopen(url, timeout=5, context=ssl_context) as r:
                            data = r.read()
                        img = Image.open(io.BytesIO(data))
                        if img.size[0] > 120:
                            break
                    except Exception as e:
                        debug_log(f"Thumbnail fetch error ({quality}): {e}")
                        continue
                
                if img is None:
                    raise Exception("All thumbnail qualities failed")
                    
                # Resize to fit preview area in landscape (16:9 aspect ratio)
                # Frame is 400x225
                img.thumbnail((390, 220), Image.Resampling.LANCZOS)
                self.after(0, lambda: self.show_thumbnail(img))
            except Exception as e:
                debug_log(f"Thumbnail load failed: {e}")
                self.after(0, lambda: self.on_thumbnail_error())
        
        # Clear image reference properly before loading new one
        self.current_thumbnail = None
        
        # Show loading state
        for widget in self.thumb_frame.winfo_children():
            widget.destroy()
        
        loading_container = ctk.CTkFrame(self.thumb_frame, fg_color="transparent")
        loading_container.place(relx=0.5, rely=0.5, anchor="center")
        
        self.thumb_label = ctk.CTkLabel(loading_container, text="Loading...", 
            font=ctk.CTkFont(size=13), text_color="gray")
        self.thumb_label.pack()
        
        self.start_btn.configure(state="disabled", fg_color="gray", hover_color="gray")
        threading.Thread(target=fetch, daemon=True).start()
    
    def on_thumbnail_error(self):
        # Clear image reference properly before showing error
        self.current_thumbnail = None
        # Recreate placeholder with error message
        for widget in self.thumb_frame.winfo_children():
            widget.destroy()
        
        preview_container = ctk.CTkFrame(self.thumb_frame, fg_color="transparent")
        preview_container.place(relx=0.5, rely=0.5, anchor="center")
        
        self.thumb_label = ctk.CTkLabel(preview_container, 
            text="⚠️ Could not load thumbnail\nPlease check the URL", 
            font=ctk.CTkFont(size=13), text_color="gray", justify="center")
        self.thumb_label.pack()
        
        self.start_btn.configure(state="disabled", fg_color="gray", hover_color="gray")
    
    def show_thumbnail(self, img):
        try:
            # Clear the preview container and show thumbnail
            for widget in self.thumb_frame.winfo_children():
                widget.destroy()
            
            # Create image with proper size
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.current_thumbnail = ctk_img
            
            # Show thumbnail centered
            self.thumb_label = ctk.CTkLabel(self.thumb_frame, image=ctk_img, text="")
            self.thumb_label.place(relx=0.5, rely=0.5, anchor="center")
            
            # Update start button state (checks both URL and cookies)
            self.update_start_button_state()
        except Exception as e:
            debug_log(f"Error showing thumbnail: {e}")
            # If thumbnail fails, still update button state
            self.update_start_button_state()

    def start_processing(self):
        # Disable button during validation
        self.start_btn.configure(state="disabled", text="Validating...")
        
        def validate_and_start():
            try:
                from openai import OpenAI
                
                # Validate Highlight Finder (required for all processing)
                ai_providers = self.config.get("ai_providers", {})
                hf_config = ai_providers.get("highlight_finder", {})
                hf_api_key = hf_config.get("api_key", "").strip()
                hf_base_url = hf_config.get("base_url", "https://api.openai.com/v1").strip()
                hf_model = hf_config.get("model", "").strip()
                
                if not hf_api_key or not hf_model:
                    self.after(0, lambda: self._on_validation_failed(
                        "Highlight Finder API is not configured!\n\n" +
                        "This is required to find viral moments in videos.\n\n" +
                        "Please configure it in Settings → AI API Settings → Highlight Finder"))
                    return
                
                # Test Highlight Finder API
                try:
                    hf_client = OpenAI(api_key=hf_api_key, base_url=hf_base_url)
                    
                    # Try to list models to verify API key and model availability
                    try:
                        hf_models = hf_client.models.list()
                        hf_available = [m.id for m in hf_models.data]
                        
                        if hf_model not in hf_available:
                            self.after(0, lambda: self._on_validation_failed(
                                f"Highlight Finder model '{hf_model}' is not available!\n\n" +
                                "Please check your configuration in:\n" +
                                "Settings → AI API Settings → Highlight Finder"))
                            return
                    except Exception as list_error:
                        # If models.list() fails, the API key might still be valid
                        # Some providers don't support models.list()
                        # Just verify the API key is not empty and continue
                        pass
                    
                except Exception as e:
                    self.after(0, lambda: self._on_validation_failed(
                        f"Highlight Finder API validation failed!\n\n" +
                        f"Error: {str(e)[:100]}\n\n" +
                        "Please check your configuration in:\n" +
                        "Settings → AI API Settings → Highlight Finder"))
                    return
                
                # Validate Caption Maker if captions are enabled
                if self.caption_var.get():
                    cm_config = ai_providers.get("caption_maker", {})
                    cm_api_key = cm_config.get("api_key", "").strip()
                    cm_base_url = cm_config.get("base_url", "https://api.openai.com/v1").strip()
                    cm_model = cm_config.get("model", "").strip()
                    
                    if not cm_api_key or not cm_model:
                        self.after(0, lambda: self._on_validation_failed(
                            "Caption Maker API is not configured!\n\n" +
                            "Captions feature requires Whisper API.\n\n" +
                            "Please either:\n" +
                            "• Configure it in Settings → AI API Settings → Caption Maker\n" +
                            "• Or disable Captions toggle"))
                        return
                    
                    try:
                        cm_client = OpenAI(api_key=cm_api_key, base_url=cm_base_url)
                        
                        # Try to list models to verify API key and model availability
                        try:
                            cm_models = cm_client.models.list()
                            cm_available = [m.id for m in cm_models.data]
                            
                            if cm_model not in cm_available:
                                self.after(0, lambda: self._on_validation_failed(
                                    f"Caption Maker model '{cm_model}' is not available!\n\n" +
                                    "Please check your configuration or disable Captions toggle."))
                                return
                        except Exception as list_error:
                            # If models.list() fails, the API key might still be valid
                            # Some providers don't support models.list()
                            pass
                        
                    except Exception as e:
                        self.after(0, lambda: self._on_validation_failed(
                            f"Caption Maker API validation failed!\n\n" +
                            f"Error: {str(e)[:100]}\n\n" +
                            "Please check your configuration or disable Captions toggle."))
                        return
                
                # Validate Hook Maker if hook is enabled
                if self.hook_var.get():
                    hm_config = ai_providers.get("hook_maker", {})
                    hm_api_key = hm_config.get("api_key", "").strip()
                    hm_base_url = hm_config.get("base_url", "https://api.openai.com/v1").strip()
                    hm_model = hm_config.get("model", "").strip()
                    
                    if not hm_api_key or not hm_model:
                        self.after(0, lambda: self._on_validation_failed(
                            "Hook Maker API is not configured!\n\n" +
                            "Hook Text feature requires TTS API.\n\n" +
                            "Please either:\n" +
                            "• Configure it in Settings → AI API Settings → Hook Maker\n" +
                            "• Or disable Hook Text toggle"))
                        return
                    
                    try:
                        hm_client = OpenAI(api_key=hm_api_key, base_url=hm_base_url)
                        
                        # Try to list models to verify API key and model availability
                        try:
                            hm_models = hm_client.models.list()
                            hm_available = [m.id for m in hm_models.data]
                            
                            if hm_model not in hm_available:
                                self.after(0, lambda: self._on_validation_failed(
                                    f"Hook Maker model '{hm_model}' is not available!\n\n" +
                                    "Please check your configuration or disable Hook Text toggle."))
                                return
                        except Exception as list_error:
                            # If models.list() fails, the API key might still be valid
                            # Some providers don't support models.list()
                            pass
                        
                    except Exception as e:
                        self.after(0, lambda: self._on_validation_failed(
                            f"Hook Maker API validation failed!\n\n" +
                            f"Error: {str(e)[:100]}\n\n" +
                            "Please check your configuration or disable Hook Text toggle."))
                        return
                
                # All validations passed, proceed with processing
                self.after(0, self._start_processing_validated)
                
            except Exception as e:
                self.after(0, lambda: self._on_validation_failed(f"Validation error: {str(e)[:100]}"))
        
        threading.Thread(target=validate_and_start, daemon=True).start()
    
    def _on_validation_failed(self, error_msg):
        """Handle validation failure"""
        self.start_btn.configure(state="normal", text="Generate Shorts")
        messagebox.showerror("Validation Failed", error_msg)
    
    def _start_processing_validated(self):
        """Start processing after validation passed"""
        self.start_btn.configure(state="normal", text="Generate Shorts")
        
        # Legacy validation (backward compatibility)
        if not self.client:
            messagebox.showerror("Error", "Configure API settings first!\nClick ⚙️ button.")
            return
        
        url = self.url_var.get().strip()
        if not extract_video_id(url):
            messagebox.showerror("Error", "Enter a valid YouTube URL!")
            return
        try:
            num_clips = int(self.clips_var.get())
            if not 1 <= num_clips <= 10:
                raise ValueError()
        except:
            messagebox.showerror("Error", "Clips must be 1-10!")
            return
        
        # Get options
        add_captions = self.caption_var.get()
        add_hook = self.hook_var.get()
        
        # Get selected subtitle language (extract code from "id - Indonesian" format)
        subtitle_selection = self.subtitle_var.get()
        subtitle_lang = subtitle_selection.split(" - ")[0] if " - " in subtitle_selection else "id"
        
        # Reset UI
        self.processing = True
        self.cancelled = False
        self.token_usage = {"gpt_input": 0, "gpt_output": 0, "whisper_seconds": 0, "tts_chars": 0}
        
        # Reset processing page UI
        self.pages["processing"].reset_ui()
        
        self.show_page("processing")
        
        output_dir = self.config.get("output_dir", str(OUTPUT_DIR))
        model = self.config.get("model", "gpt-4.1")
        
        threading.Thread(target=self.run_processing, args=(url, num_clips, output_dir, model, add_captions, add_hook, subtitle_lang), daemon=True).start()
    
    def run_processing(self, url, num_clips, output_dir, model, add_captions, add_hook, subtitle_lang="id"):
        try:
            from clipper_core import AutoClipperCore
            
            # Wrapper for log callback that also logs to console in debug mode
            def log_with_debug(msg):
                debug_log(msg)
                self.after(0, lambda: self.update_status(msg))
            
            # Get system prompt from config
            system_prompt = self.config.get("system_prompt", None)
            temperature = self.config.get("temperature", 1.0)
            tts_model = self.config.get("tts_model", "tts-1")
            watermark_settings = self.config.get("watermark", {"enabled": False})
            credit_watermark_settings = self.config.get("credit_watermark", {"enabled": False})
            
            # Get face tracking mode from config (set in settings page)
            face_tracking_mode = self.config.get("face_tracking_mode", "opencv")
            
            mediapipe_settings = self.config.get("mediapipe_settings", {
                "lip_activity_threshold": 0.15,
                "switch_threshold": 0.3,
                "min_shot_duration": 90,
                "center_weight": 0.3
            })
            
            core = AutoClipperCore(
                client=self.client,
                ffmpeg_path=get_ffmpeg_path(),
                ytdlp_path=get_ytdlp_path(),
                output_dir=output_dir,
                model=model,
                tts_model=tts_model,
                temperature=temperature,
                system_prompt=system_prompt,
                watermark_settings=watermark_settings,
                credit_watermark_settings=credit_watermark_settings,
                face_tracking_mode=face_tracking_mode,
                mediapipe_settings=mediapipe_settings,
                ai_providers=self.config.get("ai_providers"),
                subtitle_language=subtitle_lang,
                log_callback=log_with_debug,
                progress_callback=lambda s, p: self.after(0, lambda: self.update_progress(s, p)),
                token_callback=lambda a, b, c, d: self.after(0, lambda: self.update_tokens(a, b, c, d)),
                cancel_check=lambda: self.cancelled
            )
            
            # Enable GPU acceleration if configured
            gpu_settings = self.config.get("gpu_acceleration", {})
            if gpu_settings.get("enabled", False):
                core.enable_gpu_acceleration(True)
            
            core.process(url, num_clips, add_captions=add_captions, add_hook=add_hook)
            if not self.cancelled:
                self.after(0, self.on_complete)
        except Exception as e:
            error_msg = str(e)
            debug_log(f"ERROR: {error_msg}")
            
            # Log error to file with full traceback
            log_error(f"Processing failed for URL: {url}", e)
            
            if self.cancelled or "cancel" in error_msg.lower():
                self.after(0, self.on_cancelled)
            else:
                self.after(0, lambda: self.on_error(error_msg))

    def update_status(self, msg):
        self.pages["processing"].update_status(msg)
    
    def update_progress(self, status, progress):
        print(f"[DEBUG] update_progress called: status='{status}', progress={progress}")
        self.pages["processing"].update_status(status)
        
        # Update step indicators based on status text
        status_lower = status.lower()
        
        # Parse progress percentage from status if available
        # Try multiple formats: (51%) or 51.2% or 51%
        progress_match = re.search(r'\((\d+(?:\.\d+)?)%\)|(\d+(?:\.\d+)?)%', status)
        if progress_match:
            # Get the first non-None group
            step_progress = float(progress_match.group(1) or progress_match.group(2)) / 100
        else:
            step_progress = None
        
        print(f"[DEBUG] Parsed step_progress: {step_progress}")
        
        if "download" in status_lower:
            if step_progress is None:
                step_progress = 0.0
            self.steps[0].set_active(status, step_progress)
            self.steps[1].reset()
            self.steps[2].reset()
        elif "highlight" in status_lower or "finding" in status_lower:
            self.steps[0].set_done("Downloaded")
            self.steps[1].set_active(status, step_progress)
            self.steps[2].reset()
        elif "clip" in status_lower or "clean" in status_lower:
            self.steps[0].set_done("Downloaded")
            self.steps[1].set_done("Found highlights")
            
            if step_progress is None:
                step_progress = 0.0
            
            # Extract clip number to show progress
            match = re.search(r'Clip (\d+)/(\d+)', status)
            if match:
                current, total = int(match.group(1)), int(match.group(2))
                percent = current / total
                self.steps[2].set_active(f"Clip {current}/{total}", percent)
            else:
                self.steps[2].set_active(status, step_progress)
        elif "complete" in status_lower:
            for step in self.steps:
                step.set_done("Complete")
    
    def update_tokens(self, gpt_in, gpt_out, whisper, tts):
        self.token_usage["gpt_input"] += gpt_in
        self.token_usage["gpt_output"] += gpt_out
        self.token_usage["whisper_seconds"] += whisper
        self.token_usage["tts_chars"] += tts
        
        # Update processing page display
        gpt_total = self.token_usage['gpt_input'] + self.token_usage['gpt_output']
        whisper_minutes = self.token_usage['whisper_seconds'] / 60
        tts_chars = self.token_usage['tts_chars']
        self.pages["processing"].update_tokens(gpt_total, whisper_minutes, tts_chars)
    
    def cancel_processing(self):
        if messagebox.askyesno("Cancel", "Are you sure you want to cancel?"):
            self.cancelled = True
            self.pages["processing"].update_status("⚠️ Cancelling... please wait")
            self.pages["processing"].cancel_btn.configure(state="disabled")
    
    def on_cancelled(self):
        """Called when processing is cancelled"""
        self.processing = False
        self.pages["processing"].on_cancelled()
    
    def on_complete(self):
        self.processing = False
        self.pages["processing"].on_complete()
        
        # Load created clips in results page
        self.pages["results"].load_clips()
    
    def show_browse_after_complete(self):
        """Show browse page after processing complete"""
        self.show_page("browse")
    
    def on_error(self, error):
        self.processing = False
        self.pages["processing"].on_error(error)
    
    def open_output(self):
        output_dir = self.config.get("output_dir", str(OUTPUT_DIR))
        if sys.platform == "win32":
            os.startfile(output_dir)
        else:
            subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", output_dir])
    
    def open_discord(self):
        """Open Discord server invite link"""
        import webbrowser
        webbrowser.open("https://s.id/ytsdiscord")
    
    def open_github(self):
        """Open GitHub repository"""
        import webbrowser
        webbrowser.open("https://github.com/jipraks/yt-short-clipper")
    
    def check_update_silent(self):
        """Check for updates silently on startup"""
        try:
            # Get installation_id from config
            installation_id = self.config.get("installation_id", "unknown")
            url = f"{UPDATE_CHECK_URL}?installation_id={installation_id}&app_version={__version__}"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'YT-Short-Clipper'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("version", "")
                download_url = data.get("download_url", "")
                changelog = data.get("changelog", "")
                
                if latest_version and self._compare_versions(latest_version, __version__) > 0:
                    # New version available
                    self.after(0, lambda: self._show_update_notification(latest_version, download_url, changelog))
        except Exception as e:
            debug_log(f"Update check failed: {e}")
    
    def check_update_manual(self):
        """Check for updates manually from settings page"""
        try:
            # Get installation_id from config
            installation_id = self.config.get("installation_id", "unknown")
            url = f"{UPDATE_CHECK_URL}?installation_id={installation_id}&app_version={__version__}"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'YT-Short-Clipper'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("version", "")
                download_url = data.get("download_url", "")
                changelog = data.get("changelog", "")
                
                if not latest_version:
                    messagebox.showinfo("Update Check", "Could not retrieve version information.")
                    return
                
                comparison = self._compare_versions(latest_version, __version__)
                
                if comparison > 0:
                    # New version available
                    msg = f"New version available: {latest_version}\nCurrent version: {__version__}\n\n"
                    if changelog:
                        msg += f"Changelog:\n{changelog}\n\n"
                    msg += f"Download: {download_url}"
                    
                    if messagebox.askyesno("Update Available", msg + "\n\nOpen download page?"):
                        import webbrowser
                        webbrowser.open(download_url)
                elif comparison == 0:
                    messagebox.showinfo("Update Check", f"You are using the latest version ({__version__})")
                else:
                    messagebox.showinfo("Update Check", f"Your version ({__version__}) is newer than the latest release ({latest_version})")
        except Exception as e:
            messagebox.showerror("Update Check Failed", f"Could not check for updates:\n{str(e)}")
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns: 1 if v1 > v2, -1 if v1 < v2, 0 if equal"""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(parts1), len(parts2))
            parts1 += [0] * (max_len - len(parts1))
            parts2 += [0] * (max_len - len(parts2))
            
            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            return 0
        except:
            return 0
    
    def _show_update_notification(self, latest_version: str, download_url: str, changelog: str = ""):
        """Show update notification popup"""
        msg = f"New version available: {latest_version}\nCurrent version: {__version__}\n\n"
        if changelog:
            msg += f"What's new:\n{changelog}\n\n"
        msg += "Would you like to download it?"
        
        if messagebox.askyesno("Update Available", msg):
            import webbrowser
            webbrowser.open(download_url)


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to log uncaught exceptions"""
    # Don't log KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Log the exception
    log_error("Uncaught exception", exc_value)
    
    # Show error dialog to user
    try:
        import tkinter.messagebox as mb
        error_log = get_error_log_path()
        msg = f"An unexpected error occurred:\n\n{exc_value}\n\n"
        if error_log:
            msg += f"Error details saved to:\n{error_log}\n\n"
        msg += "Please report this issue with the error.log file."
        mb.showerror("Unexpected Error", msg)
    except:
        pass
    
    # Call default handler
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def main():
    # Set global exception handler
    sys.excepthook = handle_exception
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = YTShortClipperApp()
    app.mainloop()


if __name__ == "__main__":
    main()
