import os
import csv
import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import queue
from difflib import SequenceMatcher

# --- Main Application Class ---
class SmartSorterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SmartSorter (Created by: Aminul)")
        self.geometry("1500x550")

        # --- Backend Logic (encapsulated) ---
        self.VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.mov', '.avi', '.wmv']
        self.THUMBNAIL_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        self.MINIMUM_THRESHOLD = 0.05
        self.DECREMENT_STEP = 0.05

        # --- GUI Widgets ---
        self.create_widgets()

    def create_widgets(self):
        # Frame for inputs
        input_frame = tk.Frame(self, padx=10, pady=10)
        input_frame.pack(fill='x', expand=False)

        # CSV Path
        tk.Label(input_frame, text="CSV File Path:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.csv_path_var = tk.StringVar()
        self.csv_entry = tk.Entry(input_frame, textvariable=self.csv_path_var, state='readonly', width=70)
        self.csv_entry.grid(row=0, column=1, sticky='ew')
        tk.Button(input_frame, text="Browse...", command=self.browse_csv).grid(row=0, column=2, padx=5)

        # Download Folder Path
        tk.Label(input_frame, text="Download Folder:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.folder_path_var = tk.StringVar()
        self.folder_entry = tk.Entry(input_frame, textvariable=self.folder_path_var, state='readonly', width=70)
        self.folder_entry.grid(row=1, column=1, sticky='ew')
        tk.Button(input_frame, text="Browse...", command=self.browse_folder).grid(row=1, column=2, padx=5)

        input_frame.grid_columnconfigure(1, weight=1)

        # Frame for controls
        control_frame = tk.Frame(self, padx=10, pady=5)
        control_frame.pack(fill='x', expand=False)

        self.live_mode_var = tk.BooleanVar()
        tk.Checkbutton(control_frame, text="Live Mode (Actually rename and move files)", variable=self.live_mode_var).pack(side='left')

        self.start_button = tk.Button(control_frame, text="Start Processing", command=self.start_processing, bg="#4CAF50", fg="white", font=('Helvetica', 10, 'bold'))
        self.start_button.pack(side='right', padx=10)
        
        # Log window
        log_frame = tk.Frame(self, padx=10, pady=10)
        log_frame.pack(fill='both', expand=True)
        self.log_widget = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, height=20)
        self.log_widget.pack(fill='both', expand=True)

    def browse_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All files", "*.*")])
        if filepath:
            self.csv_path_var.set(filepath)

    def browse_folder(self):
        folderpath = filedialog.askdirectory()
        if folderpath:
            self.folder_path_var.set(folderpath)
            
    def log(self, message):
        self.log_widget.config(state='normal')
        self.log_widget.insert(tk.END, message + "\n")
        self.log_widget.config(state='disabled')
        self.log_widget.see(tk.END)

    def start_processing(self):
        csv_path = self.csv_path_var.get()
        folder_path = self.folder_path_var.get()
        is_live = self.live_mode_var.get()

        if not csv_path or not folder_path:
            messagebox.showerror("Error", "Please select both a CSV file and a download folder.")
            return

        if is_live:
            if not messagebox.askyesno("Confirm Live Mode", "You are in LIVE MODE. Files will be permanently renamed and moved. Are you sure you want to continue?"):
                return
        
        self.start_button.config(state='disabled', text="Processing...")
        self.log_widget.config(state='normal')
        self.log_widget.delete(1.0, tk.END)
        self.log_widget.config(state='disabled')

        # Run the backend logic in a separate thread to keep the GUI responsive
        self.processing_thread = threading.Thread(target=self.run_backend_logic, args=(csv_path, folder_path, is_live))
        self.processing_thread.start()
        
    def run_backend_logic(self, csv_path, folder_path, is_live):
        if not is_live:
            self.log("\n*** DRY RUN MODE IS ON. NO FILES WILL BE CHANGED. ***\n")
        else:
            self.log("\n*** LIVE MODE IS ON. FILES WILL BE RENAMED AND MOVED. ***\n")

        # --- The entire backend logic from the previous script goes here ---
        # (Slightly adapted to use the self.log() method)
        
        def load_csv_data(filepath):
            # ... (same as before) ...
            if not os.path.exists(filepath):
                self.log(f"--- ERROR: CSV file not found at '{filepath}'")
                return None
            video_data = []
            try:
                with open(filepath, mode='r', encoding='utf-8-sig') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader: video_data.append(row)
                self.log(f"--- Successfully loaded {len(video_data)} rows from CSV.")
                return video_data
            except Exception as e:
                self.log(f"--- ERROR: Could not read CSV file. Reason: {e}")
                return None

        def clean_filename_for_matching(filename):
             # ... (same as before) ...
            name, _ = os.path.splitext(filename)
            patterns_to_remove = [
                r'\s*\(1920p_25fps_H264-128kbit_AAC\)', r'\s*\(BQ\)', r'\s*\(HQ\)',
                r'\s*¦\s*#shorts', r'\s*#shorts', r'Leo the Wildlife Ranger'
            ]
            cleaned_name = name
            for pattern in patterns_to_remove:
                cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)
            cleaned_name = cleaned_name.replace('¦', '|').strip()
            return cleaned_name
        
        def find_best_match(cleaned_title, csv_data):
            # ... (same as before) ...
            best_score, best_match = 0, None
            for entry in csv_data:
                csv_title = entry.get('title', '')
                normalized_csv_title = csv_title.replace('|', '').strip()
                score = SequenceMatcher(None, cleaned_title, normalized_csv_title).ratio()
                if score > best_score:
                    best_score, best_match = score, entry
            return best_match, score
            
        def sanitize_for_filename(text):
            return re.sub(r'[\\/*?:"<>|]', "", text)

        video_data = load_csv_data(csv_path)
        if not video_data: 
            self.start_button.config(state='normal', text="Start Processing")
            return

        videos_dir = os.path.join(folder_path, "Videos")
        thumbnails_dir = os.path.join(folder_path, "Thumbnails")
        if not is_live:
            self.log("Dry Run: Would create 'Videos' and 'Thumbnails' directories if they don't exist.")
        else:
            os.makedirs(videos_dir, exist_ok=True)
            os.makedirs(thumbnails_dir, exist_ok=True)

        total_renamed_count = 0
        current_threshold = 0.6 # Initial Threshold
        pass_num = 1
        
        while current_threshold >= self.MINIMUM_THRESHOLD:
            files_to_process = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
            if not files_to_process:
                self.log("--- No more files to process. All tasks complete. ---")
                break
            
            self.log(f"\n--- Starting Pass #{pass_num} (Threshold: {current_threshold:.2f}) ---")
            
            processed_in_this_pass = 0
            
            for filename in files_to_process:
                if filename.endswith(".py"): continue

                cleaned_name = clean_filename_for_matching(filename)
                best_match, score = find_best_match(cleaned_name, video_data)
                
                if score > current_threshold:
                    _, extension = os.path.splitext(filename)
                    target_dir = None
                    if extension.lower() in self.VIDEO_EXTENSIONS: target_dir = videos_dir
                    elif extension.lower() in self.THUMBNAIL_EXTENSIONS: target_dir = thumbnails_dir
                    if not target_dir: continue

                    original_title, index = best_match['title'], best_match['index']
                    sanitized_title = sanitize_for_filename(original_title)
                    new_filename = f"{index} - {sanitized_title}{extension}"
                    
                    old_filepath = os.path.join(folder_path, filename)
                    new_filepath = os.path.join(target_dir, new_filename)
                    relative_new_path = os.path.relpath(new_filepath, start=folder_path)
                    
                    self.log(f"MATCH: '{filename}' -> '{relative_new_path}' (Score: {score:.2f})")
                    processed_in_this_pass += 1

                    if not is_live:
                        os.rename(old_filepath, old_filepath) # No-op to allow the loop to continue
                    else:
                        try:
                            os.rename(old_filepath, new_filepath)
                            self.log("  -> RENAMED & MOVED")
                        except Exception as e:
                            self.log(f"  -> ERROR: Could not move/rename file. Reason: {e}")
            
            total_renamed_count += processed_in_this_pass
            if processed_in_this_pass == 0: self.log("--- No new matches found in this pass. ---")

            current_threshold -= self.DECREMENT_STEP
            pass_num += 1

        self.log("\n---------------------------------------------")
        self.log("Process Complete.")
        final_skipped_files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and not f.endswith(".py")]
        
        if not is_live:
            self.log(f"Total files that would be moved: {total_renamed_count}")
        else:
            self.log(f"Total Renamed & Moved: {total_renamed_count} file(s)")
        
        self.log(f"Skipped (unmatched): {len(final_skipped_files)} file(s)")
        if final_skipped_files:
            self.log("  Unmatched files remain in the root directory.")
        self.log("======================================================")
        
        self.start_button.config(state='normal', text="Start Processing")


if __name__ == "__main__":
    app = SmartSorterApp()
    app.mainloop()