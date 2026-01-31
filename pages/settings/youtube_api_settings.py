"""
YouTube API Settings Sub-Page
"""

import threading
import webbrowser
import customtkinter as ctk
from tkinter import messagebox

from pages.settings.base_dialog import BaseSettingsSubPage


class YouTubeAPISettingsSubPage(BaseSettingsSubPage):
    """Sub-page for configuring YouTube API OAuth"""
    
    def __init__(self, parent, config, on_save_callback, on_back_callback):
        self.config = config
        self.on_save_callback = on_save_callback
        self.youtube_uploader = None
        
        super().__init__(parent, "YouTube API Settings", on_back_callback)
        
        self.create_content()
        self.check_status()
    
    def create_content(self):
        """Create page content"""
        # YouTube header
        header_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(header_frame, text="YouTube", 
            font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        self.status_badge = ctk.CTkLabel(header_frame, text="Not connected", 
            text_color="gray", font=ctk.CTkFont(size=11))
        self.status_badge.pack(side="right")
        
        # Connection Status Section
        status_section = ctk.CTkFrame(self.content, fg_color=("gray90", "gray17"), corner_radius=10)
        status_section.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(status_section, text="Connection Status", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(15, 10))
        
        status_frame = ctk.CTkFrame(status_section, fg_color="transparent")
        status_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.status_label = ctk.CTkLabel(status_frame, text="Checking...", 
            font=ctk.CTkFont(size=12), text_color="gray")
        self.status_label.pack(anchor="w")
        
        self.channel_label = ctk.CTkLabel(status_frame, text="", 
            font=ctk.CTkFont(size=11), text_color="gray")
        self.channel_label.pack(anchor="w", pady=(5, 0))
        
        # Action Buttons
        btn_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 15))
        
        self.connect_btn = ctk.CTkButton(btn_frame, text="Connect YouTube", height=40, 
            fg_color=("#c4302b", "#FF0000"), hover_color=("#ff0000", "#CC0000"),
            command=self.connect_youtube)
        self.connect_btn.pack(fill="x", pady=(0, 10))
        
        self.disconnect_btn = ctk.CTkButton(btn_frame, text="Disconnect", height=35,
            fg_color="gray", hover_color="#c0392b", command=self.disconnect_youtube)
        self.disconnect_btn.pack(fill="x")
        self.disconnect_btn.pack_forget()
        
        # Setup Instructions
        info_section = ctk.CTkFrame(self.content, fg_color=("gray90", "gray17"), corner_radius=10)
        info_section.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(info_section, text="Setup Instructions", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(15, 10))
        
        info_text = """1. Set up Google Cloud project
2. Enable YouTube Data API v3
3. Create OAuth credentials
4. Place client_secret.json in app folder

See README for detailed setup guide."""
        
        ctk.CTkLabel(info_section, text=info_text, justify="left", anchor="w",
            font=ctk.CTkFont(size=11), text_color="gray", wraplength=450).pack(anchor="w", padx=15, pady=(0, 15))
        
        # Open Google Console button
        ctk.CTkButton(info_section, text="Open Google Cloud Console", height=38,
            fg_color="gray", hover_color=("gray70", "gray30"),
            command=lambda: webbrowser.open("https://console.cloud.google.com/")).pack(fill="x", padx=15, pady=(0, 15))
    
    def check_status(self):
        """Check YouTube connection status"""
        def do_check():
            try:
                from youtube_uploader import YouTubeUploader
                self.youtube_uploader = YouTubeUploader()
                
                if not self.youtube_uploader.is_configured():
                    self.after(0, lambda: self._update_status("not_configured"))
                    return
                
                if self.youtube_uploader.is_authenticated():
                    channel = self.youtube_uploader.get_channel_info()
                    if channel:
                        self.after(0, lambda c=channel: self._update_status("connected", c))
                    else:
                        self.after(0, lambda: self._update_status("auth_error"))
                else:
                    self.after(0, lambda: self._update_status("not_connected"))
                    
            except ImportError:
                self.after(0, lambda: self._update_status("module_error"))
            except Exception as e:
                self.after(0, lambda err=str(e): self._update_status("error", error=err))
        
        threading.Thread(target=do_check, daemon=True).start()
    
    def _update_status(self, status, channel=None, error=None):
        """Update status display"""
        if status == "connected" and channel:
            channel_title = channel.get('title', 'Unknown')
            self.status_badge.configure(text=f"Connected: {channel_title}", text_color="green")
            self.status_label.configure(text="Connected", text_color="green")
            self.channel_label.configure(text=f"Channel: {channel_title}")
            self.connect_btn.pack_forget()
            self.disconnect_btn.pack(fill="x")
            
        elif status == "not_configured":
            self.status_badge.configure(text="client_secret.json not found", text_color="orange")
            self.status_label.configure(text="Not configured", text_color="orange")
            self.channel_label.configure(text="client_secret.json not found in app folder")
            self.connect_btn.configure(state="disabled")
            self.disconnect_btn.pack_forget()
            
        elif status == "not_connected":
            self.status_badge.configure(text="Not connected", text_color="gray")
            self.status_label.configure(text="Not connected", text_color="gray")
            self.channel_label.configure(text="Click 'Connect YouTube' to authorize")
            self.connect_btn.configure(state="normal")
            self.disconnect_btn.pack_forget()
            
        elif status == "auth_error":
            self.status_badge.configure(text="Auth error", text_color="orange")
            self.status_label.configure(text="Authentication error", text_color="orange")
            self.channel_label.configure(text="Try reconnecting your account")
            self.connect_btn.configure(state="normal")
            self.disconnect_btn.pack(fill="x")
            
        elif status == "module_error":
            self.status_badge.configure(text="Module not available", text_color="orange")
            self.status_label.configure(text="YouTube module not available", text_color="orange")
            self.channel_label.configure(text="Check if dependencies are installed")
            self.connect_btn.configure(state="disabled")
            self.disconnect_btn.pack_forget()
            
        else:
            self.status_badge.configure(text="Error", text_color="red")
            self.status_label.configure(text="Error", text_color="red")
            self.channel_label.configure(text=error[:50] if error else "Unknown error")
            self.connect_btn.configure(state="disabled")
            self.disconnect_btn.pack_forget()
    
    def connect_youtube(self):
        """Connect YouTube account"""
        self.connect_btn.configure(state="disabled", text="Connecting...")
        
        def do_connect():
            try:
                if not self.youtube_uploader:
                    from youtube_uploader import YouTubeUploader
                    self.youtube_uploader = YouTubeUploader()
                
                self.youtube_uploader.authenticate(callback=self._on_auth_callback)
                    
            except Exception as e:
                self.after(0, lambda err=str(e): self._on_connect_error(err))
        
        threading.Thread(target=do_connect, daemon=True).start()
    
    def _on_auth_callback(self, success, data):
        """Handle authentication callback"""
        if success:
            self.after(0, lambda d=data: self._on_connect_success(d))
        else:
            self.after(0, lambda err=str(data): self._on_connect_error(err))
    
    def _on_connect_success(self, channel):
        """Handle successful connection"""
        self.connect_btn.configure(text="Connect YouTube")
        self._update_status("connected", channel)
        
        channel_title = channel.get('title', 'Unknown') if channel else 'Unknown'
        messagebox.showinfo("Success", f"Connected to YouTube channel: {channel_title}")
        
        # Update main app status if available
        try:
            parent = self.master
            while parent:
                if hasattr(parent, 'update_connection_status'):
                    parent.update_connection_status()
                    break
                parent = getattr(parent, 'master', None)
        except:
            pass
    
    def _on_connect_error(self, error):
        """Handle connection error"""
        self.connect_btn.configure(state="normal", text="Connect YouTube")
        self.status_label.configure(text="Connection failed", text_color="red")
        messagebox.showerror("Error", f"Failed to connect:\n{error}")
    
    def disconnect_youtube(self):
        """Disconnect YouTube account"""
        if not messagebox.askyesno("Disconnect", "Are you sure you want to disconnect YouTube?"):
            return
        
        try:
            if self.youtube_uploader:
                self.youtube_uploader.disconnect()
            
            import os
            creds_file = "youtube_credentials.json"
            if os.path.exists(creds_file):
                os.remove(creds_file)
            
            self._update_status("not_connected")
            self.connect_btn.pack(fill="x", pady=(0, 10))
            messagebox.showinfo("Success", "YouTube account disconnected")
            
            # Update main app status if available
            try:
                parent = self.master
                while parent:
                    if hasattr(parent, 'update_connection_status'):
                        parent.update_connection_status()
                        break
                    parent = getattr(parent, 'master', None)
            except:
                pass
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disconnect:\n{str(e)}")
