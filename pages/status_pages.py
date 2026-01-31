"""
Status pages for API and Library checking
"""

import threading
import subprocess
import customtkinter as ctk
from tkinter import messagebox

from utils.helpers import get_ffmpeg_path, get_ytdlp_path


class APIStatusPage(ctk.CTkFrame):
    """API Status page - check OpenAI and YouTube API status"""
    
    def __init__(self, parent, get_client_callback, get_config_callback, get_youtube_status_callback, on_back_callback, refresh_icon=None):
        super().__init__(parent)
        self.get_client = get_client_callback
        self.get_config = get_config_callback
        self.get_youtube_status = get_youtube_status_callback
        self.on_back = on_back_callback
        self.refresh_icon = refresh_icon
        
        self.create_ui()
    
    def create_ui(self):
        """Create the API status page UI"""
        # Import header and footer components
        from components.page_layout import PageHeader, PageFooter
        
        # Set background color to match home page
        self.configure(fg_color=("#1a1a1a", "#0a0a0a"))
        
        # Header with back button (fixed at top)
        header = PageHeader(self, self, show_nav_buttons=False, show_back_button=True, page_title="API Status")
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        # Footer (fixed at bottom) - pack first so it stays at bottom
        footer = PageFooter(self, self)
        footer.pack(fill="x", padx=20, pady=(0, 15), side="bottom")
        
        # Scrollable content area (between header and footer)
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # ===== AI API Section =====
        ai_section = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        ai_section.pack(fill="x", pady=(15, 10))
        
        ctk.CTkLabel(ai_section, text="AI API", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(12, 8))
        
        # AI API cards row (4 cards horizontal)
        ai_cards_frame = ctk.CTkFrame(ai_section, fg_color="transparent")
        ai_cards_frame.pack(fill="x", padx=10, pady=(0, 12))
        ai_cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="ai")
        
        # Highlight Finder card
        hf_card = ctk.CTkFrame(ai_cards_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        hf_card.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(hf_card, text="🎯 Highlight Finder", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.hf_status_label = ctk.CTkLabel(hf_card, text="Checking...", font=ctk.CTkFont(size=10), text_color="gray")
        self.hf_status_label.pack(anchor="w", padx=10)
        self.hf_info_label = ctk.CTkLabel(hf_card, text="", font=ctk.CTkFont(size=9), text_color="gray")
        self.hf_info_label.pack(anchor="w", padx=10, pady=(2, 10))
        
        # Caption Maker card
        cm_card = ctk.CTkFrame(ai_cards_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        cm_card.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(cm_card, text="📝 Caption Maker", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.cm_status_label = ctk.CTkLabel(cm_card, text="Checking...", font=ctk.CTkFont(size=10), text_color="gray")
        self.cm_status_label.pack(anchor="w", padx=10)
        self.cm_info_label = ctk.CTkLabel(cm_card, text="", font=ctk.CTkFont(size=9), text_color="gray")
        self.cm_info_label.pack(anchor="w", padx=10, pady=(2, 10))
        
        # Hook Maker card
        hm_card = ctk.CTkFrame(ai_cards_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        hm_card.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(hm_card, text="🎤 Hook Maker", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.hm_status_label = ctk.CTkLabel(hm_card, text="Checking...", font=ctk.CTkFont(size=10), text_color="gray")
        self.hm_status_label.pack(anchor="w", padx=10)
        self.hm_info_label = ctk.CTkLabel(hm_card, text="", font=ctk.CTkFont(size=9), text_color="gray")
        self.hm_info_label.pack(anchor="w", padx=10, pady=(2, 10))
        
        # YouTube Title Maker card
        yt_maker_card = ctk.CTkFrame(ai_cards_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        yt_maker_card.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(yt_maker_card, text="📺 YT Title Maker", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.yt_maker_status_label = ctk.CTkLabel(yt_maker_card, text="Checking...", font=ctk.CTkFont(size=10), text_color="gray")
        self.yt_maker_status_label.pack(anchor="w", padx=10)
        self.yt_maker_info_label = ctk.CTkLabel(yt_maker_card, text="", font=ctk.CTkFont(size=9), text_color="gray")
        self.yt_maker_info_label.pack(anchor="w", padx=10, pady=(2, 10))
        
        # ===== Social Media API Section =====
        social_section = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        social_section.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(social_section, text="Social Media API", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(12, 8))
        
        # Social Media API cards row (2 cards horizontal, 50:50)
        social_cards_frame = ctk.CTkFrame(social_section, fg_color="transparent")
        social_cards_frame.pack(fill="x", padx=10, pady=(0, 12))
        social_cards_frame.grid_columnconfigure((0, 1), weight=1, uniform="social")
        
        # YouTube V3 API card
        yt_card = ctk.CTkFrame(social_cards_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        yt_card.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        yt_row = ctk.CTkFrame(yt_card, fg_color="transparent")
        yt_row.pack(fill="x", padx=10, pady=8)
        yt_left = ctk.CTkFrame(yt_row, fg_color="transparent")
        yt_left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(yt_left, text="📺 YouTube V3 API", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.yt_status_label = ctk.CTkLabel(yt_left, text="Checking...", font=ctk.CTkFont(size=10), text_color="gray")
        self.yt_status_label.pack(anchor="w")
        self.yt_info_label = ctk.CTkLabel(yt_left, text="", font=ctk.CTkFont(size=9), text_color="gray")
        self.yt_info_label.pack(anchor="w")
        self.yt_connect_btn = ctk.CTkButton(yt_row, text="Connect", width=80, height=28, font=ctk.CTkFont(size=10),
            fg_color=("#3B8ED0", "#1F6AA5"), command=self.connect_youtube)
        # Button will be shown/hidden based on status
        
        # Repliz API card
        repliz_card = ctk.CTkFrame(social_cards_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        repliz_card.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        repliz_row = ctk.CTkFrame(repliz_card, fg_color="transparent")
        repliz_row.pack(fill="x", padx=10, pady=8)
        repliz_left = ctk.CTkFrame(repliz_row, fg_color="transparent")
        repliz_left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(repliz_left, text="🎬 Repliz API", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.repliz_status_label = ctk.CTkLabel(repliz_left, text="Checking...", font=ctk.CTkFont(size=10), text_color="gray")
        self.repliz_status_label.pack(anchor="w")
        self.repliz_info_label = ctk.CTkLabel(repliz_left, text="", font=ctk.CTkFont(size=9), text_color="gray")
        self.repliz_info_label.pack(anchor="w")
        self.repliz_register_btn = ctk.CTkButton(repliz_row, text="Register", width=80, height=28, font=ctk.CTkFont(size=10),
            fg_color=("#3B8ED0", "#1F6AA5"), command=self.register_repliz)
        # Button will be shown/hidden based on status
        
        # Refresh button
        ctk.CTkButton(main, text="Refresh Status", image=self.refresh_icon, compound="left",
            height=40, command=self.refresh_status).pack(fill="x", pady=(10, 0))
    
    def update_status(self, youtube_connected, youtube_channel):
        """Update YouTube connection status (deprecated - now uses callback)"""
        pass
    
    def refresh_status(self):
        """Refresh API status"""
        # Reset to checking state - AI API
        self.hf_status_label.configure(text="Checking...", text_color="gray")
        self.hf_info_label.configure(text="")
        self.cm_status_label.configure(text="Checking...", text_color="gray")
        self.cm_info_label.configure(text="")
        self.hm_status_label.configure(text="Checking...", text_color="gray")
        self.hm_info_label.configure(text="")
        self.yt_maker_status_label.configure(text="Checking...", text_color="gray")
        self.yt_maker_info_label.configure(text="")
        
        # Reset Social Media API
        self.yt_status_label.configure(text="Checking...", text_color="gray")
        self.yt_info_label.configure(text="")
        self.yt_connect_btn.pack_forget()
        self.repliz_status_label.configure(text="Checking...", text_color="gray")
        self.repliz_info_label.configure(text="")
        self.repliz_register_btn.pack_forget()
        
        def check_status():
            from openai import OpenAI
            
            # Get config
            config = self.get_config()
            ai_providers = config.get("ai_providers", {})
            
            # Check each AI provider
            providers_to_check = [
                ("highlight_finder", self.hf_status_label, self.hf_info_label),
                ("caption_maker", self.cm_status_label, self.cm_info_label),
                ("hook_maker", self.hm_status_label, self.hm_info_label),
                ("youtube_title_maker", self.yt_maker_status_label, self.yt_maker_info_label)
            ]
            
            for provider_key, status_label, info_label in providers_to_check:
                provider_config = ai_providers.get(provider_key, {})
                api_key = provider_config.get("api_key", "")
                base_url = provider_config.get("base_url", "https://api.openai.com/v1")
                model = provider_config.get("model", "N/A")
                
                if not api_key:
                    self.after(0, lambda sl=status_label, il=info_label: (
                        sl.configure(text="✗ Not configured", text_color="orange"),
                        il.configure(text="Configure in Settings")
                    ))
                    continue
                
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    
                    try:
                        models_response = client.models.list()
                        available_models = [m.id for m in models_response.data]
                        
                        if model in available_models:
                            self.after(0, lambda sl=status_label, il=info_label, m=model: (
                                sl.configure(text="✓ Connected", text_color="green"),
                                il.configure(text=f"Model: {m}")
                            ))
                        else:
                            self.after(0, lambda sl=status_label, il=info_label, m=model: (
                                sl.configure(text="⚠ Model not found", text_color="orange"),
                                il.configure(text=f"Model: {m}")
                            ))
                    except Exception as list_error:
                        error_str = str(list_error).lower()
                        if any(x in error_str for x in ['connection', 'timeout', 'unreachable', 'invalid', 'unauthorized', 'authentication', 'api key', 'not found', '404', '401', '403', '500', '502', '503', 'error code']):
                            raise list_error
                        else:
                            self.after(0, lambda sl=status_label, il=info_label, m=model: (
                                sl.configure(text="✓ Configured", text_color="green"),
                                il.configure(text=f"Model: {m}")
                            ))
                    
                except Exception as e:
                    error_msg = str(e)[:40]
                    self.after(0, lambda sl=status_label, il=info_label, err=error_msg: (
                        sl.configure(text="✗ Error", text_color="red"),
                        il.configure(text=f"{err}")
                    ))
            
            # Check YouTube V3 API status
            youtube_connected, youtube_channel = self.get_youtube_status()
            
            if youtube_connected and youtube_channel:
                self.after(0, lambda: self.yt_status_label.configure(text="✓ Connected", text_color="green"))
                self.after(0, lambda: self.yt_info_label.configure(text=f"{youtube_channel['title']}"))
            else:
                try:
                    from youtube_uploader import YouTubeUploader
                    uploader = YouTubeUploader()
                    if not uploader.is_configured():
                        self.after(0, lambda: self.yt_status_label.configure(text="✗ Not configured", text_color="orange"))
                        self.after(0, lambda: self.yt_info_label.configure(text="client_secret.json missing"))
                    else:
                        self.after(0, lambda: self.yt_status_label.configure(text="✗ Not connected", text_color="orange"))
                        self.after(0, lambda: self.yt_info_label.configure(text=""))
                        self.after(0, lambda: self.yt_connect_btn.pack(side="right"))
                except Exception as e:
                    self.after(0, lambda: self.yt_status_label.configure(text="✗ Error", text_color="red"))
                    self.after(0, lambda: self.yt_info_label.configure(text=f"{str(e)[:40]}"))
            
            # Check Repliz API status
            repliz_config = config.get("repliz", {})
            repliz_access_key = repliz_config.get("access_key", "")
            repliz_secret_key = repliz_config.get("secret_key", "")
            
            if repliz_access_key and repliz_secret_key:
                self.after(0, lambda: self.repliz_status_label.configure(text="✓ Configured", text_color="green"))
                self.after(0, lambda: self.repliz_info_label.configure(text="Ready to upload"))
            else:
                self.after(0, lambda: self.repliz_status_label.configure(text="✗ Not configured", text_color="orange"))
                self.after(0, lambda: self.repliz_info_label.configure(text=""))
                self.after(0, lambda: self.repliz_register_btn.pack(side="right"))
        
        threading.Thread(target=check_status, daemon=True).start()
    
    def connect_youtube(self):
        """Open settings to connect YouTube"""
        self.show_page("settings")
    
    def register_repliz(self):
        """Open Repliz registration"""
        import webbrowser
        webbrowser.open("https://s.id/ytrepliz")
    
    def open_github(self):
        """Open GitHub repository"""
        import webbrowser
        webbrowser.open("https://github.com/jipraks/yt-short-clipper")
    
    def open_discord(self):
        """Open Discord server invite link"""
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


class LibStatusPage(ctk.CTkFrame):
    """Library Status page - check FFmpeg and yt-dlp"""
    
    def __init__(self, parent, on_back_callback, refresh_icon=None):
        super().__init__(parent)
        self.on_back = on_back_callback
        self.refresh_icon = refresh_icon
        self.downloading = False  # Track download state
        
        self.create_ui()
    
    def create_ui(self):
        """Create the library status page UI"""
        # Import header and footer components
        from components.page_layout import PageHeader, PageFooter
        
        # Set background color to match home page
        self.configure(fg_color=("#1a1a1a", "#0a0a0a"))
        
        # Header with back button (fixed at top)
        header = PageHeader(self, self, show_nav_buttons=False, show_back_button=True, page_title="Library Status")
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        # Footer (fixed at bottom) - pack first so it stays at bottom
        footer = PageFooter(self, self)
        footer.pack(fill="x", padx=20, pady=(0, 15), side="bottom")
        
        # Scrollable content area (between header and footer)
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # ===== Libraries Section =====
        lib_section = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        lib_section.pack(fill="x", pady=(15, 10))
        
        ctk.CTkLabel(lib_section, text="Required Libraries", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(12, 8))
        
        # Library cards row (3 cards horizontal)
        lib_cards_frame = ctk.CTkFrame(lib_section, fg_color="transparent")
        lib_cards_frame.pack(fill="x", padx=10, pady=(0, 12))
        lib_cards_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="lib")
        
        # yt-dlp card
        ytdlp_card = ctk.CTkFrame(lib_cards_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        ytdlp_card.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(ytdlp_card, text="📦 yt-dlp", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.ytdlp_status_label = ctk.CTkLabel(ytdlp_card, text="Checking...", font=ctk.CTkFont(size=10), text_color="gray")
        self.ytdlp_status_label.pack(anchor="w", padx=10)
        self.ytdlp_info_label = ctk.CTkLabel(ytdlp_card, text="", font=ctk.CTkFont(size=9), text_color="gray")
        self.ytdlp_info_label.pack(anchor="w", padx=10, pady=(2, 10))
        
        # FFmpeg card
        ffmpeg_card = ctk.CTkFrame(lib_cards_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        ffmpeg_card.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.ffmpeg_card = ffmpeg_card  # Store reference for download button
        ctk.CTkLabel(ffmpeg_card, text="🎬 FFmpeg", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.ffmpeg_status_label = ctk.CTkLabel(ffmpeg_card, text="Checking...", font=ctk.CTkFont(size=10), text_color="gray")
        self.ffmpeg_status_label.pack(anchor="w", padx=10)
        self.ffmpeg_info_label = ctk.CTkLabel(ffmpeg_card, text="", font=ctk.CTkFont(size=9), text_color="gray")
        self.ffmpeg_info_label.pack(anchor="w", padx=10, pady=(2, 5))
        self.ffmpeg_download_btn = ctk.CTkButton(ffmpeg_card, text="📥 Download", height=26, font=ctk.CTkFont(size=10),
            command=self.download_ffmpeg, fg_color=("#3B8ED0", "#1F6AA5"))
        self.ffmpeg_progress = ctk.CTkProgressBar(ffmpeg_card, height=6)
        self.ffmpeg_progress_label = ctk.CTkLabel(ffmpeg_card, text="", font=ctk.CTkFont(size=8), text_color="gray")
        
        # Deno card
        deno_card = ctk.CTkFrame(lib_cards_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        deno_card.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        self.deno_card = deno_card  # Store reference for download button
        ctk.CTkLabel(deno_card, text="🦕 Deno", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.deno_status_label = ctk.CTkLabel(deno_card, text="Checking...", font=ctk.CTkFont(size=10), text_color="gray")
        self.deno_status_label.pack(anchor="w", padx=10)
        self.deno_info_label = ctk.CTkLabel(deno_card, text="", font=ctk.CTkFont(size=9), text_color="gray")
        self.deno_info_label.pack(anchor="w", padx=10, pady=(2, 5))
        self.deno_download_btn = ctk.CTkButton(deno_card, text="📥 Download", height=26, font=ctk.CTkFont(size=10),
            command=self.download_deno, fg_color=("#3B8ED0", "#1F6AA5"))
        self.deno_progress = ctk.CTkProgressBar(deno_card, height=6)
        self.deno_progress_label = ctk.CTkLabel(deno_card, text="", font=ctk.CTkFont(size=8), text_color="gray")
        
        # Refresh button
        ctk.CTkButton(main, text="Check Libraries", image=self.refresh_icon, compound="left",
            height=40, command=self.refresh_status).pack(fill="x", pady=(10, 0))
    
    def refresh_status(self):
        """Refresh library status"""
        # Reset to checking state
        self.ytdlp_status_label.configure(text="Checking...", text_color="gray")
        self.ytdlp_info_label.configure(text="")
        self.ffmpeg_status_label.configure(text="Checking...", text_color="gray")
        self.ffmpeg_info_label.configure(text="")
        self.deno_status_label.configure(text="Checking...", text_color="gray")
        self.deno_info_label.configure(text="")
        
        # Hide download buttons
        self.ffmpeg_download_btn.pack_forget()
        self.deno_download_btn.pack_forget()
        
        def check_libs():
            from utils.helpers import get_app_dir, is_ytdlp_module_available
            from utils.dependency_manager import check_dependency
            
            app_dir = get_app_dir()
            
            # Check yt-dlp (prefer module over executable)
            if is_ytdlp_module_available():
                try:
                    import yt_dlp
                    version = yt_dlp.version.__version__
                    self.after(0, lambda: self.ytdlp_status_label.configure(text="✓ Installed", text_color="green"))
                    self.after(0, lambda: self.ytdlp_info_label.configure(text=f"v{version}"))
                except Exception as e:
                    self.after(0, lambda: self.ytdlp_status_label.configure(text="✗ Error", text_color="red"))
                    self.after(0, lambda: self.ytdlp_info_label.configure(text=f"{str(e)[:30]}"))
            else:
                # Fallback to executable check
                ytdlp_path = get_ytdlp_path()
                try:
                    result = subprocess.run([ytdlp_path, "--version"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        self.after(0, lambda: self.ytdlp_status_label.configure(text="✓ Installed", text_color="green"))
                        self.after(0, lambda: self.ytdlp_info_label.configure(text=f"v{version}"))
                    else:
                        self.after(0, lambda: self.ytdlp_status_label.configure(text="✗ Error", text_color="red"))
                        self.after(0, lambda: self.ytdlp_info_label.configure(text="Failed to get version"))
                except FileNotFoundError:
                    self.after(0, lambda: self.ytdlp_status_label.configure(text="✗ Not found", text_color="red"))
                    self.after(0, lambda: self.ytdlp_info_label.configure(text="pip install yt-dlp"))
                except Exception as e:
                    self.after(0, lambda: self.ytdlp_status_label.configure(text="✗ Error", text_color="red"))
                    self.after(0, lambda: self.ytdlp_info_label.configure(text=f"{str(e)[:30]}"))
            
            # Check FFmpeg
            ffmpeg_installed = check_dependency("ffmpeg", app_dir)
            if ffmpeg_installed:
                ffmpeg_path = get_ffmpeg_path()
                try:
                    result = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        # Extract version from first line
                        version_line = result.stdout.split('\n')[0]
                        version = version_line.split('version')[1].split()[0] if 'version' in version_line else "Unknown"
                        self.after(0, lambda: self.ffmpeg_status_label.configure(text="✓ Installed", text_color="green"))
                        self.after(0, lambda: self.ffmpeg_info_label.configure(text=f"v{version}"))
                    else:
                        self.after(0, lambda: self.ffmpeg_status_label.configure(text="✗ Error", text_color="red"))
                        self.after(0, lambda: self.ffmpeg_info_label.configure(text="Failed to get version"))
                except Exception as e:
                    self.after(0, lambda: self.ffmpeg_status_label.configure(text="✗ Error", text_color="red"))
                    self.after(0, lambda: self.ffmpeg_info_label.configure(text=f"{str(e)[:30]}"))
            else:
                self.after(0, lambda: self.ffmpeg_status_label.configure(text="✗ Not found", text_color="orange"))
                self.after(0, lambda: self.ffmpeg_info_label.configure(text="Click to download"))
                self.after(0, lambda: self.ffmpeg_download_btn.pack(fill="x", padx=10, pady=(0, 10)))
            
            # Check Deno
            deno_installed = check_dependency("deno", app_dir)
            if deno_installed:
                from utils.helpers import get_deno_path
                deno_path = get_deno_path()
                try:
                    result = subprocess.run([deno_path, "--version"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        # Extract version from first line
                        version_line = result.stdout.split('\n')[0]
                        version = version_line.split()[1] if len(version_line.split()) > 1 else "Unknown"
                        self.after(0, lambda: self.deno_status_label.configure(text="✓ Installed", text_color="green"))
                        self.after(0, lambda: self.deno_info_label.configure(text=f"v{version}"))
                    else:
                        self.after(0, lambda: self.deno_status_label.configure(text="✗ Error", text_color="red"))
                        self.after(0, lambda: self.deno_info_label.configure(text="Failed to get version"))
                except Exception as e:
                    self.after(0, lambda: self.deno_status_label.configure(text="✗ Error", text_color="red"))
                    self.after(0, lambda: self.deno_info_label.configure(text=f"{str(e)[:30]}"))
            else:
                self.after(0, lambda: self.deno_status_label.configure(text="✗ Not found", text_color="orange"))
                self.after(0, lambda: self.deno_info_label.configure(text="Click to download"))
                self.after(0, lambda: self.deno_download_btn.pack(fill="x", padx=10, pady=(0, 10)))
        
        threading.Thread(target=check_libs, daemon=True).start()
    
    def download_ffmpeg(self):
        """Download and setup FFmpeg"""
        if self.downloading:
            return
        
        self.downloading = True
        self.ffmpeg_download_btn.configure(state="disabled", text="Downloading...")
        self.ffmpeg_progress.pack(fill="x", padx=15, pady=(5, 5))
        self.ffmpeg_progress.set(0)
        self.ffmpeg_progress_label.pack(fill="x", padx=15, pady=(0, 15))
        self.ffmpeg_progress_label.configure(text="Preparing download...")
        
        def download():
            try:
                from utils.helpers import get_app_dir
                from utils.dependency_manager import setup_ffmpeg, get_ffmpeg_download_url
                
                app_dir = get_app_dir()
                
                # Check if URL is available for this OS
                url, filename = get_ffmpeg_download_url()
                if not url:
                    self.after(0, lambda: messagebox.showerror("Not Supported", 
                        "FFmpeg auto-download is not supported for your operating system.\n"
                        "Please install FFmpeg manually."))
                    self.after(0, self._reset_ffmpeg_ui)
                    self.downloading = False
                    return
                
                self.after(0, lambda: self.ffmpeg_progress_label.configure(text=f"Downloading from GitHub..."))
                
                def progress_callback(downloaded, total):
                    if total > 0:
                        progress = downloaded / total
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        self.after(0, lambda p=progress: self.ffmpeg_progress.set(p))
                        self.after(0, lambda d=mb_downloaded, t=mb_total, pr=progress: 
                            self.ffmpeg_progress_label.configure(
                                text=f"Downloading: {d:.1f} MB / {t:.1f} MB ({pr*100:.0f}%)"
                            ))
                
                success = setup_ffmpeg(app_dir, progress_callback)
                
                if success:
                    self.after(0, lambda: self.ffmpeg_progress_label.configure(text="✓ Download complete!"))
                    self.after(0, lambda: messagebox.showinfo("Success", 
                        "FFmpeg downloaded and installed successfully!\n\n"
                        "⚠️ Please restart the application to use FFmpeg properly."))
                    self.after(0, self.refresh_status)
                else:
                    self.after(0, lambda: messagebox.showerror("Download Failed", 
                        "Failed to download FFmpeg.\n\n"
                        "Possible causes:\n"
                        "- No internet connection\n"
                        "- GitHub is blocked\n"
                        "- Firewall blocking download\n\n"
                        "Please try again or download manually."))
                    self.after(0, self._reset_ffmpeg_ui)
                
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                self.after(0, lambda: messagebox.showerror("Download Error", 
                    f"An error occurred:\n\n{str(e)[:200]}\n\nCheck error.log for details."))
                self.after(0, self._reset_ffmpeg_ui)
                
                # Try to log error
                try:
                    from utils.logger import debug_log
                    debug_log(f"FFmpeg download error: {error_detail}")
                except:
                    pass
            
            self.downloading = False
        
        threading.Thread(target=download, daemon=True).start()
    
    def _reset_ffmpeg_ui(self):
        """Reset FFmpeg download UI"""
        self.ffmpeg_download_btn.configure(state="normal", text="📥 Download FFmpeg")
        self.ffmpeg_progress.pack_forget()
        self.ffmpeg_progress_label.pack_forget()
    
    def download_deno(self):
        """Download and setup Deno"""
        if self.downloading:
            return
        
        self.downloading = True
        self.deno_download_btn.configure(state="disabled", text="Downloading...")
        self.deno_progress.pack(fill="x", padx=15, pady=(5, 5))
        self.deno_progress.set(0)
        self.deno_progress_label.pack(fill="x", padx=15, pady=(0, 15))
        self.deno_progress_label.configure(text="Preparing download...")
        
        def download():
            try:
                from utils.helpers import get_app_dir
                from utils.dependency_manager import setup_deno, get_deno_download_url
                
                app_dir = get_app_dir()
                
                # Check if URL is available for this OS
                url, filename = get_deno_download_url()
                if not url:
                    self.after(0, lambda: messagebox.showerror("Not Supported", 
                        "Deno auto-download is not supported for your operating system.\n"
                        "Please install Deno manually."))
                    self.after(0, self._reset_deno_ui)
                    self.downloading = False
                    return
                
                self.after(0, lambda: self.deno_progress_label.configure(text=f"Downloading from GitHub..."))
                
                def progress_callback(downloaded, total):
                    if total > 0:
                        progress = downloaded / total
                        mb_downloaded = downloaded / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        self.after(0, lambda p=progress: self.deno_progress.set(p))
                        self.after(0, lambda d=mb_downloaded, t=mb_total, pr=progress: 
                            self.deno_progress_label.configure(
                                text=f"Downloading: {d:.1f} MB / {t:.1f} MB ({pr*100:.0f}%)"
                            ))
                
                success = setup_deno(app_dir, progress_callback)
                
                if success:
                    self.after(0, lambda: self.deno_progress_label.configure(text="✓ Download complete!"))
                    self.after(0, lambda: messagebox.showinfo("Success", 
                        "Deno downloaded and installed successfully!\n\n"
                        "⚠️ Please restart the application to use Deno properly."))
                    self.after(0, self.refresh_status)
                else:
                    self.after(0, lambda: messagebox.showerror("Download Failed", 
                        "Failed to download Deno.\n\n"
                        "Possible causes:\n"
                        "- No internet connection\n"
                        "- GitHub is blocked\n"
                        "- Firewall blocking download\n\n"
                        "Please try again or download manually."))
                    self.after(0, self._reset_deno_ui)
                
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                self.after(0, lambda: messagebox.showerror("Download Error", 
                    f"An error occurred:\n\n{str(e)[:200]}\n\nCheck error.log for details."))
                self.after(0, self._reset_deno_ui)
                
                # Try to log error
                try:
                    from utils.logger import debug_log
                    debug_log(f"Deno download error: {error_detail}")
                except:
                    pass
            
            self.downloading = False
        
        threading.Thread(target=download, daemon=True).start()
    
    def _reset_deno_ui(self):
        """Reset Deno download UI"""
        self.deno_download_btn.configure(state="normal", text="📥 Download Deno")
        self.deno_progress.pack_forget()
        self.deno_progress_label.pack_forget()
    
    def open_github(self):
        """Open GitHub repository"""
        import webbrowser
        webbrowser.open("https://github.com/jipraks/yt-short-clipper")
    
    def open_discord(self):
        """Open Discord server invite link"""
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
