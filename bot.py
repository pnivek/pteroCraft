# main.py
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

    # Use the reverse-scan method
    response_log = await websocket_manager.send_command_and_find_response(
        command_to_send=command_to_send,
        response_command_key=command_key
    )

    if response_log:
        cleaned_response = strip_ansi(response_log)
        log.debug(f"Attempting to parse list response: '{cleaned_response}'")

        # Use the refined regex from config to extract parts
        match = config.COMMAND_REGEX_MATCHERS["list"].search(cleaned_response)

        if match:
            try:
                current_players_str, max_players_str, player_list_str = match.groups()
                current_players = int(current_players_str)
                max_players = int(max_players_str)

                # Parse player names (handle None or empty string)
                player_names = []
                if player_list_str:
                    player_names = [name.strip() for name in player_list_str.split(',') if name.strip()]

                log.info(f"Parsed list: {current_players}/{max_players} players. Names: {player_names}")

                # --- Create Embed ---
                embed = discord.Embed(
                    title="Server Status",
                    color=discord.Color.blue() # Or themed color
                )
                embed.add_field(
                    name="Capacity⚡",
                    value=f"• **{current_players} / {max_players}**",
                    inline=False
                )

                # Add Player List field
                if player_names:
                    # Limit display length for embed field (1024 chars)
                    player_text = "\n".join([f"• `{name}`" for name in player_names])
                    if len(player_text) > 1020:
                         player_text = player_text[:1017] + "\n..." # Truncate
                    embed.add_field(name="Active Players👥", value=player_text, inline=False)
                else:
                    embed.add_field(name="Active Players👥", value="*No players currently online.*", inline=False)

                embed.timestamp = datetime.now(timezone.utc)  # Use timezone-aware approach
                embed.set_footer(text=f"Requested by {ctx.author.display_name}")

                # Send the embed publicly on success
                await ctx.followup.send(embed=embed, ephemeral=False)

            except ValueError:
                log.error(f"Failed to parse player counts from regex match: {match.groups()}")
                await ctx.followup.send("⚠️ Error parsing player count from server response.", ephemeral=True)
            except Exception as e:
                 log.exception(f"Error constructing list embed: {e}")
                 await ctx.followup.send("⚠️ An internal error occurred creating the response.", ephemeral=True)

        else:
            # The line found by send_command_and_find_response didn't match the *detailed* regex
            log.warning(f"Found log line for 'list', but it didn't match the detailed parsing regex. Line: '{cleaned_response}'")
            await ctx.followup.send(f"⚠️ Found a response line, but couldn't parse details. Raw:\n```\n{cleaned_response[:1900]}\n```", ephemeral=True)
    else:
        # Timeout occurred
        await ctx.followup.send(f"🟡 Command '{command_to_send}' sent, but no matching response found within timeout.", ephemeral=True)



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