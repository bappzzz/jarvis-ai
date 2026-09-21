import os
import time
import sys
import subprocess
import webbrowser
import keyboard
import speech_recognition as sr
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
import pyautogui
import pyperclip
import pygetwindow as gw
import psutil
import requests
from bs4 import BeautifulSoup
import threading
from PIL import ImageGrab, Image
import edge_tts
import asyncio
import pygame
import io
import tempfile

# --- DASHBOARD BRIDGE ---
from jarvis_state import bridge

# --- FOCUS HELPERS (Windows API) ---
try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("⚠️  pywin32 not installed. Run: pip install pywin32")

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# ============================================================
# EDGE TTS VOICE
# ============================================================

def speak(text):
    """Speak using Microsoft Edge TTS"""
    bridge.set_state("speaking")
    bridge.log("jarvis", text)

    try:
        if len(text) > 300:
            text = text[:300] + "..."

        voice = "en-GB-RyanNeural"

        async def _generate():
            communicate = edge_tts.Communicate(text, voice)
            audio_bytes = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes += chunk["data"]
            return audio_bytes

        audio_data = asyncio.run(_generate())

        if not audio_data or len(audio_data) < 100:
            print(f"⚠️  Edge TTS returned {len(audio_data)} bytes - fallback")
            return speak_fallback(text)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.write(audio_data)
        tmp.close()
        tmp_path = tmp.name

        try:
            pygame.mixer.quit()
        except:
            pass

        pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=512)
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.set_volume(1.0)
        pygame.mixer.music.play()

        timeout = time.time() + 30
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
            if time.time() > timeout:
                break

        pygame.mixer.music.unload()
        time.sleep(0.2)

        try:
            os.remove(tmp_path)
        except:
            pass

        print(f"🔊 JARVIS: {text}")
        bridge.set_state("idle")
        return True

    except Exception as e:
        print(f"⚠️  Edge TTS error: {e}")
        return speak_fallback(text)


def speak_fallback(text):
    """Fallback using pyttsx3"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        if voices:
            engine.setProperty("voice", voices[0].id)
        engine.setProperty("volume", 1.0)
        engine.setProperty("rate", 150)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        print(f"🔊 JARVIS (fallback): {text}")
        bridge.set_state("idle")
        return True
    except Exception as e:
        print(f"💬 JARVIS would say: {text}")
        bridge.set_state("idle")
        return False


# ============================================================
# WINDOW FOCUS
# ============================================================

def force_focus_chrome():
    if not WIN32_AVAILABLE:
        return focus_chrome_legacy()
    try:
        chrome_windows = []
        def enum_handler(hwnd, result):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if "Chrome" in title or "Google Chrome" in title:
                    chrome_windows.append(hwnd)
            return True
        win32gui.EnumWindows(enum_handler, None)
        if chrome_windows:
            hwnd = chrome_windows[0]
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.3)
            return True
        return False
    except Exception as e:
        print(f"Focus error: {e}")
        return focus_chrome_legacy()


def focus_chrome_legacy():
    for attempt in range(5):
        for title in ["Google Chrome", "Chrome", " - Google Chrome"]:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                try:
                    windows[0].activate()
                    time.sleep(0.3)
                    return True
                except:
                    pass
        time.sleep(0.5)
    return False


def ensure_focused():
    for attempt in range(3):
        if force_focus_chrome():
            return True
        time.sleep(0.5)
    return False


def focus_window(title_keyword):
    try:
        windows = gw.getWindowsWithTitle(title_keyword)
        if windows:
            windows[0].activate()
            time.sleep(0.3)
            return True
        return False
    except:
        return False


# ============================================================
# BROWSER
# ============================================================

chrome_opened = False


def open_chrome_with_url(url):
    global chrome_opened
    try:
        chrome_paths = [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        ]
        if not url.startswith("http"):
            url = "https://" + url
        for path in chrome_paths:
            if os.path.exists(path):
                subprocess.Popen([path, url])
                time.sleep(3)
                force_focus_chrome()
                chrome_opened = True
                return True
        webbrowser.open(url)
        time.sleep(2)
        force_focus_chrome()
        chrome_opened = True
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def search_google(query):
    global chrome_opened
    if not query:
        return "What to search?"
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    if chrome_opened:
        if ensure_focused():
            time.sleep(0.5)
            try:
                pyautogui.hotkey('ctrl', 't')
                time.sleep(0.5)
                pyautogui.write(search_url)
                time.sleep(0.3)
                pyautogui.press('enter')
                return f"Searching for {query}"
            except:
                open_chrome_with_url(search_url)
                return f"Searching for {query}"
    open_chrome_with_url(search_url)
    return f"Searching for {query}"


# ============================================================
# YOUTUBE
# ============================================================

def youtube_search(query):
    try:
        q = query.replace(' ', '+')
        url = f"https://www.youtube.com/results?search_query={q}"
        open_chrome_with_url(url)
        time.sleep(4)
        if not ensure_focused():
            return "Chrome not focused"
        return f"Searching YouTube for {query}"
    except Exception as e:
        return f"Could not search YouTube: {e}"


def youtube_play_first_video():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(1)
        positions = [(300, 300), (400, 350), (350, 320), (500, 300), (250, 280)]
        for x, y in positions:
            try:
                pyautogui.moveTo(x, y, duration=0.3)
                pyautogui.click()
                time.sleep(1)
                return "Playing first video"
            except:
                continue
        pyautogui.press('/')
        time.sleep(0.5)
        pyautogui.press('tab')
        time.sleep(0.3)
        pyautogui.press('enter')
        return "Playing first video"
    except Exception as e:
        return f"Could not play: {e}"


def youtube_play_video_number(n):
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(1)
        y_pos = 280 + (n - 1) * 120
        pyautogui.moveTo(300, y_pos, duration=0.5)
        pyautogui.click()
        return f"Playing video {n}"
    except:
        return f"Could not play video {n}"


def youtube_next_video():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(0.3)
        pyautogui.hotkey('shift', 'n')
        return "Skipping to next video"
    except:
        return "Could not skip"


def play_song_youtube(song_name):
    try:
        youtube_search(song_name)
        time.sleep(2)
        return youtube_play_first_video()
    except Exception as e:
        return f"Could not play song: {e}"


# ============================================================
# BROWSER INTERACTION
# ============================================================

def browser_click_first_result():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(0.8)
        pyautogui.press('tab')
        time.sleep(0.3)
        pyautogui.press('tab')
        time.sleep(0.3)
        pyautogui.press('enter')
        return "Clicked first result"
    except Exception as e:
        return f"Could not click: {e}"


def browser_scroll_down():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(0.3)
        for _ in range(5):
            pyautogui.press('down')
            time.sleep(0.05)
        return "Scrolled down"
    except:
        return "Could not scroll"


def browser_scroll_up():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(0.3)
        for _ in range(5):
            pyautogui.press('up')
            time.sleep(0.05)
        return "Scrolled up"
    except:
        return "Could not scroll"


def browser_continuous_scroll():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        for _ in range(10):
            pyautogui.press('down')
            time.sleep(0.1)
        return "Continuous scrolling"
    except:
        return "Could not scroll"


def browser_go_back():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(0.3)
        pyautogui.hotkey('alt', 'left')
        return "Went back"
    except:
        return "Could not go back"


def browser_refresh():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'r')
        return "Refreshed"
    except:
        return "Could not refresh"


def browser_new_tab():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 't')
        return "New tab"
    except:
        return "Could not open tab"


def browser_close_tab():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'w')
        return "Closed tab"
    except:
        return "Could not close tab"


def browser_close_chrome():
    global chrome_opened
    try:
        os.system("taskkill /f /im chrome.exe")
        chrome_opened = False
        return "Closed Chrome"
    except:
        return "Could not close Chrome"


# ============================================================
# MEDIA
# ============================================================

def media_skip():
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(0.3)
        pyautogui.hotkey('shift', 'n')
        return "Skipped"
    except:
        return "Could not skip"


def media_play_pause():
    try:
        pyautogui.press('playpause')
        return "Toggled play/pause"
    except:
        try:
            if not ensure_focused():
                return "Chrome not focused"
            pyautogui.press('space')
            return "Toggled play/pause"
        except:
            return "Could not control media"


def media_volume_up():
    try:
        for _ in range(5):
            pyautogui.press('volumeup')
            time.sleep(0.05)
        return "Volume increased"
    except:
        return "Could not change volume"


def media_volume_down():
    try:
        for _ in range(5):
            pyautogui.press('volumedown')
            time.sleep(0.05)
        return "Volume decreased"
    except:
        return "Could not change volume"


def media_mute():
    try:
        pyautogui.press('volumemute')
        return "Volume muted"
    except:
        return "Could not mute"


# ============================================================
# APP-SPECIFIC SEARCH
# ============================================================

def search_in_app(app_name, query):
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(0.5)
        if "youtube" in app_name:
            pyautogui.press('/')
            time.sleep(0.5)
            pyautogui.write(query)
            time.sleep(0.3)
            pyautogui.press('enter')
            return f"Searching YouTube for {query}"
        elif "amazon" in app_name:
            pyautogui.press('/')
            time.sleep(0.5)
            pyautogui.write(query)
            time.sleep(0.3)
            pyautogui.press('enter')
            return f"Searching Amazon for {query}"
        elif "spotify" in app_name:
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.5)
            pyautogui.write(query)
            time.sleep(0.3)
            pyautogui.press('enter')
            return f"Searching Spotify for {query}"
        else:
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.3)
            pyautogui.write(query)
            return f"Finding {query} on page"
    except:
        return "Could not search in app"


# ============================================================
# CALLING
# ============================================================

def call_on_whatsapp(contact):
    try:
        open_chrome_with_url("web.whatsapp.com")
        time.sleep(4)
        if not ensure_focused():
            return "Could not focus WhatsApp"
        pyautogui.click(200, 150, duration=0.5)
        time.sleep(0.5)
        pyautogui.write(contact)
        time.sleep(1.5)
        pyautogui.press('enter')
        time.sleep(1)
        pyautogui.click(1000, 100, duration=0.5)
        return f"Calling {contact} on WhatsApp"
    except Exception as e:
        return f"Could not call: {e}"


# ============================================================
# SYSTEM CONTROL
# ============================================================

def system_command(action):
    actions = {
        "shutdown": "shutdown /s /t 5",
        "restart": "shutdown /r /t 5",
        "lock": "rundll32.exe user32.dll,LockWorkStation",
        "sleep": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"
    }
    for key, cmd in actions.items():
        if key in action:
            os.system(cmd)
            return f"{key.capitalize()} initiated"
    return None


def volume_control(action):
    try:
        if "volume up" in action or "increase volume" in action:
            return media_volume_up()
        elif "volume down" in action or "decrease volume" in action:
            return media_volume_down()
        elif "mute" in action:
            return media_mute()
    except:
        return "Could not control volume"
    return None


# ============================================================
# NOTES
# ============================================================

notes_file = "jarvis_notes.txt"


def note_command(action):
    if "take note" in action or "remember" in action:
        note = action.replace("take note", "").replace("remember", "").strip()
        if note:
            with open(notes_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {note}\n")
            return f"Note saved: {note}"
        return "What should I remember?"
    elif "read notes" in action or "what are my notes" in action:
        try:
            with open(notes_file, "r", encoding="utf-8") as f:
                notes = f.read()
            return f"Your notes: {notes}" if notes else "No notes found"
        except:
            return "No notes found"
    elif "clear notes" in action:
        open(notes_file, "w", encoding="utf-8").close()
        return "All notes cleared"
    return None


# ============================================================
# FILES
# ============================================================

def file_command(action):
    if "list files" in action or "what's in" in action:
        folder = action.replace("list files", "").replace("what's in", "").strip()
        if not folder:
            folder = os.getcwd()
        try:
            files = os.listdir(folder)[:10]
            return f"Files: {', '.join(files)}"
        except:
            return "Could not list files"
    if "open folder" in action:
        folder = action.replace("open folder", "").strip()
        if folder and os.path.exists(folder):
            os.startfile(folder)
            return f"Opening {folder}"
        else:
            os.startfile(os.getcwd())
            return "Opening current folder"
    if "create folder" in action:
        folder_name = action.replace("create folder", "").strip()
        if folder_name:
            os.makedirs(folder_name, exist_ok=True)
            return f"Created folder: {folder_name}"
        return "What should I name the folder?"
    return None


# ============================================================
# WHATSAPP
# ============================================================

def open_whatsapp():
    try:
        open_chrome_with_url("web.whatsapp.com")
        return "Opening WhatsApp"
    except:
        return "Could not open"


def send_whatsapp_message(message):
    try:
        if not ensure_focused():
            return "Chrome not focused"
        time.sleep(1)
        pyautogui.click(600, 700, duration=0.5)
        time.sleep(0.5)
        pyautogui.write(message)
        time.sleep(0.5)
        pyautogui.press('enter')
        return f"Sent: {message}"
    except:
        return "Could not send"


# ============================================================
# VISION
# ============================================================

def detect_objects():
    try:
        from ultralytics import YOLO
        import cv2
        model = YOLO("yolov8s.pt")
        camera = cv2.VideoCapture(0)
        time.sleep(0.5)
        success, frame = camera.read()
        camera.release()
        if not success:
            return "Camera not available"
        results = model(frame, verbose=False, conf=0.3)
        objects = set()
        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                name = model.names[cls]
                if float(box.conf[0]) > 0.3:
                    objects.add(name)
        if objects:
            return "I see " + ", ".join(list(objects)[:5])
        return "Nothing clear in view"
    except Exception as e:
        return f"Vision error: {e}"


# ============================================================
# WEATHER / NEWS / STATUS
# ============================================================

def get_weather():
    try:
        url = "https://wttr.in/?format=%C+%t+%w"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.text.strip()
        return "Weather unavailable"
    except:
        return "Weather unavailable"


def get_news():
    try:
        import feedparser
        feed = feedparser.parse("http://feeds.bbci.co.uk/news/rss.xml")
        headlines = [entry.title for entry in feed.entries[:3]]
        if headlines:
            return "News: " + ". ".join(headlines)
        return "No news"
    except:
        return "News unavailable"


def get_system_status():
    try:
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        return f"CPU {cpu}%, Memory {memory}%"
    except:
        return "Status unavailable"


# ============================================================
# SCREEN CAPTURE
# ============================================================

def capture_screen():
    try:
        screenshot = ImageGrab.grab()
        temp_path = "temp_screen.png"
        screenshot.save(temp_path)
        image = Image.open(temp_path)
        response = model.generate_content([
            "Describe what you see on this screen. Mention windows, applications, text, and any content visible.",
            image
        ])
        os.remove(temp_path)
        return response.text
    except:
        return "Screen capture error"


# ============================================================
# EMERGENCY STOP
# ============================================================

def emergency_exit():
    print("\n🛑 EMERGENCY SHUTDOWN!")
    bridge.set_state("standby", "emergency stop")
    sys.exit(0)

try:
    keyboard.add_hotkey('ctrl+alt+x', emergency_exit)
    print("⚠️  Press CTRL+ALT+X for emergency stop")
except:
    pass


# ============================================================
# PROCESS COMMAND
# ============================================================

def process_command(text):
    text_lower = text.lower().strip()
    bridge.set_state("processing", text)

    if text_lower in ["exit", "quit", "goodbye", "bye", "stop", "sleep"]:
        return "exit"

    if "close chrome" in text_lower:
        return browser_close_chrome()

    if "youtube" in text_lower and any(w in text_lower for w in ["search", "play", "find"]):
        query = text_lower
        query = query.replace("search", "").replace("play", "").replace("find", "")
        query = query.replace("in youtube", "").replace("on youtube", "").replace("youtube", "")
        query = query.replace("for", "").strip()
        if query:
            return youtube_search(query)
        return "What should I search on YouTube?"

    if any(p in text_lower for p in ["select first", "select the first", "play first",
                                      "play the first", "click first", "open first"]):
        return youtube_play_first_video()

    if "play video" in text_lower:
        for n in range(1, 10):
            if str(n) in text_lower:
                return youtube_play_video_number(n)

    if any(p in text_lower for p in ["next video", "next song", "skip"]):
        return youtube_next_video()

    if "play" in text_lower and ("song" in text_lower or "music" in text_lower):
        song = text_lower.replace("play", "").replace("song", "").replace("music", "").strip()
        if song:
            return play_song_youtube(song)
        return "What song?"

    if "call" in text_lower and "whatsapp" in text_lower:
        contact = text_lower.replace("call", "").replace("whatsapp", "").replace("on", "").strip()
        if contact:
            return call_on_whatsapp(contact)
        return "Who should I call?"

    if "search in" in text_lower or "search on" in text_lower:
        if " for " in text_lower:
            parts = text_lower.split(" for ")
            app = parts[0].replace("search in", "").replace("search on", "").strip()
            query = parts[1].strip()
            return search_in_app(app, query)
        return "Say: search in youtube for cats"

    if "play" in text_lower or "pause" in text_lower:
        return media_play_pause()

    if any(word in text_lower for word in ["volume", "mute"]):
        response = volume_control(text_lower)
        if response:
            return response

    if any(word in text_lower for word in ["shutdown", "restart", "lock"]):
        response = system_command(text_lower)
        if response:
            return response

    if any(word in text_lower for word in ["note", "remember", "notes"]):
        response = note_command(text_lower)
        if response:
            return response

    if any(word in text_lower for word in ["list files", "open folder", "create folder"]):
        response = file_command(text_lower)
        if response:
            return response

    if "search" in text_lower:
        query = text_lower.replace("search", "").strip()
        if query:
            return search_google(query)
        return "What to search?"

    if "youtube" in text_lower:
        open_chrome_with_url("youtube.com")
        return "Opening YouTube"

    if "google" in text_lower and "open" in text_lower:
        open_chrome_with_url("google.com")
        return "Opening Google"

    if "open chrome" in text_lower or "chrome" in text_lower:
        open_chrome_with_url("google.com")
        return "Opening Chrome"

    if "open website" in text_lower or "go to" in text_lower:
        url = text_lower.replace("open website", "").replace("go to", "").strip()
        if url:
            open_chrome_with_url(url)
            return f"Opening {url}"
        return "Which website?"

    if "scroll down" in text_lower:
        return browser_scroll_down()
    if "scroll up" in text_lower:
        return browser_scroll_up()
    if "continuous scroll" in text_lower:
        return browser_continuous_scroll()
    if "go back" in text_lower:
        return browser_go_back()
    if "refresh" in text_lower:
        return browser_refresh()
    if "new tab" in text_lower:
        return browser_new_tab()
    if "close tab" in text_lower:
        return browser_close_tab()

    if "whatsapp" in text_lower and "open" in text_lower:
        return open_whatsapp()
    if "send" in text_lower and "whatsapp" in text_lower:
        message = text_lower.replace("send", "").replace("whatsapp", "").strip()
        if message:
            return send_whatsapp_message(message)
        return "What message?"

    if "what do you see" in text_lower:
        return detect_objects()
    if "screen capture" in text_lower:
        return capture_screen()

    if "time" in text_lower:
        return datetime.now().strftime('%I:%M %p')
    if "date" in text_lower:
        return datetime.now().strftime('%B %d, %Y')
    if "weather" in text_lower:
        return get_weather()
    if "news" in text_lower:
        return get_news()
    if "status" in text_lower:
        s = get_system_status()
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            bridge.stats(cpu, mem)
        except:
            pass
        return s

    if text_lower.startswith("open "):
        app_name = text_lower[5:].strip()
        apps = {
            "notepad": "notepad.exe", "calculator": "calc.exe",
            "paint": "mspaint.exe", "cmd": "cmd.exe",
            "powershell": "powershell.exe", "explorer": "explorer.exe",
            "vscode": "code.exe", "spotify": "spotify.exe",
            "settings": "ms-settings:", "task manager": "taskmgr.exe"
        }
        for key, path in apps.items():
            if key in app_name:
                try:
                    subprocess.Popen(path, shell=True)
                    return f"Opening {key}"
                except:
                    return f"Could not open {key}"
        try:
            subprocess.Popen(app_name, shell=True)
            return f"Opening {app_name}"
        except:
            return f"Could not open {app_name}"

    try:
        response = model.generate_content(
            f"You are JARVIS. Reply VERY SHORTLY (1 sentence max). User: {text}"
        )
        return response.text.strip()
    except:
        return "Please try again"


# ============================================================
# LISTENING
# ============================================================

def listen_for_wake():
    r = sr.Recognizer()
    r.energy_threshold = 200
    r.dynamic_energy_threshold = True
    r.pause_threshold = 1
    with sr.Microphone() as source:
        try:
            print("\n🎤 Listening for 'Hey Jarvis'...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=4)
            text = r.recognize_google(audio).lower()
            print(f"👤 Heard: {text}")
            if "hey jarvis" in text or "jarvis" in text:
                bridge.wake()
                bridge.set_state("listening", "wake word detected")
                return True
            return False
        except:
            return False


def listen_for_command():
    r = sr.Recognizer()
    r.energy_threshold = 200
    r.dynamic_energy_threshold = True
    r.pause_threshold = 1.5
    bridge.set_state("listening")
    with sr.Microphone() as source:
        try:
            print("🎤 Listening for command...")
            r.adjust_for_ambient_noise(source, duration=0.3)
            audio = r.listen(source, timeout=10, phrase_time_limit=10)
            text = r.recognize_google(audio)
            bridge.log("user", text)
            return text
        except:
            return None


# ============================================================
# MENU
# ============================================================

def show_menu():
    print("\n" + "=" * 55)
    print("📋 COMMANDS:")
    print("=" * 55)
    print("🎵 MUSIC:")
    print("   - 'play song [name]'")
    print("   - 'search [query] in youtube'")
    print("   - 'play first' / 'select first'")
    print("   - 'play video 3'")
    print("   - 'next video' / 'skip'")
    print("   - 'play' / 'pause'")
    print("")
    print("🌐 BROWSER:")
    print("   - 'search [query]'")
    print("   - 'open youtube' / 'open google' / 'open chrome'")
    print("   - 'scroll down' / 'scroll up' / 'go back' / 'refresh'")
    print("   - 'new tab' / 'close tab' / 'close chrome'")
    print("   - 'search in youtube for [query]'")
    print("")
    print("📞 CALLING:")
    print("   - 'call [name] on whatsapp'")
    print("   - 'open whatsapp'")
    print("")
    print("👁️  VISION:")
    print("   - 'what do you see' / 'screen capture'")
    print("")
    print("⏰ SYSTEM:")
    print("   - 'time' / 'date' / 'weather' / 'news' / 'status'")
    print("   - 'volume up' / 'volume down' / 'mute'")
    print("   - 'shutdown' / 'restart' / 'lock'")
    print("")
    print("📱 APPS:")
    print("   - 'open notepad' / 'open calculator' / etc.")
    print("")
    print("💾 NOTES:")
    print("   - 'take note [text]' / 'read notes' / 'clear notes'")
    print("")
    print("📁 FILES:")
    print("   - 'list files' / 'open folder' / 'create folder'")
    print("")
    print("🚪 'exit' to sleep")
    print("=" * 55)


# ============================================================
# DASHBOARD
# ============================================================

def open_dashboard():
    dashboard_path = os.path.join(os.getcwd(), "dashboard.html")
    if os.path.exists(dashboard_path):
        file_url = f"file:///{dashboard_path.replace(os.sep, '/')}"
        webbrowser.open(file_url)
        print(f"🖥️  Dashboard opened in browser")
        return True
    else:
        print("⚠️  dashboard.html not found")
        return False


# ============================================================
# STATS
# ============================================================

def stats_loop():
    while True:
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            bridge.stats(cpu, mem)
        except:
            pass
        time.sleep(3)


# ============================================================
# MAIN LOOP
# ============================================================

def main():
    global chrome_opened

    print("=" * 55)
    print("🤖 JARVIS - FULL VERSION")
    print("🎙️  Voice: British Ryan")
    print("=" * 55)

    bridge.start()
    threading.Thread(target=stats_loop, daemon=True).start()

    # Wait for bridge, but don't crash on Ctrl+C
    try:
        time.sleep(1.5)
    except KeyboardInterrupt:
        pass

    open_dashboard()

    try:
        time.sleep(2)
    except KeyboardInterrupt:
        pass

    show_menu()

    print("🔊 Say 'Hey Jarvis' to wake me up")
    print("⚠️  Press CTRL+ALT+X for emergency stop")
    print("=" * 55)

    speak("Welcome back, sir. The system is fully operational.")

    active = False
    chrome_opened = False

    try:
        while True:
            try:
                if keyboard.is_pressed('ctrl+alt+x'):
                    emergency_exit()
            except:
                pass

            if not active:
                if listen_for_wake():
                    print("✅ Wake word detected!")
                    speak("Yes sir?")
                    active = True
                    show_menu()
                continue

            command = listen_for_command()

            if command:
                print(f"👤 You: {command}")

                if "menu" in command.lower() or "help" in command.lower():
                    show_menu()
                    speak("Commands listed")
                    continue

                response = process_command(command)

                if response == "exit":
                    speak("Goodbye sir.")
                    print("\n💤 Sleeping...")
                    active = False
                    chrome_opened = False
                    continue

                speak(response)
            else:
                bridge.set_state("idle")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        try:
            speak("Goodbye!")
        except:
            pass
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("JARVIS shut down.")


if __name__ == "__main__":
    main()