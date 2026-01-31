"""
Output Settings Sub-Page
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path

from pages.settings.base_dialog import BaseSettingsSubPage


class OutputSettingsSubPage(BaseSettingsSubPage):
    """Sub-page for configuring output settings"""
    
    def __init__(self, parent, config, output_dir, on_save_callback, on_back_callback):
        self.config = config
        self.output_dir = output_dir
        self.on_save_callback = on_save_callback
        
        super().__init__(parent, "Output Settings", on_back_callback)
        
        self.create_content()
        self.load_config()
    
    def create_content(self):
        """Create page content"""
        # Output Folder Section
        folder_section = self.create_section("Output Folder")
        
        folder_frame = ctk.CTkFrame(folder_section, fg_color="transparent")
        folder_frame.pack(fill="x", padx=15, pady=(0, 12))
        
        ctk.CTkLabel(folder_frame, text="Folder where video clips will be saved", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(0, 5))
        
        path_row = ctk.CTkFrame(folder_frame, fg_color="transparent")
        path_row.pack(fill="x")
        
        self.output_var = ctk.StringVar(value=str(self.output_dir))
        self.output_entry = ctk.CTkEntry(path_row, textvariable=self.output_var, height=36)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkButton(path_row, text="Browse", width=100, height=36,
            command=self.browse_output_folder).pack(side="right")
        
        # Open folder button
        ctk.CTkButton(folder_frame, text="📂 Open Output Folder", height=36, fg_color="gray",
            command=self.open_output_folder).pack(fill="x", pady=(10, 0))
        
        # Face Tracking Mode Section
        tracking_section = self.create_section("Face Tracking Mode")
        
        tracking_frame = ctk.CTkFrame(tracking_section, fg_color="transparent")
        tracking_frame.pack(fill="x", padx=15, pady=(0, 12))
        
        ctk.CTkLabel(tracking_frame, text="Choose how the video crops to speakers", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(0, 10))
        
        self.face_tracking_var = ctk.StringVar(value="opencv")
        
        # OpenCV option
        opencv_frame = ctk.CTkFrame(tracking_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        opencv_frame.pack(fill="x", pady=(0, 10))
        
        opencv_radio = ctk.CTkRadioButton(opencv_frame, text="OpenCV (Fast)", 
            variable=self.face_tracking_var, value="opencv", 
            font=ctk.CTkFont(size=13, weight="bold"))
        opencv_radio.pack(anchor="w", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(opencv_frame, text="• Crop to largest face", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=35)
        ctk.CTkLabel(opencv_frame, text="• Faster processing", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=35)
        ctk.CTkLabel(opencv_frame, text="• Recommended for most users", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=35, pady=(0, 10))
        
        # MediaPipe option
        mediapipe_frame = ctk.CTkFrame(tracking_frame, fg_color=("gray85", "gray20"), corner_radius=8)
        mediapipe_frame.pack(fill="x")
        
        mediapipe_radio = ctk.CTkRadioButton(mediapipe_frame, text="MediaPipe (Smart)", 
            variable=self.face_tracking_var, value="mediapipe", 
            font=ctk.CTkFont(size=13, weight="bold"))
        mediapipe_radio.pack(anchor="w", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(mediapipe_frame, text="• Crop to active speaker (lip movement)", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=35)
        ctk.CTkLabel(mediapipe_frame, text="• More accurate speaker tracking", 
            font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=35)
        ctk.CTkLabel(mediapipe_frame, text="⚠ Slower processing (2-3x)", 
            font=ctk.CTkFont(size=11), text_color="orange").pack(anchor="w", padx=35, pady=(0, 10))
        
        # Save button
        self.create_save_button(self.save_settings)
    
    def browse_output_folder(self):
        """Browse for output folder"""
        dir_path = filedialog.askdirectory(initialdir=self.output_var.get())
        if dir_path:
            self.output_var.set(dir_path)
    
    def open_output_folder(self):
        """Open output folder in file explorer"""
        import subprocess
        import sys
        
        folder = self.output_var.get()
        if not folder or not Path(folder).exists():
            messagebox.showwarning("Warning", "Output folder does not exist")
            return
        
        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", folder])
            elif sys.platform == "darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {str(e)}")
    
    def load_config(self):
        """Load config into UI"""
        # Handle both ConfigManager and dict
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
        
        # Output directory
        output_dir = config_dict.get("output_dir", str(self.output_dir))
        self.output_var.set(output_dir)
        
        # Face tracking mode
        face_tracking = config_dict.get("face_tracking_mode", "opencv")
        self.face_tracking_var.set(face_tracking)
    
    def save_settings(self):
        """Save settings"""
        output_dir = self.output_var.get().strip()
        
        if not output_dir:
            messagebox.showerror("Error", "Output directory is required")
            return
        
        # Create directory if it doesn't exist
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create directory:\n{str(e)}")
            return
        
        # Handle both ConfigManager and dict
        if hasattr(self.config, 'config'):
            config_dict = self.config.config
        else:
            config_dict = self.config
        
        # Update config
        config_dict["output_dir"] = output_dir
        config_dict["face_tracking_mode"] = self.face_tracking_var.get()
        
        if self.on_save_callback:
            self.on_save_callback(config_dict)
        
        messagebox.showinfo("Success", "Output settings saved!")
        self.on_back()
