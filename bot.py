# main.py
import asyncio
import logging
import signal
import discord
from discord.commands import Option

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
    name="list",
    description="Lists the players currently online."
)
async def list_players_command(ctx: discord.ApplicationContext):
    log.info(f"Command /list_players invoked by {ctx.author}")
    await ctx.defer(ephemeral=True)
    if not websocket_manager.is_authenticated:
        await ctx.followup.send("❌ WS not authenticated.", ephemeral=True)
        return

    command_key = "list"
    command_to_send = "list"
    buffer_len_before_send = len(websocket_manager.log_buffer)
    log.debug(f"Buffer length before sending '{command_to_send}': {buffer_len_before_send}")

    response_log = await websocket_manager.send_command_and_find_response(
        command_to_send=command_to_send,
        response_command_key=command_key
    )

    if response_log:
        cleaned_response = strip_ansi(response_log)
        if "players online:" in cleaned_response.lower():
            display_response = cleaned_response[:1950] + "..." if len(cleaned_response) > 1950 else cleaned_response
            await ctx.followup.send(f"👥 **Online Players:**\n```\n{display_response}\n```", ephemeral=False)
        else:
            display_response = cleaned_response[:1900] + "..." if len(cleaned_response) > 1900 else cleaned_response
            await ctx.followup.send(f"⚠️ Unexpected response format:\n```\n{display_response}\n```", ephemeral=True)
    else:
        await ctx.followup.send(f"🟡 Sent '{command_to_send}', no matching response found.", ephemeral=True)


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