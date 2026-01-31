"""
Base class for AI Provider settings pages
"""

import threading
import customtkinter as ctk
from tkinter import messagebox

from pages.settings.base_dialog import BaseSettingsSubPage


class BaseProviderSettingsPage(BaseSettingsSubPage):
    """Base class for AI provider settings pages"""
    
    # Override in child class for fixed model list (None = load from API)
    FIXED_MODELS = None
    
    def __init__(self, parent, title, provider_key, config, on_save_callback, on_back_callback):
        self.config = config
        self.provider_key = provider_key
        self.on_save_callback = on_save_callback
        self.models_list = []
        
        super().__init__(parent, title, on_back_callback)
        
        self.create_provider_content()
        self.load_config()
    
    def create_provider_content(self):
        """Create provider settings content"""
        # Provider Type Section
        type_section = self.create_section("Provider Type")
        
        type_frame = ctk.CTkFrame(type_section, fg_color="transparent")
        type_frame.pack(fill="x", padx=15, pady=(0, 12))
        
        ctk.CTkLabel(type_frame, text="Select API Provider", font=ctk.CTkFont(size=11)).pack(anchor="w")
        
        self.provider_type_var = ctk.StringVar(value="ytclip")
        self.provider_dropdown = ctk.CTkOptionMenu(type_frame, 
            values=["🎬 YT CLIP AI", "🤖 OPEN AI", "⚙️ CUSTOM"],
            variable=self.provider_type_var, height=36,
            command=self._on_provider_type_changed)
        self.provider_dropdown.pack(fill="x", pady=(5, 0))
        
        # URL Section (only visible for custom)
        self.url_section = self.create_section("Base URL")
        self.url_section.pack_forget()  # Hidden by default
        
        url_frame = ctk.CTkFrame(self.url_section, fg_color="transparent")
        url_frame.pack(fill="x", padx=15, pady=(0, 12))
        
        ctk.CTkLabel(url_frame, text="API Base URL", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.url_entry = ctk.CTkEntry(url_frame, placeholder_text="https://api.openai.com/v1", height=36)
        self.url_entry.pack(fill="x", pady=(5, 0))
        
        # API Key Section
        key_section = self.create_section("API Key")
        
        key_frame = ctk.CTkFrame(key_section, fg_color="transparent")
        key_frame.pack(fill="x", padx=15, pady=(0, 12))
        
        ctk.CTkLabel(key_frame, text="API Key", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.key_entry = ctk.CTkEntry(key_frame, placeholder_text="sk-...", show="•", height=36)
        self.key_entry.pack(fill="x", pady=(5, 0))
        
        # Model Section
        self.model_section = self.create_section("Model")
        
        model_frame = ctk.CTkFrame(self.model_section, fg_color="transparent")
        model_frame.pack(fill="x", padx=15, pady=(0, 12))
        
        ctk.CTkLabel(model_frame, text="Model Name", font=ctk.CTkFont(size=11)).pack(anchor="w")
        
        model_row = ctk.CTkFrame(model_frame, fg_color="transparent")
        model_row.pack(fill="x", pady=(5, 0))
        
        self.model_var = ctk.StringVar(value="")
        
        # Check if using fixed models or load from API
        if self.FIXED_MODELS:
            # Fixed dropdown - no load button needed
            self.model_dropdown = ctk.CTkOptionMenu(model_row, 
                values=self.FIXED_MODELS,
                variable=self.model_var, height=36)
            self.model_dropdown.pack(fill="x")
            self.load_btn = None
        else:
            # Dynamic dropdown with load button
            self.model_dropdown = ctk.CTkOptionMenu(model_row, 
                values=["-- Click Load to fetch models --"],
                variable=self.model_var, height=36, width=200)
            self.model_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 5))
            
            self.load_btn = ctk.CTkButton(model_row, text="🔄 Load", width=80, height=36,
                command=self.load_models)
            self.load_btn.pack(side="right")
        
        # Actions
        actions_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        actions_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkButton(actions_frame, text="🔍 Validate Configuration", height=40,
            fg_color=("#3B8ED0", "#1F6AA5"), hover_color=("#36719F", "#144870"),
            command=self.validate_config).pack(fill="x", pady=(0, 10))
        
        # Save button
        self.create_save_button(self.save_settings)
    
    def _on_provider_type_changed(self, value):
        """Handle provider type dropdown change"""
        if "CUSTOM" in value:
            self.url_section.pack(fill="x", pady=(0, 10), after=self.content.winfo_children()[1])
        else:
            self.url_section.pack_forget()
    
    def _get_provider_type_key(self):
        """Get provider type key from dropdown value"""
        value = self.provider_type_var.get()
        if "YT CLIP" in value:
            return "ytclip"
        elif "OPEN AI" in value:
            return "openai"
        else:
            return "custom"
    
    def get_base_url(self):
        """Get base URL based on provider type"""
        ptype = self._get_provider_type_key()
        if ptype == "ytclip":
            return "https://ai-api.ytclip.org/v1"
        elif ptype == "openai":
            return "https://api.openai.com/v1"
        else:
            return self.url_entry.get().strip() or "https://api.openai.com/v1"
    
    def load_models(self):
        """Load available models from API"""
        if self.FIXED_MODELS:
            return  # No need to load for fixed models
            
        api_key = self.key_entry.get().strip()
        
        if not api_key:
            messagebox.showerror("Error", "Please enter API Key first")
            return
        
        url = self.get_base_url()
        self.load_btn.configure(state="disabled", text="Loading...")
        
        def do_load():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=url)
                models_response = client.models.list()
                models = [m.id for m in models_response.data]
                models.sort()
                
                self.after(0, lambda: self._on_models_loaded(models))
            except Exception as e:
                self.after(0, lambda: self._on_models_error(str(e)))
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def _on_models_loaded(self, models):
        """Handle models loaded"""
        self.load_btn.configure(state="normal", text="🔄 Load")
        self.models_list = models
        
        if models:
            # Update dropdown with loaded models
            self.model_dropdown.configure(values=models)
            # Keep current selection if valid, otherwise select first
            current = self.model_var.get()
            if current not in models:
                self.model_var.set(models[0])
            messagebox.showinfo("Success", f"Loaded {len(models)} models")
        else:
            messagebox.showwarning("Warning", "No models found")
    
    def _on_models_error(self, error):
        """Handle models load error"""
        self.load_btn.configure(state="normal", text="🔄 Load")
        messagebox.showerror("Error", f"Failed to load models:\n{error}")
    
    def validate_config(self):
        """Validate provider configuration"""
        api_key = self.key_entry.get().strip()
        model = self.model_var.get().strip()
        url = self.get_base_url()
        
        if not api_key:
            messagebox.showerror("Error", "API Key is required")
            return
        
        if not model or model.startswith("--"):
            messagebox.showerror("Error", "Please select a model")
            return
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=url)
            client.models.list()
            messagebox.showinfo("Success", f"✓ Configuration valid!\n\nModel: {model}\nURL: {url}")
        except Exception as e:
            messagebox.showerror("Error", f"Validation failed:\n{str(e)}")
    
    def load_config(self):
        """Load config into UI"""
        # Handle both ConfigManager and dict
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
            
        ai_providers = config_dict.get("ai_providers", {})
        provider = ai_providers.get(self.provider_key, {})
        
        # Determine provider type from URL
        base_url = provider.get("base_url", "")
        if "ytclip" in base_url:
            self.provider_type_var.set("🎬 YT CLIP AI")
        elif "openai.com" in base_url:
            self.provider_type_var.set("🤖 OPEN AI")
        else:
            self.provider_type_var.set("⚙️ CUSTOM")
            self.url_section.pack(fill="x", pady=(0, 10), after=self.content.winfo_children()[1])
        
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, base_url)
        
        self.key_entry.delete(0, "end")
        self.key_entry.insert(0, provider.get("api_key", ""))
        
        saved_model = provider.get("model", "")
        if saved_model:
            if self.FIXED_MODELS:
                # For fixed models, just set the value
                if saved_model in self.FIXED_MODELS:
                    self.model_var.set(saved_model)
                else:
                    self.model_var.set(self.FIXED_MODELS[0])
            else:
                # For dynamic models, add to dropdown if not empty
                self.model_var.set(saved_model)
                current_values = list(self.model_dropdown.cget("values"))
                if saved_model not in current_values:
                    self.model_dropdown.configure(values=[saved_model] + current_values)
    
    def save_settings(self):
        """Save settings"""
        api_key = self.key_entry.get().strip()
        model = self.model_var.get().strip()
        url = self.get_base_url()
        
        if not api_key:
            messagebox.showerror("Error", "API Key is required")
            return
        
        if not model or model.startswith("--"):
            messagebox.showerror("Error", "Please select a model")
            return
        
        # Handle both ConfigManager and dict
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
        
        # Update config
        if "ai_providers" not in config_dict:
            config_dict["ai_providers"] = {}
        
        config_dict["ai_providers"][self.provider_key] = {
            "base_url": url,
            "api_key": api_key,
            "model": model
        }
        
        # Call save callback with the full config dict (not just ai_providers)
        if self.on_save_callback:
            self.on_save_callback(config_dict)
        
        messagebox.showinfo("Success", f"{self.title} settings saved!")
        self.on_back()
