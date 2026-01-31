"""
Watermark Settings Sub-Page with Canvas Drag & Drop
"""

import shutil
import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import tkinter as tk

from pages.settings.base_dialog import BaseSettingsSubPage


class WatermarkSettingsSubPage(BaseSettingsSubPage):
    """Sub-page for configuring watermark settings with drag & drop canvas"""
    
    def __init__(self, parent, config, on_save_callback, on_back_callback):
        self.config = config
        self.on_save_callback = on_save_callback
        self.watermark_item = None
        self.watermark_photo = None
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        
        super().__init__(parent, "Watermark Settings", on_back_callback)
        
        self.create_content()
        self.load_config()
    
    def create_content(self):
        """Create page content with canvas for drag & drop positioning"""
        # Enable watermark toggle
        enable_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        enable_frame.pack(fill="x", pady=(0, 15))
        
        self.watermark_enabled = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(enable_frame, text="Enable Watermark", 
            variable=self.watermark_enabled,
            font=ctk.CTkFont(size=14, weight="bold"), 
            command=self.toggle_watermark).pack(side="left")
        
        # Watermark settings container
        self.watermark_settings_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.watermark_settings_frame.pack(fill="both", expand=True)
        
        # Image selection
        ctk.CTkLabel(self.watermark_settings_frame, text="Watermark Image", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(5, 5))
        
        image_frame = ctk.CTkFrame(self.watermark_settings_frame, fg_color="transparent")
        image_frame.pack(fill="x", pady=(5, 15))
        
        self.watermark_path_var = ctk.StringVar(value="")
        self.watermark_path_entry = ctk.CTkEntry(image_frame, 
            textvariable=self.watermark_path_var, 
            placeholder_text="Select PNG image...")
        self.watermark_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkButton(image_frame, text="Browse", width=100,
            command=self.browse_watermark).pack(side="right")
        
        # Position simulator with Canvas
        ctk.CTkLabel(self.watermark_settings_frame, text="Position", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10, 5))
        ctk.CTkLabel(self.watermark_settings_frame, 
            text="Drag the watermark to position it on the video", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(0, 10))
        
        # Canvas for 9:16 simulator
        self.canvas_frame = ctk.CTkFrame(self.watermark_settings_frame, 
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
        self.watermark_x = ctk.DoubleVar(value=0.85)
        self.watermark_y = ctk.DoubleVar(value=0.05)
        
        # Bind drag events
        self.canvas.bind("<Button-1>", self.on_watermark_click)
        self.canvas.bind("<B1-Motion>", self.on_watermark_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_watermark_release)
        
        # Opacity slider
        ctk.CTkLabel(self.watermark_settings_frame, text="Opacity", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10, 5))
        
        opacity_frame = ctk.CTkFrame(self.watermark_settings_frame, fg_color="transparent")
        opacity_frame.pack(fill="x", pady=(5, 15))
        
        self.watermark_opacity = ctk.DoubleVar(value=0.8)
        ctk.CTkSlider(opacity_frame, from_=0.0, to=1.0, 
            variable=self.watermark_opacity,
            command=self.update_watermark_preview, number_of_steps=20).pack(
            side="left", fill="x", expand=True, padx=(0, 10))
        
        self.opacity_label = ctk.CTkLabel(opacity_frame, text="80%", width=50, anchor="e")
        self.opacity_label.pack(side="right")
        
        # Scale slider
        ctk.CTkLabel(self.watermark_settings_frame, text="Size", 
            font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10, 5))
        
        scale_frame = ctk.CTkFrame(self.watermark_settings_frame, fg_color="transparent")
        scale_frame.pack(fill="x", pady=(5, 15))
        
        self.watermark_scale = ctk.DoubleVar(value=0.15)
        ctk.CTkSlider(scale_frame, from_=0.05, to=0.5, 
            variable=self.watermark_scale,
            command=self.update_watermark_preview, number_of_steps=45).pack(
            side="left", fill="x", expand=True, padx=(0, 10))
        
        self.scale_label = ctk.CTkLabel(scale_frame, text="15%", width=50, anchor="e")
        self.scale_label.pack(side="right")
        
        # Save button
        self.create_save_button(self.save_settings)
        
        # Initially disable watermark settings
        self.toggle_watermark()
    
    def toggle_watermark(self):
        """Toggle watermark settings visibility"""
        if self.watermark_enabled.get():
            self._set_children_state(self.watermark_settings_frame, "normal")
        else:
            self._set_children_state(self.watermark_settings_frame, "disabled")
    
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
            except:
                try:
                    self._set_children_state(child, state)
                except:
                    pass
    
    def browse_watermark(self):
        """Browse for watermark image and copy to app folder"""
        file_path = filedialog.askopenfilename(
            title="Select Watermark Image",
            filetypes=[("PNG Images", "*.png"), ("All Images", "*.png *.jpg *.jpeg")]
        )
        if file_path:
            try:
                watermarks_dir = Path("assets/watermarks")
                watermarks_dir.mkdir(parents=True, exist_ok=True)
                original_name = Path(file_path).stem
                extension = Path(file_path).suffix
                dest_filename = f"watermark_{original_name}{extension}"
                dest_path = watermarks_dir / dest_filename
                counter = 1
                while dest_path.exists():
                    dest_filename = f"watermark_{original_name}_{counter}{extension}"
                    dest_path = watermarks_dir / dest_filename
                    counter += 1
                shutil.copy2(file_path, dest_path)
                self.watermark_path_var.set(str(dest_path))
                self.update_watermark_preview()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to copy watermark: {str(e)}")
    
    def update_watermark_preview(self, *args):
        """Update watermark preview on canvas"""
        self.opacity_label.configure(text=f"{int(self.watermark_opacity.get() * 100)}%")
        self.scale_label.configure(text=f"{int(self.watermark_scale.get() * 100)}%")
        
        if self.watermark_item:
            self.canvas.delete(self.watermark_item)
            self.watermark_item = None
        
        watermark_path = self.watermark_path_var.get()
        if not watermark_path or not Path(watermark_path).exists():
            return
        
        try:
            from PIL import Image, ImageTk
            img = Image.open(watermark_path)
            canvas_width = 270
            watermark_width = int(canvas_width * self.watermark_scale.get())
            aspect_ratio = img.height / img.width
            watermark_height = int(watermark_width * aspect_ratio)
            img = img.resize((watermark_width, watermark_height), Image.Resampling.LANCZOS)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            alpha = img.split()[3]
            alpha = alpha.point(lambda p: int(p * self.watermark_opacity.get()))
            img.putalpha(alpha)
            self.watermark_photo = ImageTk.PhotoImage(img)
            x = int(self.watermark_x.get() * 270)
            y = int(self.watermark_y.get() * 480)
            self.watermark_item = self.canvas.create_image(x, y, image=self.watermark_photo, anchor="nw")
        except Exception as e:
            print(f"Error loading watermark preview: {e}")
    
    def on_watermark_click(self, event):
        """Handle watermark click for drag start"""
        if not self.watermark_item:
            return
        bbox = self.canvas.bbox(self.watermark_item)
        if bbox and bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
            self.dragging = True
            self.drag_offset_x = event.x - bbox[0]
            self.drag_offset_y = event.y - bbox[1]
    
    def on_watermark_drag(self, event):
        """Handle watermark drag movement"""
        if not self.dragging or not self.watermark_item:
            return
        new_x = max(0, min(event.x - self.drag_offset_x, 270 - 50))
        new_y = max(0, min(event.y - self.drag_offset_y, 480 - 50))
        self.watermark_x.set(new_x / 270)
        self.watermark_y.set(new_y / 480)
        self.update_watermark_preview()
    
    def on_watermark_release(self, event):
        """Handle watermark drag end"""
        self.dragging = False
    
    def load_config(self):
        """Load config into UI"""
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
        watermark = config_dict.get("watermark", {})
        self.watermark_enabled.set(watermark.get("enabled", False))
        self.watermark_path_var.set(watermark.get("image_path", ""))
        self.watermark_x.set(watermark.get("position_x", 0.85))
        self.watermark_y.set(watermark.get("position_y", 0.05))
        self.watermark_opacity.set(watermark.get("opacity", 0.8))
        self.watermark_scale.set(watermark.get("scale", 0.15))
        self.opacity_label.configure(text=f"{int(self.watermark_opacity.get() * 100)}%")
        self.scale_label.configure(text=f"{int(self.watermark_scale.get() * 100)}%")
        self.after(100, self.update_watermark_preview)
        self.toggle_watermark()
    
    def save_settings(self):
        """Save watermark settings"""
        if self.watermark_enabled.get():
            image_path = self.watermark_path_var.get().strip()
            if not image_path:
                messagebox.showerror("Error", "Please select a watermark image")
                return
            if not Path(image_path).exists():
                messagebox.showerror("Error", "Watermark image file not found")
                return
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
        config_dict["watermark"] = {
            "enabled": self.watermark_enabled.get(),
            "image_path": self.watermark_path_var.get().strip(),
            "position_x": self.watermark_x.get(),
            "position_y": self.watermark_y.get(),
            "opacity": self.watermark_opacity.get(),
            "scale": self.watermark_scale.get()
        }
        if self.on_save_callback:
            self.on_save_callback(config_dict)
        messagebox.showinfo("Success", "Watermark settings saved!")
        self.on_back()
