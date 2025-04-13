# websocket_manager.py
import asyncio
import json
import logging
import random
import re
from collections import deque
from typing import Deque, Optional, Pattern

import aiohttp
import websockets

from config import (PTERODACTYL_URL, PTERODACTYL_API_KEY, PTERODACTYL_SERVER_ID,
                    WS_RECONNECT_MIN_DELAY, WS_RECONNECT_MAX_DELAY,
                    WS_RECONNECT_FACTOR, WS_PING_INTERVAL, WS_PING_TIMEOUT,
                    LOG_BUFFER_SIZE,
                    COMMAND_REGEX_MATCHERS, COMMAND_RESPONSE_TIMEOUT)

log = logging.getLogger(__name__)

ansi_escape_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# --- Utility Function (defined within module) ---
def strip_ansi(text: object) -> str:
    if not isinstance(text, str):
        try: 
            text = str(text)
        except Exception: 
            return ""
    return ansi_escape_pattern.sub('', text)

# --- Websocket Manager Class ---
class WebsocketManager:
    def __init__(self):
        self._api_key = PTERODACTYL_API_KEY
        self._server_id = PTERODACTYL_SERVER_ID
        self._panel_url = PTERODACTYL_URL
        self._websocket_url = f"{self._panel_url}/api/client/servers/{self._server_id}/websocket"
        self._session: Optional[aiohttp.ClientSession] = None
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._is_connected: bool = False
        self._reconnect_delay: float = WS_RECONNECT_MIN_DELAY
        self.log_buffer: Deque[str] = deque(maxlen=LOG_BUFFER_SIZE)
        self.is_authenticated: bool = False
        self._command_patterns: dict[str, Pattern[str]] = COMMAND_REGEX_MATCHERS
        self._command_response_timeout: float = COMMAND_RESPONSE_TIMEOUT

    # --- Core Logic Methods ---
    async def _get_websocket_details(self) -> Optional[dict]:
        if not self._session or self._session.closed: 
            log.error("aiohttp inactive.")
            return None
            
        h = {'Authorization': f'Bearer {self._api_key}', 'Accept': 'application/json'}
        log.debug(f"Req WS details:{self._websocket_url}")
        
        try:
            async with self._session.get(self._websocket_url, headers=h, timeout=10) as r:
                if r.status == 200: 
                    d = await r.json()
                    log.info("Got WS details.")
                    return d.get('data')
                else: 
                    log.error(f"Fail WS details:{r.status}-{await r.text()}")
                    return None
        except asyncio.TimeoutError: 
            log.error("Timeout fetching WS details.")
            return None
        except aiohttp.ClientError as e: 
            log.error(f"HTTP error fetching WS details: {e}")
            return None
        except Exception as e: 
            log.exception("Err fetch WS details.")
            return None

    async def _websocket_listener(self):
        while True:
            self.is_authenticated = False
            d = await self._get_websocket_details()
            
            if not d: 
                log.warning(f"No WS details. Retry {self._reconnect_delay:.1f}s")
                await asyncio.sleep(self._reconnect_delay)
                self._update_reconnect_delay(True)
                continue
                
            url, tok = d['socket'], d['token']
            log.info(f"Connecting WS:{url}")
            
            try:
                async with websockets.connect(url, ping_interval=WS_PING_INTERVAL, ping_timeout=WS_PING_TIMEOUT) as ws:
                    self._websocket = ws
                    self._is_connected = True
                    log.info("WS connected.")
                    self._update_reconnect_delay(False)
                    
                    if not await self._authenticate(ws, tok): 
                        log.warning("Auth failed, retry.")
                        await asyncio.sleep(5)
                        continue
                        
                    self.is_authenticated = True
                    log.info("WS authenticated. Listening...")
                    await self._message_loop(ws)
            except websockets.exceptions.WebSocketException as e: 
                log.error(f"WS connection failed:{e}")
            except asyncio.CancelledError: 
                log.info("WS listener cancelled.")
                self._is_connected = False
                raise
            except Exception as e: 
                log.exception(f"Unexpected WS connect error:{e}")
                
            self._is_connected = False
            self.is_authenticated = False
            self._websocket = None
            log.info(f"WS disconnected. Retry {self._reconnect_delay:.1f}s")
            await asyncio.sleep(self._reconnect_delay)
            self._update_reconnect_delay(True)

    async def _authenticate(self, ws, token) -> bool:
        try: 
            await ws.send(json.dumps({"event": "auth", "args": [token]}))
            log.info("Sent auth token.")
        except Exception as e: 
            log.error(f"WS send err auth:{e}")
            return False
            
        try: 
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(raw)
        except asyncio.TimeoutError: 
            log.error("WS auth timed out.")
            return False
        except websockets.exceptions.ConnectionClosed: 
            log.warning("WS closed during auth.")
            return False
        except Exception as e: 
            log.exception(f"WS auth recv/decode err:{e}")
            return False
            
        if data.get("event") == "auth success": 
            log.info("WS auth ok.")
            return True
        else: 
            log.error(f"WS auth fail:{data.get('args', ['err'])[0]}")
            return False

    async def _message_loop(self, ws):
        """Handles received WebSocket messages."""
        while True:
            line = None  # Initialize line to None at the start of each loop iteration
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                ev = data.get("event")
            except websockets.exceptions.ConnectionClosedOK:
                log.info("WS closed normally.")
                break
            except websockets.exceptions.ConnectionClosedError as e:
                log.warning(f"WS closed err:{e}")
                break
            except json.JSONDecodeError as e:
                log.error(f"JSON decode err: {e}. Raw: {msg[:100]}...")
                continue  # Skip this message
            except Exception as e:
                log.exception(f"WS loop err:{e}")
                break  # Exit loop on other errors

            # Process based on event type
            if ev == "console output":
                args = data.get("args", [])
                line = args[0] if args else None  # Assign line HERE
                # --- Indent the following block ---
                if line is not None:
                    self.log_buffer.append(line)
                    log.debug(f"Log raw:{str(line)[:80]}...")
                # --- End of indented block ---
            elif ev == "status":
                log.debug(f"Status:{data.get('args', ['N/A'])[0]}")
            elif ev == "token expiring" or ev == "token expired":
                log.warning(f"'{ev}' received. Reconnecting.")
                break
            # else: # Optionally log unhandled events
            #     log.debug(f"Unhandled WS event: {ev}")

    def _update_reconnect_delay(self, i: bool, r: bool = False):
        self._reconnect_delay = (WS_RECONNECT_MIN_DELAY if r or not i 
                                else min(self._reconnect_delay * WS_RECONNECT_FACTOR, WS_RECONNECT_MAX_DELAY))
        j = random.uniform(0.1, self._reconnect_delay * 0.1 + 0.1)
        self._reconnect_delay = min(self._reconnect_delay + j, WS_RECONNECT_MAX_DELAY)
        log.debug(f"Reconnect delay:{self._reconnect_delay:.1f}s")

    # --- Public Methods ---
    async def start(self):
        if self._listener_task and not self._listener_task.done():
            log.warning("WS task running.")
            return
            
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
            log.info("Created session.")
            
        log.info("Starting WS task...")
        self._listener_task = asyncio.create_task(self._websocket_listener())
        self._listener_task.add_done_callback(self._log_task_exception)

    async def stop(self):
        log.info("Stopping WS manager...")
        
        if self._listener_task and not self._listener_task.done():
            log.info("Cancelling WS task.")
            self._listener_task.cancel()
            await asyncio.gather(self._listener_task, return_exceptions=True)
            
        if self._websocket:
            log.info("Closing WS...")
            try:
                await self._websocket.close()
            except Exception:
                pass
            self._websocket = None
            
        if self._session and not self._session.closed:
            log.info("Closing session.")
            await self._session.close()
            
        log.info("WS manager stopped.")

    async def send_command(self, cmd: str) -> bool:
        if not self.is_authenticated or not self._websocket:
            log.error(f"Cannot send '{cmd}': WS not ready.")
            return False
            
        pl = {"event": "send command", "args": [cmd]}
        log.info(f"Sending cmd: {cmd}")
        
        try:
            await self._websocket.send(json.dumps(pl))
            return True
        except websockets.exceptions.ConnectionClosed:
            log.error(f"Fail send '{cmd}': Conn closed.")
            self._is_connected = False
            self.is_authenticated = False
            self._websocket = None
            return False
        except Exception as e:
            log.exception(f"Error sending '{cmd}': {e}")
            return False

    async def send_command_and_find_response(self, command_to_send: str, response_command_key: str) -> Optional[str]:
        """
        Sends a command, then polls the buffer scanning backwards for the LATEST
        log line matching the response pattern within a timeout.

        Args:
            command_to_send: The command string to send.
            response_command_key: The key in config.COMMAND_REGEX_MATCHERS for the response.

        Returns:
            The raw log line matching the response pattern, or None if not found/timeout.
        """
        if not self.is_authenticated:
            log.error(f"Cannot process '{command_to_send}': WS not authenticated.")
            return None
            
        response_pattern = self._command_patterns.get(response_command_key)
        if not response_pattern:
            log.error(f"No pattern for key '{response_command_key}'")
            return None

        # --- Send Command ---
        if not await self.send_command(command_to_send):
            return None  # Error sending
        
        # --- sleep for 0.5 seconds to let feedback come through ---
        await asyncio.sleep(0.5)

        # --- Wait for Response (Reverse Scan) ---
        start_time = asyncio.get_running_loop().time()
        log.debug(f"Waiting {self._command_response_timeout:.1f}s for RESPONSE pattern '{response_command_key}' after sending '{command_to_send}'.")
        
        while asyncio.get_running_loop().time() - start_time < self._command_response_timeout:
            # Get a snapshot of the *entire* buffer
            # Use reversed() directly on the deque for efficiency if possible,
            # but list snapshot is safer against modification during iteration
            current_buffer_snapshot = list(self.log_buffer)
            log.debug(f"Reverse Scan Poll: Buffer len={len(current_buffer_snapshot)}")

            # Scan backwards (newest to oldest)
            for i in range(len(current_buffer_snapshot) - 1, -1, -1):
                try:
                    raw_line = current_buffer_snapshot[i]
                    cleaned_line = strip_ansi(raw_line).strip()
                    if not cleaned_line:
                        continue

                    # Match pattern against cleaned line
                    if response_pattern.search(cleaned_line):
                        log.info(f"Found LATEST response pattern '{response_command_key}' at index {i}. Raw: '{raw_line[:100]}...'")
                        return raw_line  # Success: return the raw line

                except Exception as e:
                    log.error(f"Error processing log during reverse scan at index {i}: {e}")

            # Wait before polling again
            await asyncio.sleep(0.2)  # Polling interval

        log.warning(f"Timeout ({self._command_response_timeout:.1f}s) finding response pattern '{response_command_key}' for command '{command_to_send}'.")
        return None
    # --- END REVISED METHOD ---

    # --- Log Accessor Methods ---
    def get_last_log(self) -> str | None:
        try:
            return str(self.log_buffer[-1]) if self.log_buffer else None
        except Exception as e:
            log.error(f"Err get_last_log: {e}")
            return None

    def get_clean_last_log(self) -> str | None:
        last = self.get_last_log()
        return strip_ansi(last) if last else None

    def get_recent_logs(self, num: int = 1) -> list[str]:
        if num < 1:
            return []
        try:
            buf_list = list(self.log_buffer)
            str_logs = [str(l) for l in buf_list if isinstance(l, (str, bytes, bytearray))]
            return str_logs[-num:]
        except Exception as e:
            log.error(f"Err get_recent_logs: {e}")
            return []

    def get_clean_recent_logs(self, num: int = 1) -> list[str]:
        raw = self.get_recent_logs(num)
        return [strip_ansi(l) for l in raw]

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def _log_task_exception(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("Exception from WS task:")