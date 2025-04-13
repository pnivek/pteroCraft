# config.py
import os
import logging
import re
from dotenv import load_dotenv

load_dotenv()

# --- Discord/Pterodactyl/WebSocket/Buffer Config ---
TOKEN = os.getenv("DISCORD_TOKEN"); GUILD_ID = os.getenv("DISCORD_GUILD_ID")
try: GUILD_ID = int(GUILD_ID) if GUILD_ID else None
except ValueError: logging.critical("DISCORD_GUILD_ID invalid!"); GUILD_ID = None
PTERODACTYL_URL = os.getenv("PTERODACTYL_URL"); PTERODACTYL_API_KEY = os.getenv("PTERODACTYL_API_KEY"); PTERODACTYL_SERVER_ID = os.getenv("PTERODACTYL_SERVER_ID")
WS_RECONNECT_MIN_DELAY = 1.0; WS_RECONNECT_MAX_DELAY = 60.0; WS_RECONNECT_FACTOR = 2.0
WS_PING_INTERVAL = 20; WS_PING_TIMEOUT = 10
LOG_BUFFER_SIZE = 500

# --- Command/Response Configuration ---
COMMAND_RESPONSE_TIMEOUT = 5.0 # Keep previous adjustment

# Pre-compile regex for efficiency
# ----- MODIFIED: Add capture groups to 'list' regex -----
COMMAND_REGEX_MATCHERS = {
    # Group 1: Current players (\d+)
    # Group 2: Max players (\d+)
    # Group 3: Optional player list string (.*) - may be None if no colon/players
    "list": re.compile(r"There are (\d+) of a max of (\d+) players online:(?:\s*(.*))?$"),
    # ----- END MODIFICATION -----
}

# --- Logging Configuration ---
LOG_LEVEL = logging.INFO # Set back to INFO unless debugging
LOG_FORMAT = '%(asctime)s:%(levelname)s:%(name)s:%(funcName)s: %(message)s'
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
log = logging.getLogger(__name__)

# --- Validation ---
REQUIRED_ENV_VARS = { "DISCORD_TOKEN": TOKEN, "DISCORD_GUILD_ID": GUILD_ID, "PTERODACTYL_URL": PTERODACTYL_URL, "PTERODACTYL_API_KEY": PTERODACTYL_API_KEY, "PTERODACTYL_SERVER_ID": PTERODACTYL_SERVER_ID }
missing_vars = [name for name, value in REQUIRED_ENV_VARS.items() if value is None]
if missing_vars: log.critical(f"Missing critical env vars: {', '.join(missing_vars)}.")