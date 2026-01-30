"""
Settings page for YT Short Clipper
"""

import os
import sys
import subprocess
import threading
import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog, messagebox
from openai import OpenAI

from dialogs.model_selector import SearchableModelDropdown
from version import __version__


class SettingsPage(ctk.CTkFrame):
    """Settings page - embedded in main window"""
    
    def __init__(self, parent, config, on_save_callback, on_back_callback, output_dir, check_update_callback=None):
        super().__init__(parent)
        self.config = config
        self.on_save = on_save_callback
        self.on_back = on_back_callback
        self.output_dir = output_dir
        self.check_update = check_update_callback
        self.models_list = []
        self.youtube_uploader = None
        self.tiktok_uploader = None
        
        self.create_ui()
        self.load_config()
    
    def create_ui(self):
        """Create the settings UI"""
        # Import header and footer components
        from components.page_layout import PageHeader, PageFooter
        
        # Set background color to match home page
        self.configure(fg_color=("#1a1a1a", "#0a0a0a"))
        
        # Header with back button
        header = PageHeader(self, self, show_nav_buttons=False, show_back_button=True, page_title="Settings")
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        # Main content with tabs
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Create tabview with custom styling
        self.tabview = ctk.CTkTabview(main, height=40, segmented_button_fg_color=("gray80", "gray20"),
            segmented_button_selected_color=("#3B8ED0", "#1F6AA5"),
            segmented_button_selected_hover_color=("#36719F", "#144870"),
            segmented_button_unselected_color=("gray85", "gray25"),
            segmented_button_unselected_hover_color=("gray75", "gray30"))
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tabview.add("AI API Settings")
        self.tabview.add("Performance")
        self.tabview.add("Output")
        self.tabview.add("Watermark")
        self.tabview.add("Repliz")
        self.tabview.add("Social Accounts")
        self.tabview.add("About")
        
        self.create_openai_tab()
        self.create_performance_tab()
        self.create_output_tab()
        self.create_watermark_tab()
        self.create_repliz_tab()
        self.create_social_accounts_tab()
        self.create_about_tab()
        
        # Footer
        footer = PageFooter(self, self)
        footer.pack(fill="x", padx=20, pady=(0, 15), side="bottom")
    
    def create_openai_tab(self):
        """Create AI API settings tab with nested tabs for each provider"""
        main = self.tabview.tab("AI API Settings")
        
        # Header description
        header_frame = ctk.CTkFrame(main, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(header_frame, text="AI API Settings", 
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(fill="x")
        
        # Provider selector cards (YT CLIP AI, OPEN AI, CUSTOM)
        cards_frame = ctk.CTkFrame(main, fg_color="transparent")
        cards_frame.pack(fill="x", padx=15, pady=(10, 15))
        
        # Create variable to track selected provider type
        self.provider_type_var = ctk.StringVar(value="ytclip")
        
        # Card container with 3 columns
        cards_container = ctk.CTkFrame(cards_frame, fg_color="transparent")
        cards_container.pack(fill="x")
        
        # YT CLIP AI Card
        ytclip_card = ctk.CTkFrame(cards_container, fg_color=("gray85", "gray20"), 
            corner_radius=10, border_width=2, border_color=("gray70", "gray30"))
        ytclip_card.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ytclip_btn = ctk.CTkButton(ytclip_card, text="🎬 YT CLIP AI", height=60,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent", hover_color=("#3B8ED0", "#1F6AA5"),
            command=lambda: self._select_provider_type("ytclip", ytclip_card, openai_card, custom_card))
        ytclip_btn.pack(fill="both", expand=True, padx=3, pady=3)
        
        self.ytclip_card = ytclip_card
        
        # OPEN AI Card
        openai_card = ctk.CTkFrame(cards_container, fg_color=("gray85", "gray20"), 
            corner_radius=10, border_width=2, border_color=("gray70", "gray30"))
        openai_card.pack(side="left", fill="both", expand=True, padx=5)
        
        openai_btn = ctk.CTkButton(openai_card, text="🤖 OPEN AI", height=60,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent", hover_color=("#3B8ED0", "#1F6AA5"),
            command=lambda: self._select_provider_type("openai", ytclip_card, openai_card, custom_card))
        openai_btn.pack(fill="both", expand=True, padx=3, pady=3)
        
        self.openai_card = openai_card
        
        # CUSTOM Card
        custom_card = ctk.CTkFrame(cards_container, fg_color=("gray85", "gray20"), 
            corner_radius=10, border_width=2, border_color=("gray70", "gray30"))
        custom_card.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        custom_btn = ctk.CTkButton(custom_card, text="⚙️ CUSTOM", height=60,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent", hover_color=("#3B8ED0", "#1F6AA5"),
            command=lambda: self._select_provider_type("custom", ytclip_card, openai_card, custom_card))
        custom_btn.pack(fill="both", expand=True, padx=3, pady=3)
        
        self.custom_card = custom_card
        
        # Nested tabview for providers
        self.provider_tabview = ctk.CTkTabview(main, height=40,
            segmented_button_fg_color=("gray80", "gray20"),
            segmented_button_selected_color=("#3B8ED0", "#1F6AA5"),
            segmented_button_selected_hover_color=("#36719F", "#144870"),
            segmented_button_unselected_color=("gray85", "gray25"),
            segmented_button_unselected_hover_color=("gray75", "gray30"))
        self.provider_tabview.pack(fill="both", expand=True, padx=10, pady=(10, 10))
        
        # Add tabs for each provider
        self.provider_tabview.add("🎯 Highlight Finder")
        self.provider_tabview.add("📝 Caption Maker")
        self.provider_tabview.add("🎤 Hook Maker")
        self.provider_tabview.add("📺 YouTube Title")
        
        # Create content for each tab
        self.create_highlight_finder_tab()
        self.create_caption_maker_tab()
        self.create_hook_maker_tab()
        self.create_youtube_title_tab()
        
        # Save button at bottom
        ctk.CTkButton(main, text="💾 Save All Settings", height=45, 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#27ae60", "#27ae60"), hover_color=("#229954", "#229954"),
            command=self.save_settings).pack(fill="x", padx=15, pady=(10, 15))
    
    
    def open_yt_model_selector(self):
        """Open searchable model selector dialog for YouTube Title Maker"""
        if not self.yt_models_list:
            messagebox.showwarning("Warning", "No models available.\n\nTry clicking 'Load' first.")
            return
        
        SearchableModelDropdown(self, self.yt_models_list, self.yt_model_var.get(), 
            lambda m: self.yt_model_var.set(m))
    
    def load_yt_models(self):
        """Load available models from YouTube Title Maker API"""
        # Get URL based on current provider type
        provider_type = self.provider_type_var.get()
        if provider_type == "ytclip":
            url = "https://ai-api.ytclip.org/v1"
        elif provider_type == "openai":
            url = "https://api.openai.com/v1"
        else:
            url = self.yt_url_entry.get().strip() or "https://api.openai.com/v1"
        
        api_key = self.yt_key_entry.get().strip()
        
        if not api_key:
            messagebox.showerror("Error", "Please enter API Key first")
            return
        
        self.yt_load_models_btn.configure(state="disabled", text="Loading...")
        
        def do_load():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=url)
                models_response = client.models.list()
                
                # Filter for chat models (exclude whisper, tts, embeddings, etc.)
                all_models = [m.id for m in models_response.data]
                chat_models = [m for m in all_models if not any(x in m.lower() for x in ['whisper', 'tts', 'embedding', 'dall-e', 'davinci'])]
                
                # Sort models with GPT-4 variants first
                def sort_key(model):
                    if 'gpt-4' in model.lower():
                        return (0, model)
                    elif 'gpt-3.5' in model.lower():
                        return (1, model)
                    else:
                        return (2, model)
                
                chat_models.sort(key=sort_key)
                
                if not chat_models:
                    chat_models = all_models  # Fallback to all models if filtering removes everything
                
                self.after(0, lambda m=chat_models: self._on_yt_models_loaded(m))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda err=error_msg: self._on_yt_models_load_error(err))
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def _on_yt_models_loaded(self, models):
        """Handle successful models loading for YouTube Title"""
        self.yt_load_models_btn.configure(state="normal", text="🔄 Load")
        
        if models:
            # Store models list
            self.yt_models_list = models
            
            # Set current value if it exists in list, otherwise set first model
            current = self.yt_model_var.get()
            if current not in models:
                self.yt_model_var.set(models[0])
            
            messagebox.showinfo("Success", f"✓ Loaded {len(models)} models successfully!\n\nClick 'Select' to choose a model.")
        else:
            messagebox.showwarning("Warning", "No models found")
    
    def _on_yt_models_load_error(self, error):
        """Handle models loading error for YouTube Title"""
        self.yt_load_models_btn.configure(state="normal", text="🔄 Load")
        messagebox.showerror("Error", f"Failed to load models:\n\n{error}")
    
    def validate_yt_config(self):
        """Validate YouTube Title Maker configuration"""
        # Get URL based on current provider type
        provider_type = self.provider_type_var.get()
        if provider_type == "ytclip":
            url = "https://ai-api.ytclip.org/v1"
        elif provider_type == "openai":
            url = "https://api.openai.com/v1"
        else:
            url = self.yt_url_entry.get().strip() or "https://api.openai.com/v1"
        
        api_key = self.yt_key_entry.get().strip()
        model = self.yt_model_var.get().strip()
        
        if not api_key:
            messagebox.showerror("Error", "API Key is required")
            return
        
        if not model:
            messagebox.showerror("Error", "Model is required")
            return
        
        # Disable button during validation
        validate_btn = None
        for widget in self.provider_tabview.tab("📺 YouTube Title").winfo_children():
            if isinstance(widget, ctk.CTkScrollableFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkFrame):
                        for btn in child.winfo_children():
                            if isinstance(btn, ctk.CTkButton) and "Validate" in btn.cget("text"):
                                validate_btn = btn
                                break
        
        if validate_btn:
            validate_btn.configure(state="disabled", text="Validating...")
        
        def do_validate():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=url)
                
                # Try to list models to verify API key and model availability
                try:
                    models_response = client.models.list()
                    available_models = [m.id for m in models_response.data]
                    
                    # Check if model is available
                    if model not in available_models:
                        err_msg = f"Model '{model}' not found in available models.\n\nAvailable models: {', '.join(available_models[:5])}..."
                        self.after(0, lambda e=err_msg, b=validate_btn: self._on_yt_validate_error(e, b))
                        return
                except Exception as list_error:
                    # If listing models fails, the API key might still be valid
                    # Some providers don't support models.list()
                    # Just verify the API key is not empty and continue
                    pass
                
                self.after(0, lambda m=model, u=url, b=validate_btn: self._on_yt_validate_success(m, u, b))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda err=error_msg, b=validate_btn: self._on_yt_validate_error(err, b))
        
        threading.Thread(target=do_validate, daemon=True).start()
    
    def _on_yt_validate_success(self, model, url, validate_btn):
        """Handle successful validation for YouTube Title"""
        if validate_btn:
            validate_btn.configure(state="normal", text="🔍 Validate Configuration")
        messagebox.showinfo("Success", 
            f"✓ Configuration validated successfully!\n\nModel: {model}\nProvider: {url}")
    
    def _on_yt_validate_error(self, error, validate_btn):
        """Handle validation error for YouTube Title"""
        if validate_btn:
            validate_btn.configure(state="normal", text="🔍 Validate Configuration")
        messagebox.showerror("Validation Failed", 
            f"Failed to validate configuration:\n\n{error}")
    
    def open_hf_model_selector(self):
        """Open searchable model selector dialog for Highlight Finder"""
        if not self.hf_models_list:
            messagebox.showwarning("Warning", "No models available.\n\nTry clicking 'Load' first.")
            return
        
        SearchableModelDropdown(self, self.hf_models_list, self.hf_model_var.get(), 
            lambda m: self.hf_model_var.set(m))
    
    def load_hf_models(self):
        """Load available models from Highlight Finder API"""
        # Get URL based on current provider type
        provider_type = self.provider_type_var.get()
        if provider_type == "ytclip":
            url = "https://ai-api.ytclip.org/v1"
        elif provider_type == "openai":
            url = "https://api.openai.com/v1"
        else:
            url = self.hf_url_entry.get().strip() or "https://api.openai.com/v1"
        
        api_key = self.hf_key_entry.get().strip()
        
        if not api_key:
            messagebox.showerror("Error", "Please enter API Key first")
            return
        
        self.hf_load_models_btn.configure(state="disabled", text="Loading...")
        
        def do_load():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=url)
                models_response = client.models.list()
                
                # Filter for chat models (exclude whisper, tts, embeddings, etc.)
                all_models = [m.id for m in models_response.data]
                chat_models = [m for m in all_models if not any(x in m.lower() for x in ['whisper', 'tts', 'embedding', 'dall-e', 'davinci'])]
                
                # Sort models with GPT-4 variants first
                def sort_key(model):
                    if 'gpt-4' in model.lower():
                        return (0, model)
                    elif 'gpt-3.5' in model.lower():
                        return (1, model)
                    else:
                        return (2, model)
                
                chat_models.sort(key=sort_key)
                
                if not chat_models:
                    chat_models = all_models  # Fallback to all models if filtering removes everything
                
                self.after(0, lambda m=chat_models: self._on_models_loaded(m))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda err=error_msg: self._on_models_load_error(err))
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def _on_models_loaded(self, models):
        """Handle successful models loading"""
        self.hf_load_models_btn.configure(state="normal", text="🔄 Load")
        
        if models:
            # Store models list
            self.hf_models_list = models
            
            # Set current value if it exists in list, otherwise set first model
            current = self.hf_model_var.get()
            if current not in models:
                self.hf_model_var.set(models[0])
            
            messagebox.showinfo("Success", f"✓ Loaded {len(models)} models successfully!\n\nClick 'Select' to choose a model.")
        else:
            messagebox.showwarning("Warning", "No models found")
    
    def _on_models_load_error(self, error):
        """Handle models loading error"""
        self.hf_load_models_btn.configure(state="normal", text="🔄 Load")
        messagebox.showerror("Error", f"Failed to load models:\n\n{error}")
    
    def validate_hf_config(self):
        """Validate Highlight Finder configuration"""
        # Get URL based on current provider type
        provider_type = self.provider_type_var.get()
        if provider_type == "ytclip":
            url = "https://ai-api.ytclip.org/v1"
        elif provider_type == "openai":
            url = "https://api.openai.com/v1"
        else:
            url = self.hf_url_entry.get().strip() or "https://api.openai.com/v1"
        
        api_key = self.hf_key_entry.get().strip()
        model = self.hf_model_var.get().strip()
        
        if not api_key:
            messagebox.showerror("Error", "API Key is required")
            return
        
        if not model:
            messagebox.showerror("Error", "Model is required")
            return
        
        # Disable button during validation
        validate_btn = None
        for widget in self.provider_tabview.tab("🎯 Highlight Finder").winfo_children():
            if isinstance(widget, ctk.CTkScrollableFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkFrame):
                        for btn in child.winfo_children():
                            if isinstance(btn, ctk.CTkButton) and "Validate" in btn.cget("text"):
                                validate_btn = btn
                                break
        
        if validate_btn:
            validate_btn.configure(state="disabled", text="Validating...")
        
        def do_validate():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=url)
                
                # Try to list models to verify API key and model availability
                try:
                    models_response = client.models.list()
                    available_models = [m.id for m in models_response.data]
                    
                    # Check if model is available
                    if model not in available_models:
                        err_msg = f"Model '{model}' not found in available models.\n\nAvailable models: {', '.join(available_models[:5])}..."
                        self.after(0, lambda e=err_msg, b=validate_btn: self._on_hf_validate_error(e, b))
                        return
                except Exception as list_error:
                    # If listing models fails, the API key might still be valid
                    # Some providers don't support models.list()
                    # Just verify the API key is not empty and continue
                    pass
                
                self.after(0, lambda m=model, u=url, b=validate_btn: self._on_hf_validate_success(m, u, b))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda err=error_msg, b=validate_btn: self._on_hf_validate_error(err, b))
        
        threading.Thread(target=do_validate, daemon=True).start()
    
    def _on_hf_validate_success(self, model, url, validate_btn):
        """Handle successful validation"""
        if validate_btn:
            validate_btn.configure(state="normal", text="🔍 Validate Configuration")
        messagebox.showinfo("Success", 
            f"✓ Configuration validated successfully!\n\nModel: {model}\nProvider: {url}")
    
    def _on_hf_validate_error(self, error, validate_btn):
        """Handle validation error"""
        if validate_btn:
            validate_btn.configure(state="normal", text="🔍 Validate Configuration")
        messagebox.showerror("Validation Failed", 
            f"Failed to validate configuration:\n\n{error}")
    
    def validate_provider_simple(self, provider_key, url_entry, key_entry, model_entry):
        """Validate provider configuration"""
        # Get URL based on current provider type
        provider_type = self.provider_type_var.get()
        if provider_type == "ytclip":
            url = "https://ai-api.ytclip.org/v1"
        elif provider_type == "openai":
            url = "https://api.openai.com/v1"
        else:
            url = url_entry.get().strip() or "https://api.openai.com/v1"
        
        api_key = key_entry.get().strip()
        model = model_entry.get().strip()
        
        if not api_key:
            messagebox.showerror("Error", "API Key is required")
            return
        
        if not model:
            messagebox.showerror("Error", "Model is required")
            return
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=url)
            
            # All providers: Try to list models to verify API connection
            try:
                models_response = client.models.list()
                available_models = [m.id for m in models_response.data]
                
                # Check if model is available
                if model in available_models:
                    messagebox.showinfo("Success", 
                        f"✓ Configuration validated successfully!\n\nModel: {model}\nProvider: {url}")
                else:
                    # Model not found, but connection works
                    messagebox.showwarning("Warning", 
                        f"Model '{model}' not found in available models.\n\n" +
                        f"Available models: {', '.join(available_models[:5])}...")
                    
            except Exception as list_error:
                # Check if it's a connection/authentication error
                error_str = str(list_error).lower()
                if any(x in error_str for x in ['connection', 'timeout', 'unreachable', 'invalid', 'unauthorized', 'authentication', 'api key', 'not found', '404', '401', '403']):
                    # Real error - connection or auth failed
                    raise list_error
                else:
                    # Provider might not support models.list()
                    # Show success with note based on provider type
                    if provider_key == "caption_maker":
                        if "whisper" not in model.lower():
                            messagebox.showwarning("Warning", 
                                f"Model '{model}' doesn't look like a Whisper model.\n\nExpected: whisper-1 or similar")
                            return
                    elif provider_key == "hook_maker":
                        if "tts" not in model.lower():
                            messagebox.showwarning("Warning", 
                                f"Model '{model}' doesn't look like a TTS model.\n\nExpected: tts-1, tts-1-hd or similar")
                            return
                    
                    messagebox.showinfo("Success", 
                        f"✓ API Key validated!\n\nModel: {model}\nProvider: {url}\n\n" +
                        "Note: Could not verify model availability (provider may not support models.list)")
        
        except Exception as e:
            messagebox.showerror("Validation Failed", 
                f"Failed to validate configuration:\n\n{str(e)}")
    
    def apply_url_key_to_all_simple(self, url, api_key):
        """Apply URL and API Key to all providers"""
        if not url and not api_key:
            messagebox.showwarning("Warning", "Please enter URL and API Key first")
            return
        
        if messagebox.askyesno("Apply to All", 
            "Apply this URL and API Key to all AI providers?\n\n(Models will remain separate)"):
            
            url = url or "https://api.openai.com/v1"
            
            # Apply to all entry fields
            self.hf_url_entry.delete(0, "end")
            self.hf_url_entry.insert(0, url)
            self.hf_key_entry.delete(0, "end")
            self.hf_key_entry.insert(0, api_key)
            
            self.cm_url_entry.delete(0, "end")
            self.cm_url_entry.insert(0, url)
            self.cm_key_entry.delete(0, "end")
            self.cm_key_entry.insert(0, api_key)
            
            self.hm_url_entry.delete(0, "end")
            self.hm_url_entry.insert(0, url)
            self.hm_key_entry.delete(0, "end")
            self.hm_key_entry.insert(0, api_key)
            
            self.yt_url_entry.delete(0, "end")
            self.yt_url_entry.insert(0, url)
            self.yt_key_entry.delete(0, "end")
            self.yt_key_entry.insert(0, api_key)
            
            messagebox.showinfo("Success", "✓ URL and API Key applied to all providers!")
    
    def _select_provider_type(self, provider_type, ytclip_card, openai_card, custom_card):
        """Handle provider type selection and update UI"""
        self.provider_type_var.set(provider_type)
        
        # Update card borders to show selection
        ytclip_card.configure(border_color=("gray70", "gray30"))
        openai_card.configure(border_color=("gray70", "gray30"))
        custom_card.configure(border_color=("gray70", "gray30"))
        
        if provider_type == "ytclip":
            ytclip_card.configure(border_color=("#3B8ED0", "#1F6AA5"))
            base_url = "https://ai-api.ytclip.org/v1"
        elif provider_type == "openai":
            openai_card.configure(border_color=("#3B8ED0", "#1F6AA5"))
            base_url = "https://api.openai.com/v1"
        else:  # custom
            custom_card.configure(border_color=("#3B8ED0", "#1F6AA5"))
            base_url = self.hf_url_entry.get().strip() or "https://api.openai.com/v1"
        
        # Update all URL fields
        if hasattr(self, 'hf_url_entry'):
            self.hf_url_entry.delete(0, "end")
            self.hf_url_entry.insert(0, base_url)
        
        if hasattr(self, 'cm_url_entry'):
            self.cm_url_entry.delete(0, "end")
            self.cm_url_entry.insert(0, base_url)
        
        if hasattr(self, 'hm_url_entry'):
            self.hm_url_entry.delete(0, "end")
            self.hm_url_entry.insert(0, base_url)
        
        if hasattr(self, 'yt_url_entry'):
            self.yt_url_entry.delete(0, "end")
            self.yt_url_entry.insert(0, base_url)
        
        # Show/hide URL entry fields based on selection
        self._toggle_url_fields(provider_type == "custom")
    
    def _toggle_url_fields(self, show_custom):
        """Show or hide URL entry fields based on provider type"""
        # For YT CLIP AI and OPEN AI: hide URL fields completely
        # For CUSTOM: show URL fields
        if show_custom:
            # Show URL frames
            if hasattr(self, 'hf_url_frame'):
                self.hf_url_frame.pack(fill="x", padx=10, pady=(0, 15), before=self.hf_key_frame)
            if hasattr(self, 'cm_url_frame'):
                self.cm_url_frame.pack(fill="x", padx=10, pady=(0, 15), before=self.cm_key_frame)
            if hasattr(self, 'hm_url_frame'):
                self.hm_url_frame.pack(fill="x", padx=10, pady=(0, 15), before=self.hm_key_frame)
            if hasattr(self, 'yt_url_frame'):
                self.yt_url_frame.pack(fill="x", padx=10, pady=(0, 15), before=self.yt_key_frame)
        else:
            # Hide URL frames
            if hasattr(self, 'hf_url_frame'):
                self.hf_url_frame.pack_forget()
            if hasattr(self, 'cm_url_frame'):
                self.cm_url_frame.pack_forget()
            if hasattr(self, 'hm_url_frame'):
                self.hm_url_frame.pack_forget()
            if hasattr(self, 'yt_url_frame'):
                self.yt_url_frame.pack_forget()
    
    def create_highlight_finder_tab(self):
        """Create Highlight Finder configuration tab"""
        tab = self.provider_tabview.tab("🎯 Highlight Finder")
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Description
        desc_frame = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        desc_frame.pack(fill="x", pady=(10, 15), padx=10)
        
        ctk.CTkLabel(desc_frame, text="ℹ️ Highlight Finder", 
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(desc_frame, 
            text="AI model for analyzing video transcripts and finding viral moments. Recommended: GPT-4, GPT-4o, or compatible models.",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w", wraplength=450).pack(fill="x", padx=15, pady=(0, 12))
        
        # API Base URL (will be hidden for YT CLIP AI and OPEN AI)
        self.hf_url_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        # Don't pack yet, will be shown/hidden by _toggle_url_fields
        
        ctk.CTkLabel(self.hf_url_frame, text="API Base URL", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        self.hf_url_entry = ctk.CTkEntry(self.hf_url_frame, height=38,
            placeholder_text="https://api.openai.com/v1")
        self.hf_url_entry.pack(fill="x", pady=(5, 0))
        self.hf_url_entry.insert(0, "https://api.openai.com/v1")
        
        # API Key
        self.hf_key_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.hf_key_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(self.hf_key_frame, text="API Key", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        self.hf_key_entry = ctk.CTkEntry(self.hf_key_frame, height=38, show="*",
            placeholder_text="sk-...")
        self.hf_key_entry.pack(fill="x", pady=(5, 0))
        
        # Model
        model_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        model_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(model_frame, text="Model", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        
        model_select_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
        model_select_frame.pack(fill="x", pady=(5, 0))
        
        # Display current model
        self.hf_model_var = ctk.StringVar(value="gpt-4.1")
        self.hf_model_display = ctk.CTkLabel(model_select_frame, textvariable=self.hf_model_var,
            height=38, anchor="w", fg_color=("gray85", "gray20"), corner_radius=6,
            padx=12, font=ctk.CTkFont(size=13))
        self.hf_model_display.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Button to open model selector
        self.hf_select_model_btn = ctk.CTkButton(model_select_frame, text="📋 Select", width=100, height=38,
            fg_color="gray", command=self.open_hf_model_selector)
        self.hf_select_model_btn.pack(side="right", padx=(0, 10))
        
        self.hf_load_models_btn = ctk.CTkButton(model_select_frame, text="🔄 Load", width=100, height=38,
            fg_color="gray", command=self.load_hf_models)
        self.hf_load_models_btn.pack(side="right")
        
        # Store models list
        self.hf_models_list = []
        
        # Temperature
        temp_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        temp_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(temp_frame, text="Temperature", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(temp_frame, 
            text="Control AI creativity (0.0 = consistent, 2.0 = creative)",
            font=ctk.CTkFont(size=10), text_color="gray", anchor="w").pack(fill="x", pady=(2, 5))
        
        temp_slider_frame = ctk.CTkFrame(temp_frame, fg_color="transparent")
        temp_slider_frame.pack(fill="x", pady=(5, 0))
        
        self.temp_var = ctk.DoubleVar(value=1.0)
        self.temp_slider = ctk.CTkSlider(temp_slider_frame, from_=0.0, to=2.0, variable=self.temp_var, 
            command=self.update_temp_label, number_of_steps=20)
        self.temp_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.temp_label = ctk.CTkLabel(temp_slider_frame, text="1.0", width=40, anchor="e",
            font=ctk.CTkFont(size=13, weight="bold"))
        self.temp_label.pack(side="right")
        
        # System Prompt
        prompt_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        prompt_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(prompt_frame, text="System Prompt", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(prompt_frame, 
            text="Use {num_clips}, {video_context}, {transcript} as placeholders",
            font=ctk.CTkFont(size=10), text_color="gray", anchor="w").pack(fill="x", pady=(2, 5))
        
        self.prompt_text = ctk.CTkTextbox(prompt_frame, height=180, wrap="word")
        self.prompt_text.pack(fill="both", expand=True, pady=(5, 5))
        
        # Prompt buttons
        prompt_btn_frame = ctk.CTkFrame(prompt_frame, fg_color="transparent")
        prompt_btn_frame.pack(fill="x", pady=(5, 0))
        
        ctk.CTkButton(prompt_btn_frame, text="Reset to Default", width=130, height=32,
            fg_color="gray", command=self.reset_prompt).pack(side="left")
        
        self.prompt_char_count = ctk.CTkLabel(prompt_btn_frame, text="0 chars", 
            text_color="gray", font=ctk.CTkFont(size=10))
        self.prompt_char_count.pack(side="right")
        
        # Bind text change
        self.prompt_text.bind("<KeyRelease>", self.update_prompt_char_count)
        
        # Buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkButton(btn_frame, text="🔍 Validate Configuration", height=38,
            fg_color=("#3B8ED0", "#1F6AA5"), 
            command=self.validate_hf_config).pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkButton(btn_frame, text="📋 Apply URL & Key to All", height=38,
            fg_color="gray",
            command=lambda: self.apply_url_key_to_all_simple(self.hf_url_entry.get(), self.hf_key_entry.get())).pack(side="left", fill="x", expand=True, padx=(5, 0))
    
    def create_caption_maker_tab(self):
        """Create Caption Maker configuration tab"""
        tab = self.provider_tabview.tab("📝 Caption Maker")
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Description
        desc_frame = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        desc_frame.pack(fill="x", pady=(10, 15), padx=10)
        
        ctk.CTkLabel(desc_frame, text="ℹ️ Caption Maker", 
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(desc_frame, 
            text="Whisper model for generating word-level captions with precise timestamps. Recommended: whisper-1 or compatible models.",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w", wraplength=450).pack(fill="x", padx=15, pady=(0, 12))
        
        # API Base URL (will be hidden for YT CLIP AI and OPEN AI)
        self.cm_url_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        
        ctk.CTkLabel(self.cm_url_frame, text="API Base URL", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        self.cm_url_entry = ctk.CTkEntry(self.cm_url_frame, height=38,
            placeholder_text="https://api.openai.com/v1")
        self.cm_url_entry.pack(fill="x", pady=(5, 0))
        self.cm_url_entry.insert(0, "https://api.openai.com/v1")
        
        # API Key
        self.cm_key_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.cm_key_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(self.cm_key_frame, text="API Key", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        self.cm_key_entry = ctk.CTkEntry(self.cm_key_frame, height=38, show="*",
            placeholder_text="sk-...")
        self.cm_key_entry.pack(fill="x", pady=(5, 0))
        
        # Model
        model_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        model_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(model_frame, text="Model", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        self.cm_model_entry = ctk.CTkEntry(model_frame, height=38,
            placeholder_text="whisper-1")
        self.cm_model_entry.pack(fill="x", pady=(5, 0))
        
        # Buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkButton(btn_frame, text="🔍 Validate Configuration", height=38,
            fg_color=("#3B8ED0", "#1F6AA5"), 
            command=lambda: self.validate_provider_simple("caption_maker", self.cm_url_entry, self.cm_key_entry, self.cm_model_entry)).pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkButton(btn_frame, text="📋 Apply URL & Key to All", height=38,
            fg_color="gray",
            command=lambda: self.apply_url_key_to_all_simple(self.cm_url_entry.get(), self.cm_key_entry.get())).pack(side="left", fill="x", expand=True, padx=(5, 0))
    
    def create_hook_maker_tab(self):
        """Create Hook Maker configuration tab"""
        tab = self.provider_tabview.tab("🎤 Hook Maker")
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Description
        desc_frame = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        desc_frame.pack(fill="x", pady=(10, 15), padx=10)
        
        ctk.CTkLabel(desc_frame, text="ℹ️ Hook Maker", 
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(desc_frame, 
            text="TTS model for generating audio hooks with natural voice. Recommended: tts-1, tts-1-hd, or compatible models.",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w", wraplength=450).pack(fill="x", padx=15, pady=(0, 12))
        
        # API Base URL (will be hidden for YT CLIP AI and OPEN AI)
        self.hm_url_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        
        ctk.CTkLabel(self.hm_url_frame, text="API Base URL", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        self.hm_url_entry = ctk.CTkEntry(self.hm_url_frame, height=38,
            placeholder_text="https://api.openai.com/v1")
        self.hm_url_entry.pack(fill="x", pady=(5, 0))
        self.hm_url_entry.insert(0, "https://api.openai.com/v1")
        
        # API Key
        self.hm_key_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.hm_key_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(self.hm_key_frame, text="API Key", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        self.hm_key_entry = ctk.CTkEntry(self.hm_key_frame, height=38, show="*",
            placeholder_text="sk-...")
        self.hm_key_entry.pack(fill="x", pady=(5, 0))
        
        # Model
        model_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        model_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(model_frame, text="Model", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        self.hm_model_entry = ctk.CTkEntry(model_frame, height=38,
            placeholder_text="tts-1")
        self.hm_model_entry.pack(fill="x", pady=(5, 0))
        
        # Buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkButton(btn_frame, text="🔍 Validate Configuration", height=38,
            fg_color=("#3B8ED0", "#1F6AA5"), 
            command=lambda: self.validate_provider_simple("hook_maker", self.hm_url_entry, self.hm_key_entry, self.hm_model_entry)).pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkButton(btn_frame, text="📋 Apply URL & Key to All", height=38,
            fg_color="gray",
            command=lambda: self.apply_url_key_to_all_simple(self.hm_url_entry.get(), self.hm_key_entry.get())).pack(side="left", fill="x", expand=True, padx=(5, 0))
    
    def create_youtube_title_tab(self):
        """Create YouTube Title Maker configuration tab"""
        tab = self.provider_tabview.tab("📺 YouTube Title")
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Description
        desc_frame = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        desc_frame.pack(fill="x", pady=(10, 15), padx=10)
        
        ctk.CTkLabel(desc_frame, text="ℹ️ YouTube Title Maker", 
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(desc_frame, 
            text="AI model for generating SEO-optimized titles, descriptions, and tags. Recommended: GPT-4, GPT-4o, or compatible models.",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w", wraplength=450).pack(fill="x", padx=15, pady=(0, 12))
        
        # API Base URL (will be hidden for YT CLIP AI and OPEN AI)
        self.yt_url_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        
        ctk.CTkLabel(self.yt_url_frame, text="API Base URL", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        self.yt_url_entry = ctk.CTkEntry(self.yt_url_frame, height=38,
            placeholder_text="https://api.openai.com/v1")
        self.yt_url_entry.pack(fill="x", pady=(5, 0))
        self.yt_url_entry.insert(0, "https://api.openai.com/v1")
        
        # API Key
        self.yt_key_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.yt_key_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(self.yt_key_frame, text="API Key", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        self.yt_key_entry = ctk.CTkEntry(self.yt_key_frame, height=38, show="*",
            placeholder_text="sk-...")
        self.yt_key_entry.pack(fill="x", pady=(5, 0))
        
        # Model
        model_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        model_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(model_frame, text="Model", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        
        model_select_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
        model_select_frame.pack(fill="x", pady=(5, 0))
        
        # Display current model
        self.yt_model_var = ctk.StringVar(value="gpt-4.1")
        self.yt_model_display = ctk.CTkLabel(model_select_frame, textvariable=self.yt_model_var,
            height=38, anchor="w", fg_color=("gray85", "gray20"), corner_radius=6,
            padx=12, font=ctk.CTkFont(size=13))
        self.yt_model_display.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Button to open model selector
        self.yt_select_model_btn = ctk.CTkButton(model_select_frame, text="📋 Select", width=100, height=38,
            fg_color="gray", command=self.open_yt_model_selector)
        self.yt_select_model_btn.pack(side="right", padx=(0, 10))
        
        self.yt_load_models_btn = ctk.CTkButton(model_select_frame, text="🔄 Load", width=100, height=38,
            fg_color="gray", command=self.load_yt_models)
        self.yt_load_models_btn.pack(side="right")
        
        # Store models list
        self.yt_models_list = []
        
        # Buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkButton(btn_frame, text="🔍 Validate Configuration", height=38,
            fg_color=("#3B8ED0", "#1F6AA5"), 
            command=self.validate_yt_config).pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ctk.CTkButton(btn_frame, text="📋 Apply URL & Key to All", height=38,
            fg_color="gray",
            command=lambda: self.apply_url_key_to_all_simple(self.yt_url_entry.get(), self.yt_key_entry.get())).pack(side="left", fill="x", expand=True, padx=(5, 0))
    
    def create_performance_tab(self):
        """Create performance settings tab with GPU detection"""
        main = self.tabview.tab("Performance")
        
        # Scrollable frame
        scroll = ctk.CTkScrollableFrame(main)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header
        header_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(15, 10))
        
        ctk.CTkLabel(header_frame, text="Hardware Acceleration", 
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(header_frame, 
            text="Use GPU to speed up video processing. GPU encoding is 3-5x faster than CPU.",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w", wraplength=500).pack(fill="x", pady=(5, 0))
        
        # GPU Detection section
        detection_frame = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        detection_frame.pack(fill="x", padx=10, pady=(10, 15))
        
        ctk.CTkLabel(detection_frame, text="🔍 GPU Detection", 
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x", padx=15, pady=(15, 10))
        
        # GPU info display
        self.gpu_info_frame = ctk.CTkFrame(detection_frame, fg_color=("gray90", "gray15"), corner_radius=8)
        self.gpu_info_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.gpu_status_label = ctk.CTkLabel(self.gpu_info_frame, text="Detecting GPU...", 
            font=ctk.CTkFont(size=12), anchor="w", justify="left")
        self.gpu_status_label.pack(fill="x", padx=15, pady=15)
        
        # Detect button
        self.detect_gpu_btn = ctk.CTkButton(detection_frame, text="🔄 Detect GPU", height=38,
            fg_color=("#3B8ED0", "#1F6AA5"), command=self.detect_gpu)
        self.detect_gpu_btn.pack(fill="x", padx=15, pady=(0, 15))
        
        # GPU Acceleration toggle
        self.gpu_enabled_var = ctk.BooleanVar(value=False)
        
        toggle_frame = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        toggle_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(toggle_frame, text="⚡ GPU Acceleration", 
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x", padx=15, pady=(15, 10))
        
        self.gpu_switch = ctk.CTkSwitch(toggle_frame, text="Enable GPU Acceleration", 
            variable=self.gpu_enabled_var, font=ctk.CTkFont(size=13),
            command=self.toggle_gpu_acceleration, state="disabled")
        self.gpu_switch.pack(anchor="w", padx=15, pady=(0, 10))
        
        # Info about GPU acceleration
        info_text = ctk.CTkLabel(toggle_frame, 
            text="When enabled, video encoding will use your GPU instead of CPU.\n" +
                 "This significantly speeds up processing but requires compatible hardware.",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w", justify="left", wraplength=480)
        info_text.pack(fill="x", padx=15, pady=(0, 15))
        
        # Technical details section
        details_frame = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        details_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(details_frame, text="ℹ️ Technical Details", 
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(fill="x", padx=15, pady=(15, 10))
        
        self.encoder_info_label = ctk.CTkLabel(details_frame, 
            text="Encoder: Not detected\nPreset: N/A\nStatus: Click 'Detect GPU' to check",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w", justify="left")
        self.encoder_info_label.pack(fill="x", padx=15, pady=(0, 15))
        
        # Save button
        ctk.CTkButton(scroll, text="💾 Save Settings", height=45, 
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#27ae60", "#27ae60"), hover_color=("#229954", "#229954"),
            command=self.save_settings).pack(fill="x", padx=10, pady=(10, 15))
        
        # Auto-detect on load
        self.after(500, self.detect_gpu)
    
    def detect_gpu(self):
        """Detect GPU and update UI"""
        self.detect_gpu_btn.configure(state="disabled", text="Detecting...")
        
        def do_detect():
            try:
                from utils.gpu_detector import GPUDetector
                detector = GPUDetector()
                
                # Detect GPU
                gpu_info = detector.detect_gpu()
                recommendation = detector.get_recommended_encoder()
                
                self.after(0, lambda g=gpu_info, r=recommendation: self._on_gpu_detected(g, r))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda err=error_msg: self._on_gpu_detect_error(err))
        
        threading.Thread(target=do_detect, daemon=True).start()
    
    def _on_gpu_detected(self, gpu_info, recommendation):
        """Handle GPU detection result"""
        self.detect_gpu_btn.configure(state="normal", text="🔄 Detect GPU")
        
        if gpu_info['available']:
            # GPU found
            gpu_type_emoji = {
                'nvidia': '🟢',
                'amd': '🔴',
                'intel': '🔵'
            }
            emoji = gpu_type_emoji.get(gpu_info['type'], '⚪')
            
            status_text = f"{emoji} GPU Detected\n\n"
            status_text += f"Name: {gpu_info['name']}\n"
            status_text += f"Type: {gpu_info['type'].upper()}"
            
            self.gpu_status_label.configure(text=status_text, text_color=("green", "lightgreen"))
            
            # Update encoder info
            if recommendation['available']:
                encoder_text = f"Encoder: {recommendation['encoder']}\n"
                encoder_text += f"Preset: {recommendation['preset']}\n"
                encoder_text += f"Status: ✓ Ready to use"
                self.encoder_info_label.configure(text=encoder_text, text_color=("green", "lightgreen"))
                
                # Enable GPU switch
                self.gpu_switch.configure(state="normal")
            else:
                encoder_text = f"Encoder: Not available\n"
                encoder_text += f"Reason: {recommendation['reason']}"
                self.encoder_info_label.configure(text=encoder_text, text_color=("orange", "yellow"))
                
                # Disable GPU switch
                self.gpu_switch.configure(state="disabled")
                self.gpu_enabled_var.set(False)
        else:
            # No GPU found
            status_text = "⚪ No GPU Detected\n\n"
            status_text += "No compatible GPU found on this system.\n"
            status_text += "Video processing will use CPU."
            
            self.gpu_status_label.configure(text=status_text, text_color="gray")
            
            # Update encoder info
            encoder_text = "Encoder: libx264 (CPU)\n"
            encoder_text += "Preset: fast\n"
            encoder_text += "Status: Using CPU encoding"
            self.encoder_info_label.configure(text=encoder_text, text_color="gray")
            
            # Disable GPU switch
            self.gpu_switch.configure(state="disabled")
            self.gpu_enabled_var.set(False)
    
    def _on_gpu_detect_error(self, error):
        """Handle GPU detection error"""
        self.detect_gpu_btn.configure(state="normal", text="🔄 Detect GPU")
        
        status_text = "❌ Detection Error\n\n"
        status_text += f"Error: {error}"
        
        self.gpu_status_label.configure(text=status_text, text_color=("red", "orange"))
        
        # Disable GPU switch
        self.gpu_switch.configure(state="disabled")
        self.gpu_enabled_var.set(False)
    
    def toggle_gpu_acceleration(self):
        """Handle GPU acceleration toggle"""
        if self.gpu_enabled_var.get():
            # Enabled
            messagebox.showinfo("GPU Acceleration Enabled", 
                "GPU acceleration is now enabled.\n\n" +
                "Video processing will use your GPU for faster encoding.\n\n" +
                "Don't forget to click 'Save Settings' to apply changes.")
        else:
            # Disabled
            messagebox.showinfo("GPU Acceleration Disabled", 
                "GPU acceleration is now disabled.\n\n" +
                "Video processing will use CPU encoding.\n\n" +
                "Don't forget to click 'Save Settings' to apply changes.")
    
    def create_output_tab(self):
        """Create output folder settings tab"""
        main = self.tabview.tab("Output")
        
        ctk.CTkLabel(main, text="Output Folder", anchor="w", font=ctk.CTkFont(size=14, weight="bold")).pack(fill="x", pady=(15, 5))
        ctk.CTkLabel(main, text="Folder where video clips will be saved", anchor="w", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(fill="x", pady=(0, 10))
        
        output_frame = ctk.CTkFrame(main, fg_color="transparent")
        output_frame.pack(fill="x", pady=(5, 15))
        self.output_var = ctk.StringVar(value=str(self.output_dir))
        self.output_entry = ctk.CTkEntry(output_frame, textvariable=self.output_var)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(output_frame, text="Browse", width=100, command=self.browse_output_folder).pack(side="right")
        
        # Open folder button
        ctk.CTkButton(main, text="Open Output Folder", height=40, fg_color="gray",
            command=lambda: self.open_folder(self.output_var.get())).pack(fill="x", pady=(0, 15))
        
        # Face Tracking Mode section
        ctk.CTkLabel(main, text="Face Tracking Mode", anchor="w", font=ctk.CTkFont(size=14, weight="bold")).pack(fill="x", pady=(15, 5))
        ctk.CTkLabel(main, text="Choose how the video crops to speakers", anchor="w", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(fill="x", pady=(0, 10))
        
        # Radio buttons for face tracking mode
        self.face_tracking_var = ctk.StringVar(value="opencv")
        
        opencv_frame = ctk.CTkFrame(main, fg_color=("gray85", "gray20"))
        opencv_frame.pack(fill="x", pady=(5, 10))
        opencv_radio = ctk.CTkRadioButton(opencv_frame, text="OpenCV (Fast)", variable=self.face_tracking_var, 
            value="opencv", font=ctk.CTkFont(size=13, weight="bold"))
        opencv_radio.pack(anchor="w", padx=15, pady=(10, 5))
        ctk.CTkLabel(opencv_frame, text="• Crop to largest face", anchor="w", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=35, pady=0)
        ctk.CTkLabel(opencv_frame, text="• Faster processing", anchor="w", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=35, pady=0)
        ctk.CTkLabel(opencv_frame, text="• Recommended for most users", anchor="w", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=35, pady=(0, 10))
        
        mediapipe_frame = ctk.CTkFrame(main, fg_color=("gray85", "gray20"))
        mediapipe_frame.pack(fill="x", pady=(0, 10))
        mediapipe_radio = ctk.CTkRadioButton(mediapipe_frame, text="MediaPipe (Smart)", variable=self.face_tracking_var, 
            value="mediapipe", font=ctk.CTkFont(size=13, weight="bold"))
        mediapipe_radio.pack(anchor="w", padx=15, pady=(10, 5))
        ctk.CTkLabel(mediapipe_frame, text="• Crop to active speaker (lip movement)", anchor="w", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=35, pady=0)
        ctk.CTkLabel(mediapipe_frame, text="• More accurate speaker tracking", anchor="w", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=35, pady=0)
        ctk.CTkLabel(mediapipe_frame, text="⚠ Slower processing (2-3x)", anchor="w", 
            font=ctk.CTkFont(size=11), text_color="orange").pack(anchor="w", padx=35, pady=(0, 10))
        
        ctk.CTkButton(main, text="Save Settings", height=40, command=self.save_settings).pack(fill="x", pady=(10, 0))
    
    def create_watermark_tab(self):
        """Create watermark settings tab"""
        main = self.tabview.tab("Watermark")
        
        # Scrollable frame
        scroll = ctk.CTkScrollableFrame(main)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Enable watermark toggle
        self.watermark_enabled = ctk.BooleanVar(value=False)
        enable_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        enable_frame.pack(fill="x", pady=(10, 15))
        
        ctk.CTkSwitch(enable_frame, text="Enable Watermark", variable=self.watermark_enabled,
            font=ctk.CTkFont(size=14, weight="bold"), command=self.toggle_watermark).pack(side="left")
        
        # Watermark settings container
        self.watermark_settings_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.watermark_settings_frame.pack(fill="both", expand=True)
        
        # Image selection
        ctk.CTkLabel(self.watermark_settings_frame, text="Watermark Image", anchor="w", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(fill="x", pady=(5, 5))
        
        image_frame = ctk.CTkFrame(self.watermark_settings_frame, fg_color="transparent")
        image_frame.pack(fill="x", pady=(5, 15))
        
        self.watermark_path_var = ctk.StringVar(value="")
        self.watermark_path_entry = ctk.CTkEntry(image_frame, textvariable=self.watermark_path_var, 
            placeholder_text="Select PNG image...")
        self.watermark_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(image_frame, text="Browse", width=100, command=self.browse_watermark).pack(side="right")
        
        # Position simulator
        ctk.CTkLabel(self.watermark_settings_frame, text="Position", anchor="w", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(fill="x", pady=(10, 5))
        ctk.CTkLabel(self.watermark_settings_frame, text="Drag the watermark to position it on the video", 
            anchor="w", font=ctk.CTkFont(size=11), text_color="gray").pack(fill="x", pady=(0, 10))
        
        # Canvas for 9:16 simulator
        self.canvas_frame = ctk.CTkFrame(self.watermark_settings_frame, fg_color=("gray85", "gray20"))
        self.canvas_frame.pack(fill="x", pady=(5, 15))
        
        import tkinter as tk
        self.canvas = tk.Canvas(self.canvas_frame, width=270, height=480, bg="#1a1a1a", 
            highlightthickness=1, highlightbackground="gray")
        self.canvas.pack(padx=10, pady=10)
        
        # Draw 9:16 frame
        self.canvas.create_rectangle(0, 0, 270, 480, outline="gray", width=2)
        self.canvas.create_text(135, 240, text="9:16 Video Preview", fill="gray50", 
            font=("Arial", 12))
        
        # Watermark placeholder
        self.watermark_item = None
        self.watermark_x = ctk.DoubleVar(value=0.85)
        self.watermark_y = ctk.DoubleVar(value=0.05)
        
        # Bind drag events
        self.canvas.bind("<Button-1>", self.on_watermark_click)
        self.canvas.bind("<B1-Motion>", self.on_watermark_drag)
        
        # Opacity slider
        ctk.CTkLabel(self.watermark_settings_frame, text="Opacity", anchor="w", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(fill="x", pady=(10, 5))
        
        opacity_frame = ctk.CTkFrame(self.watermark_settings_frame, fg_color="transparent")
        opacity_frame.pack(fill="x", pady=(5, 15))
        
        self.watermark_opacity = ctk.DoubleVar(value=0.8)
        opacity_slider = ctk.CTkSlider(opacity_frame, from_=0.0, to=1.0, variable=self.watermark_opacity,
            command=self.update_watermark_preview, number_of_steps=20)
        opacity_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.opacity_label = ctk.CTkLabel(opacity_frame, text="80%", width=50, anchor="e")
        self.opacity_label.pack(side="right")
        
        # Scale slider
        ctk.CTkLabel(self.watermark_settings_frame, text="Size", anchor="w", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(fill="x", pady=(10, 5))
        
        scale_frame = ctk.CTkFrame(self.watermark_settings_frame, fg_color="transparent")
        scale_frame.pack(fill="x", pady=(5, 15))
        
        self.watermark_scale = ctk.DoubleVar(value=0.15)
        scale_slider = ctk.CTkSlider(scale_frame, from_=0.05, to=0.5, variable=self.watermark_scale,
            command=self.update_watermark_preview, number_of_steps=45)
        scale_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.scale_label = ctk.CTkLabel(scale_frame, text="15%", width=50, anchor="e")
        self.scale_label.pack(side="right")
        
        # Save button
        ctk.CTkButton(scroll, text="Save Settings", height=40, command=self.save_settings).pack(fill="x", pady=(10, 0))
        
        # Initially disable watermark settings
        self.toggle_watermark()
    
    def toggle_watermark(self):
        """Toggle watermark settings visibility"""
        if self.watermark_enabled.get():
            # Enable all child widgets recursively
            self._set_children_state(self.watermark_settings_frame, "normal")
        else:
            # Disable all child widgets recursively
            self._set_children_state(self.watermark_settings_frame, "disabled")
    
    def _set_children_state(self, widget, state):
        """Recursively set state for all children widgets"""
        for child in widget.winfo_children():
            widget_type = child.winfo_class()
            
            # Skip frames and labels (they don't have state)
            if widget_type in ('Frame', 'Label', 'Canvas'):
                # Recursively process children of frames
                if widget_type == 'Frame':
                    self._set_children_state(child, state)
                continue
            
            # Try to set state for widgets that support it
            try:
                if hasattr(child, 'configure'):
                    child.configure(state=state)
            except Exception:
                # If widget doesn't support state, try its children
                try:
                    self._set_children_state(child, state)
                except:
                    pass
    
    def browse_watermark(self):
        """Browse for watermark image and copy to app folder"""
        from tkinter import filedialog
        import shutil
        
        file_path = filedialog.askopenfilename(
            title="Select Watermark Image",
            filetypes=[("PNG Images", "*.png"), ("All Images", "*.png *.jpg *.jpeg")]
        )
        if file_path:
            try:
                # Create watermarks folder if not exists
                watermarks_dir = Path("assets/watermarks")
                watermarks_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate unique filename
                original_name = Path(file_path).stem
                extension = Path(file_path).suffix
                dest_filename = f"watermark_{original_name}{extension}"
                dest_path = watermarks_dir / dest_filename
                
                # If file already exists, add number suffix
                counter = 1
                while dest_path.exists():
                    dest_filename = f"watermark_{original_name}_{counter}{extension}"
                    dest_path = watermarks_dir / dest_filename
                    counter += 1
                
                # Copy file to app folder
                shutil.copy2(file_path, dest_path)
                
                # Save the new path
                self.watermark_path_var.set(str(dest_path))
                self.update_watermark_preview()
                
                self.log(f"Watermark copied to: {dest_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to copy watermark: {str(e)}")
    
    def log(self, message: str):
        """Log message (helper method)"""
        print(message)
    
    def update_watermark_preview(self, *args):
        """Update watermark preview on canvas"""
        # Update labels
        opacity_percent = int(self.watermark_opacity.get() * 100)
        self.opacity_label.configure(text=f"{opacity_percent}%")
        
        scale_percent = int(self.watermark_scale.get() * 100)
        self.scale_label.configure(text=f"{scale_percent}%")
        
        # Update canvas preview
        if self.watermark_item:
            self.canvas.delete(self.watermark_item)
            self.watermark_item = None
        
        watermark_path = self.watermark_path_var.get()
        if not watermark_path or not Path(watermark_path).exists():
            return
        
        try:
            from PIL import Image, ImageTk
            
            # Load and resize watermark
            img = Image.open(watermark_path)
            
            # Calculate size based on scale (relative to canvas width)
            canvas_width = 270
            watermark_width = int(canvas_width * self.watermark_scale.get())
            aspect_ratio = img.height / img.width
            watermark_height = int(watermark_width * aspect_ratio)
            
            img = img.resize((watermark_width, watermark_height), Image.Resampling.LANCZOS)
            
            # Apply opacity
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            alpha = img.split()[3]
            alpha = alpha.point(lambda p: int(p * self.watermark_opacity.get()))
            img.putalpha(alpha)
            
            # Keep reference to prevent garbage collection
            self.watermark_photo = ImageTk.PhotoImage(img)
            
            # Calculate position
            x = int(self.watermark_x.get() * 270)
            y = int(self.watermark_y.get() * 480)
            
            # Draw on canvas
            self.watermark_item = self.canvas.create_image(x, y, image=self.watermark_photo, anchor="nw")
            
        except Exception as e:
            print(f"Error loading watermark preview: {e}")
    
    def on_watermark_click(self, event):
        """Handle watermark click"""
        if not self.watermark_item:
            return
        
        # Check if click is on watermark
        bbox = self.canvas.bbox(self.watermark_item)
        if bbox and bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
            self.dragging = True
            self.drag_offset_x = event.x - bbox[0]
            self.drag_offset_y = event.y - bbox[1]
    
    def on_watermark_drag(self, event):
        """Handle watermark drag"""
        if not hasattr(self, 'dragging') or not self.dragging:
            return
        
        # Calculate new position (constrained to canvas)
        new_x = max(0, min(event.x - self.drag_offset_x, 270 - 50))
        new_y = max(0, min(event.y - self.drag_offset_y, 480 - 50))
        
        # Update position variables (as percentage)
        self.watermark_x.set(new_x / 270)
        self.watermark_y.set(new_y / 480)
        
        # Redraw
        self.update_watermark_preview()
    
    def create_repliz_tab(self):
        """Create Repliz integration tab"""
        main = self.tabview.tab("Repliz")
        
        # Scrollable frame for content
        scroll = ctk.CTkScrollableFrame(main)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header description
        header_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(header_frame, text="🚀 Repliz Integration", 
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(header_frame, 
            text="Multi-platform video scheduling made easy. Upload to YouTube, TikTok, Instagram Reels, and Facebook from one place.",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w", wraplength=500).pack(fill="x", pady=(5, 0))
        
        # Why Repliz card
        why_card = ctk.CTkFrame(scroll, fg_color=("#e8f5e9", "#1b5e20"), corner_radius=10)
        why_card.pack(fill="x", padx=10, pady=(10, 15))
        
        ctk.CTkLabel(why_card, text="✨ Why Use Repliz?", 
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=15, pady=(15, 10))
        
        why_text = """• Upload to ALL platforms at once (YouTube, TikTok, Instagram, Facebook)
• Official API integration - safe from bans
• No need for complex Google Console or TikTok Developer setup
• Schedule posts in advance across all platforms
• Affordable: Only $1.74/month (29,000 IDR) for Premium plan

Perfect for content creators who want to save time and reach more audiences!"""
        
        ctk.CTkLabel(why_card, text=why_text, justify="left", anchor="w",
            font=ctk.CTkFont(size=11), wraplength=480).pack(fill="x", padx=15, pady=(0, 15))
        
        # Sign up CTA (for users without account)
        signup_frame = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        signup_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(signup_frame, text="🎯 Don't Have a Repliz Account Yet?", 
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(signup_frame, 
            text="Sign up now and get started with multi-platform scheduling. Premium plan required for API access.",
            justify="left", anchor="w", font=ctk.CTkFont(size=11), text_color="gray", wraplength=480).pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkButton(signup_frame, text="🌐 Sign Up for Repliz", height=40,
            fg_color=("#2196F3", "#1976D2"), hover_color=("#1976D2", "#1565C0"),
            command=lambda: self.open_url("https://s.id/ytrepliz")).pack(fill="x", padx=15, pady=(0, 15))
        
        # Configuration section
        config_section = ctk.CTkFrame(scroll, fg_color=("gray90", "gray17"), corner_radius=10)
        config_section.pack(fill="x", padx=10, pady=(0, 15))
        
        # Section header with status
        config_header = ctk.CTkFrame(config_section, fg_color="transparent")
        config_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(config_header, text="API Configuration", 
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(side="left")
        
        self.repliz_status_label = ctk.CTkLabel(config_header, text="Not configured", text_color="gray",
            font=ctk.CTkFont(size=11))
        self.repliz_status_label.pack(side="right")
        
        # Access Key
        access_frame = ctk.CTkFrame(config_section, fg_color="transparent")
        access_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(access_frame, text="Access Key", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(access_frame, text="Your Repliz API Access Key", 
            font=ctk.CTkFont(size=10), text_color="gray", anchor="w").pack(fill="x", pady=(2, 5))
        
        self.repliz_access_key_entry = ctk.CTkEntry(access_frame, height=38,
            placeholder_text="Enter your Repliz Access Key")
        self.repliz_access_key_entry.pack(fill="x", pady=(0, 0))
        
        # Secret Key
        secret_frame = ctk.CTkFrame(config_section, fg_color="transparent")
        secret_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(secret_frame, text="Secret Key", 
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(secret_frame, text="Your Repliz API Secret Key (kept secure)", 
            font=ctk.CTkFont(size=10), text_color="gray", anchor="w").pack(fill="x", pady=(2, 5))
        
        self.repliz_secret_key_entry = ctk.CTkEntry(secret_frame, height=38, show="*",
            placeholder_text="Enter your Repliz Secret Key")
        self.repliz_secret_key_entry.pack(fill="x", pady=(0, 0))
        
        # Buttons
        btn_frame = ctk.CTkFrame(config_section, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.repliz_validate_btn = ctk.CTkButton(btn_frame, text="🔍 Validate Keys", height=40,
            fg_color=("#3B8ED0", "#1F6AA5"), hover_color=("#36719F", "#144870"),
            command=self.validate_repliz_keys)
        self.repliz_validate_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.repliz_save_btn = ctk.CTkButton(btn_frame, text="💾 Save Configuration", height=40,
            fg_color=("#27ae60", "#27ae60"), hover_color=("#229954", "#229954"),
            command=self.save_repliz_config)
        self.repliz_save_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        # Connected Accounts section (initially hidden)
        self.repliz_accounts_section = ctk.CTkFrame(scroll, fg_color=("gray90", "gray17"), corner_radius=10)
        # Don't pack yet - will be shown after successful validation
        
        accounts_header = ctk.CTkFrame(self.repliz_accounts_section, fg_color="transparent")
        accounts_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(accounts_header, text="📱 Connected Social Media Accounts", 
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(side="left")
        
        self.repliz_accounts_count = ctk.CTkLabel(accounts_header, text="0 accounts", text_color="gray",
            font=ctk.CTkFont(size=11))
        self.repliz_accounts_count.pack(side="right")
        
        # Grid frame for accounts cards (non-scrollable)
        self.repliz_accounts_list = ctk.CTkFrame(self.repliz_accounts_section, 
            fg_color="transparent")
        self.repliz_accounts_list.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # How to get keys section
        howto_section = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        howto_section.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(howto_section, text="📖 How to Get API Keys", 
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", padx=15, pady=(15, 10))
        
        howto_text = """1. Log in to your Repliz account at https://repliz.com
2. Go to Settings → Public API
3. Generate your Access Key and Secret Key
4. Copy both keys and paste them above
5. Click "Validate Keys" to verify the connection
6. Click "Save Configuration" to save

Requirements:
• Premium plan subscription ($1.74/month or 29,000 IDR)
• At least one social media account connected in Repliz dashboard

Note: Keep your Secret Key secure and never share it publicly."""
        
        ctk.CTkLabel(howto_section, text=howto_text, justify="left", anchor="w",
            font=ctk.CTkFont(size=11), text_color="gray", wraplength=480).pack(fill="x", padx=15, pady=(0, 15))
        
        # Open Repliz dashboard button
        ctk.CTkButton(howto_section, text="🌐 Open Repliz Dashboard", height=38,
            fg_color="gray", hover_color=("gray70", "gray30"),
            command=lambda: self.open_url("https://repliz.com")).pack(fill="x", padx=15, pady=(0, 15))
        
        # Check status on load
        self.check_repliz_status()
    
    def create_social_accounts_tab(self):
        """Create Social Accounts settings tab with YouTube and TikTok"""
        main = self.tabview.tab("Social Accounts")
        
        # Scrollable frame for content
        scroll = ctk.CTkScrollableFrame(main)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header description
        header_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(header_frame, text="Social Accounts", 
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(header_frame, 
            text="Connect your social media accounts to upload clips directly from the app.",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w", wraplength=500).pack(fill="x", pady=(5, 0))
        
        # ===== YOUTUBE SECTION =====
        youtube_section = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        youtube_section.pack(fill="x", padx=10, pady=(10, 15))
        
        # YouTube header
        yt_header = ctk.CTkFrame(youtube_section, fg_color="transparent")
        yt_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(yt_header, text="📺 YouTube", 
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(side="left")
        
        # YouTube status
        self.yt_status_label = ctk.CTkLabel(yt_header, text="Not connected", text_color="gray",
            font=ctk.CTkFont(size=11))
        self.yt_status_label.pack(side="right")
        
        # YouTube buttons
        yt_btn_frame = ctk.CTkFrame(youtube_section, fg_color="transparent")
        yt_btn_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.yt_connect_btn = ctk.CTkButton(yt_btn_frame, text="Connect YouTube", height=40, 
            fg_color=("#c4302b", "#FF0000"), hover_color=("#ff0000", "#CC0000"),
            command=self.connect_youtube)
        self.yt_connect_btn.pack(fill="x", pady=(0, 5))
        
        self.yt_disconnect_btn = ctk.CTkButton(yt_btn_frame, text="Disconnect", height=35,
            fg_color="gray", hover_color="#c0392b", command=self.disconnect_youtube)
        self.yt_disconnect_btn.pack(fill="x")
        self.yt_disconnect_btn.pack_forget()  # Hide initially
        
        # YouTube info
        yt_info_frame = ctk.CTkFrame(youtube_section, fg_color=("gray90", "gray17"), corner_radius=6)
        yt_info_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        yt_info_text = """ℹ️ YouTube Setup:
1. Set up Google Cloud project
2. Enable YouTube Data API v3
3. Create OAuth credentials
4. Place client_secret.json in app folder

See README for detailed setup guide."""
        
        ctk.CTkLabel(yt_info_frame, text=yt_info_text, justify="left", anchor="w",
            font=ctk.CTkFont(size=10), text_color="gray", wraplength=450).pack(padx=12, pady=12)
        
        # ===== TIKTOK SECTION (COMING SOON) =====
        tiktok_section = ctk.CTkFrame(scroll, fg_color=("gray85", "gray20"), corner_radius=10)
        tiktok_section.pack(fill="x", padx=10, pady=(0, 15))
        
        # TikTok header
        tt_header = ctk.CTkFrame(tiktok_section, fg_color="transparent")
        tt_header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(tt_header, text="🎵 TikTok", 
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(side="left")
        
        ctk.CTkLabel(tt_header, text="🚧 Coming Soon", 
            text_color="orange", font=ctk.CTkFont(size=11, weight="bold")).pack(side="right")
        
        # Coming Soon message
        coming_soon_frame = ctk.CTkFrame(tiktok_section, fg_color=("gray90", "gray17"))
        coming_soon_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        coming_soon_text = """🚧 TikTok Upload - Coming Soon

TikTok direct upload feature is currently under development.

Why disabled?
• TikTok API requires backend server for security
• Sandbox mode has strict limitations (private accounts only)
• We're working on a proper solution

Alternative:
For now, you can use Repliz integration (see Repliz tab) to upload 
to TikTok, or manually download your processed videos and upload 
them to TikTok app directly.

Stay tuned for updates! 🎵"""
        
        ctk.CTkLabel(coming_soon_frame, text=coming_soon_text, justify="left", anchor="w",
            font=ctk.CTkFont(size=11), text_color="gray", wraplength=450).pack(padx=15, pady=15)
        
        # Check YouTube status
        self.check_youtube_status()
    
    def check_youtube_status(self):
        """Check if YouTube is configured and connected"""
        try:
            from youtube_uploader import YouTubeUploader
            self.youtube_uploader = YouTubeUploader()
            
            if not self.youtube_uploader.is_configured():
                self.yt_status_label.configure(text="⚠️ client_secret.json not found", text_color="orange")
                self.yt_connect_btn.configure(state="disabled")
                return
            
            if self.youtube_uploader.is_authenticated():
                channel = self.youtube_uploader.get_channel_info()
                if channel:
                    self.yt_status_label.configure(
                        text=f"✓ Connected: {channel['title']}", 
                        text_color="green"
                    )
                    self.yt_connect_btn.pack_forget()
                    self.yt_disconnect_btn.pack(fill="x", padx=10, pady=(0, 10))
                    return
            
            self.yt_status_label.configure(text="Not connected", text_color="gray")
            self.yt_connect_btn.configure(state="normal")
            
        except ImportError:
            self.yt_status_label.configure(text="⚠️ YouTube module not available", text_color="orange")
            self.yt_connect_btn.configure(state="disabled")
        except Exception as e:
            self.yt_status_label.configure(text=f"Error: {str(e)[:30]}", text_color="red")
    
    def connect_youtube(self):
        """Start YouTube OAuth flow"""
        self.yt_connect_btn.configure(state="disabled", text="Connecting...")
        
        def do_connect():
            try:
                self.youtube_uploader.authenticate(callback=self.on_youtube_connected)
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda err=error_msg: self.on_youtube_error(err))
        
        threading.Thread(target=do_connect, daemon=True).start()
    
    def on_youtube_connected(self, success, data):
        """Callback when YouTube connection completes"""
        if success:
            self.after(0, lambda d=data: self._update_youtube_connected(d))
        else:
            error_msg = str(data)
            self.after(0, lambda err=error_msg: self.on_youtube_error(err))
    
    def _update_youtube_connected(self, channel):
        """Update UI after YouTube connection"""
        if channel and channel.get('title'):
            self.yt_status_label.configure(
                text=f"✓ Connected: {channel['title']}", 
                text_color="green"
            )
            self.yt_connect_btn.pack_forget()
            self.yt_disconnect_btn.pack(fill="x", padx=10, pady=(0, 10))
            # Update main app status
            if hasattr(self.master, 'master') and hasattr(self.master.master, 'update_connection_status'):
                self.master.master.update_connection_status()
            messagebox.showinfo("Success", f"Connected to YouTube channel: {channel['title']}")
        else:
            # Channel info not available but auth succeeded
            self.yt_status_label.configure(
                text="✓ Connected", 
                text_color="green"
            )
            self.yt_connect_btn.pack_forget()
            self.yt_disconnect_btn.pack(fill="x", padx=10, pady=(0, 10))
            if hasattr(self.master, 'master') and hasattr(self.master.master, 'update_connection_status'):
                self.master.master.update_connection_status()
            messagebox.showinfo("Success", "Connected to YouTube!")
    
    def on_youtube_error(self, error):
        """Handle YouTube connection error"""
        self.yt_status_label.configure(text="Connection failed", text_color="red")
        self.yt_connect_btn.configure(state="normal", text="🔗 Connect YouTube")
        messagebox.showerror("Error", f"Failed to connect: {error}")
    
    def disconnect_youtube(self):
        """Disconnect YouTube account"""
        if messagebox.askyesno("Disconnect", "Are you sure you want to disconnect YouTube?"):
            if self.youtube_uploader:
                self.youtube_uploader.disconnect()
            self.yt_status_label.configure(text="Not connected", text_color="gray")
            self.yt_disconnect_btn.pack_forget()
            self.yt_connect_btn.configure(state="normal", text="Connect YouTube")
            self.yt_connect_btn.pack(fill="x", pady=(0, 5))
            # Update main app status
            if hasattr(self.master, 'master') and hasattr(self.master.master, 'update_connection_status'):
                self.master.master.update_connection_status()
    
    def check_repliz_status(self):
        """Check if Repliz is configured"""
        repliz_config = self.config.get("repliz", {})
        access_key = repliz_config.get("access_key", "")
        secret_key = repliz_config.get("secret_key", "")
        
        if access_key and secret_key:
            self.repliz_status_label.configure(text="✓ Configured", text_color="green")
            # Load keys into entry fields
            self.repliz_access_key_entry.delete(0, "end")
            self.repliz_access_key_entry.insert(0, access_key)
            self.repliz_secret_key_entry.delete(0, "end")
            self.repliz_secret_key_entry.insert(0, secret_key)
            
            # Auto-load accounts if keys are configured
            self.load_repliz_accounts_silent()
        else:
            self.repliz_status_label.configure(text="Not configured", text_color="gray")
    
    def load_repliz_accounts_silent(self):
        """Silently load Repliz accounts in background (no popup)"""
        access_key = self.repliz_access_key_entry.get().strip()
        secret_key = self.repliz_secret_key_entry.get().strip()
        
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
                    self.after(0, lambda d=data: self._display_accounts_only(d))
                    
            except Exception:
                # Silently fail - don't show error on auto-load
                pass
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def _display_accounts_only(self, data):
        """Display accounts without showing success popup"""
        total_accounts = data.get("totalDocs", 0)
        accounts = data.get("docs", [])
        
        # Update accounts count
        self.repliz_accounts_count.configure(text=f"{total_accounts} account(s)")
        
        # Clear existing accounts list
        for widget in self.repliz_accounts_list.winfo_children():
            widget.destroy()
        
        if total_accounts > 0:
            # Show accounts section
            self.repliz_accounts_section.pack(fill="x", padx=10, pady=(0, 15))
            
            # Display each account in grid
            for idx, account in enumerate(accounts):
                self._create_account_card(account, idx)
        else:
            # Hide accounts section if no accounts
            self.repliz_accounts_section.pack_forget()
    
    def validate_repliz_keys(self):
        """Validate Repliz API keys by calling /public/account endpoint"""
        access_key = self.repliz_access_key_entry.get().strip()
        secret_key = self.repliz_secret_key_entry.get().strip()
        
        if not access_key or not secret_key:
            messagebox.showerror("Error", "Please enter both Access Key and Secret Key")
            return
        
        self.repliz_validate_btn.configure(state="disabled", text="Validating...")
        self.repliz_status_label.configure(text="Validating...", text_color="yellow")
        
        def do_validate():
            try:
                import requests
                from requests.auth import HTTPBasicAuth
                
                # Call Repliz API /public/account endpoint with required pagination params
                url = "https://api.repliz.com/public/account"
                params = {
                    "page": 1,
                    "limit": 1  # Only need 1 result to validate
                }
                
                # Use Basic Authentication with Access Key as username and Secret Key as password
                response = requests.get(
                    url, 
                    params=params,
                    auth=HTTPBasicAuth(access_key, secret_key),
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.after(0, lambda d=data: self._on_repliz_validate_success(d))
                else:
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", error_msg)
                    except:
                        if response.status_code == 401:
                            error_msg = "invalid authorization header"
                        pass
                    err = error_msg
                    self.after(0, lambda e=err: self._on_repliz_validate_error(e))
                    
            except requests.exceptions.Timeout:
                self.after(0, lambda: self._on_repliz_validate_error("Request timeout"))
            except requests.exceptions.ConnectionError:
                self.after(0, lambda: self._on_repliz_validate_error("Connection error"))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda err=error_msg: self._on_repliz_validate_error(err))
        
        threading.Thread(target=do_validate, daemon=True).start()
    
    def _on_repliz_validate_success(self, data):
        """Handle successful Repliz validation"""
        self.repliz_validate_btn.configure(state="normal", text="🔍 Validate Keys")
        self.repliz_status_label.configure(text="✓ Valid", text_color="green")
        
        # Extract account info from response
        total_accounts = data.get("totalDocs", 0)
        accounts = data.get("docs", [])
        
        # Update accounts count
        self.repliz_accounts_count.configure(text=f"{total_accounts} account(s)")
        
        # Clear existing accounts list
        for widget in self.repliz_accounts_list.winfo_children():
            widget.destroy()
        
        if total_accounts > 0:
            # Show accounts section
            self.repliz_accounts_section.pack(fill="x", padx=10, pady=(0, 15))
            
            # Display each account in grid
            for idx, account in enumerate(accounts):
                self._create_account_card(account, idx)
            
            info_msg = f"✓ API Keys validated successfully!\n\nYou have {total_accounts} connected account(s)."
        else:
            # Hide accounts section if no accounts
            self.repliz_accounts_section.pack_forget()
            
            # No accounts connected yet, but API keys are valid
            info_msg = "✓ API Keys validated successfully!\n\nYou don't have any connected social media accounts yet.\n\nGo to Repliz dashboard to connect your accounts."
        
        messagebox.showinfo("Success", info_msg)
    
    def _create_account_card(self, account, index):
        """Create a grid card for displaying account info with profile picture"""
        # Platform icon and name
        platform_type = account.get("type", "unknown")
        platform_icons = {
            "youtube": "📺",
            "tiktok": "🎵",
            "instagram": "📸",
            "threads": "🧵",
            "facebook": "👥"
        }
        icon = platform_icons.get(platform_type, "🔗")
        
        # Calculate grid position (3 columns)
        row = index // 3
        col = index % 3
        
        # Create card with fixed width for grid layout
        card = ctk.CTkFrame(self.repliz_accounts_list, fg_color=("gray95", "gray25"), 
            corner_radius=10, width=160, height=200)
        card.pack_propagate(False)  # Prevent card from shrinking
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        
        # Profile picture frame (circular)
        picture_url = account.get("picture", "")
        
        if picture_url:
            # Load profile picture from URL
            self._load_profile_picture(card, picture_url, icon)
        else:
            # Fallback: Show platform icon
            icon_label = ctk.CTkLabel(card, text=icon, 
                font=ctk.CTkFont(size=48))
            icon_label.pack(pady=(15, 5))
        
        # Platform type badge
        platform_badge = ctk.CTkLabel(card, 
            text=platform_type.upper(), 
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=("gray80", "gray30"),
            corner_radius=4,
            padx=8, pady=2)
        platform_badge.pack(pady=(5, 5))
        
        # Account name (truncate if too long)
        account_name = account.get("name", "Unknown")
        if len(account_name) > 15:
            account_name = account_name[:13] + "..."
        
        name_label = ctk.CTkLabel(card, 
            text=account_name,
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=140)
        name_label.pack(pady=(0, 2))
        
        # Username (truncate if too long)
        username = account.get("username", "")
        if username:
            if len(username) > 18:
                username = username[:16] + "..."
            username_text = f"@{username}" if not username.startswith("@") else username
            username_label = ctk.CTkLabel(card, 
                text=username_text,
                font=ctk.CTkFont(size=10),
                text_color="gray",
                wraplength=140)
            username_label.pack(pady=(0, 8))
        
        # Connection status badge at bottom
        is_connected = account.get("isConnected", False)
        status_text = "✓ Connected" if is_connected else "✗ Disconnected"
        status_color = ("green", "green") if is_connected else ("red", "red")
        
        status_badge = ctk.CTkLabel(card, 
            text=status_text,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="white",
            fg_color=status_color,
            corner_radius=4,
            padx=10, pady=4)
        status_badge.pack(side="bottom", pady=(0, 10))
    
    def _load_profile_picture(self, parent, url, fallback_icon):
        """Load profile picture from URL and display in circular frame"""
        def do_load():
            try:
                import requests
                from PIL import Image, ImageDraw, ImageOps
                from io import BytesIO
                
                # Download image
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    # Open image
                    img = Image.open(BytesIO(response.content))
                    
                    # Resize to 80x80
                    img = img.resize((80, 80), Image.Resampling.LANCZOS)
                    
                    # Convert to RGB if needed
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Create circular mask
                    mask = Image.new('L', (80, 80), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, 80, 80), fill=255)
                    
                    # Apply mask
                    output = ImageOps.fit(img, (80, 80), centering=(0.5, 0.5))
                    output.putalpha(mask)
                    
                    # Convert to CTkImage
                    from customtkinter import CTkImage
                    ctk_img = CTkImage(light_image=output, dark_image=output, size=(80, 80))
                    
                    # Update UI in main thread
                    self.after(0, lambda p=parent, img=ctk_img: self._display_profile_picture(p, img))
                else:
                    # Fallback to icon
                    self.after(0, lambda p=parent, icon=fallback_icon: self._display_fallback_icon(p, icon))
                    
            except Exception as e:
                # Fallback to icon on error
                self.after(0, lambda p=parent, icon=fallback_icon: self._display_fallback_icon(p, icon))
        
        # Show loading placeholder
        loading_label = ctk.CTkLabel(parent, text="⏳", 
            font=ctk.CTkFont(size=40))
        loading_label.pack(pady=(15, 5))
        
        # Load in background thread
        threading.Thread(target=do_load, daemon=True).start()
    
    def _display_profile_picture(self, parent, ctk_img):
        """Display loaded profile picture"""
        # Remove loading placeholder
        for widget in parent.winfo_children():
            if isinstance(widget, ctk.CTkLabel) and widget.cget("text") == "⏳":
                widget.destroy()
                break
        
        # Display profile picture
        img_label = ctk.CTkLabel(parent, image=ctk_img, text="")
        img_label.pack(pady=(15, 5))
    
    def _display_fallback_icon(self, parent, icon):
        """Display fallback icon if image loading fails"""
        # Remove loading placeholder
        for widget in parent.winfo_children():
            if isinstance(widget, ctk.CTkLabel) and widget.cget("text") == "⏳":
                widget.destroy()
                break
        
        # Display fallback icon
        icon_label = ctk.CTkLabel(parent, text=icon, 
            font=ctk.CTkFont(size=48))
        icon_label.pack(pady=(15, 5))
    
    def _on_repliz_validate_error(self, error):
        """Handle Repliz validation error"""
        self.repliz_validate_btn.configure(state="normal", text="🔍 Validate Keys")
        self.repliz_status_label.configure(text="✗ Invalid", text_color="red")
        messagebox.showerror("Validation Failed", 
            f"Failed to validate Repliz keys:\n\n{error}\n\nPlease check your Access Key and Secret Key.")
    
    def save_repliz_config(self):
        """Save Repliz configuration"""
        access_key = self.repliz_access_key_entry.get().strip()
        secret_key = self.repliz_secret_key_entry.get().strip()
        
        if not access_key or not secret_key:
            messagebox.showerror("Error", "Please enter both Access Key and Secret Key")
            return
        
        # Save to config
        repliz_config = {
            "access_key": access_key,
            "secret_key": secret_key
        }
        
        self.config.set("repliz", repliz_config)
        self.repliz_status_label.configure(text="✓ Configured", text_color="green")
        messagebox.showinfo("Success", "✓ Repliz configuration saved successfully!")
    
    
    
    def create_about_tab(self):
        """Create about tab"""
        main = self.tabview.tab("About")
        
        # App info
        info_frame = ctk.CTkFrame(main, fg_color="transparent")
        info_frame.pack(fill="x", pady=(20, 15))
        
        ctk.CTkLabel(info_frame, text="YT Short Clipper", font=ctk.CTkFont(size=20, weight="bold")).pack()
        ctk.CTkLabel(info_frame, text=f"v{__version__}", font=ctk.CTkFont(size=12), text_color="gray").pack(pady=(5, 0))
        
        # Check for updates button
        if self.check_update:
            ctk.CTkButton(info_frame, text="Check for Updates", height=35, width=150,
                fg_color="gray", hover_color=("gray70", "gray30"),
                command=self.check_update).pack(pady=(10, 0))
        
        # Description
        desc_frame = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        desc_frame.pack(fill="x", pady=10, padx=5)
        
        desc_text = """Automated YouTube to Short-Form Content Pipeline

Transform long-form YouTube videos into engaging 
short-form content for TikTok, Instagram Reels, 
and YouTube Shorts."""
        
        ctk.CTkLabel(desc_frame, text=desc_text, justify="center", 
            font=ctk.CTkFont(size=11), wraplength=380).pack(padx=15, pady=15)
        
        # Credits
        credits_frame = ctk.CTkFrame(main, fg_color="transparent")
        credits_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(credits_frame, text="Made with ☕ by", font=ctk.CTkFont(size=11), 
            text_color="gray").pack()
        ctk.CTkLabel(credits_frame, text="Aji Prakoso", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(5, 0))
        
        # Links
        links_frame = ctk.CTkFrame(main, fg_color="transparent")
        links_frame.pack(fill="x", pady=15)
        
        ctk.CTkButton(links_frame, text="⭐ GitHub Repository", height=40,
            fg_color=("#24292e", "#0d1117"), hover_color=("#2c3136", "#161b22"),
            command=lambda: self.open_url("https://github.com/jipraks/yt-short-clipper")).pack(fill="x", pady=2)
        
        ctk.CTkButton(links_frame, text="📸 @jipraks on Instagram", height=40,
            fg_color=("#E4405F", "#C13584"), hover_color=("#F56040", "#E1306C"),
            command=lambda: self.open_url("https://instagram.com/jipraks")).pack(fill="x", pady=2)
        
        ctk.CTkButton(links_frame, text="🎬 YouTube Channel", height=40,
            fg_color=("#c4302b", "#FF0000"), hover_color=("#ff0000", "#CC0000"),
            command=lambda: self.open_url("https://youtube.com/@jipraks")).pack(fill="x", pady=2)
        
        # Footer
        footer_frame = ctk.CTkFrame(main, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", pady=(10, 5))
        
        ctk.CTkLabel(footer_frame, text="Open Source • MIT License", 
            font=ctk.CTkFont(size=10), text_color="gray").pack()
    
    def open_url(self, url: str):
        """Open URL in browser"""
        import webbrowser
        webbrowser.open(url)
    
    def open_folder(self, folder_path: str):
        """Open folder in file explorer"""
        if sys.platform == "win32":
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder_path])
        else:
            subprocess.run(["xdg-open", folder_path])
    
    def load_config(self):
        """Load configuration into UI"""
        # Load AI provider configurations
        ai_providers = self.config.get("ai_providers", {})
        
        # Load provider type (ytclip, openai, custom)
        provider_type = self.config.get("provider_type", "ytclip")
        self.provider_type_var.set(provider_type)
        
        # Update card selection visually
        if provider_type == "ytclip":
            self.ytclip_card.configure(border_color=("#3B8ED0", "#1F6AA5"))
            self.openai_card.configure(border_color=("gray70", "gray30"))
            self.custom_card.configure(border_color=("gray70", "gray30"))
        elif provider_type == "openai":
            self.ytclip_card.configure(border_color=("gray70", "gray30"))
            self.openai_card.configure(border_color=("#3B8ED0", "#1F6AA5"))
            self.custom_card.configure(border_color=("gray70", "gray30"))
        else:  # custom
            self.ytclip_card.configure(border_color=("gray70", "gray30"))
            self.openai_card.configure(border_color=("gray70", "gray30"))
            self.custom_card.configure(border_color=("#3B8ED0", "#1F6AA5"))
        
        # Highlight Finder
        hf = ai_providers.get("highlight_finder", {})
        self.hf_url_entry.configure(state="normal")
        self.hf_url_entry.delete(0, "end")
        self.hf_url_entry.insert(0, hf.get("base_url", "https://ai-api.ytclip.org/v1" if provider_type == "ytclip" else "https://api.openai.com/v1"))
        self.hf_key_entry.delete(0, "end")
        self.hf_key_entry.insert(0, hf.get("api_key", ""))
        self.hf_model_var.set(hf.get("model", "gpt-4.1"))
        
        # Caption Maker
        cm = ai_providers.get("caption_maker", {})
        self.cm_url_entry.configure(state="normal")
        self.cm_url_entry.delete(0, "end")
        self.cm_url_entry.insert(0, cm.get("base_url", "https://ai-api.ytclip.org/v1" if provider_type == "ytclip" else "https://api.openai.com/v1"))
        self.cm_key_entry.delete(0, "end")
        self.cm_key_entry.insert(0, cm.get("api_key", ""))
        self.cm_model_entry.delete(0, "end")
        self.cm_model_entry.insert(0, cm.get("model", "whisper-1"))
        
        # Hook Maker
        hm = ai_providers.get("hook_maker", {})
        self.hm_url_entry.configure(state="normal")
        self.hm_url_entry.delete(0, "end")
        self.hm_url_entry.insert(0, hm.get("base_url", "https://ai-api.ytclip.org/v1" if provider_type == "ytclip" else "https://api.openai.com/v1"))
        self.hm_key_entry.delete(0, "end")
        self.hm_key_entry.insert(0, hm.get("api_key", ""))
        self.hm_model_entry.delete(0, "end")
        self.hm_model_entry.insert(0, hm.get("model", "tts-1"))
        
        # YouTube Title Maker
        yt = ai_providers.get("youtube_title_maker", {})
        self.yt_url_entry.configure(state="normal")
        self.yt_url_entry.delete(0, "end")
        self.yt_url_entry.insert(0, yt.get("base_url", "https://ai-api.ytclip.org/v1" if provider_type == "ytclip" else "https://api.openai.com/v1"))
        self.yt_key_entry.delete(0, "end")
        self.yt_key_entry.insert(0, yt.get("api_key", ""))
        self.yt_model_var.set(yt.get("model", "gpt-4.1"))
        
        # Set URL fields state based on provider type
        self._toggle_url_fields(provider_type == "custom")
        
        # Load output folder
        self.output_var.set(self.config.get("output_dir", str(self.output_dir)) or str(self.output_dir))
        
        # Load temperature
        temperature = self.config.get("temperature", 1.0)
        self.temp_var.set(temperature)
        self.update_temp_label(temperature)
        
        # Load face tracking mode
        face_tracking_mode = self.config.get("face_tracking_mode", "opencv")
        self.face_tracking_var.set(face_tracking_mode)
        
        # Load watermark settings
        watermark = self.config.get("watermark", {})
        self.watermark_enabled.set(watermark.get("enabled", False))
        self.watermark_path_var.set(watermark.get("image_path", ""))
        self.watermark_x.set(watermark.get("position_x", 0.85))
        self.watermark_y.set(watermark.get("position_y", 0.05))
        self.watermark_opacity.set(watermark.get("opacity", 0.8))
        self.watermark_scale.set(watermark.get("scale", 0.15))
        self.toggle_watermark()
        self.update_watermark_preview()
        
        # Load system prompt
        from clipper_core import AutoClipperCore
        system_prompt = self.config.get("system_prompt", AutoClipperCore.get_default_prompt())
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", system_prompt)
        self.update_prompt_char_count()
        
        # Load GPU acceleration settings
        gpu_settings = self.config.get("gpu_acceleration", {})
        self.gpu_enabled_var.set(gpu_settings.get("enabled", False))
    
    def browse_output_folder(self):
        """Browse for output folder"""
        folder = filedialog.askdirectory(initialdir=self.output_var.get())
        if folder:
            self.output_var.set(folder)

    def validate_key(self):
        """Validate OpenAI API key"""
        api_key = self.key_entry.get().strip()
        base_url = self.url_entry.get().strip() or "https://api.openai.com/v1"
        self.key_status.configure(text="Validating...", text_color="yellow")
        self.validate_btn.configure(state="disabled")
        
        def do_validate():
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                models = sorted([m.id for m in client.models.list().data])
                self.models_list = models
                self.after(0, lambda m=models: self._on_success(m))
            except:
                self.after(0, self._on_error)
        threading.Thread(target=do_validate, daemon=True).start()
    
    def _on_success(self, models):
        """Handle successful API key validation"""
        self.key_status.configure(text="✓ Valid", text_color="green")
        self.validate_btn.configure(state="normal")
        self.model_count.configure(text=f"{len(models)} models")
        if self.model_var.get() not in models:
            for p in ["gpt-4.1", "gpt-4o", "gpt-4o-mini"]:
                if p in models:
                    self.model_var.set(p)
                    break
    
    def _on_error(self):
        """Handle API key validation error"""
        self.key_status.configure(text="✗ Invalid", text_color="red")
        self.validate_btn.configure(state="normal")
        self.models_list = []
    
    def open_model_selector(self):
        """Open model selector dialog"""
        if not self.models_list:
            messagebox.showwarning("Warning", "Validate API key first")
            return
        SearchableModelDropdown(self, self.models_list, self.model_var.get(), lambda m: self.model_var.set(m))
    
    def save_settings(self):
        """Save settings"""
        output_dir = self.output_var.get().strip() or str(self.output_dir)
        system_prompt = self.prompt_text.get("1.0", "end-1c").strip()
        
        # Validate system prompt
        if not system_prompt:
            messagebox.showerror("Error", "System prompt cannot be empty")
            return
        
        # Validate placeholders
        required_placeholders = ["{num_clips}", "{video_context}", "{transcript}"]
        missing = [p for p in required_placeholders if p not in system_prompt]
        if missing:
            messagebox.showwarning("Warning", 
                f"System prompt missing placeholders: {', '.join(missing)}\n\nPrompt might not work correctly.")
        
        # Collect AI provider configurations from entry fields
        ai_providers = {
            "highlight_finder": {
                "base_url": self.hf_url_entry.get().strip() or "https://api.openai.com/v1",
                "api_key": self.hf_key_entry.get().strip(),
                "model": self.hf_model_var.get().strip()
            },
            "caption_maker": {
                "base_url": self.cm_url_entry.get().strip() or "https://api.openai.com/v1",
                "api_key": self.cm_key_entry.get().strip(),
                "model": self.cm_model_entry.get().strip()
            },
            "hook_maker": {
                "base_url": self.hm_url_entry.get().strip() or "https://api.openai.com/v1",
                "api_key": self.hm_key_entry.get().strip(),
                "model": self.hm_model_entry.get().strip()
            },
            "youtube_title_maker": {
                "base_url": self.yt_url_entry.get().strip() or "https://api.openai.com/v1",
                "api_key": self.yt_key_entry.get().strip(),
                "model": self.yt_model_var.get().strip()
            }
        }
        
        # Validate each provider has required fields
        provider_names = {
            "highlight_finder": "Highlight Finder",
            "caption_maker": "Caption Maker",
            "hook_maker": "Hook Maker",
            "youtube_title_maker": "YouTube Title Maker"
        }
        
        for provider_key, provider_config in ai_providers.items():
            if not provider_config["api_key"]:
                messagebox.showerror("Error", 
                    f"{provider_names[provider_key]} is missing API Key.\n\nPlease configure all providers or use 'Apply URL & Key to All' button.")
                return
            
            if not provider_config["model"]:
                messagebox.showerror("Error", 
                    f"{provider_names[provider_key]} is missing Model.\n\nPlease configure all providers.")
                return
        
        # Create output folder if not exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Save all configurations
        self.config.set("provider_type", self.provider_type_var.get())
        self.config.set("ai_providers", ai_providers)
        self.config.set("output_dir", output_dir)
        self.config.set("temperature", self.temp_var.get())
        self.config.set("system_prompt", system_prompt)
        self.config.set("face_tracking_mode", self.face_tracking_var.get())
        
        # Save watermark settings
        watermark_settings = {
            "enabled": self.watermark_enabled.get(),
            "image_path": self.watermark_path_var.get(),
            "position_x": self.watermark_x.get(),
            "position_y": self.watermark_y.get(),
            "opacity": self.watermark_opacity.get(),
            "scale": self.watermark_scale.get()
        }
        self.config.set("watermark", watermark_settings)
        
        # Save GPU acceleration settings
        gpu_settings = {
            "enabled": self.gpu_enabled_var.get()
        }
        self.config.set("gpu_acceleration", gpu_settings)
        
        # For backward compatibility, also save first provider as default
        highlight_finder = ai_providers.get("highlight_finder", {})
        self.config.set("api_key", highlight_finder.get("api_key", ""))
        self.config.set("base_url", highlight_finder.get("base_url", "https://api.openai.com/v1"))
        self.config.set("model", highlight_finder.get("model", "gpt-4.1"))
        
        hook_maker = ai_providers.get("hook_maker", {})
        self.config.set("tts_model", hook_maker.get("model", "tts-1"))
        
        # Call parent callback with highlight_finder config (for backward compatibility)
        self.on_save(highlight_finder.get("api_key", ""), 
                    highlight_finder.get("base_url", "https://api.openai.com/v1"),
                    highlight_finder.get("model", "gpt-4.1"))
        
        messagebox.showinfo("Success", "✓ Settings saved successfully!")
        self.on_back()
    
    def reset_prompt(self):
        """Reset system prompt to default"""
        if messagebox.askyesno("Reset Prompt", "Reset system prompt to default?"):
            from clipper_core import AutoClipperCore
            default_prompt = AutoClipperCore.get_default_prompt()
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.insert("1.0", default_prompt)
            self.update_prompt_char_count()
    
    def update_prompt_char_count(self, event=None):
        """Update character count for system prompt"""
        text = self.prompt_text.get("1.0", "end-1c")
        char_count = len(text)
        self.prompt_char_count.configure(text=f"{char_count} chars")
    
    def update_temp_label(self, value):
        """Update temperature label"""
        self.temp_label.configure(text=f"{float(value):.1f}")
    
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
        # This is needed for header navigation buttons
        # Try to find the main app instance
        try:
            # Navigate up the widget hierarchy to find the main app
            parent = self.master
            while parent and not hasattr(parent, 'show_page'):
                parent = parent.master
            if parent and hasattr(parent, 'show_page'):
                parent.show_page(page_name)
        except:
            pass
