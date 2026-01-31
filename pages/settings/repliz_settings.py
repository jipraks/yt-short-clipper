"""
Repliz Settings Sub-Page
"""

import threading
import webbrowser
import customtkinter as ctk
from tkinter import messagebox

from pages.settings.base_dialog import BaseSettingsSubPage


class ReplizSettingsSubPage(BaseSettingsSubPage):
    """Sub-page for configuring Repliz integration"""
    
    def __init__(self, parent, config, on_save_callback, on_back_callback):
        self.config = config
        self.on_save_callback = on_save_callback
        
        super().__init__(parent, "Repliz Settings", on_back_callback)
        
        self.create_content()
        self.load_config()
    
    def create_content(self):
        """Create page content"""
        # Why Repliz card
        why_card = ctk.CTkFrame(self.content, fg_color=("#e8f5e9", "#1b5e20"), corner_radius=10)
        why_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(why_card, text="Why Use Repliz?", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(15, 10))
        
        why_text = """Upload to ALL platforms at once (YouTube, TikTok, Instagram, Facebook)
Official API integration - safe from bans
No need for complex Google Console or TikTok Developer setup
Schedule posts in advance across all platforms
Affordable: Only $1.74/month (29,000 IDR) for Premium plan"""
        
        ctk.CTkLabel(why_card, text=why_text, justify="left",
            font=ctk.CTkFont(size=11), wraplength=480).pack(anchor="w", padx=15, pady=(0, 15))
        
        # Sign up CTA
        signup_frame = ctk.CTkFrame(self.content, fg_color=("gray85", "gray20"), corner_radius=10)
        signup_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(signup_frame, text="Don't Have a Repliz Account Yet?", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(signup_frame, 
            text="Sign up now and get started with multi-platform scheduling.",
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=15, pady=(0, 10))
        
        ctk.CTkButton(signup_frame, text="Sign Up for Repliz", height=40,
            fg_color=("#2196F3", "#1976D2"), hover_color=("#1976D2", "#1565C0"),
            command=lambda: webbrowser.open("https://s.id/ytrepliz")).pack(fill="x", padx=15, pady=(0, 15))
        
        # API Configuration section
        config_section = ctk.CTkFrame(self.content, fg_color=("gray90", "gray17"), corner_radius=10)
        config_section.pack(fill="x", pady=(0, 15))
        
        config_header = ctk.CTkFrame(config_section, fg_color="transparent")
        config_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(config_header, text="API Configuration", 
            font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        self.repliz_status_label = ctk.CTkLabel(config_header, text="Not configured", 
            text_color="gray", font=ctk.CTkFont(size=11))
        self.repliz_status_label.pack(side="right")
        
        # Access Key
        access_frame = ctk.CTkFrame(config_section, fg_color="transparent")
        access_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(access_frame, text="Access Key", 
            font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(access_frame, text="Your Repliz API Access Key", 
            font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w", pady=(2, 5))
        
        self.access_key_entry = ctk.CTkEntry(access_frame, height=38,
            placeholder_text="Enter your Repliz Access Key")
        self.access_key_entry.pack(fill="x")
        
        # Secret Key
        secret_frame = ctk.CTkFrame(config_section, fg_color="transparent")
        secret_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(secret_frame, text="Secret Key", 
            font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(secret_frame, text="Your Repliz API Secret Key (kept secure)", 
            font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w", pady=(2, 5))
        
        self.secret_key_entry = ctk.CTkEntry(secret_frame, height=38, show="*",
            placeholder_text="Enter your Repliz Secret Key")
        self.secret_key_entry.pack(fill="x")
        
        # Buttons
        btn_frame = ctk.CTkFrame(config_section, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.validate_btn = ctk.CTkButton(btn_frame, text="Validate Keys", height=40,
            fg_color=("#3B8ED0", "#1F6AA5"), command=self.validate_keys)
        self.validate_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Connected Accounts section (initially hidden)
        self.accounts_section = ctk.CTkFrame(self.content, fg_color=("gray90", "gray17"), corner_radius=10)
        
        accounts_header = ctk.CTkFrame(self.accounts_section, fg_color="transparent")
        accounts_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(accounts_header, text="Connected Social Media Accounts", 
            font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        self.accounts_count = ctk.CTkLabel(accounts_header, text="0 accounts", 
            text_color="gray", font=ctk.CTkFont(size=11))
        self.accounts_count.pack(side="right")
        
        self.accounts_list = ctk.CTkFrame(self.accounts_section, fg_color="transparent")
        self.accounts_list.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Save button
        self.create_save_button(self.save_settings)
    
    def load_config(self):
        """Load config into UI"""
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
        
        repliz = config_dict.get("repliz", {})
        access_key = repliz.get("access_key", "")
        secret_key = repliz.get("secret_key", "")
        
        if access_key:
            self.access_key_entry.delete(0, "end")
            self.access_key_entry.insert(0, access_key)
        
        if secret_key:
            self.secret_key_entry.delete(0, "end")
            self.secret_key_entry.insert(0, secret_key)
        
        if access_key and secret_key:
            self.repliz_status_label.configure(text="Configured", text_color="green")
            self.after(100, self.load_accounts_silent)

    def load_accounts_silent(self):
        """Load accounts silently in background (no popup)"""
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
        
        repliz = config_dict.get("repliz", {})
        access_key = repliz.get("access_key", "")
        secret_key = repliz.get("secret_key", "")
        
        if not access_key or not secret_key:
            return
        
        def do_load():
            try:
                import requests
                from requests.auth import HTTPBasicAuth
                
                url = "https://api.repliz.com/public/account"
                params = {"page": 1, "limit": 10}
                
                response = requests.get(
                    url, 
                    params=params,
                    auth=HTTPBasicAuth(access_key, secret_key),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.after(0, lambda d=data: self._display_accounts(d, show_popup=False))
                    
            except Exception:
                pass
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def validate_keys(self):
        """Validate Repliz API keys"""
        access_key = self.access_key_entry.get().strip()
        secret_key = self.secret_key_entry.get().strip()
        
        if not access_key or not secret_key:
            messagebox.showerror("Error", "Please enter both Access Key and Secret Key")
            return
        
        self.validate_btn.configure(state="disabled", text="Validating...")
        self.repliz_status_label.configure(text="Validating...", text_color="yellow")
        
        def do_validate():
            try:
                import requests
                from requests.auth import HTTPBasicAuth
                
                url = "https://api.repliz.com/public/account"
                params = {"page": 1, "limit": 10}
                
                response = requests.get(
                    url, 
                    params=params,
                    auth=HTTPBasicAuth(access_key, secret_key),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.after(0, lambda d=data: self._on_validate_success(d))
                else:
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", error_msg)
                    except:
                        if response.status_code == 401:
                            error_msg = "Invalid authorization header"
                    self.after(0, lambda e=error_msg: self._on_validate_error(e))
                    
            except Exception as e:
                self.after(0, lambda err=str(e): self._on_validate_error(err))
        
        threading.Thread(target=do_validate, daemon=True).start()
    
    def _on_validate_success(self, data):
        """Handle successful validation"""
        self.validate_btn.configure(state="normal", text="Validate Keys")
        self.repliz_status_label.configure(text="Valid", text_color="green")
        
        self._display_accounts(data, show_popup=True)
    
    def _display_accounts(self, data, show_popup=False):
        """Display connected accounts"""
        total_accounts = data.get("totalDocs", 0)
        accounts = data.get("docs", [])
        
        self.accounts_count.configure(text=f"{total_accounts} account(s)")
        
        for widget in self.accounts_list.winfo_children():
            widget.destroy()
        
        if total_accounts > 0:
            self.accounts_section.pack(fill="x", pady=(0, 15))
            
            for idx, account in enumerate(accounts):
                self._create_account_card(account, idx)
            
            if show_popup:
                messagebox.showinfo("Success", 
                    f"API Keys validated!\n\nYou have {total_accounts} connected account(s).")
        else:
            self.accounts_section.pack_forget()
            if show_popup:
                messagebox.showinfo("Success", 
                    "API Keys validated!\n\nNo connected accounts yet.\nGo to Repliz dashboard to connect accounts.")
    
    def _on_validate_error(self, error):
        """Handle validation error"""
        self.validate_btn.configure(state="normal", text="Validate Keys")
        self.repliz_status_label.configure(text="Invalid", text_color="red")
        messagebox.showerror("Validation Failed", f"Failed to validate:\n\n{error}")
    
    def _create_account_card(self, account, index):
        """Create account card with profile picture"""
        platform_type = account.get("type", "unknown")
        platform_icons = {
            "youtube": "",
            "tiktok": "",
            "instagram": "",
            "threads": "",
            "facebook": ""
        }
        icon = platform_icons.get(platform_type, "")
        
        row = index // 3
        col = index % 3
        
        card = ctk.CTkFrame(self.accounts_list, fg_color=("gray95", "gray25"), 
            corner_radius=10, width=160, height=200)
        card.pack_propagate(False)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        
        picture_url = account.get("picture", "")
        
        if picture_url:
            self._load_profile_picture(card, picture_url, icon)
        else:
            ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=48)).pack(pady=(15, 5))
        
        ctk.CTkLabel(card, text=platform_type.upper(), 
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=("gray80", "gray30"), corner_radius=4,
            padx=8, pady=2).pack(pady=(5, 5))
        
        account_name = account.get("name", "Unknown")
        if len(account_name) > 15:
            account_name = account_name[:13] + "..."
        
        ctk.CTkLabel(card, text=account_name,
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=140).pack(pady=(0, 2))
        
        username = account.get("username", "")
        if username:
            if len(username) > 18:
                username = username[:16] + "..."
            username_text = f"@{username}" if not username.startswith("@") else username
            ctk.CTkLabel(card, text=username_text,
                font=ctk.CTkFont(size=10), text_color="gray",
                wraplength=140).pack(pady=(0, 8))
        
        is_connected = account.get("isConnected", False)
        status_text = "Connected" if is_connected else "Disconnected"
        status_color = ("green", "green") if is_connected else ("red", "red")
        
        ctk.CTkLabel(card, text=status_text,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="white", fg_color=status_color,
            corner_radius=4, padx=10, pady=4).pack(side="bottom", pady=(0, 10))
    
    def _load_profile_picture(self, parent, url, fallback_icon):
        """Load profile picture from URL"""
        def do_load():
            try:
                import requests
                from PIL import Image, ImageDraw, ImageOps
                from io import BytesIO
                
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    img = img.resize((80, 80), Image.Resampling.LANCZOS)
                    
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    mask = Image.new('L', (80, 80), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, 80, 80), fill=255)
                    
                    output = ImageOps.fit(img, (80, 80), centering=(0.5, 0.5))
                    output.putalpha(mask)
                    
                    from customtkinter import CTkImage
                    ctk_img = CTkImage(light_image=output, dark_image=output, size=(80, 80))
                    
                    self.after(0, lambda p=parent, img=ctk_img: self._display_profile_picture(p, img))
                else:
                    self.after(0, lambda p=parent, icon=fallback_icon: self._display_fallback_icon(p, icon))
                    
            except Exception:
                self.after(0, lambda p=parent, icon=fallback_icon: self._display_fallback_icon(p, icon))
        
        ctk.CTkLabel(parent, text="...", font=ctk.CTkFont(size=40)).pack(pady=(15, 5))
        threading.Thread(target=do_load, daemon=True).start()
    
    def _display_profile_picture(self, parent, ctk_img):
        """Display loaded profile picture"""
        for widget in parent.winfo_children():
            if isinstance(widget, ctk.CTkLabel) and widget.cget("text") == "...":
                widget.destroy()
                break
        
        ctk.CTkLabel(parent, image=ctk_img, text="").pack(pady=(15, 5))
    
    def _display_fallback_icon(self, parent, icon):
        """Display fallback icon"""
        for widget in parent.winfo_children():
            if isinstance(widget, ctk.CTkLabel) and widget.cget("text") == "...":
                widget.destroy()
                break
        
        ctk.CTkLabel(parent, text=icon, font=ctk.CTkFont(size=48)).pack(pady=(15, 5))
    
    def save_settings(self):
        """Save Repliz settings"""
        access_key = self.access_key_entry.get().strip()
        secret_key = self.secret_key_entry.get().strip()
        
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
        
        config_dict["repliz"] = {
            "access_key": access_key,
            "secret_key": secret_key
        }
        
        if self.on_save_callback:
            self.on_save_callback(config_dict)
        
        if access_key and secret_key:
            self.repliz_status_label.configure(text="Configured", text_color="green")
        
        messagebox.showinfo("Success", "Repliz settings saved!")
        self.on_back()
