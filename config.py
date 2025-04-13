# config.py
import os
import logging
import re
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN"); GUILD_ID = os.getenv("DISCORD_GUILD_ID")
try: GUILD_ID = int(GUILD_ID) if GUILD_ID else None
except ValueError: logging.critical("DISCORD_GUILD_ID invalid!"); GUILD_ID = None
PTERODACTYL_URL = os.getenv("PTERODACTYL_URL"); PTERODACTYL_API_KEY = os.getenv("PTERODACTYL_API_KEY"); PTERODACTYL_SERVER_ID = os.getenv("PTERODACTYL_SERVER_ID")
WS_RECONNECT_MIN_DELAY = 1.0; WS_RECONNECT_MAX_DELAY = 60.0; WS_RECONNECT_FACTOR = 2.0
WS_PING_INTERVAL = 20; WS_PING_TIMEOUT = 10

# --- Log Buffer Configuration ---
LOG_BUFFER_SIZE = 500 # Increased size

# --- Command/Response Configuration ---
COMMAND_RESPONSE_TIMEOUT = 7.0
COMMAND_ECHO_TIMEOUT = 2.0 # Keep echo timeout relatively short

# Pre-compile regex for efficiency
COMMAND_REGEX_MATCHERS = {
    "list": re.compile(r"There are \d+ of a max of \d+ players online:.*"),
}

# --- Logging Configuration ---
LOG_LEVEL = logging.INFO # Change DEBUG to INFO
LOG_FORMAT = '%(asctime)s:%(levelname)s:%(name)s:%(funcName)s: %(message)s'
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
log = logging.getLogger(__name__)

# --- Validation ---
REQUIRED_ENV_VARS = {
    "DISCORD_TOKEN": TOKEN, "DISCORD_GUILD_ID": GUILD_ID, "PTERODACTYL_URL": PTERODACTYL_URL,
    "PTERODACTYL_API_KEY": PTERODACTYL_API_KEY, "PTERODACTYL_SERVER_ID": PTERODACTYL_SERVER_ID
}
missing_vars = [name for name, value in REQUIRED_ENV_VARS.items() if value is None]
if missing_vars: log.critical(f"Missing critical env vars: {', '.join(missing_vars)}.")