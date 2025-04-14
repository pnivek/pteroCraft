# main.py
import re
import asyncio
import logging
import signal
import discord
from discord.commands import Option
from datetime import datetime, timezone

import config
from websocket_manager import WebsocketManager, strip_ansi

log = logging.getLogger(__name__)

# --- Global Variables & Setup ---
shutdown_event = asyncio.Event()
intents = discord.Intents.default()
bot = discord.Bot(intents=intents)
websocket_manager = WebsocketManager()

# --- Signal Handler & Events ---
def handle_signal(sig, frame):
    signal_name = signal.Signals(sig).name
    log.warning(f"Signal {sig} ({signal_name}) received.")
    shutdown_event.set()

@bot.event
async def on_ready():
    log.info(f'{bot.user.name} ready.')
    guild_id = config.GUILD_ID
    if guild_id:
        log.info(f'Operating in guild {guild_id}')
        await bot.sync_commands(guild_ids=[guild_id])
    else:
        log.warning("No GUILD_ID. Global commands.")
        await bot.sync_commands()
    if not shutdown_event.is_set():
        await websocket_manager.start()

@bot.event
async def on_disconnect():
    log.warning("Bot disconnected.")

@bot.event
async def on_resumed():
    log.info("Bot resumed.")

# --- Bot Commands ---
@bot.slash_command(
    guild_ids=[config.GUILD_ID] if config.GUILD_ID else None,
    name="log",
    description="Prints recent console log lines."
)
async def print_log_command(
    ctx: discord.ApplicationContext,
    lines: int = Option(int, "Number of recent lines", required=False, default=1, min_value=1, max_value=10)
):
    log.info(f"/print_log by {ctx.author} (lines={lines})")
    if not websocket_manager.is_authenticated:
        await ctx.respond("WS not ready.", ephemeral=True)
        return

    logs = websocket_manager.get_clean_recent_logs(num=lines)
    if logs:
        header = f"Last {len(logs)} log(s):"
        body = "\n".join(logs)
        max_len = 1980  # Discord message character limit is 2000, leave some buffer
        if len(body) > max_len:
            body = f"... (truncated)\n{body[-max_len:]}"
        response = f"{header}\n```\n{body}\n```"
    else:
        response = "Log buffer empty."

    await ctx.respond(response, ephemeral=True)

@bot.slash_command(
    guild_ids=[config.GUILD_ID] if config.GUILD_ID else None,
    name="status",
    description="Shows WebSocket connection status."
)
async def websocket_status_command(ctx: discord.ApplicationContext):
    log.info(f"/ws_status by {ctx.author}")
    if websocket_manager.is_authenticated:
        status = "✅ Auth & Listening"
    elif websocket_manager.is_connected:
        status = "🟠 Connected (Pending Auth)"
    else:
        status = "❌ Disconnected"
    await ctx.respond(f"WS Status: {status}", ephemeral=True)

@bot.slash_command(
    guild_ids=[config.GUILD_ID] if config.GUILD_ID else None,
    name="list", # Keep command name simple
    description="Lists the players currently online on the server."
)
async def list_players_command(ctx: discord.ApplicationContext):
    """Handles the /list command, parsing the response into an embed."""
    log.info(f"Command /list invoked by {ctx.author}")
    await ctx.defer(ephemeral=True) # Defer initially

    if not websocket_manager.is_authenticated:
        await ctx.followup.send("❌ Cannot process command: WebSocket not authenticated.", ephemeral=True)
        return

    command_key = "list"
    command_to_send = "list"
    
    result_tuple = await websocket_manager.send_command_and_find_response(
        command_to_send=command_to_send,
        response_command_key=command_key
    )

    if result_tuple:
        matched_pattern, response_log = result_tuple # Unpack tuple
        cleaned_response = strip_ansi(response_log)
        log.debug(f"Attempting to parse list response: '{cleaned_response}'")

        # Use the *specific matched pattern* for parsing
        match = matched_pattern.search(cleaned_response)
        if match:
            try:
                current_players_str, max_players_str, player_list_str = match.groups()
                current_players = int(current_players_str); max_players = int(max_players_str)
                player_names = [name.strip() for name in player_list_str.split(',') if name.strip()] if player_list_str else []
                log.info(f"Parsed list: {current_players}/{max_players} players. Names: {player_names}")

                embed = discord.Embed(title="Server Status", color=discord.Color.blue())
                embed.add_field(name="Capacity⚡", value=f"• **{current_players} / {max_players}**", inline=False)
                if player_names:
                    player_text = "\n".join([f"• `{name}`" for name in player_names])
                    if len(player_text) > 1020: player_text = player_text[:1017] + "\n..."
                    embed.add_field(name="Active Players👥", value=player_text, inline=False)
                else:
                    embed.add_field(name="Active Players👥", value="*No players currently online.*", inline=False)
                embed.timestamp = datetime.now(timezone.utc)
                embed.set_footer(text=f"Requested by {ctx.author.display_name}")
                await ctx.followup.send(embed=embed, ephemeral=False) # Public success

            except Exception as e:
                 log.exception(f"Error constructing list embed: {e}")
                 await ctx.followup.send("⚠️ Error parsing/displaying server response.", ephemeral=True)
        else:
             log.warning(f"Found log line for 'list', but pattern {matched_pattern.pattern} didn't match cleaned response: '{cleaned_response}'")
             await ctx.followup.send(f"⚠️ Found response line, but couldn't parse details. Raw:\n```\n{cleaned_response[:1900]}\n```", ephemeral=True)
    else:
        await ctx.followup.send(f"🟡 Sent '{command_to_send}', no matching response found.", ephemeral=True)

@bot.slash_command(
    guild_ids=[config.GUILD_ID] if config.GUILD_ID else None,
    name="whitelist",
    description="Adds or removes a player from the server whitelist."
)
async def whitelist_command(
    ctx: discord.ApplicationContext,
    action: str = Option(str, "Choose action", choices=["add", "remove"]),
    username: str = Option(str, "Minecraft username (case-sensitive)")
):
    """Handles adding/removing players from the whitelist using exact string matching."""
    log.info(f"/whitelist {action} {username} by {ctx.author}")
    await ctx.defer(ephemeral=True) # Start private

    if not websocket_manager.is_authenticated:
        await ctx.followup.send("❌ Cannot process command: WebSocket not authenticated.", ephemeral=True)
        return
    if not re.match(r"^\w{3,16}$", username): # Basic Minecraft username check
        await ctx.followup.send("❌ Invalid username format.", ephemeral=True)
        return

    command_to_send = f"whitelist {action} {username}"

    # --- Construct the EXACT expected response strings ---
    # NOTE: These MUST match the server output *exactly* after cleaning (strip_ansi)
    expected_responses = []
    add_success_str = f"Added {username} to the whitelist"
    add_fail_str = "Player is already whitelisted"
    remove_success_str = f"Removed {username} from the whitelist"
    remove_fail_str = "Player is not whitelisted"
    not_found_str = "That player does not exist"

    if action == "add":
        expected_responses.extend([add_success_str, add_fail_str, not_found_str])
    elif action == "remove":
        expected_responses.extend([remove_success_str, remove_fail_str, not_found_str])

    # --- Call the new manager method ---
    matched_string = await websocket_manager.send_command_and_await_strings(
        command_to_send=command_to_send,
        expected_strings=expected_responses
    )

    # --- Process the result ---
    if matched_string:
        log.info(f"Whitelist command response received: '{matched_string}'")
        response_message = "🟡 Command sent, but result unclear." # Default

        # Compare the *cleaned* matched string with our *cleaned* expected strings
        if matched_string == strip_ansi(add_success_str).strip():
             response_message = f"✅ Added `{username}` to the whitelist."
        elif matched_string == strip_ansi(add_fail_str).strip():
             response_message = f"ℹ️ Player `{username}` is already whitelisted."
        elif matched_string == strip_ansi(remove_success_str).strip():
             response_message = f"✅ Removed `{username}` from the whitelist."
        elif matched_string == strip_ansi(remove_fail_str).strip():
             response_message = f"ℹ️ Player `{username}` is not on the whitelist."
        elif matched_string == strip_ansi(not_found_str).strip():
             response_message = f"❌ Player `{username}` does not exist."
        else:
            log.error(f"Matched string '{matched_string}' doesn't match known expected strings for whitelist?")
            response_message = f"⚠️ Unknown response received:\n```\n{matched_string[:1900]}\n```"

        await ctx.followup.send(response_message, ephemeral=True)

    else:
        # Timeout finding any relevant response string
        await ctx.followup.send(f"🟡 Command '{command_to_send}' sent, but no confirmation received.", ephemeral=True)


# --- Main Execution Logic ---
async def run_discord_bot():
    try:
        log.info("Attempting discord bot start...")
        async with bot:
            await bot.start(config.TOKEN)
        log.info("bot.start() completed normally.")  # This might only be reached if start returns
    except discord.LoginFailure:
        log.critical("Discord login failed. Check token.")
        shutdown_event.set()
    except asyncio.CancelledError:
        log.info("Discord bot task was cancelled.")
        # No need to set shutdown_event here, cancellation is usually part of shutdown
    except Exception as e:
        log.exception(f"Unhandled exception in run_discord_bot: {e}")
        shutdown_event.set()  # Signal shutdown on unexpected errors
    finally:
        log.info("run_discord_bot coroutine finished.")

async def main():
    loop = asyncio.get_running_loop()
    log.debug("Registering signals...")
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal, sig, None)
            log.debug(f"Registered asyncio handler for {sig}.")
        except NotImplementedError:
            log.warning(f"Asyncio handler not supported for {sig}. Using fallback.")
            signal.signal(sig, handle_signal)
        except Exception as e:
            log.error(f"Failed signal handler setup for {sig}: {e}")
    
    log.info("Launching bot...")
    discord_task = loop.create_task(run_discord_bot(), name="DiscordBotTask")
    log.info("Waiting for shutdown signal...")
    await shutdown_event.wait()
    log.info("Shutdown event received.")
    
    log.info("Initiating final cleanup...")
    await asyncio.sleep(0.1)
    
    if websocket_manager:
        log.info("Stopping WS manager...")
        await websocket_manager.stop()
    
    if bot and not bot.is_closed():
        log.info("Closing bot...")
        await bot.close()
    
    if discord_task and not discord_task.done():
        log.info("Cancelling Discord task...")
        discord_task.cancel()
        await discord_task
    
    await asyncio.sleep(0.5)
    log.info("Cleanup complete.")

if __name__ == "__main__":
    if config.missing_vars:
        log.critical("Missing config. Aborting.")
    else:
        asyncio.run(main())