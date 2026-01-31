"""
Credit Watermark Settings Sub-Page
Text watermark showing channel name as video source credit
"""

import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk

from pages.settings.base_dialog import BaseSettingsSubPage


class CreditWatermarkSettingsSubPage(BaseSettingsSubPage):
    """Sub-page for configuring credit watermark (channel name text)"""
    
    def __init__(self, parent, config, on_save_callback, on_back_callback):
        self.config = config
        self.on_save_callback = on_save_callback
        self.text_item = None
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        
        super().__init__(parent, "Credit Watermark", on_back_callback)
        
        self.create_content()
        self.load_config()
    
    def create_content(self):
        """Create page content with canvas for drag & drop positioning"""
        # Enable credit watermark toggle
        enable_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        enable_frame.pack(fill="x", pady=(0, 15))
        
        self.credit_enabled = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(enable_frame, text="Enable Credit Watermark", 
            variable=self.credit_enabled,
            font=ctk.CTkFont(size=14, weight="bold"), 
            command=self.toggle_credit).pack(side="left")
        
        # Credit settings container
        self.credit_settings_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.credit_settings_frame.pack(fill="both", expand=True)
        
        # Info text
        ctk.CTkLabel(self.credit_settings_frame, 
            text="Automatically adds channel name as credit text on generated clips", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(0, 15))
        
        # Position simulator with Canvas
        ctk.CTkLabel(self.credit_settings_frame, text="Position", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10, 5))
        ctk.CTkLabel(self.credit_settings_frame, 
            text="Drag the text to position it on the video", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(0, 10))
        
        # Canvas for 9:16 simulator
        self.canvas_frame = ctk.CTkFrame(self.credit_settings_frame, 
            fg_color=("gray85", "gray20"))
        self.canvas_frame.pack(fill="x", pady=(5, 15))
        
        self.canvas = tk.Canvas(self.canvas_frame, width=270, height=480, 
            bg="#1a1a1a", highlightthickness=1, highlightbackground="gray")
        self.canvas.pack(padx=10, pady=10)
        
        # Draw 9:16 frame
        self.canvas.create_rectangle(0, 0, 270, 480, outline="gray", width=2)
        self.canvas.create_text(135, 240, text="9:16 Video Preview", 
            fill="gray50", font=("Arial", 12))
        
        # Position variables (as percentage)
        self.credit_x = ctk.DoubleVar(value=0.5)  # Center horizontally
        self.credit_y = ctk.DoubleVar(value=0.95)  # Near bottom
        
        # Bind drag events
        self.canvas.bind("<Button-1>", self.on_text_click)
        self.canvas.bind("<B1-Motion>", self.on_text_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_text_release)
        
        # Size slider
        ctk.CTkLabel(self.credit_settings_frame, text="Text Size", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10, 5))
        
        size_frame = ctk.CTkFrame(self.credit_settings_frame, fg_color="transparent")
        size_frame.pack(fill="x", pady=(5, 15))
        
        self.credit_size = ctk.DoubleVar(value=0.03)  # 3% of video height
        size_slider = ctk.CTkSlider(size_frame, from_=0.02, to=0.08, 
            variable=self.credit_size,
            command=self.update_preview, number_of_steps=30)
        size_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.size_label = ctk.CTkLabel(size_frame, text="3%", width=50, anchor="e")
        self.size_label.pack(side="right")
        
        # Opacity slider
        ctk.CTkLabel(self.credit_settings_frame, text="Opacity", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10, 5))
        
        opacity_frame = ctk.CTkFrame(self.credit_settings_frame, fg_color="transparent")
        opacity_frame.pack(fill="x", pady=(5, 15))
        
        self.credit_opacity = ctk.DoubleVar(value=0.7)
        opacity_slider = ctk.CTkSlider(opacity_frame, from_=0.1, to=1.0, 
            variable=self.credit_opacity,
            command=self.update_preview, number_of_steps=18)
        opacity_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.opacity_label = ctk.CTkLabel(opacity_frame, text="70%", width=50, anchor="e")
        self.opacity_label.pack(side="right")
        
        # Save button
        self.create_save_button(self.save_settings)
        
        # Initially disable settings
        self.toggle_credit()
        
        # Initial preview
        self.after(100, self.update_preview)
    
    def toggle_credit(self):
        """Toggle credit settings visibility"""
        if self.credit_enabled.get():
            self._set_children_state(self.credit_settings_frame, "normal")
        else:
            self._set_children_state(self.credit_settings_frame, "disabled")
    
    def _set_children_state(self, widget, state):
        """Recursively set state for all children widgets"""
        for child in widget.winfo_children():
            widget_type = child.winfo_class()
            
            if widget_type in ('Frame', 'Label', 'Canvas'):
                if widget_type == 'Frame':
                    self._set_children_state(child, state)
                continue
            
            try:
                if hasattr(child, 'configure'):
                    child.configure(state=state)
            except Exception:
                try:
                    self._set_children_state(child, state)
                except:
                    pass
    
    def update_preview(self, *args):
        """Update text preview on canvas"""
        # Update labels
        size_percent = int(self.credit_size.get() * 100)
        self.size_label.configure(text=f"{size_percent}%")
        
        opacity_percent = int(self.credit_opacity.get() * 100)
        self.opacity_label.configure(text=f"{opacity_percent}%")
        
        # Clear previous text
        if self.text_item:
            self.canvas.delete(self.text_item)
            self.text_item = None
        
        # Calculate font size based on canvas (270x480 represents 1080x1920)
        # Scale factor: 270/1080 = 0.25
        base_font_size = int(1920 * self.credit_size.get() * 0.25)
        font_size = max(8, min(base_font_size, 24))  # Clamp between 8-24 for preview
        
        # Calculate opacity for color
        opacity = self.credit_opacity.get()
        gray_value = int(255 * opacity)
        text_color = f"#{gray_value:02x}{gray_value:02x}{gray_value:02x}"
        
        # Calculate position
        x = int(self.credit_x.get() * 270)
        y = int(self.credit_y.get() * 480)
        
        # Draw text
        self.text_item = self.canvas.create_text(
            x, y,
            text="Source: This is Channel Name",
            fill=text_color,
            font=("Arial", font_size),
            anchor="center"
        )
    
    def on_text_click(self, event):
        """Handle text click for drag start"""
        if not self.text_item:
            return
        
        # Check if click is near text
        bbox = self.canvas.bbox(self.text_item)
        if bbox:
            # Expand hit area slightly
            margin = 10
            if (bbox[0] - margin <= event.x <= bbox[2] + margin and 
                bbox[1] - margin <= event.y <= bbox[3] + margin):
                self.dragging = True
                center_x = (bbox[0] + bbox[2]) / 2
                center_y = (bbox[1] + bbox[3]) / 2
                self.drag_offset_x = event.x - center_x
                self.drag_offset_y = event.y - center_y
    
    def on_text_drag(self, event):
        """Handle text drag movement"""
        if not self.dragging or not self.text_item:
            return
        
        # Calculate new position (constrained to canvas)
        new_x = max(50, min(event.x - self.drag_offset_x, 220))
        new_y = max(20, min(event.y - self.drag_offset_y, 460))
        
        # Update position variables (as percentage)
        self.credit_x.set(new_x / 270)
        self.credit_y.set(new_y / 480)
        
        # Redraw
        self.update_preview()
    
    def on_text_release(self, event):
        """Handle text drag end"""
        self.dragging = False
    
    def load_config(self):
        """Load config into UI"""
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
            
        credit = config_dict.get("credit_watermark", {})
        
        self.credit_enabled.set(credit.get("enabled", False))
        self.credit_x.set(credit.get("position_x", 0.5))
        self.credit_y.set(credit.get("position_y", 0.95))
        self.credit_size.set(credit.get("size", 0.03))
        self.credit_opacity.set(credit.get("opacity", 0.7))
        
        # Update labels
        self.size_label.configure(text=f"{int(self.credit_size.get() * 100)}%")
        self.opacity_label.configure(text=f"{int(self.credit_opacity.get() * 100)}%")
        
        # Update preview after a short delay
        self.after(100, self.update_preview)
        
        # Toggle settings state
        self.toggle_credit()
    
    def save_settings(self):
        """Save credit watermark settings"""
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
        
        config_dict["credit_watermark"] = {
            "enabled": self.credit_enabled.get(),
            "position_x": self.credit_x.get(),
            "position_y": self.credit_y.get(),
            "size": self.credit_size.get(),
            "opacity": self.credit_opacity.get()
        }
        
        if self.on_save_callback:
            self.on_save_callback(config_dict)
        
        messagebox.showinfo("Success", "Credit watermark settings saved!")
        self.on_back()
