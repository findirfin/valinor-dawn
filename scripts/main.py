# scripts/main.py
import pygame
import datetime
import time
import os
import json
import logging
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
import sys
import argparse
# Removed select import as we'll use blocking input in ambient mode

# --- Add puzzle_generator import ---
try:
    import puzzle_generator
except ImportError:
    print("Error: puzzle_generator.py not found in the scripts directory.")
    logging.error("puzzle_generator.py not found.") # Log error too
    sys.exit(1)

# --- State Management ---
class AppState(Enum):
    WAITING = "waiting" # Now includes Ambient Interaction
    ALARMING = "alarming"
    PUZZLE = "puzzle"
    DASHBOARD_REMINDERS = "dashboard_reminders"
    DASHBOARD_WEATHER = "dashboard_weather"
    DASHBOARD_NEWS = "dashboard_news"
    COUNTDOWN = "countdown"
    IDLE = "idle" # Now includes Ambient Interaction
    SETTINGS = "settings"
    ADDING_REMINDER = "adding_reminder" # Optional state if needed, or handle directly

# --- Configuration ---
# More robust path handling relative to this script's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "..", "config")
CACHE_DIR = os.path.join(BASE_DIR, "..", "cache")
LOG_DIR = os.path.join(BASE_DIR, "..", "logs")
ALARM_DIR = os.path.join(BASE_DIR, "..", "alarms")

# --- Logging Setup ---
def setup_logging():
    """Configure logging"""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "status.log")
    # Ensure handlers are not added multiple times if called again
    root_logger = logging.getLogger()
    if not root_logger.hasHandlers():
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout) # Also print logs to console
            ]
        )
    logging.info(f"Logging initialized. Log file: {log_file}")

# --- Config Loading & Initialization ---
def init_config_dirs():
    """Initialize configuration directories and default config files if missing"""
    dirs = [CONFIG_DIR, CACHE_DIR, LOG_DIR, ALARM_DIR]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)

    default_settings = {
        "audio_device": "default", # Placeholder
        "alarm_sound": "../alarms/rooster.mp3", # Default sound
        "puzzles_required": 3,
        "check_internet": True, # For daily_updater, not directly used here
        "puzzle_difficulty": "easy"
    }

    default_schedule = {day: {
        "wake_up": "07:00",
        "breakfast": "07:30",
        "leave_house": "08:15"
    } for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]}
    default_schedule.update({day: {
        "wake_up": "09:00",
        "breakfast": "09:30",
        "leave_house": "10:30"
    } for day in ["saturday", "sunday"]})

    settings_path = os.path.join(CONFIG_DIR, "settings.json")
    schedule_path = os.path.join(CONFIG_DIR, "schedule.json")

    # Create default files only if they don't exist
    if not os.path.exists(settings_path):
        try:
            with open(settings_path, 'w') as f:
                json.dump(default_settings, f, indent=4)
            logging.info("Created default settings.json")
        except IOError as e:
            logging.error(f"Failed to create default settings.json: {e}")
    if not os.path.exists(schedule_path):
        try:
            with open(schedule_path, 'w') as f:
                json.dump(default_schedule, f, indent=4)
            logging.info("Created default schedule.json")
        except IOError as e:
            logging.error(f"Failed to create default schedule.json: {e}")

def load_config():
    """Load configuration from JSON files"""
    settings_path = os.path.join(CONFIG_DIR, "settings.json")
    schedule_path = os.path.join(CONFIG_DIR, "schedule.json")
    settings = {}
    schedule = {}
    try:
        with open(settings_path) as f:
            settings = json.load(f)
        with open(schedule_path) as f:
            schedule = json.load(f)

        # Ensure alarm_sound_path is always derived correctly
        alarm_filename = os.path.basename(settings.get('alarm_sound', 'rooster.mp3')) # Get just filename
        settings['alarm_sound_path'] = os.path.join(ALARM_DIR, alarm_filename)
        # Store the relative path format expected by settings file
        settings['alarm_sound'] = f"../alarms/{alarm_filename}"

        logging.info("Configuration loaded successfully.")
        return settings, schedule
    except FileNotFoundError as e:
        logging.error(f"Configuration file not found: {e}. Please ensure settings.json and schedule.json exist in {CONFIG_DIR}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in configuration file: {e}")
        raise
    except KeyError as e:
        logging.error(f"Missing key in configuration file: {e}")
        raise

# --- Sound Functions ---
def init_mixer():
    """Initialize pygame mixer"""
    if pygame.mixer.get_init():
        return # Already initialized
    try:
        pygame.mixer.init()
        logging.info("Pygame mixer initialized.")
    except pygame.error as e:
        logging.error(f"Failed to initialize pygame mixer: {e}")

def play_sound(sound_file, loops=0):
    """Plays a sound file. loops=-1 for infinite loop."""
    if not os.path.exists(sound_file):
        logging.error(f"Sound file not found: {sound_file}")
        return False
    try:
        init_mixer() # Ensure mixer is initialized
        if not pygame.mixer.get_init():
            logging.error("Cannot play sound, mixer not initialized.")
            return False

        # Stop previous music if playing (important for previews)
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()

        pygame.mixer.music.load(sound_file)
        pygame.mixer.music.play(loops)
        logging.info(f"Playing sound: {os.path.basename(sound_file)} (loops={loops})")
        return True
    except pygame.error as e:
        logging.error(f"Error playing sound {sound_file}: {e}")
        return False

def stop_sound():
    """Stops the currently playing music/sound."""
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            logging.info("Sound stopped.")
    except pygame.error as e:
        logging.error(f"Error stopping sound: {e}")

# --- Time & Schedule Functions ---
# get_today_schedule, check_alarm_time, get_next_events remain the same as before
def get_today_schedule(schedule):
    """Gets the schedule dictionary for the current day."""
    now = datetime.datetime.now()
    today_name = now.strftime("%A").lower()
    if today_name not in schedule:
        logging.warning(f"No schedule found for {today_name}. Using Monday as default.")
        today_name = "monday" # Fallback
    return schedule.get(today_name, {})

def check_alarm_time(today_schedule, debug_flag=False):
    """Checks if it's time for the alarm based on today's schedule or debug flag."""
    if debug_flag:
        return True # Trigger immediately if debug flag is set

    if "wake_up" not in today_schedule:
        logging.warning("Wake up time not defined in today's schedule.")
        return False
    try:
        wake_time_str = today_schedule["wake_up"]
        wake_time = datetime.datetime.strptime(wake_time_str, "%H:%M").time()
        now = datetime.datetime.now()
        # Check current minute matches wake up minute
        return now.hour == wake_time.hour and now.minute == wake_time.minute
    except ValueError:
        logging.error(f"Invalid time format for wake_up: {wake_time_str}. Use HH:MM.")
        return False

def get_next_events(today_schedule):
    """Gets upcoming events and time remaining."""
    now = datetime.datetime.now()
    upcoming = []
    # Define order - can be customized or read from config later
    event_order = ["breakfast", "leave_house"]

    for event_key in event_order:
        event_time_str = today_schedule.get(event_key)
        if event_time_str:
            try:
                event_dt = datetime.datetime.combine(now.date(), datetime.datetime.strptime(event_time_str, "%H:%M").time())
                if event_dt > now:
                    delta = event_dt - now
                    minutes_left = int(delta.total_seconds() / 60)
                    event_name = event_key.replace("_", " ").title()
                    upcoming.append({"name": event_name, "time_str": event_time_str, "minutes_left": minutes_left})
            except ValueError:
                 logging.error(f"Invalid time format for {event_key}: {event_time_str}. Use HH:MM.")

    return upcoming


# --- Display Functions ---
console = Console()

def display_panel(content, title="", style="white", border_style="blue", expand=False):
    """Helper to display content in a rich Panel."""
    console.print(Panel(content, title=title, style=style, border_style=border_style, expand=expand))

def display_alarm_alert():
    """Displays the visual alarm alert."""
    display_panel(Text("⏰ WAKE UP! ⏰", justify="center", style="bold red on black"),
                  title="[blink]ALARM ACTIVE[/]", border_style="red")

# display_reminders, get_weather_art, display_weather, display_news remain the same
def display_reminders():
    """Loads and displays reminders."""
    try:
        reminders_file = os.path.join(CACHE_DIR, "reminders.json")
        if not os.path.exists(reminders_file):
             raise FileNotFoundError # Handle missing file explicitly

        with open(reminders_file) as f:
            data = json.load(f)
        # Optional: Add timestamp check here if needed

        reminders = data.get("reminders", [])
        tasks = [r["content"] for r in reminders if r.get("type") == "task"]
        notes = [r["content"] for r in reminders if r.get("type") == "note"]

        content = ""
        if tasks:
            content += "[bold cyan]📌 Tasks:[/]\n" + "\n".join(f"• {t}" for t in tasks)
        if notes:
            if tasks: content += "\n\n" # Add spacing if both exist
            content += "[bold magenta]📝 Notes:[/]\n" + "\n".join(f"• {n}" for n in notes)

        if not content:
            content = "[dim]No reminders for today.[/]"

        display_panel(content, title="Reminders & Notes")
        console.input("[grey50]Press Enter for Weather...[/]")
        return True # Success
    except FileNotFoundError:
        logging.info("No current reminders found.")
        display_panel("[dim]No reminders found for today.[/]", title="Reminders & Notes")
        console.input("[grey50]Press Enter for Weather...[/]")
        return True # Allow progression even if file missing
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logging.error(f"Error reading or parsing reminders.json: {e}")
        display_panel("[red]Error loading reminders.[/]", title="Reminders & Notes")
        console.input("[grey50]Press Enter for Weather...[/]")
        return False # Indicate error

def get_weather_art(conditions_str):
    """Returns simple ASCII art based on weather conditions."""
    conditions_lower = conditions_str.lower() if conditions_str else ""
    if "clear" in conditions_lower or "sun" in conditions_lower:
        return "☀️", "[yellow]" # Emoji + Style
    elif "cloud" in conditions_lower:
        return "☁️", "[grey70]"
    elif "rain" in conditions_lower or "drizzle" in conditions_lower:
        return "🌧️", "[blue]"
    elif "snow" in conditions_lower:
        return "❄️", "[cyan]"
    elif "storm" in conditions_lower or "thunder" in conditions_lower:
        return "⛈️", "[bold yellow]"
    elif "mist" in conditions_lower or "fog" in conditions_lower:
        return "🌫️", "[grey50]"
    else:
        return "🌡️", "[white]" # Default

def display_weather():
    """Loads and displays weather with basic art."""
    try:
        weather_file = os.path.join(CACHE_DIR, "weather.json")
        if not os.path.exists(weather_file):
            raise FileNotFoundError

        with open(weather_file) as f:
            weather = json.load(f)
        # Optional: Add timestamp check here

        temp = weather.get('temp', 'N/A')
        conditions = weather.get('conditions', 'Unknown')
        timestamp = weather.get('timestamp', '')
        try: # Format timestamp nicely
            ts_dt = datetime.datetime.fromisoformat(timestamp)
            ts_formatted = ts_dt.strftime("%Y-%m-%d %H:%M")
        except:
            ts_formatted = timestamp # Fallback to raw string

        art, style = get_weather_art(conditions)

        content = f"{style}{art} {conditions.title()}[/]\n\n" \
                  f"[bold]Temperature:[/] {temp}°C\n" \
                  f"[dim]Updated: {ts_formatted}[/]"

        display_panel(Text(content, justify="center"), title="Weather Update")
        console.input("[grey50]Press Enter for News...[/]")
        return True
    except FileNotFoundError:
        logging.info("No current weather data found.")
        display_panel("[dim]No weather data found.[/]", title="Weather Update")
        console.input("[grey50]Press Enter for News...[/]")
        return True
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logging.error(f"Error reading or parsing weather.json: {e}")
        display_panel("[red]Error loading weather.[/]", title="Weather Update")
        console.input("[grey50]Press Enter for News...[/]")
        return False

def display_news():
    """Loads and displays news headlines."""
    try:
        news_file = os.path.join(CACHE_DIR, "news.json")
        if not os.path.exists(news_file):
            raise FileNotFoundError

        with open(news_file) as f:
            news = json.load(f)
        # Optional: Add timestamp check

        headlines = news.get("headlines", [])
        timestamp = news.get('timestamp', '')
        try:
            ts_dt = datetime.datetime.fromisoformat(timestamp)
            ts_formatted = ts_dt.strftime("%Y-%m-%d %H:%M")
        except:
            ts_formatted = timestamp

        if headlines:
             content = "\n".join(f"• {h}" for h in headlines) + f"\n\n[dim]Updated: {ts_formatted}[/]"
        else:
             content = "[dim]No headlines found.[/]"

        display_panel(content, title="📰 News Headlines")
        console.input("[grey50]Press Enter for Countdown...[/]")
        return True
    except FileNotFoundError:
        logging.info("No current news data found.")
        display_panel("[dim]No news data found.[/]", title="📰 News Headlines")
        console.input("[grey50]Press Enter for Countdown...[/]")
        return True
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logging.error(f"Error reading or parsing news.json: {e}")
        display_panel("[red]Error loading news.[/]", title="📰 News Headlines")
        console.input("[grey50]Press Enter for Countdown...[/]")
        return False


def generate_countdown_panel(today_schedule):
    """Generates the panel content for the live countdown."""
    next_events = get_next_events(today_schedule)
    if not next_events:
        return Panel("[green]All scheduled events for today have passed.[/]", title="⏳ Countdown", border_style="green")

    content = ""
    for event in next_events:
        content += f"[bold cyan]{event['name']}[/] at {event['time_str']} ([yellow]{event['minutes_left']} min[/])\n"

    return Panel(content.strip(), title="⏳ Countdown", border_style="blue")

# --- Settings & Ambient Mode Functions ---

def list_audio_files():
    """Lists all audio files in the alarms directory."""
    audio_files = []
    try:
        if not os.path.exists(ALARM_DIR):
            logging.warning(f"Alarm directory not found: {ALARM_DIR}")
            return []
        for file in os.listdir(ALARM_DIR):
            if file.lower().endswith(('.mp3', '.wav', '.ogg')):
                audio_files.append(file)
    except OSError as e:
        logging.error(f"Error listing audio files in {ALARM_DIR}: {e}")
    return sorted(audio_files)

def select_audio_file_ui(current_selection_relative):
    """Interactive audio file selector with preview capability."""
    console.clear()
    audio_files = list_audio_files()
    if not audio_files:
        console.print("[yellow]No audio files found in alarms directory.[/]")
        time.sleep(2)
        return None # Indicate no selection made

    selected_index = -1
    current_filename = os.path.basename(current_selection_relative) if current_selection_relative else None
    if current_filename in audio_files:
        selected_index = audio_files.index(current_filename)

    while True:
        console.clear()
        options = []
        for i, file in enumerate(audio_files):
            prefix = "[bold green]>[/]" if i == selected_index else " "
            star = "[yellow] ★[/]" if file == current_filename else ""
            options.append(f"{prefix} {i+1}. [cyan]{file}[/]{star}")

        display_panel(
            "\n".join(options) + "\n\n[dim]Keys: (up/down) navigate, (enter) select, (p) preview, (s) stop, (q) cancel[/]",
            title="🔊 Select Alarm Sound"
        )

        # Use console.input for simplicity, or a more advanced key listener if needed
        # For cross-platform key listening without extra libraries, this is tricky.
        # We'll use simple input commands for now.
        choice = console.input("Command (number/p/s/q): ").lower().strip()

        if choice == 'q':
            stop_sound()
            return None # Cancelled
        elif choice == 's':
            stop_sound()
        elif choice == 'p':
            if selected_index != -1:
                preview_path = os.path.join(ALARM_DIR, audio_files[selected_index])
                play_sound(preview_path, loops=0) # Play once
            else:
                console.print("[yellow]Select a file first using its number.[/]")
                time.sleep(1)
        else:
            try:
                num = int(choice)
                if 1 <= num <= len(audio_files):
                    selected_index = num - 1
                    # Preview on selection change? Or require 'p'? Let's require 'p'.
                    # If user presses Enter after selecting a number, confirm selection
                    confirm = console.input(f"Select '{audio_files[selected_index]}'? (y/n): ").lower()
                    if confirm == 'y':
                        stop_sound()
                        # Return the relative path format used in settings.json
                        return f"../alarms/{audio_files[selected_index]}"
                else:
                    console.print("[red]Invalid number.[/]")
                    time.sleep(1)
            except ValueError:
                console.print("[red]Invalid command.[/]")
                time.sleep(1)

def display_settings(settings, schedule):
    """Displays and manages settings page."""
    console.clear()
    trigger_alarm_flag = False # Flag to signal debug alarm trigger

    while True:
        # Reload settings in case they were changed (like alarm sound)
        current_alarm_filename = os.path.basename(settings.get('alarm_sound', 'N/A'))

        console.print(Panel(f"""
[bold cyan]Settings Menu[/]

1. [yellow]Trigger Debug Alarm[/] (Next cycle)
2. Select Alarm Sound ([dim]current: {current_alarm_filename}[/])
3. Set Puzzle Count ([dim]current: {settings.get('puzzles_required', 3)}[/])
4. Set Puzzle Difficulty ([dim]current: {settings.get('puzzle_difficulty', 'easy')}[/])
5. Save & Exit
""", title="⚙️ Settings"))

        choice = console.input("Select option (1-5): ").strip()

        if choice == "1":
            trigger_alarm_flag = True
            console.print("[green]Debug alarm will trigger on next check.[/]")
            time.sleep(1.5)
        elif choice == "2":
            new_sound_relative = select_audio_file_ui(settings.get('alarm_sound'))
            if new_sound_relative:
                settings['alarm_sound'] = new_sound_relative # Store relative path
                # Update the full path for immediate use if needed (though load_config does this)
                settings['alarm_sound_path'] = os.path.join(ALARM_DIR, os.path.basename(new_sound_relative))
                console.print(f"[green]Alarm sound set to: {os.path.basename(new_sound_relative)}[/]")
                time.sleep(1.5)
            else:
                 console.print("[yellow]Alarm sound selection cancelled.[/]")
                 time.sleep(1.5)

        elif choice == "3":
            try:
                count_str = console.input(f"Enter number of puzzles (1-5) [current: {settings.get('puzzles_required', 3)}]: ").strip()
                if count_str: # Only update if user entered something
                    count = int(count_str)
                    if 1 <= count <= 5: # Limit puzzles
                        settings['puzzles_required'] = count
                    else:
                        console.print("[red]Invalid count. Must be between 1 and 5.[/]")
                        time.sleep(1.5)
            except ValueError:
                console.print("[red]Invalid input. Must be a number.[/]")
                time.sleep(1.5)
        elif choice == "4":
            diff_str = console.input(f"Enter difficulty (easy/medium/hard) [current: {settings.get('puzzle_difficulty', 'easy')}]: ").strip().lower()
            if diff_str in ['easy', 'medium', 'hard']:
                settings['puzzle_difficulty'] = diff_str
            elif diff_str: # Only show error if they typed something invalid
                console.print("[red]Invalid difficulty. Choose easy, medium, or hard.[/]")
                time.sleep(1.5)
        elif choice == "5":
            # Save settings
            settings_path = os.path.join(CONFIG_DIR, "settings.json")
            try:
                # Create a copy without the full path to save
                save_settings = settings.copy()
                if 'alarm_sound_path' in save_settings:
                    del save_settings['alarm_sound_path'] # Don't save absolute path

                with open(settings_path, 'w') as f:
                    json.dump(save_settings, f, indent=4)
                logging.info("Settings saved successfully.")
                console.print("[green]Settings saved.[/]")
                time.sleep(1)
                # Return the debug flag status
                return "trigger_alarm" if trigger_alarm_flag else None
            except IOError as e:
                 logging.error(f"Failed to save settings: {e}")
                 console.print(f"[red]Error saving settings: {e}[/]")
                 time.sleep(2)
                 # Still return, but don't trigger alarm if save failed
                 return None
        else:
            console.print("[red]Invalid option.[/]")
            time.sleep(1)

        console.clear() # Clear screen for next menu display

def add_reminder_ui():
    """Handles the UI for adding a new reminder or task."""
    console.clear()
    try:
        display_panel(
            "[cyan]Add New Reminder[/]\n"
            "1. Task (actionable to-do item)\n"
            "2. Note (general info/reminder)\n"
            "\n[dim](Press Enter or Q to cancel)[/]",
            title="📝 New Reminder"
        )

        choice = console.input("Select type (1 or 2): ").strip()

        if choice == '1':
            reminder_type = "task"
        elif choice == '2':
            reminder_type = "note"
        else:
            console.print("[yellow]Cancelled.[/]")
            time.sleep(1)
            return False # Cancelled

        content = console.input(f"Enter content for {reminder_type}: ").strip()
        if not content:
            console.print("[yellow]Cancelled (empty content).[/]")
            time.sleep(1)
            return False # Cancelled

        # --- Load, Append, Save ---
        reminders_file = os.path.join(CACHE_DIR, "reminders.json")
        data = {"timestamp": datetime.now().isoformat(), "reminders": []} # Default structure
        try:
            if os.path.exists(reminders_file):
                with open(reminders_file, 'r') as f:
                    # Handle potential empty or invalid JSON file
                    try:
                        loaded_data = json.load(f)
                        if isinstance(loaded_data, dict) and "reminders" in loaded_data:
                            data = loaded_data
                    except json.JSONDecodeError:
                         logging.warning(f"reminders.json is invalid, starting fresh.")

        except IOError as e:
            logging.warning(f"Could not read reminders file {reminders_file}: {e}. Starting fresh.")

        # Ensure reminders list exists
        if not isinstance(data.get("reminders"), list):
            data["reminders"] = []

        data["reminders"].append({
            "type": reminder_type,
            "content": content
            # Removed timestamp per item, using main timestamp
        })
        data["timestamp"] = datetime.now().isoformat() # Update main timestamp

        # Save back
        with open(reminders_file, 'w') as f:
            json.dump(data, f, indent=4)

        logging.info(f"Added {reminder_type}: {content}")
        console.print(f"[green]✅ Added {reminder_type}![/]")
        time.sleep(1.5)
        return True # Success

    except Exception as e:
        logging.error(f"Error adding reminder: {e}", exc_info=True)
        console.print(f"[red]Error saving reminder: {e}[/]")
        time.sleep(2)
        return False # Failed

def display_ambient_mode(schedule):
    """Display an interactive ambient mode interface."""
    console.clear()
    today_schedule = get_today_schedule(schedule)
    next_events = get_next_events(today_schedule)
    now = datetime.datetime.now()

    # --- Build Content ---
    content_lines = [
        f"[bold magenta]Valinor Dawn[/] - {now.strftime('%A, %B %d, %Y %H:%M:%S')}",
        "\n[bold cyan]Commands:[/]",
        "  [yellow]s[/] : Settings",
        "  [yellow]r[/] : Add Reminder/Task",
        "  [yellow]q[/] : Quit",
    ]

    # Next Alarm Info
    wake_time_str = today_schedule.get("wake_up", "N/A")
    content_lines.append(f"\n[bold cyan]Next Alarm:[/]\n  Wake up at {wake_time_str}")

    # Upcoming Events
    if next_events:
        content_lines.append("\n[bold cyan]Upcoming Today:[/]")
        for event in next_events:
            content_lines.append(f"  • {event['name']} at {event['time_str']} ([yellow]{event['minutes_left']} min[/])")
    else:
        content_lines.append("\n[dim]No further scheduled events today.[/]")

    display_panel(
        "\n".join(content_lines),
        title="🌙 Ambient Mode",
        style="white",
        border_style="dim blue" # Dimmer border
    )

    # Blocking input wait
    command = console.input("\n[dim]Enter command (s, r, q): [/]").lower().strip()
    return command


# --- Main Program ---
def main():
    parser = argparse.ArgumentParser(description='Valinor Dawn Alarm System')
    parser.add_argument('--debug-alarm', action='store_true', help='Trigger alarm immediately for testing')
    args = parser.parse_args()

    setup_logging()
    logging.info("--- Valinor Dawn Starting Up ---")
    if args.debug_alarm:
        logging.info("Debug mode: Alarm will trigger immediately")
    init_mixer()

    try:
        init_config_dirs()
        settings, schedule = load_config()
    except Exception as e:
        console.print(f"[bold red]CRITICAL STARTUP ERROR: {e}[/]")
        logging.critical(f"Startup failed: {e}", exc_info=True)
        return

    current_state = AppState.WAITING
    alarm_triggered_today = False
    puzzles_to_solve = []
    current_puzzle_index = 0
    # Flag to control immediate alarm trigger from settings or args
    trigger_alarm_now = args.debug_alarm

    console.print("[bold green]Valinor Dawn - Ready[/]")
    logging.info(f"Initial state: {current_state.value}")
    time.sleep(1) # Brief pause before first ambient display

    try:
        while True:
            now = datetime.datetime.now()
            today_schedule = get_today_schedule(schedule)

            # --- Daily Reset ---
            # Check only once shortly after midnight
            if now.hour == 0 and now.minute == 0 and now.second < 10:
                if alarm_triggered_today:
                    alarm_triggered_today = False
                    # Ensure state returns to WAITING after reset
                    if current_state != AppState.WAITING:
                         current_state = AppState.WAITING
                         logging.info("State reset to WAITING for the new day.")
                    logging.info("Daily alarm trigger reset.")
                    console.print("[dim]Daily reset complete.[/]")
                    time.sleep(10) # Prevent multiple resets in first minute
                # else: # If already reset, just wait
                #     time.sleep(30)
                continue # Skip rest of loop iteration just after reset check

            # --- State Machine ---
            if current_state == AppState.WAITING or current_state == AppState.IDLE:
                # Check for alarm time FIRST
                should_alarm = not alarm_triggered_today and check_alarm_time(today_schedule, trigger_alarm_now)

                if should_alarm:
                    logging.info("Wake up time detected" + (" (DEBUG TRIGGER)" if trigger_alarm_now else ""))
                    if play_sound(settings['alarm_sound_path'], loops=-1): # Play alarm sound
                        current_state = AppState.ALARMING
                        display_alarm_alert()
                        logging.info("Transitioning to ALARMING state.")
                        trigger_alarm_now = False  # Reset debug trigger after use
                    else:
                        logging.error("Failed to play alarm sound. Staying in current state.")
                        # Consider adding a retry mechanism or visual-only alarm
                    continue # Process ALARMING state immediately

                # If not alarming, display ambient mode and wait for input
                command = display_ambient_mode(schedule) # Pass schedule for display

                if command == 's':
                    console.clear()
                    settings_result = display_settings(settings, schedule) # Pass current settings
                    if settings_result == "trigger_alarm":
                        trigger_alarm_now = True # Set flag for next loop check
                        logging.info("Debug alarm trigger requested from settings.")
                    # Reload config in case settings changed
                    settings, schedule = load_config()
                    # Stay in WAITING/IDLE after settings
                    current_state = AppState.WAITING if current_state != AppState.IDLE else AppState.IDLE
                    logging.info(f"Returning to {current_state.value} state after settings.")
                    continue # Re-display ambient mode immediately

                elif command == 'r':
                    console.clear()
                    add_reminder_ui() # Handle UI and saving within the function
                    # Stay in WAITING/IDLE after adding reminder
                    current_state = AppState.WAITING if current_state != AppState.IDLE else AppState.IDLE
                    logging.info(f"Returning to {current_state.value} state after reminder attempt.")
                    continue # Re-display ambient mode immediately

                elif command == 'q':
                    raise KeyboardInterrupt # Trigger clean shutdown

                # If no command or invalid command, the loop will naturally check time again
                # Add a small sleep to prevent high CPU usage if input is spammed
                time.sleep(0.5)


            elif current_state == AppState.ALARMING:
                # Select puzzles
                puzzles_to_solve = puzzle_generator.select_puzzles(
                    settings.get("puzzles_required", 3),
                    settings.get("puzzle_difficulty", "easy")
                )
                current_puzzle_index = 0
                if not puzzles_to_solve:
                     logging.warning("No puzzles generated. Skipping puzzle state.")
                     stop_sound()
                     current_state = AppState.DASHBOARD_REMINDERS
                     logging.info("Transitioning directly to DASHBOARD_REMINDERS state.")
                else:
                    current_state = AppState.PUZZLE
                    logging.info(f"Transitioning to PUZZLE state with {len(puzzles_to_solve)} puzzles.")
                console.clear() # Clear alarm alert
                continue

            elif current_state == AppState.PUZZLE:
                if current_puzzle_index >= len(puzzles_to_solve):
                    logging.info("All puzzles solved.")
                    stop_sound()
                    current_state = AppState.DASHBOARD_REMINDERS
                    logging.info("Transitioning to DASHBOARD_REMINDERS state.")
                    console.print("[bold green]🎉 Puzzles Solved! Alarm Disabled. 🎉[/]")
                    time.sleep(2)
                    console.clear()
                    continue

                current_puzzle = puzzles_to_solve[current_puzzle_index]

                # Special handling for memory puzzle display
                if current_puzzle.get("type") == "memory":
                    console.clear()
                    display_panel(current_puzzle['question'], title=f"Puzzle {current_puzzle_index + 1}/{len(puzzles_to_solve)} - MEMORIZE!")
                    time.sleep(4) # Show sequence for 4 seconds
                    console.clear()
                    display_panel("Enter the sequence you saw:", title=f"Puzzle {current_puzzle_index + 1}/{len(puzzles_to_solve)}")
                else:
                    # Standard display for other types
                    display_panel(current_puzzle['question'], title=f"Puzzle {current_puzzle_index + 1}/{len(puzzles_to_solve)}")

                user_answer = console.input("Your answer: ")

                if puzzle_generator.validate_answer(current_puzzle, user_answer):
                    console.print("[green]✅ Correct![/]")
                    current_puzzle_index += 1
                    time.sleep(1)
                    console.clear()
                else:
                    console.print("[yellow]❌ Incorrect. Try again.[/]")
                    time.sleep(1.5)
                    # Re-display same puzzle (don't clear immediately)

            elif current_state == AppState.DASHBOARD_REMINDERS:
                 console.clear()
                 if display_reminders():
                     current_state = AppState.DASHBOARD_WEATHER
                     logging.info("Transitioning to DASHBOARD_WEATHER state.")
                 else:
                     logging.error("Error displaying reminders. Skipping to weather.")
                     current_state = AppState.DASHBOARD_WEATHER
                 continue

            elif current_state == AppState.DASHBOARD_WEATHER:
                 console.clear()
                 if display_weather():
                     current_state = AppState.DASHBOARD_NEWS
                     logging.info("Transitioning to DASHBOARD_NEWS state.")
                 else:
                     logging.error("Error displaying weather. Skipping to news.")
                     current_state = AppState.DASHBOARD_NEWS
                 continue

            elif current_state == AppState.DASHBOARD_NEWS:
                 console.clear()
                 if display_news():
                     current_state = AppState.COUNTDOWN
                     logging.info("Transitioning to COUNTDOWN state.")
                 else:
                     logging.error("Error displaying news. Skipping to countdown.")
                     current_state = AppState.COUNTDOWN
                 continue

            elif current_state == AppState.COUNTDOWN:
                console.clear()
                logging.info("Entering countdown display loop.")
                try:
                    # Use a loop with Live that checks for events passing
                    with Live(console=console, auto_refresh=False, vertical_overflow="visible") as live:
                        while True:
                            panel_content = generate_countdown_panel(today_schedule)
                            live.update(panel_content, refresh=True)
                            time.sleep(30) # Update roughly every 30 seconds
                            next_events = get_next_events(today_schedule)
                            if not next_events: # Check if all events have passed
                                logging.info("All countdown events passed.")
                                break # Exit the inner while loop

                    # After 'live' context manager finishes
                    current_state = AppState.IDLE
                    logging.info("Transitioning to IDLE state.")
                    console.clear()
                    console.print(Panel("[dim]Entering Idle/Ambient Mode...[/]", style="grey50"))
                    time.sleep(1) # Pause before showing ambient mode
                except Exception as e:
                    logging.error(f"Error during countdown live display: {e}", exc_info=True)
                    current_state = AppState.IDLE # Fail safe to idle
                    logging.warning("Transitioning to IDLE state due to countdown error.")
                continue

            # Removed SETTINGS state handling from here, it's handled via ambient mode input

            # --- Loop Sleep ---
            # Sleep only if not actively processing input in ambient mode
            if current_state not in [AppState.WAITING, AppState.IDLE]:
                 time.sleep(0.5) # Short sleep during active states if needed

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Shutting down.")
        print("\nValinor Dawn shutting down...")
    except Exception as e:
        logging.critical(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
        print(f"\n[bold red]CRITICAL ERROR: {e}. Check logs.[/]")
    finally:
        stop_sound() # Ensure sound is stopped on exit
        if pygame.get_init() and pygame.mixer.get_init(): # Check both pygame and mixer init
            pygame.mixer.quit()
            pygame.quit() # Quit pygame fully
        logging.info("--- Valinor Dawn Shutdown Complete ---")
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
