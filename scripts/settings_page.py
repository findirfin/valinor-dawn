import json

def load_settings():
    with open('../config/settings.json', 'r') as f:
        settings = json.load(f)
    return settings

def save_settings(settings):
    with open('../config/settings.json', 'w') as f:
        json.dump(settings, f, indent=4)

def display_settings(settings):
    print("Current Settings:")
    for key, value in settings.items():
        print(f"{key}: {value}")

def update_setting(settings, key, value):
    if key in settings:
        settings[key] = value
        save_settings(settings)
        print(f"Updated {key} to {value}")
    else:
        print(f"{key} not found in settings.")

def main():
    settings = load_settings()
    display_settings(settings)

    while True:
        print("\nEnter a setting to update (or 'exit' to quit):")
        key = input("Setting: ")
        if key.lower() == 'exit':
            break
        value = input(f"New value for {key}: ")
        update_setting(settings, key, value)

if __name__ == "__main__":
    main()