# 🎙️ MASSY - MP3 to Text Transcription Application 📝
![python_rWYcWc6Ccv](https://github.com/taskmasterpeace/Massey/assets/47542160/b4b56d5f-f4c7-4898-a9b5-7146ec533236)

## 🌟 Overview

MASSY (MP3 to Audio Summarization SYstem) is a powerful tool designed to transcribe multiple MP3 audio files in bulk using OpenAI's state-of-the-art Whisper model. While it may seem like a simple bulk transcription tool on the surface, MASSY offers much more under the hood.

### 🚀 Key Features

- 🗃️ Bulk transcription of MP3 files
- 🔄 Automatic file splitting for large audio files
- 📄 Dual output formats: SRT (SubRip Subtitle) and plain text
- ⏱️ Precise timestamp information in SRT format
- 📊 Detailed transcription reports
- 🖥️ User-friendly GUI with progress tracking

## 🎯 Purpose

MASSY serves two primary purposes:

1. **Human-Readable Transcripts**: Generate plain text transcripts for easy reading and analysis.
2. **Machine-Readable Transcripts**: Create SRT files with timestamp information for advanced processing and analysis.

The SRT format allows for a deeper understanding of the audio content, including:
- Precise timing of spoken words
- Detection of silence or pauses
- Improved context for AI-driven analysis

## 🔧 How It Works

1. **File Selection**: Choose a folder containing MP3 files.
2. **Transcription**: MASSY uses OpenAI's Whisper model to transcribe each audio file.
3. **File Splitting**: Large files (>24MB) are automatically split and merged after transcription.
4. **Output Generation**: Creates SRT and/or plain text files based on user preference.
5. **Metadata Addition**: Adds relevant metadata to each transcript, including:
   - File name
   - Recording date (extracted from filename)
   - Duration
   - Transcription date
6. **Report Generation**: Produces a summary report of the transcription process.

## 🚀 Getting Started

### Prerequisites

- Python 3.7+
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/massy.git
   ```
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

### Usage

1. Run the application:
   ```
   python massy.py
   ```
2. Enter your OpenAI API key.
3. Select the folder containing your MP3 files.
4. Choose your preferred output format (SRT, Text, or Both).
5. Click "Transcribe" and monitor the progress.

## 🧠 Integration with AI Systems

MASSY is designed to be part of a larger AI-driven analysis system. The SRT output, with its precise timing information, is particularly useful for:

- 🔍 Semantic search and retrieval
- 📊 Time-based sentiment analysis
- 🗣️ Speaker diarization
- 🔗 Contextual understanding in language models

By providing both human-readable and machine-readable formats, MASSY bridges the gap between human interpretation and advanced AI analysis.

## 🤝 Contributing

We welcome contributions to MASSY! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to get started.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## 🙏 Acknowledgments

- OpenAI for the Whisper model
- All contributors and users of MASSY

---

🌟 Remember: MASSY is more than just a transcription tool – it's a bridge between human understanding and machine analysis of audio content!
