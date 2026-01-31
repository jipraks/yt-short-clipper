"""
Progress step component for showing processing status - Card style
"""

import customtkinter as ctk


class ProgressStep(ctk.CTkFrame):
    """A single step card in the progress indicator"""
    
    def __init__(self, parent, step_num: int, title: str):
        super().__init__(parent, fg_color=("gray85", "gray20"), corner_radius=8)
        self.step_num = step_num
        self.status = "pending"  # pending, active, done, error
        
        # Main content frame
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)
        
        # Step indicator circle
        self.indicator = ctk.CTkLabel(
            content, 
            text=str(step_num), 
            width=30, 
            height=30,
            fg_color=("gray70", "gray30"), 
            corner_radius=15, 
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.indicator.pack(pady=(0, 8))
        
        # Step title
        self.title_label = ctk.CTkLabel(
            content, 
            text=title, 
            font=ctk.CTkFont(size=11, weight="bold"), 
            wraplength=120,
            justify="center"
        )
        self.title_label.pack()
        
        # Status label
        self.status_label = ctk.CTkLabel(
            content, 
            text="Waiting...", 
            font=ctk.CTkFont(size=10), 
            text_color="gray"
        )
        self.status_label.pack(pady=(4, 0))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(content, height=6, width=100)
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

    def set_active(self, status_text: str = "Processing...", progress: float = None):
        """Set step to active state with optional progress"""
        self.status = "active"
        self.indicator.configure(fg_color=("#3498db", "#2980b9"), text="●")
        self.status_label.configure(text=status_text, text_color=("#3498db", "#5dade2"))
        
        if progress is None:
            progress = 0.0
        
        self.progress_bar.pack(pady=(6, 0))
        self.progress_bar.set(progress)
    
    def set_done(self, status_text: str = "Complete"):
        """Set step to done state"""
        self.status = "done"
        self.indicator.configure(fg_color=("#27ae60", "#1e8449"), text="✓")
        self.status_label.configure(text=status_text, text_color=("#27ae60", "#2ecc71"))
        self.progress_bar.pack_forget()
    
    def set_error(self, status_text: str = "Failed"):
        """Set step to error state"""
        self.status = "error"
        self.indicator.configure(fg_color=("#e74c3c", "#c0392b"), text="✗")
        self.status_label.configure(text=status_text, text_color=("#e74c3c", "#ec7063"))
        self.progress_bar.pack_forget()
    
    def reset(self):
        """Reset step to initial pending state"""
        self.status = "pending"
        self.indicator.configure(fg_color=("gray70", "gray30"), text=str(self.step_num))
        self.status_label.configure(text="Waiting...", text_color="gray")
        self.progress_bar.pack_forget()
        self.progress_bar.set(0)
