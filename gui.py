#!/usr/bin/env python3
"""
Simple GUI interface for the AI Search Agent.
Provides an easy-to-use interface for non-technical users.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import os
import sys
from pathlib import Path
import subprocess

try:
    from ai_search_agent import AISearchAgent
    from config import validate_environment
except ImportError:
    print("Core modules not found. Please ensure ai_search_agent.py is in the same directory.")
    sys.exit(1)


class SearchAgentGUI:
    """GUI application for the AI Search Agent."""
    
    def __init__(self, root):
        """Initialize the GUI."""
        self.root = root
        self.root.title("Microsoft Rewards Agent - AI Search Automation")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Variables
        self.agent = None
        self.is_running = False
        self.message_queue = queue.Queue()
        
        # Setup GUI
        self.setup_gui()
        self.check_environment()
        
        # Start message processing
        self.process_messages()
    
    def setup_gui(self):
        """Setup the GUI layout."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="AI Search Agent", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # API Key
        ttk.Label(config_frame, text="Gemini API Key:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(config_frame, textvariable=self.api_key_var, show="*", width=40)
        api_key_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(config_frame, text="Browse .env", 
                  command=self.browse_env_file).grid(row=0, column=2)
        
        # Search cycles
        ttk.Label(config_frame, text="Search Cycles:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.cycles_var = tk.StringVar(value="54")
        cycles_spinbox = ttk.Spinbox(config_frame, from_=1, to=100, 
                                   textvariable=self.cycles_var, width=10)
        cycles_spinbox.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        # Delay settings
        delay_frame = ttk.Frame(config_frame)
        delay_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        delay_frame.columnconfigure(2, weight=1)
        
        ttk.Label(delay_frame, text="Delay Range:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.min_delay_var = tk.StringVar(value="10")
        ttk.Spinbox(delay_frame, from_=1, to=60, textvariable=self.min_delay_var, 
                   width=5).grid(row=0, column=1, padx=(0, 5))
        ttk.Label(delay_frame, text="to").grid(row=0, column=2, padx=(0, 5))
        self.max_delay_var = tk.StringVar(value="59")
        ttk.Spinbox(delay_frame, from_=5, to=120, textvariable=self.max_delay_var, 
                   width=5).grid(row=0, column=3, padx=(0, 5))
        ttk.Label(delay_frame, text="seconds").grid(row=0, column=4)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Search Agent", 
                                      command=self.start_agent, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stop Agent", 
                                     command=self.stop_agent, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Test Setup", 
                  command=self.test_setup).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="View Reports", 
                  command=self.view_reports).pack(side=tk.LEFT)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Log display
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
          # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var,
                                          maximum=100, mode='determinate')
        self.progress_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def log_message(self, message: str):
        """Add message to log display."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def check_environment(self):
        """Check if environment is properly configured."""
        try:
            # Try to load existing .env file
            if os.path.exists(".env"):
                with open(".env", "r") as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            key = line.split("=", 1)[1].strip()
                            if key and key != "your_gemini_api_key_here":
                                self.api_key_var.set(key)
            
            # Validate environment
            result = validate_environment()
            if result['valid']:
                self.status_var.set("Environment configured correctly")
                self.log_message("[SUCCESS] Environment validation passed")
            else:
                self.status_var.set("Environment needs configuration")
                self.log_message("[WARNING] Environment issues found:")
                for issue in result['issues']:
                    self.log_message(f"  - {issue}")
                    
        except Exception as e:
            self.log_message(f"Error checking environment: {e}")
    
    def browse_env_file(self):
        """Browse for .env file."""
        filename = filedialog.askopenfilename(
            title="Select .env file",
            filetypes=[("Environment files", "*.env"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, "r") as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            key = line.split("=", 1)[1].strip()
                            if key:
                                self.api_key_var.set(key)
                                self.log_message(f"Loaded API key from {filename}")
                                break
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read {filename}: {e}")
    
    def test_setup(self):
        """Test the current setup."""
        def run_test():
            try:
                self.log_message("[TEST] Testing setup...")
                self.status_var.set("Testing...")
                
                # Save current settings to .env
                self.save_env_file()
                
                # Test environment
                result = validate_environment()
                if not result['valid']:
                    self.message_queue.put(("error", "Environment validation failed"))
                    return
                
                # Test Gemini connection
                from ai_search_agent import AISearchAgent
                agent = AISearchAgent()
                
                query, category, query_type = agent.generate_search_query()
                agent.cleanup()
                
                self.message_queue.put(("success", f"Test successful! Generated query: {query}"))
                
            except Exception as e:
                self.message_queue.put(("error", f"Test failed: {e}"))
        
        threading.Thread(target=run_test, daemon=True).start()
    
    def save_env_file(self):
        """Save current settings to .env file."""
        env_content = f"""# Microsoft Rewards Agent Environment Variables
GEMINI_API_KEY={self.api_key_var.get()}
EDGE_DRIVER_PATH=auto
DEBUG_MODE=False
LOG_LEVEL=INFO
MAX_SEARCH_CYCLES={self.cycles_var.get()}
MIN_DELAY={self.min_delay_var.get()}
MAX_DELAY={self.max_delay_var.get()}
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
    
    def start_agent(self):
        """Start the search agent."""
        if not self.api_key_var.get():
            messagebox.showerror("Error", "Please enter your Gemini API key")
            return
        
        def run_agent():
            try:
                self.message_queue.put(("status", "Initializing agent..."))
                
                # Save settings
                self.save_env_file()
                
                # Create and run agent
                from ai_search_agent import AISearchAgent
                agent = AISearchAgent()
                
                pc_cycles = int(self.cycles_var.get()) // 2
                mobile_cycles = int(self.cycles_var.get()) - pc_cycles
                self.message_queue.put(("start", pc_cycles + mobile_cycles))
                
                # Run with progress updates
                for cycle in range(1, pc_cycles + 1):
                    if not self.is_running:
                        break
                    
                    try:
                        query, category, query_type = agent.generate_search_query()
                        self.message_queue.put(("query", f"Cycle {cycle}: {query} (PC)"))
                        success, url, execution_time = agent.execute_search(query, "pc")
                        
                        if success:
                            self.message_queue.put(("success", f"[SUCCESS] PC Search completed in {execution_time:.2f}s"))
                        else:
                            self.message_queue.put(("error", "[FAIL] PC Search failed"))
                        
                        progress = (cycle / (pc_cycles + mobile_cycles)) * 100
                        self.message_queue.put(("progress", progress))
                        
                        # Random delay (simplified for GUI)
                        if cycle < pc_cycles and self.is_running:
                            import random
                            delay = random.randint(int(self.min_delay_var.get()), 
                                                 int(self.max_delay_var.get()))
                            
                            for remaining in range(delay, 0, -1):
                                if not self.is_running:
                                    break
                                self.message_queue.put(("delay", f"Next search in: {remaining}s"))
                                threading.Event().wait(1)
                    
                    except Exception as e:
                        self.message_queue.put(("error", f"PC Cycle {cycle} failed: {e}"))
                
                for cycle in range(1, mobile_cycles + 1):
                    if not self.is_running:
                        break
                    
                    try:
                        query, category, query_type = agent.generate_search_query()
                        self.message_queue.put(("query", f"Cycle {cycle + pc_cycles}: {query} (Mobile)"))
                        success, url, execution_time = agent.execute_search(query, "mobile")
                        
                        if success:
                            self.message_queue.put(("success", f"[SUCCESS] Mobile Search completed in {execution_time:.2f}s"))
                        else:
                            self.message_queue.put(("error", "[FAIL] Mobile Search failed"))
                        
                        progress = ((cycle + pc_cycles) / (pc_cycles + mobile_cycles)) * 100
                        self.message_queue.put(("progress", progress))
                        
                        # Random delay (simplified for GUI)
                        if cycle < mobile_cycles and self.is_running:
                            import random
                            delay = random.randint(int(self.min_delay_var.get()), 
                                                 int(self.max_delay_var.get()))
                            
                            for remaining in range(delay, 0, -1):
                                if not self.is_running:
                                    break
                                self.message_queue.put(("delay", f"Next search in: {remaining}s"))
                                threading.Event().wait(1)
                    
                    except Exception as e:
                        self.message_queue.put(("error", f"Mobile Cycle {cycle} failed: {e}"))
                
                agent.cleanup()
                self.message_queue.put(("complete", "Agent finished"))
                
            except Exception as e:
                self.message_queue.put(("error", f"Agent failed: {e}"))
        
        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
        threading.Thread(target=run_agent, daemon=True).start()
    
    def stop_agent(self):
        """Stop the search agent."""
        self.is_running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("Stopping...")
        self.log_message("🛑 Stop requested")
    
    def view_reports(self):
        """Open reports directory."""
        reports_dir = Path("reports")
        if reports_dir.exists():
            if os.name == 'nt':  # Windows
                os.startfile(reports_dir)
            elif os.name == 'posix':  # macOS/Linux
                subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', reports_dir])
        else:
            messagebox.showinfo("Info", "No reports directory found. Run the agent first to generate reports.")
    
    def process_messages(self):
        """Process messages from background threads."""
        try:
            while True:
                msg_type, msg_data = self.message_queue.get_nowait()
                
                if msg_type == "status":
                    self.status_var.set(msg_data)
                elif msg_type == "error":
                    self.log_message(f"❌ {msg_data}")
                    self.status_var.set("Error occurred")
                elif msg_type == "success":
                    self.log_message(f"✅ {msg_data}")
                elif msg_type == "query":
                    self.log_message(f"🤖 {msg_data}")
                elif msg_type == "start":
                    self.log_message(f"🚀 Starting {msg_data} search cycles")
                    self.progress_var.set(0)
                elif msg_type == "progress":
                    self.progress_var.set(msg_data)
                elif msg_type == "delay":
                    self.status_var.set(msg_data)
                elif msg_type == "complete":
                    self.log_message(f"🎉 {msg_data}")
                    self.status_var.set("Complete")
                    self.progress_var.set(100)
                    self.start_button.config(state="normal")
                    self.stop_button.config(state="disabled")
                    self.is_running = False
                
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_messages)


def main():
    """Main GUI function."""
    root = tk.Tk()
    
    # Set theme (if available)
    try:
        style = ttk.Style()
        style.theme_use('winnative' if os.name == 'nt' else 'clam')
    except Exception:
        pass
    
    app = SearchAgentGUI(root)
    
    # Handle window closing
    def on_closing():
        if app.is_running:
            if messagebox.askokcancel("Quit", "Agent is running. Do you want to stop it and quit?"):
                app.stop_agent()
                root.after(1000, root.destroy)  # Give time to stop
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()