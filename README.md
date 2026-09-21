# JARVIS AI

A voice-controlled desktop assistant inspired by Tony Stark's J.A.R.V.I.S. It listens for the wake word **"Hey Jarvis"**, understands spoken commands, controls Chrome and your system, sees through your webcam, and replies out loud in a British voice — alongside a live animated HUD dashboard.

---

## ✨ Features

### 🎙️ Voice Interaction
- Wake word detection ("Hey Jarvis" / "Jarvis")
- Natural spoken commands, no fixed syntax
- British voice replies via Microsoft Edge TTS (`en-GB-RyanNeural`), with a `pyttsx3` fallback if Edge TTS fails
- Emergency stop hotkey: **Ctrl+Alt+X**

### 🌐 Browser Control (Chrome)
- Google search, open Google / YouTube / any website
- Scroll up/down, go back, refresh, new tab, close tab, close Chrome
- App-aware search inside YouTube, Amazon, or Spotify (once focused)

### 🎵 YouTube / Media
- Search YouTube and play the first result
- Play a specific result by number ("play video 3")
- Skip to next video, play/pause, volume up/down/mute

### 📱 WhatsApp
- Open WhatsApp Web
- Voice-call a contact (opens the chat and clicks the call icon)
- Send a message to whichever chat is currently open

### 👁️ Computer Vision
- "What do you see?" — captures a webcam frame and runs YOLOv8 object detection
- "Screen capture" — grabs a screenshot and asks Gemini to describe it

### 💻 System Control
- Volume up / down / mute
- Shutdown / restart / lock
- Open apps: Notepad, Calculator, Paint, CMD, PowerShell, File Explorer, VS Code, Spotify, Settings, Task Manager (or any app by name)

### 📝 Productivity
- Voice notes: "take note …", "read notes", "clear notes" (saved to `jarvis_notes.txt`)
- "list files", "open folder", "create folder [name]"
- Time, date, weather (via wttr.in), news headlines (BBC RSS), CPU/memory status

### 🖥️ Live HUD Dashboard
- `dashboard.html` opens automatically on startup — an animated arc-reactor-style interface built in HTML/CSS/canvas
- Connects to JARVIS over a local **WebSocket** (`ws://localhost:8765`) served by the bridge module
- Shows live state (standby / listening / processing / speaking), a scrolling command/response log, CPU & memory meters, wake count, and session uptime
- Falls back to a self-running demo animation if it can't connect, so the UI still looks alive without the backend running

---

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3 |
| AI / LLM | Google Gemini (`google-generativeai`, model `gemini-2.5-flash`) — free-form replies and screen-capture description |
| Computer Vision | Ultralytics YOLOv8 (`yolov8s.pt`), OpenCV |
| Speech → Text | `SpeechRecognition` (Google Web Speech API) + `PyAudio` for mic input |
| Text → Speech | `edge-tts` (fallback: `pyttsx3`) |
| Audio Playback | `pygame` |
| Desktop / Browser Automation | `pyautogui`, `pygetwindow`, `pywin32` (`win32gui`, `win32con`) |
| Hotkeys | `keyboard` |
| System Monitoring | `psutil` |
| Web / Data | `requests`, `beautifulsoup4`, `feedparser` |
| Screenshots | `Pillow` (`ImageGrab`) |
| Config | `python-dotenv` |
| Clipboard | `pyperclip` |
| Dashboard link | `websockets`, vanilla JS/HTML/CSS (canvas animation) |

---

## 📋 Prerequisites

- **Windows 10/11** — the code relies on Windows-only APIs (`pywin32`, `taskkill`, `shutdown`, `rundll32`) and will not run as-is on macOS/Linux
- **Python 3.9+**
- **Google Chrome**, installed at the default path (`C:\Program Files\Google\Chrome\...`) or discoverable via the system default browser
- A working **microphone** and **webcam**
- A **Google Gemini API key** — [get one here](https://aistudio.google.com/app/apikey)
- Internet connection (speech recognition, Gemini, weather, and news all call external services)

---

## 🚀 Setup

```bash
# 1. Clone the repo
git clone https://github.com/bappzzz/jarvis-ai.git
cd jarvis-ai

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install pywin32 ultralytics opencv-python

# 4. Add your Gemini API key
# Create a file named .env in the project root:
GEMINI_API_KEY=your_key_here
```

> ⚠️ **`requirements.txt` is currently missing `pywin32`, `ultralytics`, and `opencv-python`**, all of which `JARVIS.py` imports directly (for window focus and object detection). Add them to `requirements.txt` so a single `pip install -r requirements.txt` covers everything.

You'll also need, in the same folder as `JARVIS.py`:
- `jarvis_state.py` — the dashboard bridge module; runs the WebSocket server on port 8765 and exposes `bridge.start()`, `bridge.log()`, `bridge.set_state()`, `bridge.stats()`, `bridge.wake()`
- `dashboard.html` — included in this repo
- `yolov8s.pt` will download automatically the first time object detection runs, if not already present

---

## ▶️ Running

```bash
python JARVIS.py
```

On startup it opens the dashboard in your browser, greets you out loud, and starts listening. Say **"Hey Jarvis"**, wait for "Yes sir?", then speak a command. Say **"exit"** (or "quit" / "goodbye" / "stop" / "sleep") to put it back to sleep, or press **Ctrl+Alt+X** for an immediate shutdown.

---

## 🎤 Example Commands

| Say this | JARVIS does |
|---|---|
| "Hey Jarvis" | Wakes up and listens |
| "search latest AI news" | Opens Google and searches |
| "play [song]" | Searches YouTube and plays the first result |
| "search in youtube for cats" | Searches inside YouTube directly |
| "next video" | Skips to the next video |
| "call [name] on whatsapp" | Opens WhatsApp Web and calls the contact |
| "open whatsapp" | Opens WhatsApp Web |
| "what do you see" | Runs object detection on the webcam |
| "screen capture" | Describes what's on your screen |
| "take note buy groceries" | Saves a timestamped note |
| "read notes" | Reads back saved notes |
| "list files" | Lists files in the current folder |
| "create folder projects" | Makes a new folder |
| "open notepad" | Launches Notepad |
| "volume up" / "mute" | Adjusts system volume |
| "shutdown" / "restart" / "lock" | Controls the PC |
| "what's the weather" | Reports current weather |
| "news" | Reads top BBC headlines |
| "status" | Reports CPU and memory usage |
| Anything else | Passed to Gemini for a short spoken reply |

---

## 📁 Project Structure

```
jarvis-ai/
├── JARVIS.py           # Main entry point — voice loop, command processing
├── jarvis_state.py     # Dashboard bridge — WebSocket server + state broadcasting
├── dashboard.html       # Live HUD interface
├── requirements.txt
├── jarvis_notes.txt     # Auto-created when you save your first voice note
├── .env                 # Your Gemini API key (not committed)
└── README.md
```

---

## ⚠️ Known Limitations

- Windows-only: several features call Windows-specific commands directly
- Browser automation is coordinate/keystroke-based (`pyautogui`), so it can break if Chrome's window layout, zoom level, or page design changes
- "Calling" a WhatsApp contact clicks fixed screen coordinates — fragile, and may need tuning for different screen resolutions
- Requires the Chrome window to stay focusable; other windows stealing focus can interrupt automation
- No persistent conversation memory between sessions beyond the notes file

---

## 📜 License

Add a license of your choice (e.g., MIT) if you want others to be able to reuse this code.

---

## 🙋 Author

Built by **Rashin** — [GitHub](https://github.com/bappzzz)
