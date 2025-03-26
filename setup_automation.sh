#!/bin/bash

# --- Configuration ---
WATCHDOG_SCRIPT_NAME="watchdog.sh"
UPDATER_SCRIPT_NAME="daily_updater.py"
MAIN_SCRIPT_NAME="main.py"
# Cron schedules (adjust as needed)
WATCHDOG_SCHEDULE="*/5 * * * *" # Every 5 minutes
UPDATER_SCHEDULE="0 8,13,18 * * *" # At 8:00, 13:00, 18:00 daily

# --- Helper Functions ---
echo_info() {
    echo "[INFO] $1"
}

echo_warn() {
    echo "[WARN] $1"
}

echo_error() {
    echo "[ERROR] $1" >&2
}

# --- Get Absolute Paths ---
echo_info "Determining absolute paths..."
PROJECT_DIR=$(pwd) # Assumes script is run from project root
SCRIPTS_DIR="${PROJECT_DIR}/scripts"
LOGS_DIR="${PROJECT_DIR}/logs" # For cron output redirection

# Check if scripts directory exists
if [ ! -d "$SCRIPTS_DIR" ]; then
    echo_error "Scripts directory not found at ${SCRIPTS_DIR}"
    echo_error "Please run this script from the root of the valinor_dawn project."
    exit 1
fi

# Find Python 3 executable
PYTHON_EXEC=$(which python3)
if [ -z "$PYTHON_EXEC" ]; then
    echo_error "python3 command not found in PATH."
    echo_error "Please ensure Python 3 is installed and accessible."
    exit 1
fi
echo_info "Using Python 3 executable: ${PYTHON_EXEC}"
echo_info "Project directory: ${PROJECT_DIR}"

# --- Create Watchdog Script ---
WATCHDOG_PATH="${SCRIPTS_DIR}/${WATCHDOG_SCRIPT_NAME}"
MAIN_SCRIPT_PATH="${SCRIPTS_DIR}/${MAIN_SCRIPT_NAME}"
echo_info "Creating/Updating watchdog script: ${WATCHDOG_PATH}"

# Use cat with EOF to write the script content
cat << EOF > "$WATCHDOG_PATH"
#!/bin/bash
# Watchdog for Valinor Dawn - Automatically generated

# Absolute path to the main script
MAIN_APP_PATH="${MAIN_SCRIPT_PATH}"
PYTHON_EXEC_PATH="${PYTHON_EXEC}"
APP_DIR="\$(dirname "\$MAIN_APP_PATH")" # Directory where main.py is

# Check if the main script is running
# pgrep -f looks for the full command line
if ! pgrep -f "\$PYTHON_EXEC_PATH \$MAIN_APP_PATH" > /dev/null; then
    echo "\$(date): Valinor Dawn (main.py) not running. Starting..."
    # Change to the script's directory before running to handle relative paths within main.py
    cd "\$APP_DIR" || exit 1
    # Start in the background (&) and redirect output (optional)
    nohup "\$PYTHON_EXEC_PATH" "\$MAIN_APP_PATH" > /dev/null 2>&1 &
else
    # Optional: Log that it's already running
    # echo "\$(date): Valinor Dawn (main.py) is already running."
    : # No-op, already running
fi
EOF

# Make watchdog executable
chmod +x "$WATCHDOG_PATH"
if [ $? -ne 0 ]; then
    echo_error "Failed to make watchdog script executable."
    exit 1
fi
echo_info "Watchdog script created and made executable."

# --- Setup Cron Jobs ---
echo_info "Setting up cron jobs..."

# Check if crontab command exists
if ! command -v crontab &> /dev/null; then
    echo_error "'crontab' command not found. Cannot automate cron job setup."
    echo_error "Please add the following lines manually to your cron configuration:"
    echo "# Valinor Dawn Watchdog"
    echo "${WATCHDOG_SCHEDULE} ${WATCHDOG_PATH} >> ${LOGS_DIR}/cron_watchdog.log 2>&1"
    echo "# Valinor Dawn Daily Updater"
    echo "${UPDATER_SCHEDULE} ${PYTHON_EXEC} ${SCRIPTS_DIR}/${UPDATER_SCRIPT_NAME} >> ${LOGS_DIR}/cron_updater.log 2>&1"
    exit 1
fi

# Define cron job lines and comments
WATCHDOG_COMMENT="# Valinor Dawn Watchdog"
WATCHDOG_JOB="${WATCHDOG_SCHEDULE} ${WATCHDOG_PATH} >> ${LOGS_DIR}/cron_watchdog.log 2>&1"
UPDATER_COMMENT="# Valinor Dawn Daily Updater"
UPDATER_JOB="${UPDATER_SCHEDULE} ${PYTHON_EXEC} ${SCRIPTS_DIR}/${UPDATER_SCRIPT_NAME} >> ${LOGS_DIR}/cron_updater.log 2>&1"

# Get current crontab content, handling case where it might be empty
CURRENT_CRON=$(crontab -l 2>/dev/null || true) # Get content or empty string

# Check and add watchdog job
if echo "$CURRENT_CRON" | grep -Fq "$WATCHDOG_COMMENT"; then
    echo_info "Watchdog cron job already exists. Skipping."
else
    echo_info "Adding watchdog cron job..."
    (echo "$CURRENT_CRON"; echo "$WATCHDOG_COMMENT"; echo "$WATCHDOG_JOB") | crontab -
    if [ $? -ne 0 ]; then echo_error "Failed to add watchdog cron job."; else echo_info "Watchdog job added."; fi
fi

# Refresh CURRENT_CRON after potential modification
CURRENT_CRON=$(crontab -l 2>/dev/null || true)

# Check and add updater job
if echo "$CURRENT_CRON" | grep -Fq "$UPDATER_COMMENT"; then
    echo_info "Daily updater cron job already exists. Skipping."
else
    echo_info "Adding daily updater cron job..."
    (echo "$CURRENT_CRON"; echo "$UPDATER_COMMENT"; echo "$UPDATER_JOB") | crontab -
    if [ $? -ne 0 ]; then echo_error "Failed to add daily updater cron job."; else echo_info "Daily updater job added."; fi
fi

echo_info "Cron job setup finished."
echo_warn "Make sure the logs directory (${LOGS_DIR}) exists and is writable by the user running cron."
echo_info "To view your cron jobs, run: crontab -l"
echo_info "To remove these jobs later, run 'crontab -e' and delete the lines under the Valinor Dawn comments."
echo_info "Setup complete!"

exit 0
