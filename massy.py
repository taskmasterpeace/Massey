import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
from openai import OpenAI
import json
from pydub import AudioSegment
import math
import datetime
import re
class TranscriptionApp:
    def __init__(self, master):
        self.master = master
        self.master.title("MASSY - MP3 to Text Transcription")
        self.master.geometry("1000x600")

        self.create_widgets()

        self.client = None
        self.stop_event = threading.Event()
        self.file_progress = {}
        self.completed_files = 0
        self.total_files = 0
        self.queued_files = []
        self.processed_files = []
        self.skipped_files = []

    def create_widgets(self):
        # API Key Entry
        tk.Label(self.master, text="OpenAI API Key:").pack()
        self.api_key_entry = tk.Entry(self.master, width=50, show="*")
        self.api_key_entry.pack()

        # Folder Selection
        tk.Button(self.master, text="Select MP3 Folder", command=self.select_folder).pack(pady=10)
        self.folder_path_var = tk.StringVar()
        tk.Label(self.master, textvariable=self.folder_path_var).pack()

        # Output Format Selection
        self.output_format_var = tk.StringVar(value="both")
        tk.Label(self.master, text="Output Format:").pack()
        tk.Radiobutton(self.master, text="SRT", variable=self.output_format_var, value="srt").pack()
        tk.Radiobutton(self.master, text="Text", variable=self.output_format_var, value="text").pack()
        tk.Radiobutton(self.master, text="Both", variable=self.output_format_var, value="both").pack()

        # Transcribe Button
        self.transcribe_button = tk.Button(self.master, text="Transcribe", command=self.start_transcription)
        self.transcribe_button.pack(pady=10)

        # Stop Button
        self.stop_button = tk.Button(self.master, text="Stop", command=self.stop_transcription, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        # Overall Progress Bar
        self.overall_progress = ttk.Progressbar(self.master, length=900, mode='determinate')
        self.overall_progress.pack(pady=10)

        # Progress Display
        self.progress_frame = tk.Frame(self.master)
        self.progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.progress_canvas = tk.Canvas(self.progress_frame)
        self.scrollbar_y = ttk.Scrollbar(self.progress_frame, orient="vertical", command=self.progress_canvas.yview)
        self.scrollbar_x = ttk.Scrollbar(self.progress_frame, orient="horizontal", command=self.progress_canvas.xview)
        self.scrollable_frame = tk.Frame(self.progress_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.progress_canvas.configure(
                scrollregion=self.progress_canvas.bbox("all")
            )
        )

        self.progress_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.progress_canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)

        self.progress_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar_y.pack(side="right", fill="y")
        self.scrollbar_x.pack(side="bottom", fill="x")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path_var.set(folder_path)

    def start_transcription(self):
        api_key = self.api_key_entry.get()
        folder_path = self.folder_path_var.get()

        if not api_key or not folder_path:
            messagebox.showerror("Error", "Please enter API key and select a folder.")
            return

        self.client = OpenAI(api_key=api_key)
        self.stop_event.clear()
        self.transcribe_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Clear previous progress displays
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.queued_files = []
        self.processed_files = []
        self.skipped_files = []

        threading.Thread(target=self.process_files, args=(folder_path,), daemon=True).start()

    def stop_transcription(self):
        self.stop_event.set()
        self.stop_button.config(state=tk.DISABLED)

    def process_files(self, folder_path):
        mp3_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.mp3')]
        self.total_files = len(mp3_files)
        self.completed_files = 0

        for file_name in mp3_files:
            if self.stop_event.is_set():
                break

            file_path = os.path.join(folder_path, file_name)
            file_size = os.path.getsize(file_path)

            if file_size > 24 * 1024 * 1024:  # 24 MB
                self.split_and_transcribe(file_path)
            else:
                self.transcribe_file(self.client, file_path)

        self.generate_report()
        self.transcribe_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        messagebox.showinfo("Transcription Complete", f"Processed {self.completed_files} out of {self.total_files} files.")

    def split_and_transcribe(self, file_path):
        file_name = os.path.basename(file_path)
        self.update_file_progress(file_name, "Splitting", 10)

        audio = AudioSegment.from_mp3(file_path)
        duration_ms = len(audio)
        chunk_size_ms = 12 * 60 * 1000  # 12 minutes in milliseconds
        num_chunks = math.ceil(duration_ms / chunk_size_ms)

        for i in range(num_chunks):
            if self.stop_event.is_set():
                break

            start = i * chunk_size_ms
            end = min((i + 1) * chunk_size_ms, duration_ms)
            chunk = audio[start:end]

            chunk_name = f"{os.path.splitext(file_name)[0]}_part{i+1}.mp3"
            chunk_path = os.path.join(os.path.dirname(file_path), chunk_name)
            chunk.export(chunk_path, format="mp3")

            self.transcribe_file(self.client, chunk_path, original_file=file_name)

        self.merge_transcripts(file_path, num_chunks)

    def transcribe_file(self, client, file_path, original_file=None):
        file_name = os.path.basename(file_path)
        try:
            self.update_file_progress(original_file or file_name, "Uploading", 25)
            with open(file_path, "rb") as audio_file:
                self.update_file_progress(original_file or file_name, "Transcribing", 50)
                
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="srt"
                )
                
                self.update_file_progress(original_file or file_name, "Saving transcript", 75)
                
                # Save SRT file
                if self.output_format_var.get() in ["srt", "both"]:
                    srt_path = self.get_transcript_path(file_path, "srt")
                    with open(srt_path, "w", encoding="utf-8") as f:
                        f.write(self.add_metadata_to_srt(transcript, file_name))
                
                # Save text file
                if self.output_format_var.get() in ["text", "both"]:
                    text_path = self.get_transcript_path(file_path, "txt")
                    with open(text_path, "w", encoding="utf-8") as f:
                        f.write(self.clean_transcript(transcript, file_name))
            
            if not original_file:
                self.update_file_progress(file_name, "Completed", 100)
                self.completed_files += 1
                self.processed_files.append(file_name)
            else:
                self.update_file_progress(original_file, f"Processed part {file_name}", 75)

        except Exception as e:
            error_message = str(e)
            self.update_file_progress(original_file or file_name, f"Failed: {error_message}", 100)
            self.skipped_files.append((original_file or file_name, error_message))

    def merge_transcripts(self, original_file_path, num_chunks):
        file_name = os.path.basename(original_file_path)
        self.update_file_progress(file_name, "Merging transcripts", 90)

        base_name = os.path.splitext(file_name)[0]
        merged_srt = ""
        merged_text = ""

        for i in range(num_chunks):
            chunk_name = f"{base_name}_part{i+1}.mp3"
            chunk_path = os.path.join(os.path.dirname(original_file_path), chunk_name)

            if self.output_format_var.get() in ["srt", "both"]:
                srt_path = self.get_transcript_path(chunk_path, "srt")
                with open(srt_path, "r", encoding="utf-8") as f:
                    merged_srt += f.read() + "\n\n"
                os.remove(srt_path)

            if self.output_format_var.get() in ["text", "both"]:
                text_path = self.get_transcript_path(chunk_path, "txt")
                with open(text_path, "r", encoding="utf-8") as f:
                    merged_text += f.read() + "\n\n"
                os.remove(text_path)

            os.remove(chunk_path)

        if self.output_format_var.get() in ["srt", "both"]:
            merged_srt_path = self.get_transcript_path(original_file_path, "srt")
            with open(merged_srt_path, "w", encoding="utf-8") as f:
                f.write(self.add_metadata_to_srt(merged_srt, file_name))

        if self.output_format_var.get() in ["text", "both"]:
            merged_text_path = self.get_transcript_path(original_file_path, "txt")
            with open(merged_text_path, "w", encoding="utf-8") as f:
                f.write(self.add_metadata_to_text(merged_text, file_name))

        self.update_file_progress(file_name, "Completed", 100)
        self.completed_files += 1
        self.processed_files.append(file_name)

    def get_transcript_path(self, file_path, extension):
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        return os.path.join(os.path.dirname(file_path), f"{base_name}_transcript.{extension}")

    def update_file_progress(self, file_name, status, progress):
        if file_name not in self.file_progress:
            frame = tk.Frame(self.scrollable_frame)
            frame.pack(fill=tk.X, padx=5, pady=5)

            label = tk.Label(frame, text=file_name, width=40, anchor="w")
            label.pack(side=tk.LEFT)

            progress_bar = ttk.Progressbar(frame, length=200, mode='determinate')
            progress_bar.pack(side=tk.LEFT, padx=5)

            status_label = tk.Label(frame, text="", width=50, anchor="w")
            status_label.pack(side=tk.LEFT)

            self.file_progress[file_name] = {"frame": frame, "progress": progress_bar, "status": status_label}

        self.file_progress[file_name]["progress"]["value"] = progress
        self.file_progress[file_name]["status"].config(text=status)
        self.update_overall_progress()

    def update_overall_progress(self):
        overall_progress = (self.completed_files / self.total_files) * 100
        self.overall_progress["value"] = overall_progress
        self.master.update_idletasks()

    def clean_transcript(self, srt_content, file_name):
        # Remove line numbers, timestamps, and empty lines
        cleaned = re.sub(r'^\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', srt_content, flags=re.MULTILINE)
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        
        # Join lines and remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Add proper spacing after punctuation
        cleaned = re.sub(r'([.!?])(\S)', r'\1 \2', cleaned)
        
        # Split into paragraphs (every 5 sentences)
        sentences = re.split(r'(?<=[.!?]) +', cleaned)
        paragraphs = [' '.join(sentences[i:i+5]) for i in range(0, len(sentences), 5)]
        
        # Add metadata
        return self.add_metadata_to_text('\n\n'.join(paragraphs), file_name)

    def add_metadata_to_srt(self, srt_content, file_name):
        recording_date = self.extract_date_from_filename(file_name)
        total_duration = self.get_total_duration(srt_content)
        
        metadata = (f"File: {file_name}\n"
                    f"Recording Date: {recording_date}\n"
                    f"Duration: {total_duration}\n"
                    f"Transcription Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        return metadata + srt_content

    def add_metadata_to_text(self, text_content, file_name):
        recording_date = self.extract_date_from_filename(file_name)
        total_duration = self.get_total_duration_from_text(text_content)
        
        metadata = (f"File: {file_name}\n"
                    f"Recording Date: {recording_date}\n"



                    def add_metadata_to_text(self, text_content, file_name):
        recording_date = self.extract_date_from_filename(file_name)
        total_duration = self.get_total_duration_from_text(text_content)
        
        metadata = (f"File: {file_name}\n"
                    f"Recording Date: {recording_date}\n"
                    f"Duration: {total_duration}\n"
                    f"Transcription Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        return metadata + text_content

    def extract_date_from_filename(self, file_name):
        date_match = re.search(r'(\d{6})_', file_name)
        if date_match:
            date_str = date_match.group(1)
            return datetime.datetime.strptime(date_str, '%y%m%d').strftime('%Y-%m-%d')
        return "Unknown"

    def get_total_duration(self, srt_content):
        last_timestamp = re.findall(r'\d{2}:\d{2}:\d{2},\d{3}', srt_content)[-1]
        time_parts = last_timestamp.split(':')
        hours, minutes, seconds = map(float, [time_parts[0], time_parts[1], time_parts[2].replace(',', '.')])
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return f"{int(total_seconds // 3600):02d}:{int((total_seconds % 3600) // 60):02d}:{total_seconds % 60:05.2f}"

    def get_total_duration_from_text(self, text_content):
        # Assuming the duration is included in the metadata of the text file
        duration_match = re.search(r'Duration: (\d{2}:\d{2}:\d{2}\.\d{2})', text_content)
        if duration_match:
            return duration_match.group(1)
        return "Unknown"

    def generate_report(self):
        report_filename = f"transcript_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = os.path.join(self.folder_path_var.get(), report_filename)
        
        with open(report_path, "w", encoding="utf-8") as report_file:
            report_file.write(f"MASSY Transcription Report\n")
            report_file.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            report_file.write(f"Total files processed: {self.total_files}\n")
            report_file.write(f"Successfully transcribed: {len(self.processed_files)}\n")
            report_file.write(f"Skipped files: {len(self.skipped_files)}\n\n")
            
            report_file.write("Processed Files:\n")
            for file in self.processed_files:
                report_file.write(f"- {file}\n")
            
            report_file.write("\nSkipped Files:\n")
            for file, reason in self.skipped_files:
                report_file.write(f"- {file}: {reason}\n")

        messagebox.showinfo("Report Generated", f"Transcription report saved as {report_filename}")

if __name__ == "__main__":
    app = TranscriptionApp(root)
    root.mainloop()