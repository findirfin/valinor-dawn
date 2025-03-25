# scripts/puzzle_generator.py
import random
import json
import os
from datetime import datetime, timedelta

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "..", "cache")
HISTORY_FILE = os.path.join(CACHE_DIR, "puzzle_history.json")
HISTORY_DAYS = 7 # Don't repeat puzzles shown in the last 7 days

# --- Static Data (Example) ---
RIDDLES = [
    ("I have cities, but no houses; forests, but no trees; and water, but no fish. What am I?", "A map"),
    ("What has an eye, but cannot see?", "A needle"),
    ("What is always in front of you but can’t be seen?", "The future"),
    ("What has keys, but opens no locks?", "A piano"),
    # Add more riddles
]

TYPING_PHRASES = [
    "The quick brown fox jumps over the lazy dog",
    "Valinor Dawn guides the start of your day",
    "Solve the puzzle to silence the morning call",
    # Add more phrases
]

# --- History Functions ---
def load_history():
    """Load puzzle history from file."""
    try:
        with open(HISTORY_FILE, "r") as f:
            # Filter out entries older than HISTORY_DAYS
            history_data = json.load(f)
            cutoff_date = datetime.now() - timedelta(days=HISTORY_DAYS)
            valid_entries = [
                p for p in history_data.get("recent_puzzles", [])
                if datetime.strptime(p.get("date", "1970-01-01"), "%Y-%m-%d") >= cutoff_date
            ]
            return {"recent_puzzles": valid_entries}
    except (FileNotFoundError, json.JSONDecodeError):
        return {"recent_puzzles": []}

def save_history(history):
    """Save puzzle history to file."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=4)
    except IOError as e:
        print(f"Error saving puzzle history: {e}") # Use logging in main app

def get_recent_puzzle_identifiers(history):
    """Extracts unique identifiers (e.g., question text) from recent history."""
    return {p.get("identifier") for p in history.get("recent_puzzles", [])}

def add_to_history(history, puzzle_type, identifier, question):
    """Add a puzzle to the history."""
    history.setdefault("recent_puzzles", []).append({
        "type": puzzle_type,
        "identifier": identifier, # A unique way to identify this specific puzzle
        "question": question, # Store question for potential debugging/review
        "date": datetime.now().strftime("%Y-%m-%d")
    })
    # Keep history size manageable (optional)
    # history["recent_puzzles"] = history["recent_puzzles"][-100:] # Keep last 100
    save_history(history)


# --- Puzzle Generation Functions ---
def generate_math_puzzle(difficulty):
    if difficulty == "easy":
        a, b = random.randint(1, 10), random.randint(1, 10)
        op = random.choice(['+', '-'])
        if op == '+': question, answer = f"What is {a} + {b}?", a + b
        else: question, answer = f"What is {max(a,b)} - {min(a,b)}?", max(a,b) - min(a,b) # Avoid negative
    elif difficulty == "medium":
        a, b = random.randint(2, 12), random.randint(2, 12)
        op = random.choice(['*', '+', '-'])
        if op == '*': question, answer = f"What is {a} * {b}?", a * b
        elif op == '+': question, answer = f"What is {a+5} + {b+5}?", a + b + 10
        else: question, answer = f"What is {max(a,b)*2} - {min(a,b)}?", max(a,b)*2 - min(a,b)
    else: # hard
        a, b, c = random.randint(5, 20), random.randint(2, 10), random.randint(2, 10)
        question, answer = f"Solve: ({a} + {b}) * {c}?", (a + b) * c
    identifier = question # Use the question itself as the identifier for math
    return {"type": "math", "identifier": identifier, "question": question, "answer": str(answer)}

def generate_memory_puzzle(difficulty):
    length = 4 if difficulty == "easy" else (6 if difficulty == "medium" else 8)
    sequence = [str(random.randint(0, 9)) for _ in range(length)]
    question = f"Remember: {' '.join(sequence)}" # Display sequence briefly in main.py
    answer = "".join(sequence) # User types the sequence without spaces
    identifier = answer # Use the sequence itself as identifier
    return {"type": "memory", "identifier": identifier, "question": question, "answer": answer, "sequence": sequence} # Pass sequence back

def generate_riddle_puzzle(difficulty=None): # Difficulty less relevant here
    if not RIDDLES: return None
    riddle, answer = random.choice(RIDDLES)
    identifier = answer # Use the answer as the identifier
    return {"type": "riddle", "identifier": identifier, "question": riddle, "answer": answer}

def generate_typing_puzzle(difficulty=None):
    if not TYPING_PHRASES: return None
    phrase = random.choice(TYPING_PHRASES)
    question = f"Type this exactly:\n'{phrase}'"
    answer = phrase
    identifier = phrase # Use the phrase itself
    return {"type": "typing", "identifier": identifier, "question": question, "answer": answer}

# --- Main Selection Function ---
MAX_GENERATION_ATTEMPTS = 20 # Prevent infinite loops if all puzzles are recent

def select_puzzles(count, difficulty="easy"):
    """Selects a list of unique, non-recent puzzles."""
    selected_puzzles = []
    history = load_history()
    recent_identifiers = get_recent_puzzle_identifiers(history)
    available_types = ["math", "memory", "riddle", "typing"] # Add more types here

    if count > len(available_types):
        print(f"Warning: Requested {count} puzzles, but only {len(available_types)} types available. Duplicates possible.")
        # Adjust logic if you want strict non-duplication of types per day

    attempts = 0
    while len(selected_puzzles) < count and attempts < MAX_GENERATION_ATTEMPTS:
        puzzle_type = random.choice(available_types)
        puzzle_data = None

        if puzzle_type == "math":
            puzzle_data = generate_math_puzzle(difficulty)
        elif puzzle_type == "memory":
            puzzle_data = generate_memory_puzzle(difficulty)
        elif puzzle_type == "riddle":
            puzzle_data = generate_riddle_puzzle(difficulty)
        elif puzzle_type == "typing":
             puzzle_data = generate_typing_puzzle(difficulty)
        # Add elif for other types

        if puzzle_data and puzzle_data["identifier"] not in recent_identifiers:
            selected_puzzles.append(puzzle_data)
            # Add to history immediately to prevent selecting same puzzle twice in one run
            add_to_history(history, puzzle_data["type"], puzzle_data["identifier"], puzzle_data["question"])
            recent_identifiers.add(puzzle_data["identifier"]) # Update local set
        else:
            # print(f"Debug: Skipping recent or invalid puzzle: {puzzle_data.get('identifier') if puzzle_data else 'None'}")
            pass

        attempts += 1

    if len(selected_puzzles) < count:
         print(f"Warning: Could only select {len(selected_puzzles)} unique non-recent puzzles after {attempts} attempts.")

    # Final save of history after selection is complete
    save_history(history)
    return selected_puzzles


# --- Validation Function (moved from main.py for consistency) ---
def validate_answer(puzzle_data, user_answer):
    """Validates the user's answer against the puzzle's expected answer."""
    expected = puzzle_data.get("answer", "")
    # Case-insensitive, strip whitespace for robustness
    is_correct = str(user_answer).strip().lower() == str(expected).strip().lower()
    # print(f"DEBUG: Validating '{user_answer}' against '{expected}' -> {is_correct}") # Debugging
    return is_correct

