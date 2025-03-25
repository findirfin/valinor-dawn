# Valinor Dawn

Valinor Dawn is a comprehensive alarm and puzzle application designed to enhance your daily routine with customizable features and engaging puzzles.

## Project Structure

- **alarms/sounds**: Contains alarm sound files in formats such as .mp3 or .wav.
- **cache/**: Stores temporary data:
  - `weather.json`: Cached weather data, updated by `daily_updater.py`.
  - `news.json`: Cached news headlines, updated by `daily_updater.py`.
  - `reminders.json`: User-added reminders/tasks for the next morning.
  - `puzzle_history.json`: Tracks recently shown puzzles to avoid repetition.
  
- **config/**: Holds configuration files:
  - `settings.json`: User settings including audio device preferences, alarm sound choices, and internet checks.
  - `schedule.json`: Weekly schedule detailing wake-up, breakfast, and leave times for each day.

- **logs/**: Contains application logs:
  - `status.log`: Logs events, errors, and status updates for debugging.

- **scripts/**: Contains executable scripts:
  - `main.py`: The core Valinor Dawn program managing alarms, puzzles, and the dashboard.
  - `daily_updater.py`: Runs periodically to fetch and cache weather/news.
  - `settings_page.py`: Launches the interactive settings interface.
  - `reminders.py`: Manages the interface for adding reminders/tasks.
  - `puzzle_generator.py`: Contains functions to generate dynamic puzzles.
  - `watchdog.sh`: Ensures `main.py` is running, typically used with cron.

- **assets/**: Optional folder for visual assets:
  - **fonts/**: Custom fonts for ASCII art.

- **requirements.txt**: Lists Python dependencies required for the project (e.g., rich, pygame, requests).

- **crontab.txt**: Contains example crontab entries for automation.

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd valinor_dawn
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure your settings in `config/settings.json` and `config/schedule.json`.

5. Run the main application:
   ```
   python scripts/main.py
   ```

## Usage

- Set alarms and customize sounds through the settings interface.
- View and manage reminders and puzzles directly from the application.

## Troubleshooting

- Check `logs/status.log` for any errors or status updates.
- Ensure all dependencies are installed and up to date.

For further assistance, please refer to the documentation or open an issue in the repository.