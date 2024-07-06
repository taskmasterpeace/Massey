import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from openai import OpenAI
import threading
import queue
from pydub import AudioSegment
import time
import emoji

class TranscriptionApp:
    def __init__(self, master):
        self.master = master
        self.master.title("MP3 Transcription App")
        self.master.geometry("800x600")

        self.api_key = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.overall_progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar()
        self.status_var.set("Ready 🔍")
        self.only_large_files = tk.BooleanVar()

        self.create_widgets()
        self.file_progress = {}
        self.transcription_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.total_files = 0
        self.completed_files = 0

    def create_widgets(self):
        # API Key
        tk.Label(self.master, text="OpenAI API Key:").pack(pady=5)
        tk.Entry(self.master, textvariable=self.api_key, show="*", width=50).pack()

        # Folder Selection
        folder_frame = tk.Frame(self.master)
        folder_frame.pack(pady=10)
        tk.Label(folder_frame, text="Select Folder:").pack(side=tk.LEFT)
        tk.Entry(folder_frame, textvariable=self.folder_path, width=40).pack(side=tk.LEFT, padx=5)
        tk.Button(folder_frame, text="Browse", command=self.select_folder).pack(side=tk.LEFT)

        # Checkbox for large files only
        tk.Checkbutton(self.master, text="Only transcribe files > 25MB", variable=self.only_large_files).pack()

        # Transcribe Button
        tk.Button(self.master, text="Transcribe", command=self.start_transcription).pack(pady=10)

        # Overall Progress Bar
        tk.Label(self.master, text="Overall Progress:").pack()
        self.overall_progress_bar = ttk.Progressbar(self.master, variable=self.overall_progress_var, maximum=100, length=700)
        self.overall_progress_bar.pack(pady=5)

        # Status Label
        self.status_label = tk.Label(self.master, textvariable=self.status_var, wraplength=700, font=("Segoe UI Emoji", 10))
        self.status_label.pack(pady=5)

        # Individual File Progress Frame
        self.file_progress_frame = tk.Frame(self.master)
        self.file_progress_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        # Scrollable Frame for File Progress
        self.canvas = tk.Canvas(self.file_progress_frame)
        self.scrollbar = ttk.Scrollbar(self.file_progress_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.file_progress_frame.pack(fill="both", expand=True)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def update_status(self, message, emoji_code):
        emoji_message = f"{emoji.emojize(emoji_code)} {message}"
        self.status_var.set(emoji_message)
        self.master.update_idletasks()

    def update_file_progress(self, file_name, status, progress):
        if file_name not in self.file_progress:
            frame = tk.Frame(self.scrollable_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            label = tk.Label(frame, text=file_name, width=30, anchor='w')
            label.pack(side=tk.LEFT)
            progress_bar = ttk.Progressbar(frame, length=200, maximum=100)
            progress_bar.pack(side=tk.LEFT, padx=5)
            status_label = tk.Label(frame, text="", width=20)
            status_label.pack(side=tk.LEFT)
            self.file_progress[file_name] = (frame, progress_bar, status_label)
        
        _, progress_bar, status_label = self.file_progress[file_name]
        progress_bar['value'] = progress
        status_label.config(text=status)
        
        if status == "Completed" and progress == 100:
            self.completed_files += 1
        
        self.update_overall_progress()
        self.master.update_idletasks()

    def update_overall_progress(self):
        if self.total_files > 0:
            progress = (self.completed_files / self.total_files) * 100
            self.overall_progress_var.set(progress)
            if self.completed_files == self.total_files:
                self.update_status("Transcription complete", ":party_popper:")
            else:
                self.update_status(f"Processing files... ({self.completed_files}/{self.total_files})", ":gear:")

    def start_transcription(self):
        self.stop_event.clear()
        threading.Thread(target=self.pre_check_and_transcribe, daemon=True).start()

    def pre_check_and_transcribe(self):
        api_key = self.api_key.get()
        folder_path = self.folder_path.get()

        if not api_key or not folder_path:
            messagebox.showerror("Error", "Please enter API key and select a folder.")
            return

        self.update_status("Pre-checking files...", ":mag:")
        mp3_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.mp3')]
        total_files = len(mp3_files)
        files_to_process = []

        for i, file_name in enumerate(mp3_files, 1):
            if self.stop_event.is_set():
                return

            file_path = os.path.join(folder_path, file_name)
            transcript_path = self.get_transcript_path(file_path)
            
            if os.path.exists(transcript_path):
                self.update_file_progress(file_name, "Skipped (exists)", 100)
            else:
                files_to_process.append(file_path)
                self.update_file_progress(file_name, "Queued", 0)
            
            self.overall_progress_var.set(i / total_files * 50)  # Pre-check is 50% of overall progress

        self.total_files = len(files_to_process)
        self.completed_files = 0
        self.update_status(f"Pre-check complete. Processing {self.total_files} files.", ":rocket:")
        self.transcribe_files(api_key, files_to_process)

    def transcribe_files(self, api_key, files_to_process):
        client = OpenAI(api_key=api_key)

        for i, file_path in enumerate(files_to_process, 1):
            if self.stop_event.is_set():
                break

            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            is_large_file = file_size > 25 * 1024 * 1024

            if self.only_large_files.get() and not is_large_file:
                self.update_file_progress(file_name, "Skipped (size)", 100)
                self.completed_files += 1
                continue

            if is_large_file:
                self.split_and_queue_file(file_path)
            else:
                self.queue_file(file_path)

        self.update_status("Processing queued files...", ":gear:")
        threading.Thread(target=self.process_queue, args=(client,), daemon=True).start()

    def split_and_queue_file(self, file_path):
        file_name = os.path.basename(file_path)
        self.update_file_progress(file_name, "Splitting", 25)
        
        audio = AudioSegment.from_mp3(file_path)
        mid_point = len(audio) // 2
        part1 = audio[:mid_point]
        part2 = audio[mid_point:]

        base_name = os.path.splitext(file_name)[0]
        part1_name = f"{base_name}_part1.mp3"
        part2_name = f"{base_name}_part2.mp3"
        part1_path = os.path.join(os.path.dirname(file_path), part1_name)
        part2_path = os.path.join(os.path.dirname(file_path), part2_name)

        self.update_file_progress(file_name, "Saving parts", 50)
        part1.export(part1_path, format="mp3")
        part2.export(part2_path, format="mp3")

        self.update_file_progress(file_name, "Queued", 75)
        self.queue_file(part1_path)
        self.queue_file(part2_path)

    def queue_file(self, file_path):
        file_name = os.path.basename(file_path)
        self.transcription_queue.put(file_path)
        self.update_file_progress(file_name, "Queued", 0)

    def process_queue(self, client):
        while not self.transcription_queue.empty() and not self.stop_event.is_set():
            file_path = self.transcription_queue.get()
            self.transcribe_file(client, file_path)
        self.update_overall_progress()
        self.show_summary()

    def transcribe_file(self, client, file_path):
        file_name = os.path.basename(file_path)
        try:
            self.update_file_progress(file_name, "Uploading", 25)

            with open(file_path, "rb") as audio_file:
                self.update_file_progress(file_name, "Transcribing", 50)
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )

            self.update_file_progress(file_name, "Saving", 75)
            transcript_path = self.get_transcript_path(file_path)
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript.text)

            self.update_file_progress(file_name, "Completed", 100)

        except Exception as e:
            self.update_file_progress(file_name, f"Failed: {str(e)}", 100)

    def get_transcript_path(self, file_path):
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        return os.path.join(os.path.dirname(file_path), f"{base_name}_transcript.txt")

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)

    def show_summary(self):
        summary = f"Transcription complete.\n"
        summary += f"Successfully transcribed: {self.completed_files}/{self.total_files}\n"
        if self.completed_files < self.total_files:
            failed = self.total_files - self.completed_files
            summary += f"Failed: {failed}\n"
        messagebox.showinfo("Transcription Summary", summary)

if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()