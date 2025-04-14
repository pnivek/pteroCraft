# config.py
import os
import logging
import re
from dotenv import load_dotenv
from typing import Dict, List, Pattern, Final, Tuple

load_dotenv()

# --- Response Type Constants ---
LIST_SUCCESS: Final = "LIST_SUCCESS"
WL_ADD_OK: Final = "WL_ADD_OK"
WL_ALREADY: Final = "WL_ALREADY"
WL_RM_OK: Final = "WL_RM_OK"
WL_NOT_LISTED: Final = "WL_NOT_LISTED"
WL_NOT_EXIST: Final = "WL_NOT_EXIST"

# --- (Discord <-> WebSocket <-> Pterodactyl) Buffer Config ---
TOKEN = os.getenv("DISCORD_TOKEN"); GUILD_ID = os.getenv("DISCORD_GUILD_ID")
try: GUILD_ID = int(GUILD_ID) if GUILD_ID else None
except ValueError: logging.critical("DISCORD_GUILD_ID invalid!"); GUILD_ID = None
PTERODACTYL_URL = os.getenv("PTERODACTYL_URL");
PTERODACTYL_API_KEY = os.getenv("PTERODACTYL_API_KEY");
PTERODACTYL_SERVER_ID = os.getenv("PTERODACTYL_SERVER_ID")
WS_RECONNECT_MIN_DELAY = 1.0;
WS_RECONNECT_MAX_DELAY = 60.0;
WS_RECONNECT_FACTOR = 2.0
WS_PING_INTERVAL = 20; WS_PING_TIMEOUT = 10
LOG_BUFFER_SIZE = 500

# --- Command/Response Configuration ---
COMMAND_RESPONSE_TIMEOUT = 5.0

# Patterns match CLEANED log lines (ANSI codes, timestamps stripped)
# Order matters: More specific patterns should come first if overlap exists.
COMMAND_RESPONSES: Dict[str, List[Tuple[Pattern[str], str]]] = {
    "list": [
        (re.compile(r"There are (\d+) of a max of (\d+) players online:(?:\s*(.*))?$"), LIST_SUCCESS)
    ],
    "whitelist": [
        # Order: specific successes, specific failures, general failures
        (re.compile(r"Added (?P<username>\S+) to the whitelist"), WL_ADD_OK),
        (re.compile(r"Player is already whitelisted"), WL_ALREADY),
        (re.compile(r"Removed (?P<username>\S+) from the whitelist"), WL_RM_OK),
        (re.compile(r"Player is not whitelisted"), WL_NOT_LISTED),
        (re.compile(r"That player does not exist"), WL_NOT_EXIST),
    ],
    # "seed": [(re.compile(r"Seed: \[([-\d]+)\]"), "SEED_SUCCESS")],
}

# --- Logging Configuration ---
LOG_LEVEL = logging.INFO # Keep INFO unless debugging
LOG_FORMAT = '%(asctime)s:%(levelname)s:%(name)s:%(funcName)s: %(message)s'
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
log = logging.getLogger(__name__)

# --- Validation ---
REQUIRED_ENV_VARS = {
    "DISCORD_TOKEN": TOKEN,
    "DISCORD_GUILD_ID": GUILD_ID,
    "PTERODACTYL_URL": PTERODACTYL_URL,
    "PTERODACTYL_API_KEY": PTERODACTYL_API_KEY,
    "PTERODACTYL_SERVER_ID": PTERODACTYL_SERVER_ID
}
missing_vars = [name for name, value in REQUIRED_ENV_VARS.items() if value is None]
if missing_vars: log.critical(f"Missing critical env vars: {', '.join(missing_vars)}.")