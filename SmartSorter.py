import os
import csv
import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
from difflib import SequenceMatcher

# --- Main Application Class ---
class SmartSorterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SmartSorter (Created by: Aminul)")
        self.geometry("1000x600") # Increased height for better logging view

        # --- Backend Logic (encapsulated) ---
        self.VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.mov', '.avi', '.wmv', '.webm']
        self.THUMBNAIL_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        self.DECREMENT_STEP = 0.05
        self.YOUTUBE_ID_MATCH_THRESHOLD = 0.8 # Corresponds to a 0.2 mismatch tolerance

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
        # Ensure UI updates happen on the main thread
        self.after(0, self._log_update, message)
        
    def _log_update(self, message):
        self.log_widget.config(state='normal')
        self.log_widget.insert(tk.END, message + "\n")
        self.log_widget.config(state='disabled')
        self.log_widget.see(tk.END)

    def start_processing(self):
        csv_path = self.csv_path_var.get()
        folder_path = self.folder_path_var.get()

        if not csv_path or not folder_path:
            messagebox.showerror("Error", "Please select both a CSV file and a download folder.")
            return

        if not messagebox.askyesno("Confirm Action", "This will permanently rename and move files. Are you sure you want to continue?"):
            return
        
        self.start_button.config(state='disabled', text="Processing...")
        self.log_widget.config(state='normal')
        self.log_widget.delete(1.0, tk.END)
        self.log_widget.config(state='disabled')

        self.processing_thread = threading.Thread(target=self.run_backend_logic, args=(csv_path, folder_path))
        self.processing_thread.start()
        
    def run_backend_logic(self, csv_path, folder_path):
        self.log("\n*** LIVE MODE IS ON. FILES WILL BE RENAMED AND MOVED. ***\n")
        
        def extract_youtube_id(text):
            """Extracts an 11-character YouTube ID from a URL or filename."""
            if not text:
                return None
            # --- MODIFIED --- More specific regex to avoid ambiguity with full URLs as filenames
            match = re.search(r'(?:watch\?v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})', text)
            return match.group(1) if match else None

        def load_csv_data(filepath):
            if not os.path.exists(filepath):
                self.log(f"--- ERROR: CSV file not found at '{filepath}'")
                return None
            video_data = []
            try:
                with open(filepath, mode='r', encoding='utf-8-sig', errors='ignore') as csvfile:
                    reader = csv.DictReader(csvfile)
                    headers = [h.lower() for h in reader.fieldnames]
                    title_key = next((h for h in reader.fieldnames if h.lower() == 'title'), None)
                    index_key = next((h for h in reader.fieldnames if h.lower() == 'index'), None)
                    url_key = next((h for h in reader.fieldnames if h.lower() == 'url'), None)

                    if not title_key or not index_key:
                        self.log(f"--- ERROR: CSV must contain 'title' and 'index' columns (case-insensitive).")
                        return None
                    
                    if url_key:
                        self.log("--- Found 'url' column. Will prioritize YouTube ID matching.")
                    else:
                        self.log("--- No 'url' column found. Proceeding with title matching only.")

                    for row in reader:
                        entry = {'title': row[title_key], 'index': row[index_key]}
                        if url_key and row[url_key]:
                            # Extract and store the YouTube ID directly
                            entry['youtube_id'] = extract_youtube_id(row[url_key])
                        video_data.append(entry)

                self.log(f"--- Successfully loaded {len(video_data)} rows from CSV.")
                return video_data
            except Exception as e:
                self.log(f"--- ERROR: Could not read CSV file. Reason: {e}")
                return None

        def clean_filename_for_matching(filename):
            name, _ = os.path.splitext(filename)
            patterns_to_remove = [
                r'\s*\(1920p_30fps_H264-128kbit_AAC\)', r'\s*\(1920p_25fps_H264-128kbit_AAC\)', r'\s*\(BQ\)', r'\s*\(HQ\)',
                r'\s*¦\s*#shorts', r'\s*#shorts', r'Leo the Wildlife Ranger'
            ]
            cleaned_name = name
            for pattern in patterns_to_remove: cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)
            cleaned_name = cleaned_name.replace('¦', '|').strip()
            return cleaned_name

        def find_best_match(cleaned_title, csv_data):
            best_score, best_match = 0, None
            for entry in csv_data:
                csv_title = entry.get('title', '')
                normalized_csv_title = csv_title.replace('|', '').strip()
                score = SequenceMatcher(None, cleaned_title, normalized_csv_title).ratio()
                if score > best_score: best_score, best_match = score, entry
            return best_match, score

        def find_all_matches_sorted(cleaned_title, csv_data):
            matches = []
            for entry in csv_data:
                csv_title = entry.get('title', '')
                normalized_csv_title = csv_title.replace('|', '').strip()
                score = SequenceMatcher(None, cleaned_title, normalized_csv_title).ratio()
                matches.append({'entry': entry, 'score': score})
            return sorted(matches, key=lambda x: x['score'], reverse=True)
            
        def sanitize_for_filename(text):
            return re.sub(r'[\\/*?:"<>|]', "", text)

        video_data = load_csv_data(csv_path)
        if not video_data: 
            self.after(0, lambda: self.start_button.config(state='normal', text="Start Processing"))
            return

        videos_dir = os.path.join(folder_path, "Videos")
        thumbnails_dir = os.path.join(folder_path, "Thumbnails")
        os.makedirs(videos_dir, exist_ok=True)
        os.makedirs(thumbnails_dir, exist_ok=True)

        total_renamed_count = 0
        
        # --- PHASE 0: YOUTUBE ID-BASED MATCHING ---
        self.log("\n--- Starting Phase 0: YouTube ID Matching ---")
        # Create a map of YouTube ID -> CSV data entry for fast lookups
        id_map = {entry['youtube_id']: entry for entry in video_data if 'youtube_id' in entry and entry['youtube_id']}
        
        if not id_map:
            self.log("--- No valid YouTube IDs found in CSV. Skipping this phase. ---")
        else:
            files_in_folder = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and not f.endswith(".py")]
            processed_in_this_phase = 0
            
            for filename in files_in_folder:
                # Extract potential YouTube ID from the filename itself
                id_from_filename = extract_youtube_id(filename)
                if not id_from_filename:
                    continue # Skip files that don't seem to have a YouTube ID

                match_entry = None
                match_type = ""
                score = 1.0

                # 1. Attempt Exact Match
                if id_from_filename in id_map:
                    match_entry = id_map[id_from_filename]
                    match_type = "Exact ID"
                
                # 2. Attempt Fuzzy Match if no exact match was found
                else:
                    best_id_score = 0
                    best_id_match = None
                    for csv_id, entry in id_map.items():
                        similarity = SequenceMatcher(None, id_from_filename, csv_id).ratio()
                        if similarity > best_id_score:
                            best_id_score = similarity
                            best_id_match = entry
                    
                    if best_id_score >= self.YOUTUBE_ID_MATCH_THRESHOLD:
                        match_entry = best_id_match
                        match_type = "Fuzzy ID"
                        score = best_id_score

                # If a match was found (either exact or fuzzy), process the file
                if match_entry:
                    _, extension = os.path.splitext(filename)
                    target_dir = None
                    if extension.lower() in self.VIDEO_EXTENSIONS: target_dir = videos_dir
                    elif extension.lower() in self.THUMBNAIL_EXTENSIONS: target_dir = thumbnails_dir
                    else: continue
                    
                    original_title, index = match_entry['title'], match_entry['index']
                    new_filename = f"{index} - {sanitize_for_filename(original_title)}{extension}"
                    new_filepath = os.path.join(target_dir, new_filename)

                    if not os.path.exists(new_filepath):
                        self.log(f"MATCH ({match_type}): '{filename}' -> '{os.path.relpath(new_filepath, folder_path)}' (Score: {score:.2f})")
                        try:
                            os.rename(os.path.join(folder_path, filename), new_filepath)
                            self.log("  -> RENAMED & MOVED")
                            processed_in_this_phase += 1
                        except Exception as e:
                            self.log(f"  -> ERROR: Could not move/rename. Reason: {e}")
                    else:
                        self.log(f"INFO: Destination for '{filename}' already exists: '{new_filename}'. Skipped.")
            
            total_renamed_count += processed_in_this_phase
            self.log(f"--- Processed {processed_in_this_phase} file(s) based on YouTube ID match. ---")


        # --- PHASE 1: HIGH-CONFIDENCE FUZZY MATCHING ---
        self.log("\n--- Starting Phase 1: High-Confidence Title Matching (for remaining files) ---")
        current_threshold = 0.6
        LAST_RESORT_THRESHOLD = 0.05
        pass_num = 1
        
        while current_threshold >= LAST_RESORT_THRESHOLD:
            files_to_process = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and not f.endswith(".py")]
            if not files_to_process: break
            
            self.log(f"\n--- Starting Pass #{pass_num} (Threshold: {current_threshold:.2f}) ---")
            processed_in_this_pass = 0
            
            for filename in files_to_process:
                cleaned_name = clean_filename_for_matching(filename)
                best_match, score = find_best_match(cleaned_name, video_data)
                
                if best_match and score >= current_threshold:
                    _, extension = os.path.splitext(filename)
                    target_dir = None
                    if extension.lower() in self.VIDEO_EXTENSIONS: target_dir = videos_dir
                    elif extension.lower() in self.THUMBNAIL_EXTENSIONS: target_dir = thumbnails_dir
                    else: continue

                    original_title, index = best_match['title'], best_match['index']
                    new_filename = f"{index} - {sanitize_for_filename(original_title)}{extension}"
                    new_filepath = os.path.join(target_dir, new_filename)
                    
                    if not os.path.exists(new_filepath):
                        self.log(f"MATCH (Title): '{filename}' -> '{os.path.relpath(new_filepath, folder_path)}' (Score: {score:.2f})")
                        try:
                            os.rename(os.path.join(folder_path, filename), new_filepath)
                            self.log("  -> RENAMED & MOVED")
                            processed_in_this_pass += 1
                        except Exception as e:
                            self.log(f"  -> ERROR: Could not move/rename. Reason: {e}")
                    else:
                        self.log(f"INFO: Best match for '{filename}' is taken. Will retry in last resort pass.")
            
            total_renamed_count += processed_in_this_pass
            if processed_in_this_pass == 0: self.log("--- No new high-confidence matches found in this pass. ---")
            
            current_threshold -= self.DECREMENT_STEP
            pass_num += 1

        # --- PHASE 2: LAST RESORT MATCHING ---
        self.log(f"\n\n--- Starting Phase 2: Last Resort Title Matching (For remaining files) ---")
        remaining_files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and not f.endswith(".py")]
        
        if not remaining_files:
            self.log("--- No remaining files to process. ---")
        else:
            processed_in_last_resort = 0
            for filename in remaining_files:
                cleaned_name = clean_filename_for_matching(filename)
                all_matches = find_all_matches_sorted(cleaned_name, video_data)
                
                file_renamed = False
                for match_info in all_matches:
                    if match_info['score'] < 0.01: 
                        break

                    best_match = match_info['entry']
                    score = match_info['score']
                    
                    _, extension = os.path.splitext(filename)
                    target_dir = None
                    if extension.lower() in self.VIDEO_EXTENSIONS: target_dir = videos_dir
                    elif extension.lower() in self.THUMBNAIL_EXTENSIONS: target_dir = thumbnails_dir
                    else: continue

                    original_title, index = best_match['title'], best_match['index']
                    new_filename = f"{index} - {sanitize_for_filename(original_title)}{extension}"
                    new_filepath = os.path.join(target_dir, new_filename)

                    if not os.path.exists(new_filepath):
                        self.log(f"MATCH (Last Resort): '{filename}' -> '{os.path.relpath(new_filepath, folder_path)}' (Score: {score:.2f})")
                        try:
                            os.rename(os.path.join(folder_path, filename), new_filepath)
                            self.log("  -> RENAMED & MOVED")
                            processed_in_last_resort += 1
                            file_renamed = True
                            break 
                        except Exception as e:
                            self.log(f"  -> ERROR: Could not move/rename. Reason: {e}")
                            break
            total_renamed_count += processed_in_last_resort
            if processed_in_last_resort > 0:
                 self.log(f"--- Found {processed_in_last_resort} matches in last resort pass. ---")
            else:
                 self.log("--- No new matches found in last resort pass. ---")


        self.log("\n---------------------------------------------")
        self.log("Process Complete.")
        final_skipped_files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and not f.endswith(".py")]
        self.log(f"Total Renamed & Moved: {total_renamed_count} file(s)")
        self.log(f"Skipped (unmatched): {len(final_skipped_files)} file(s)")
        if final_skipped_files:
            self.log("  Unmatched files remain in the root directory.")
        self.log("======================================================")
        
        # Ensure the button is re-enabled on the main thread
        self.after(0, lambda: self.start_button.config(state='normal', text="Start Processing"))

if __name__ == "__main__":
    app = SmartSorterApp()
    app.mainloop()
