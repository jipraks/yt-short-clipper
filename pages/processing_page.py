"""
Processing page for video processing workflow
"""

import customtkinter as ctk
from components.progress_step import ProgressStep
from utils.logger import get_error_log_path


class ProcessingPage(ctk.CTkFrame):
    """Processing page - shows progress during video processing"""
    
    def __init__(self, parent, on_cancel_callback, on_back_callback, on_open_output_callback, on_browse_callback):
        super().__init__(parent)
        self.on_cancel = on_cancel_callback
        self.on_back = on_back_callback
        self.on_open_output = on_open_output_callback
        self.on_browse = on_browse_callback
        
        self.create_ui()
    
    def open_github(self):
        """Open GitHub repository"""
        import webbrowser
        webbrowser.open("https://github.com/jipraks/yt-short-clipper")
    
    def open_discord(self):
        """Open Discord server"""
        import webbrowser
        webbrowser.open("https://s.id/ytsdiscord")
    
    def show_page(self, page_name: str):
        """Navigate to another page"""
        pass
    
    def create_ui(self):
        """Create the processing page UI"""
        from components.page_layout import PageHeader, PageFooter
        
        self.configure(fg_color=("#1a1a1a", "#0a0a0a"))
        
        # Header
        header = PageHeader(self, self, show_nav_buttons=False, show_back_button=True, page_title="🎬 Processing")
        header.pack(fill="x", padx=20, pady=(15, 10))
        
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Progress steps - 3 cards horizontal
        steps_frame = ctk.CTkFrame(main, fg_color=("gray90", "gray17"))
        steps_frame.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(steps_frame, text="Progress", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(12, 8))
        
        cards_frame = ctk.CTkFrame(steps_frame, fg_color="transparent")
        cards_frame.pack(fill="x", padx=10, pady=(0, 12))
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="step")
        
        self.steps = []
        step_titles = [
            "Downloading Video & Subtitles",
            "Finding Highlights with AI", 
            "Processing Video"
        ]
        
        for i, title in enumerate(step_titles):
            step = ProgressStep(cards_frame, i + 1, title)
            step.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            self.steps.append(step)
        
        # Current status
        self.status_frame = ctk.CTkFrame(main)
        self.status_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="Initializing...", 
            font=ctk.CTkFont(size=13), wraplength=480)
        self.status_label.pack(pady=12)
        
        # Token usage (compact)
        token_frame = ctk.CTkFrame(main)
        token_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(token_frame, text="API Usage", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(8, 5))
        stats = ctk.CTkFrame(token_frame, fg_color="transparent")
        stats.pack(fill="x", padx=10, pady=(0, 8))
        
        for label, attr in [("GPT", "gpt_label"), ("Whisper", "whisper_label"), ("TTS", "tts_label")]:
            f = ctk.CTkFrame(stats, fg_color=("gray80", "gray25"), corner_radius=8)
            f.pack(side="left", fill="x", expand=True, padx=2)
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10), text_color="gray").pack(side="left", padx=(8, 5), pady=5)
            lbl = ctk.CTkLabel(f, text="0", font=ctk.CTkFont(size=12, weight="bold"))
            lbl.pack(side="right", padx=(5, 8), pady=5)
            setattr(self, attr, lbl)

        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        row1 = ctk.CTkFrame(btn_frame, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 5))
        
        self.cancel_btn = ctk.CTkButton(row1, text="❌ Cancel", height=45, fg_color="#c0392b", 
            hover_color="#e74c3c", command=self.on_cancel)
        self.cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.back_btn = ctk.CTkButton(row1, text="← Back", height=45, state="disabled", command=self.on_back)
        self.back_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        row2 = ctk.CTkFrame(btn_frame, fg_color="transparent")
        row2.pack(fill="x")
        
        self.open_btn = ctk.CTkButton(row2, text="📂 Open Output", height=45, state="disabled", command=self.on_open_output)
        self.open_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.results_btn = ctk.CTkButton(row2, text="📂 Browse Videos", height=45, state="disabled", 
            fg_color="#27ae60", hover_color="#2ecc71", command=self.on_browse)
        self.results_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Footer
        footer = PageFooter(self, self)
        footer.pack(fill="x", padx=20, pady=(10, 15), side="bottom")
    
    def reset_ui(self):
        """Reset UI for new processing"""
        for step in self.steps:
            step.reset()
        
        self.status_label.configure(text="Initializing...")
        self.gpt_label.configure(text="0")
        self.whisper_label.configure(text="0")
        self.tts_label.configure(text="0")
        self.cancel_btn.configure(state="normal")
        self.open_btn.configure(state="disabled")
        self.back_btn.configure(state="disabled")
        self.results_btn.configure(state="disabled")
    
    def update_status(self, msg: str):
        """Update status label"""
        self.status_label.configure(text=msg)
    
    def update_tokens(self, gpt_total: int, whisper_minutes: float, tts_chars: int):
        """Update token usage display"""
        self.gpt_label.configure(text=f"{gpt_total:,}")
        self.whisper_label.configure(text=f"{whisper_minutes:.1f}m")
        self.tts_label.configure(text=f"{tts_chars:,}")
    
    def on_complete(self):
        """Called when processing completes successfully"""
        self.status_label.configure(text="✅ All clips created successfully!")
        self.cancel_btn.configure(state="disabled")
        self.open_btn.configure(state="normal")
        self.back_btn.configure(state="normal")
        self.results_btn.configure(state="normal")
        for step in self.steps:
            step.set_done("Complete")
    
    def on_cancelled(self):
        """Called when processing is cancelled"""
        self.status_label.configure(text="⚠️ Cancelled by user")
        self.cancel_btn.configure(state="disabled")
        self.back_btn.configure(state="normal")
        for step in self.steps:
            if step.status == "active":
                step.set_error("Cancelled")
    
    def on_error(self, error: str):
        """Called when processing encounters an error"""
        error_log = get_error_log_path()
        
        if error_log:
            error_msg = f"❌ {error}\n\n📄 Error details saved to:\n{error_log}"
        else:
            error_msg = f"❌ {error}"
        
        self.status_label.configure(text=error_msg)
        self.cancel_btn.configure(state="disabled")
        self.back_btn.configure(state="normal")
        for step in self.steps:
            if step.status == "active":
                step.set_error("Failed")
