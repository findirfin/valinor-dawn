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
import argparse  # Add at the top with other imports

# --- Add puzzle_generator import ---
try:
    import puzzle_generator
except ImportError:
    print("Error: puzzle_generator.py not found in the scripts directory.")
    sys.exit(1)

# --- State Management ---
class AppState(Enum):
    WAITING = "waiting"
    ALARMING = "alarming"
    PUZZLE = "puzzle"
    DASHBOARD_REMINDERS = "dashboard_reminders"
    DASHBOARD_WEATHER = "dashboard_weather"
    DASHBOARD_NEWS = "dashboard_news"
    COUNTDOWN = "countdown"
    IDLE = "idle"

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
        # logging.info(f"Ensured directory exists: {dir_path}") # Less verbose

    default_settings = {
        "alarm_sound_filename": "rooster.mp3", # Store only filename
        "puzzles_required": 3,
        "check_internet": True,
        "audio_device": "default", # Placeholder for future use
        "puzzle_difficulty": "easy"
    }

    default_schedule = {day: {
        "wake_up": "07:00", # More realistic default
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

    if not os.path.exists(settings_path):
        with open(settings_path, 'w') as f:
            json.dump(default_settings, f, indent=4)
            logging.info("Created default settings.json")

    if not os.path.exists(schedule_path):
        with open(schedule_path, 'w') as f:
            json.dump(default_schedule, f, indent=4)
            logging.info("Created default schedule.json")

def load_config():
    """Load configuration from JSON files"""
    settings_path = os.path.join(CONFIG_DIR, "settings.json")
    schedule_path = os.path.join(CONFIG_DIR, "schedule.json")
    try:
        with open(settings_path) as f:
            settings = json.load(f)
        with open(schedule_path) as f:
            schedule = json.load(f)
        # Construct full alarm path
        settings['alarm_sound_path'] = os.path.join(ALARM_DIR, settings.get('alarm_sound_filename', 'alarm.mp3'))
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
    try:
        pygame.mixer.init()
        logging.info("Pygame mixer initialized.")
    except pygame.error as e:
        logging.error(f"Failed to initialize pygame mixer: {e}")

def play_alarm_sound(sound_file):
    """Starts playing the alarm sound in a loop (non-blocking)."""
    if not os.path.exists(sound_file):
        logging.error(f"Alarm sound file not found: {sound_file}")
        return False
    try:
        if not pygame.mixer.get_init(): # Initialize if not already done
             init_mixer()
        if not pygame.mixer.get_init(): # Check again if init failed
            logging.error("Cannot play sound, mixer not initialized.")
            return False

        pygame.mixer.music.load(sound_file)
        pygame.mixer.music.play(-1) # Loop indefinitely
        logging.info(f"Playing alarm: {os.path.basename(sound_file)}")
        return True
    except pygame.error as e:
        logging.error(f"Error playing sound {sound_file}: {e}")
        return False

def stop_alarm_sound():
    """Stops the currently playing alarm sound."""
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload() # Free up memory
            logging.info("Alarm sound stopped.")
    except pygame.error as e:
        logging.error(f"Error stopping sound: {e}")

# --- Time & Schedule Functions ---
def get_today_schedule(schedule):
    """Gets the schedule dictionary for the current day."""
    now = datetime.datetime.now()
    today_name = now.strftime("%A").lower()
    if today_name not in schedule:
        logging.warning(f"No schedule found for {today_name}. Using Monday as default.")
        today_name = "monday" # Fallback
    return schedule.get(today_name, {})

def check_alarm_time(today_schedule, debug_time=None):
    """Checks if it's time for the alarm based on today's schedule."""
    if debug_time:  # If debug time is provided, use it instead
        return True

    if "wake_up" not in today_schedule:
        logging.warning("Wake up time not defined in today's schedule.")
        return False
    try:
        wake_time_str = today_schedule["wake_up"]
        wake_time = datetime.datetime.strptime(wake_time_str, "%H:%M").time()
        now = datetime.datetime.now()
        return now.hour == wake_time.hour and now.minute == wake_time.minute
    except ValueError:
        logging.error(f"Invalid time format for wake_up: {wake_time_str}. Use HH:MM.")
        return False

def get_next_events(today_schedule):
    """Gets upcoming events and time remaining."""
    now = datetime.datetime.now()
    upcoming = []
    event_order = ["breakfast", "leave_house"] # Define order

    for event_key in event_order:
        if event_key in today_schedule:
            try:
                event_time_str = today_schedule[event_key]
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

def display_panel(content, title="", style="white", border_style="blue"):
    """Helper to display content in a rich Panel."""
    console.print(Panel(content, title=title, style=style, border_style=border_style, expand=False))

def display_alarm_alert():
    """Displays the visual alarm alert."""
    display_panel(Text("⏰ WAKE UP! ⏰", justify="center", style="bold red on black"),
                  title="[blink]ALARM ACTIVE[/]", border_style="red")

def display_reminders():
    """Loads and displays reminders."""
    try:
        with open(os.path.join(CACHE_DIR, "reminders.json")) as f:
            data = json.load(f)
        reminders = data.get("reminders", [])
        tasks = [r["content"] for r in reminders if r.get("type") == "task"]
        notes = [r["content"] for r in reminders if r.get("type") == "note"]

        content = ""
        if tasks:
            content += "[bold cyan]📌 Tasks:[/]\n" + "\n".join(f"• {t}" for t in tasks)
        if notes:
            if tasks: content += "\n\n"
            content += "[bold magenta]📝 Notes:[/]\n" + "\n".join(f"• {n}" for n in notes)

        if not content:
            content = "[dim]No reminders for today.[/]"

        display_panel(content, title="Reminders & Notes")
        console.input("[grey50]Press Enter for Weather...[/]")
        return True
    except FileNotFoundError:
        logging.info("No current reminders found.")
        display_panel("[dim]No reminders found for today.[/]", title="Reminders & Notes")
        console.input("[grey50]Press Enter for Weather...[/]")
        return True
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logging.error(f"Error reading or parsing reminders.json: {e}")
        display_panel("[red]Error loading reminders.[/]", title="Reminders & Notes")
        console.input("[grey50]Press Enter for Weather...[/]")
        return False

def get_weather_art(conditions_str):
    """Returns simple ASCII art based on weather conditions."""
    conditions_lower = conditions_str.lower()
    if "clear" in conditions_lower or "sun" in conditions_lower:
        return "☀️", "[yellow]"
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
        return "🌡️", "[white]"

def display_weather():
    """Loads and displays weather with basic art."""
    try:
        with open(os.path.join(CACHE_DIR, "weather.json")) as f:
            weather = json.load(f)

        temp = weather.get('temp', 'N/A')
        conditions = weather.get('conditions', 'Unknown')
        timestamp = weather.get('timestamp', '')
        try:
            ts_dt = datetime.datetime.fromisoformat(timestamp)
            ts_formatted = ts_dt.strftime("%Y-%m-%d %H:%M")
        except:
            ts_formatted = timestamp

        art, style = get_weather_art(conditions)
        # Removed Text wrapper and adjusted formatting
        content = f"{style}{art} {conditions.title()}[/]\n\n" \
                  f"[bold]Temperature:[/] {temp}°C\n" \
                  f"[dim]Updated: {ts_formatted}[/]"

        display_panel(content, title="Weather Update", border_style="blue")
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
        with open(os.path.join(CACHE_DIR, "news.json")) as f:
            news = json.load(f)

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

# --- Main Program ---
def main():
    # Add argument parsing at the start of main()
    parser = argparse.ArgumentParser(description='Valinor Dawn Alarm System')
    parser.add_argument('--debug-alarm', action='store_true', help='Trigger alarm immediately for testing')
    args = parser.parse_args()

    setup_logging()
    logging.info("--- Valinor Dawn Starting Up ---")
    if args.debug_alarm:
        logging.info("Debug mode: Alarm will trigger immediately")
    init_mixer() # Initialize mixer early

    try:
        init_config_dirs()
        settings, schedule = load_config()
    except Exception as e: # Catch broader exceptions during startup
        console.print(f"[bold red]CRITICAL STARTUP ERROR: {e}[/]")
        logging.critical(f"Startup failed: {e}", exc_info=True)
        return # Exit if config fails

    current_state = AppState.WAITING
    alarm_triggered_today = False
    puzzles_to_solve = []
    current_puzzle_index = 0

    console.print("[bold green]Valinor Dawn - Active and Waiting[/]")
    logging.info(f"Initial state: {current_state.value}")

    try: # Main loop wrapped in try/finally for cleanup
        while True:
            now = datetime.datetime.now()
            today_schedule = get_today_schedule(schedule)

            # --- Daily Reset ---
            if now.hour == 0 and now.minute == 0 and now.second < 5: # Check briefly around midnight
                if alarm_triggered_today: # Only reset if it triggered
                    alarm_triggered_today = False
                    current_state = AppState.WAITING
                    logging.info("Daily reset performed. Returning to WAITING state.")
                    console.print("[dim]Daily reset. Waiting for next alarm.[/]")
                time.sleep(60) # Avoid multiple resets in the first minute
                continue

            # --- State Machine ---
            if current_state == AppState.WAITING:
                if not alarm_triggered_today and (args.debug_alarm or check_alarm_time(today_schedule)):
                    logging.info("Wake up time detected" + (" (DEBUG MODE)" if args.debug_alarm else ""))
                    if play_alarm_sound(settings['alarm_sound_path']):
                        current_state = AppState.ALARMING
                        display_alarm_alert()
                        logging.info("Transitioning to ALARMING state.")
                        args.debug_alarm = False  # Reset debug trigger after first use
                    else:
                        logging.error("Failed to play alarm sound. Staying in WAITING state.")
                        # Maybe retry later? For now, just log.
                # else: # Debugging check time
                    # print(f"Waiting... {now.strftime('%H:%M:%S')}")
                pass # Continue checking time

            elif current_state == AppState.ALARMING:
                # Immediately transition to puzzle state after showing alert
                puzzles_to_solve = puzzle_generator.select_puzzles(
                    settings.get("puzzles_required", 3),
                    settings.get("puzzle_difficulty", "easy")
                )
                current_puzzle_index = 0
                if not puzzles_to_solve:
                     logging.warning("No puzzles generated. Skipping puzzle state.")
                     stop_alarm_sound()
                     current_state = AppState.DASHBOARD_REMINDERS # Go straight to dashboard
                     logging.info("Transitioning directly to DASHBOARD_REMINDERS state.")
                else:
                    current_state = AppState.PUZZLE
                    logging.info(f"Transitioning to PUZZLE state with {len(puzzles_to_solve)} puzzles.")
                continue # Process PUZZLE state in next loop iteration

            elif current_state == AppState.PUZZLE:
                if current_puzzle_index >= len(puzzles_to_solve):
                    # All puzzles solved
                    logging.info("All puzzles solved.")
                    stop_alarm_sound()
                    current_state = AppState.DASHBOARD_REMINDERS
                    logging.info("Transitioning to DASHBOARD_REMINDERS state.")
                    console.print("[bold green]🎉 Puzzles Solved! Alarm Disabled. 🎉[/]")
                    time.sleep(2) # Brief pause
                    console.clear()
                    continue

                current_puzzle = puzzles_to_solve[current_puzzle_index]
                display_panel(current_puzzle['question'], title=f"Puzzle {current_puzzle_index + 1}/{len(puzzles_to_solve)}")
                user_answer = console.input("Your answer: ")

                if puzzle_generator.validate_answer(current_puzzle, user_answer):
                    console.print("[green]✅ Correct![/]")
                    current_puzzle_index += 1
                    time.sleep(1) # Brief pause
                    console.clear() # Clear for next puzzle or dashboard
                else:
                    console.print("[yellow]❌ Incorrect. Try again.[/]")
                    time.sleep(1.5) # Longer pause for incorrect
                    # Stay in PUZZLE state, loop will re-display the same puzzle index

            elif current_state == AppState.DASHBOARD_REMINDERS:
                 console.clear()
                 if display_reminders():
                     current_state = AppState.DASHBOARD_WEATHER
                     logging.info("Transitioning to DASHBOARD_WEATHER state.")
                 else:
                     # Handle error - maybe retry or skip? For now, skip.
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
                    with Live(generate_countdown_panel(today_schedule), refresh_per_second=0.5, console=console, vertical_overflow="visible") as live:
                        while True:
                            time.sleep(30) # Update roughly every 30 seconds
                            next_events = get_next_events(today_schedule)
                            if not next_events: # Check if all events have passed
                                logging.info("All countdown events passed.")
                                break # Exit the 'live' loop
                            live.update(generate_countdown_panel(today_schedule))
                    # After 'live' loop finishes
                    current_state = AppState.IDLE
                    logging.info("Transitioning to IDLE state.")
                    console.clear()
                    console.print(Panel("[dim]Entering Idle Mode...[/]", style="grey50"))
                    # Add placeholder for idle animation start here if desired
                except Exception as e:
                    logging.error(f"Error during countdown live display: {e}", exc_info=True)
                    current_state = AppState.IDLE # Fail safe to idle
                    logging.warning("Transitioning to IDLE state due to countdown error.")
                continue

            elif current_state == AppState.IDLE:
                # In Idle mode, do very little. The main loop's sleep handles waiting.
                # Placeholder for potential ambient animation updates or checks
                # print("Idling...") # Debugging
                pass

            # --- Loop Sleep ---
            # Shorter sleep for responsiveness, longer if only waiting
            sleep_duration = 5 if current_state == AppState.WAITING else 1
            time.sleep(sleep_duration)

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Shutting down.")
        print("\nValinor Dawn shutting down...")
    except Exception as e:
        logging.critical(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
        print(f"\n[bold red]CRITICAL ERROR: {e}. Check logs.[/]")
    finally:
        stop_alarm_sound() # Ensure sound is stopped on exit
        if pygame.mixer.get_init():
            pygame.mixer.quit() # Clean up mixer fully
        logging.info("--- Valinor Dawn Shutdown Complete ---")
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
