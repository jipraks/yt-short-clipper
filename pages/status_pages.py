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
        
        # Header with back button
        header = PageHeader(self, self, show_nav_buttons=False, show_back_button=True, page_title="API Status")
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        # Main content
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # AI API Status (parent card)
        ai_frame = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        ai_frame.pack(fill="x", pady=(15, 10))
        
        ai_header = ctk.CTkFrame(ai_frame, fg_color="transparent")
        ai_header.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(ai_header, text="AI API", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        # Sub-providers
        providers_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
        providers_frame.pack(fill="x", padx=15, pady=(10, 15))
        
        # Highlight Finder
        hf_frame = ctk.CTkFrame(providers_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        hf_frame.pack(fill="x", pady=(0, 8))
        
        hf_header = ctk.CTkFrame(hf_frame, fg_color="transparent")
        hf_header.pack(fill="x", padx=12, pady=(10, 5))
        
        ctk.CTkLabel(hf_header, text="🎯 Highlight Finder", font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(side="left")
        self.hf_status_label = ctk.CTkLabel(hf_header, text="Checking...", font=ctk.CTkFont(size=12), text_color="gray")
        self.hf_status_label.pack(side="right")
        
        self.hf_info_label = ctk.CTkLabel(hf_frame, text="", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self.hf_info_label.pack(fill="x", padx=12, pady=(0, 10))
        
        # Caption Maker
        cm_frame = ctk.CTkFrame(providers_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        cm_frame.pack(fill="x", pady=(0, 8))
        
        cm_header = ctk.CTkFrame(cm_frame, fg_color="transparent")
        cm_header.pack(fill="x", padx=12, pady=(10, 5))
        
        ctk.CTkLabel(cm_header, text="📝 Caption Maker", font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(side="left")
        self.cm_status_label = ctk.CTkLabel(cm_header, text="Checking...", font=ctk.CTkFont(size=12), text_color="gray")
        self.cm_status_label.pack(side="right")
        
        self.cm_info_label = ctk.CTkLabel(cm_frame, text="", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self.cm_info_label.pack(fill="x", padx=12, pady=(0, 10))
        
        # Hook Maker
        hm_frame = ctk.CTkFrame(providers_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        hm_frame.pack(fill="x", pady=(0, 8))
        
        hm_header = ctk.CTkFrame(hm_frame, fg_color="transparent")
        hm_header.pack(fill="x", padx=12, pady=(10, 5))
        
        ctk.CTkLabel(hm_header, text="🎤 Hook Maker", font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(side="left")
        self.hm_status_label = ctk.CTkLabel(hm_header, text="Checking...", font=ctk.CTkFont(size=12), text_color="gray")
        self.hm_status_label.pack(side="right")
        
        self.hm_info_label = ctk.CTkLabel(hm_frame, text="", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self.hm_info_label.pack(fill="x", padx=12, pady=(0, 10))
        
        # YouTube Title Maker
        yt_maker_frame = ctk.CTkFrame(providers_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        yt_maker_frame.pack(fill="x", pady=(0, 0))
        
        yt_maker_header = ctk.CTkFrame(yt_maker_frame, fg_color="transparent")
        yt_maker_header.pack(fill="x", padx=12, pady=(10, 5))
        
        ctk.CTkLabel(yt_maker_header, text="📺 YouTube Title Maker", font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(side="left")
        self.yt_maker_status_label = ctk.CTkLabel(yt_maker_header, text="Checking...", font=ctk.CTkFont(size=12), text_color="gray")
        self.yt_maker_status_label.pack(side="right")
        
        self.yt_maker_info_label = ctk.CTkLabel(yt_maker_frame, text="", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self.yt_maker_info_label.pack(fill="x", padx=12, pady=(0, 10))
        
        # YouTube API Status
        yt_frame = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        yt_frame.pack(fill="x", pady=(0, 10))
        
        yt_header = ctk.CTkFrame(yt_frame, fg_color="transparent")
        yt_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(yt_header, text="YouTube API", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        self.yt_status_label = ctk.CTkLabel(yt_header, text="Checking...", font=ctk.CTkFont(size=13), text_color="gray")
        self.yt_status_label.pack(side="right")
        
        self.yt_info_label = ctk.CTkLabel(yt_frame, text="", font=ctk.CTkFont(size=12), text_color="gray", anchor="w")
        self.yt_info_label.pack(fill="x", padx=15, pady=(0, 15))
        
        # Refresh button
        ctk.CTkButton(main, text="Refresh Status", image=self.refresh_icon, compound="left",
            height=45, command=self.refresh_status).pack(fill="x", pady=(10, 0))
        
        # Footer
        footer = PageFooter(self, self)
        footer.pack(fill="x", padx=20, pady=(0, 15), side="bottom")
    
    def update_status(self, youtube_connected, youtube_channel):
        """Update YouTube connection status (deprecated - now uses callback)"""
        pass
    
    def refresh_status(self):
        """Refresh API status"""
        # Reset to checking state
        self.hf_status_label.configure(text="Checking...", text_color="gray")
        self.hf_info_label.configure(text="")
        self.cm_status_label.configure(text="Checking...", text_color="gray")
        self.cm_info_label.configure(text="")
        self.hm_status_label.configure(text="Checking...", text_color="gray")
        self.hm_info_label.configure(text="")
        self.yt_maker_status_label.configure(text="Checking...", text_color="gray")
        self.yt_maker_info_label.configure(text="")
        self.yt_status_label.configure(text="Checking...", text_color="gray")
        self.yt_info_label.configure(text="")
        
        def check_status():
            from openai import OpenAI
            
            # Get config
            config = self.get_config()
            ai_providers = config.get("ai_providers", {})
            
            # Check each AI provider
            providers_to_check = [
                ("highlight_finder", "🎯 Highlight Finder", self.hf_status_label, self.hf_info_label, "chat"),
                ("caption_maker", "📝 Caption Maker", self.cm_status_label, self.cm_info_label, "whisper"),
                ("hook_maker", "🎤 Hook Maker", self.hm_status_label, self.hm_info_label, "tts"),
                ("youtube_title_maker", "📺 YouTube Title Maker", self.yt_maker_status_label, self.yt_maker_info_label, "chat")
            ]
            
            for provider_key, provider_name, status_label, info_label, provider_type in providers_to_check:
                provider_config = ai_providers.get(provider_key, {})
                api_key = provider_config.get("api_key", "")
                base_url = provider_config.get("base_url", "https://api.openai.com/v1")
                model = provider_config.get("model", "N/A")
                
                if not api_key:
                    self.after(0, lambda sl=status_label, il=info_label: (
                        sl.configure(text="✗ Not configured", text_color="orange"),
                        il.configure(text="Please configure API key in Settings")
                    ))
                    continue
                
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    
                    # Try to list models to verify API key and model availability
                    try:
                        models_response = client.models.list()
                        available_models = [m.id for m in models_response.data]
                        
                        # Check if configured model is available
                        if model in available_models:
                            self.after(0, lambda sl=status_label, il=info_label, m=model: (
                                sl.configure(text="✓ Connected", text_color="green"),
                                il.configure(text=f"Model: {m}")
                            ))
                        else:
                            self.after(0, lambda sl=status_label, il=info_label, m=model: (
                                sl.configure(text="⚠ Model not found", text_color="orange"),
                                il.configure(text=f"Model '{m}' not in available models")
                            ))
                    except Exception as list_error:
                        # Check if it's a connection/authentication error
                        error_str = str(list_error).lower()
                        if any(x in error_str for x in ['connection', 'timeout', 'unreachable', 'invalid', 'unauthorized', 'authentication', 'api key', 'not found', '404', '401', '403', '500', '502', '503', 'error code']):
                            # Real error - connection or auth failed
                            raise list_error
                        else:
                            # Provider might not support models.list(), show configured status
                            self.after(0, lambda sl=status_label, il=info_label, m=model: (
                                sl.configure(text="✓ Configured", text_color="green"),
                                il.configure(text=f"Model: {m} (provider doesn't support model listing)")
                            ))
                    
                except Exception as e:
                    error_msg = str(e)[:60]
                    self.after(0, lambda sl=status_label, il=info_label, err=error_msg: (
                        sl.configure(text="✗ Error", text_color="red"),
                        il.configure(text=f"Error: {err}")
                    ))
            
            # Check YouTube status
            youtube_connected, youtube_channel = self.get_youtube_status()
            
            if youtube_connected and youtube_channel:
                self.after(0, lambda: self.yt_status_label.configure(text="✓ Connected", text_color="green"))
                self.after(0, lambda: self.yt_info_label.configure(text=f"Channel: {youtube_channel['title']}"))
            else:
                try:
                    from youtube_uploader import YouTubeUploader
                    uploader = YouTubeUploader()
                    if not uploader.is_configured():
                        self.after(0, lambda: self.yt_status_label.configure(text="✗ Not configured", text_color="orange"))
                        self.after(0, lambda: self.yt_info_label.configure(text="client_secret.json not found"))
                    else:
                        self.after(0, lambda: self.yt_status_label.configure(text="✗ Not connected", text_color="orange"))
                        self.after(0, lambda: self.yt_info_label.configure(text="Connect in Settings → YouTube tab"))
                except Exception as e:
                    self.after(0, lambda: self.yt_status_label.configure(text="✗ Error", text_color="red"))
                    self.after(0, lambda: self.yt_info_label.configure(text=f"Error: {str(e)[:60]}"))
        
        threading.Thread(target=check_status, daemon=True).start()
    
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
        
        # Header with back button
        header = PageHeader(self, self, show_nav_buttons=False, show_back_button=True, page_title="Library Status")
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        # Main content
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # yt-dlp Status
        ytdlp_frame = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        ytdlp_frame.pack(fill="x", pady=(15, 10))
        
        ytdlp_header = ctk.CTkFrame(ytdlp_frame, fg_color="transparent")
        ytdlp_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(ytdlp_header, text="yt-dlp", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        self.ytdlp_status_label = ctk.CTkLabel(ytdlp_header, text="Checking...", font=ctk.CTkFont(size=13), text_color="gray")
        self.ytdlp_status_label.pack(side="right")
        
        self.ytdlp_info_label = ctk.CTkLabel(ytdlp_frame, text="", font=ctk.CTkFont(size=12), text_color="gray", anchor="w")
        self.ytdlp_info_label.pack(fill="x", padx=15, pady=(0, 15))
        
        # FFmpeg Status
        ffmpeg_frame = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        ffmpeg_frame.pack(fill="x", pady=(0, 10))
        
        ffmpeg_header = ctk.CTkFrame(ffmpeg_frame, fg_color="transparent")
        ffmpeg_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(ffmpeg_header, text="FFmpeg", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        self.ffmpeg_status_label = ctk.CTkLabel(ffmpeg_header, text="Checking...", font=ctk.CTkFont(size=13), text_color="gray")
        self.ffmpeg_status_label.pack(side="right")
        
        self.ffmpeg_info_label = ctk.CTkLabel(ffmpeg_frame, text="", font=ctk.CTkFont(size=12), text_color="gray", anchor="w")
        self.ffmpeg_info_label.pack(fill="x", padx=15, pady=(0, 5))
        
        # FFmpeg download button (hidden by default)
        self.ffmpeg_download_btn = ctk.CTkButton(ffmpeg_frame, text="📥 Download FFmpeg", 
            height=36, command=self.download_ffmpeg, fg_color=("#3B8ED0", "#1F6AA5"))
        
        # FFmpeg progress bar (hidden by default)
        self.ffmpeg_progress = ctk.CTkProgressBar(ffmpeg_frame, height=8)
        self.ffmpeg_progress_label = ctk.CTkLabel(ffmpeg_frame, text="", font=ctk.CTkFont(size=10), text_color="gray")
        
        # Deno Status
        deno_frame = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        deno_frame.pack(fill="x", pady=(0, 10))
        
        deno_header = ctk.CTkFrame(deno_frame, fg_color="transparent")
        deno_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(deno_header, text="Deno", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        self.deno_status_label = ctk.CTkLabel(deno_header, text="Checking...", font=ctk.CTkFont(size=13), text_color="gray")
        self.deno_status_label.pack(side="right")
        
        self.deno_info_label = ctk.CTkLabel(deno_frame, text="", font=ctk.CTkFont(size=12), text_color="gray", anchor="w")
        self.deno_info_label.pack(fill="x", padx=15, pady=(0, 5))
        
        # Deno download button (hidden by default)
        self.deno_download_btn = ctk.CTkButton(deno_frame, text="📥 Download Deno", 
            height=36, command=self.download_deno, fg_color=("#3B8ED0", "#1F6AA5"))
        
        # Deno progress bar (hidden by default)
        self.deno_progress = ctk.CTkProgressBar(deno_frame, height=8)
        self.deno_progress_label = ctk.CTkLabel(deno_frame, text="", font=ctk.CTkFont(size=10), text_color="gray")
        
        # Refresh button
        ctk.CTkButton(main, text="Check Libraries", image=self.refresh_icon, compound="left",
            height=45, command=self.refresh_status).pack(fill="x", pady=(10, 0))
        
        # Footer
        footer = PageFooter(self, self)
        footer.pack(fill="x", padx=20, pady=(0, 15), side="bottom")
    
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
                    self.after(0, lambda: self.ytdlp_status_label.configure(text="✓ Installed (module)", text_color="green"))
                    self.after(0, lambda: self.ytdlp_info_label.configure(text=f"Version: {version}"))
                except Exception as e:
                    self.after(0, lambda: self.ytdlp_status_label.configure(text="✗ Error", text_color="red"))
                    self.after(0, lambda: self.ytdlp_info_label.configure(text=f"Error: {str(e)[:50]}"))
            else:
                # Fallback to executable check
                ytdlp_path = get_ytdlp_path()
                try:
                    result = subprocess.run([ytdlp_path, "--version"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        self.after(0, lambda: self.ytdlp_status_label.configure(text="✓ Installed", text_color="green"))
                        self.after(0, lambda: self.ytdlp_info_label.configure(text=f"Version: {version}"))
                    else:
                        self.after(0, lambda: self.ytdlp_status_label.configure(text="✗ Error", text_color="red"))
                        self.after(0, lambda: self.ytdlp_info_label.configure(text="Failed to get version"))
                except FileNotFoundError:
                    self.after(0, lambda: self.ytdlp_status_label.configure(text="✗ Not found", text_color="red"))
                    self.after(0, lambda: self.ytdlp_info_label.configure(text="yt-dlp not installed. Run: pip install yt-dlp"))
                except Exception as e:
                    self.after(0, lambda: self.ytdlp_status_label.configure(text="✗ Error", text_color="red"))
                    self.after(0, lambda: self.ytdlp_info_label.configure(text=f"Error: {str(e)[:50]}"))
            
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
                        self.after(0, lambda: self.ffmpeg_info_label.configure(text=f"Version: {version}"))
                    else:
                        self.after(0, lambda: self.ffmpeg_status_label.configure(text="✗ Error", text_color="red"))
                        self.after(0, lambda: self.ffmpeg_info_label.configure(text="Failed to get version"))
                except Exception as e:
                    self.after(0, lambda: self.ffmpeg_status_label.configure(text="✗ Error", text_color="red"))
                    self.after(0, lambda: self.ffmpeg_info_label.configure(text=f"Error: {str(e)[:50]}"))
            else:
                self.after(0, lambda: self.ffmpeg_status_label.configure(text="✗ Not found", text_color="orange"))
                self.after(0, lambda: self.ffmpeg_info_label.configure(text="Click button below to download automatically"))
                self.after(0, lambda: self.ffmpeg_download_btn.pack(fill="x", padx=15, pady=(0, 15)))
            
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
                        self.after(0, lambda: self.deno_info_label.configure(text=f"Version: {version}"))
                    else:
                        self.after(0, lambda: self.deno_status_label.configure(text="✗ Error", text_color="red"))
                        self.after(0, lambda: self.deno_info_label.configure(text="Failed to get version"))
                except Exception as e:
                    self.after(0, lambda: self.deno_status_label.configure(text="✗ Error", text_color="red"))
                    self.after(0, lambda: self.deno_info_label.configure(text=f"Error: {str(e)[:50]}"))
            else:
                self.after(0, lambda: self.deno_status_label.configure(text="✗ Not found", text_color="orange"))
                self.after(0, lambda: self.deno_info_label.configure(text="Click button below to download automatically"))
                self.after(0, lambda: self.deno_download_btn.pack(fill="x", padx=15, pady=(0, 15)))
        
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
                    self.after(0, lambda: messagebox.showinfo("Success", "FFmpeg downloaded and installed successfully!"))
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
                    self.after(0, lambda: messagebox.showinfo("Success", "Deno downloaded and installed successfully!"))
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
