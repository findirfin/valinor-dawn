import json

def load_reminders():
    try:
        with open('cache/reminders.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_reminders(reminders):
    with open('cache/reminders.json', 'w') as file:
        json.dump(reminders, file)

def add_reminder(reminders, reminder):
    reminders.append(reminder)
    save_reminders(reminders)

def display_reminders(reminders):
    if not reminders:
        print("No reminders found.")
    else:
        print("Your reminders:")
        for idx, reminder in enumerate(reminders, start=1):
            print(f"{idx}. {reminder}")

def main():
    reminders = load_reminders()
    while True:
        print("\n1. Add Reminder")
        print("2. View Reminders")
        print("3. Exit")
        choice = input("Choose an option: ")

        if choice == '1':
            reminder = input("Enter your reminder: ")
            add_reminder(reminders, reminder)
            print("Reminder added.")
        elif choice == '2':
            display_reminders(reminders)
        elif choice == '3':
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()