# main.py
import re
import asyncio
import logging
import signal
import discord #pycord
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
    lines: int = Option(int, "Number of recent lines", required=False, default=1, min_value=1, max_value=50)
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
    name="list",  # Keep command name simple
    description="Lists the players currently online on the server."
)
async def list_players_command(ctx: discord.ApplicationContext):
    log.info(f"Command /list invoked by {ctx.author}")
    await ctx.defer(ephemeral=True)
    if not websocket_manager.is_authenticated:
        await ctx.followup.send("❌ WS not authenticated.", ephemeral=True)
        return

    command_key = "list"
    command_to_send = "list"

    result_tuple = await websocket_manager.send_command_and_get_response(
        command_to_send=command_to_send,
        response_command_key=command_key
    )

    if result_tuple:
        response_type, response_log = result_tuple  # Unpack response type and raw log
        cleaned_response = strip_ansi(response_log)

        # Check if the response type matches what we expect for list success
        if response_type == config.LIST_SUCCESS:
            # Use the specific pattern associated with LIST_SUCCESS for parsing
            # Find the correct pattern tuple from config
            list_pattern_tuple = next((item for item in config.COMMAND_RESPONSES[command_key] 
                                      if item[1] == config.LIST_SUCCESS), None)
            if list_pattern_tuple:
                list_pattern = list_pattern_tuple[0]
                match = list_pattern.search(cleaned_response)
                if match:
                    try:
                        current, max_p, p_list_str = match.groups()
                        current = int(current)
                        max_p = int(max_p)
                        p_names = [n.strip() for n in p_list_str.split(',') if n.strip()] if p_list_str else []
                        log.info(f"Parsed list: {current}/{max_p}. Names: {p_names}")
                        
                        embed = discord.Embed(title="Server Status", color=discord.Color.blue())
                        embed.add_field(name="Capacity⚡", value=f"• **{current} / {max_p}**", inline=False)
                        
                        p_text = "\n".join([f"• `{n}`" for n in p_names]) if p_names else "*No players online.*"
                        if len(p_text) > 1020:
                            p_text = p_text[:1017] + "\n..."
                            
                        embed.add_field(name="Active Players👥", value=p_text, inline=False)
                        embed.timestamp = datetime.now(timezone.utc)
                        embed.set_footer(text=f"Req by {ctx.author.display_name}")
                        await ctx.followup.send(embed=embed, ephemeral=False)
                    except Exception as e:
                        log.exception(f"Err construct embed:{e}")
                        await ctx.followup.send("⚠️ Err parse/display.", ephemeral=True)
                else:
                    log.warning(f"List success type received, but regex no match:'{cleaned_response}'")
                    await ctx.followup.send(
                        f"⚠️ Received response, but couldn't parse details:\n```\n{cleaned_response[:1900]}\n```", 
                        ephemeral=True
                    )
            else:
                log.error("Internal config error: LIST_SUCCESS pattern not found")
                await ctx.followup.send("⚠️ Internal configuration error.", ephemeral=True)
        else:
            # Should not happen if config is correct for 'list', but handle unexpected type
            log.warning(f"Received unexpected response type '{response_type}' for list command.")
            await ctx.followup.send(
                f"⚠️ Received unexpected response type:\n```\n{cleaned_response[:1900]}\n```", 
                ephemeral=True
            )
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
    log.info(f"/whitelist {action} {username} by {ctx.author}")
    await ctx.defer(ephemeral=True)
    
    if not websocket_manager.is_authenticated:
        await ctx.followup.send("❌ WS not authenticated.", ephemeral=True)
        return
        
    if not re.match(r"^\w{3,16}$", username):
        await ctx.followup.send("❌ Invalid username format.", ephemeral=True)
        return

    command_key = "whitelist"
    command_to_send = f"whitelist {action} {username}"

    result_tuple = await websocket_manager.send_command_and_get_response(
        command_to_send=command_to_send,
        response_command_key=command_key
    )

    if result_tuple:
        response_type, response_log = result_tuple  # Unpack response type and raw log
        # We typically don't need the cleaned log here unless debugging
        # cleaned_response = strip_ansi(response_log)
        log.info(f"Whitelist response received, type: {response_type}")

        # Default message
        response_message = f"🟡 Command '{command_to_send}' sent, unknown result ({response_type})."

        # --- Compare response_type against config constants ---
        if response_type == config.WL_ADD_OK:
            response_message = f"✅ Added `{username}` to the whitelist."
        elif response_type == config.WL_ALREADY:
            response_message = f"ℹ️ Player `{username}` is already whitelisted."
        elif response_type == config.WL_RM_OK:
            response_message = f"✅ Removed `{username}` from the whitelist."
        elif response_type == config.WL_NOT_LISTED:
            response_message = f"ℹ️ Player `{username}` is not on the whitelist."
        elif response_type == config.WL_NOT_EXIST:
            response_message = f"❌ Player `{username}` does not exist."
        else:
            log.error(f"Received unexpected response type '{response_type}' for whitelist command.")
            # Potentially show raw log in this case? Be careful with sensitive info.
            # response_message = f"⚠️ Unexpected response type: {response_type}"

        await ctx.followup.send(response_message, ephemeral=True)
    else:
        # Timeout finding *any* relevant response
        await ctx.followup.send(
            f"🟡 Command '{command_to_send}' sent, but no confirmation received.", 
            ephemeral=True
        )


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