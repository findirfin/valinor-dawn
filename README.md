# 🌅 Valinor Dawn

A smart alarm system that ensures you're truly awake through puzzles and keeps you informed with your morning dashboard.

## ✨ Features

- 🧩 Solve puzzles to disable the alarm
- 📅 Customizable daily wake-up schedules
- 💡 Smart morning dashboard including:
  - 📌 Daily reminders and notes
  - 🌤️ Weather updates
  - 📰 News headlines
  - ⏳ Dynamic countdown for daily events

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/findirfin/valinor-dawn.git
cd valinor-dawn

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Place your alarm sound in `/alarms` directory
2. Configure your settings in `/config/settings.json`:
```json
{
    "alarm_sound_filename": "your-sound.mp3",
    "puzzles_required": 3,
    "puzzle_difficulty": "easy"
}
```

3. Set your schedule in `/config/schedule.json`

## 🎮 Usage

```bash
# Normal start
python scripts/main.py

# Debug mode (triggers alarm immediately)
python scripts/main.py --debug-alarm
```

## 📁 Project Structure

```
valinor-dawn/
├── alarms/         # Alarm sound files
├── cache/          # Temporary data storage
├── config/         # Configuration files
├── logs/           # Application logs
└── scripts/        # Python source code
```

## ⚙️ Configuration Files

### settings.json
- `alarm_sound_filename`: Sound file for the alarm
- `puzzles_required`: Number of puzzles to solve
- `check_internet`: Enable/disable online features
- `puzzle_difficulty`: Easy, medium, or hard

### schedule.json
Configure wake-up times and daily events for each day of the week.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 💡 Acknowledgments

- Inspired by the need for a more engaging wake-up experience
- Built with Python and the excellent [rich](https://github.com/Textualize/rich) library