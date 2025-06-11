# pteroCraft

This project is a Discord <-> Minecraft bridge. Specifically, its a Discord bot that interacts with a Pterodactyl panel Minecraft server's console via the panel's WebSocket API. It allows viewing logs, checking status, listing players, and managing the server's whitelist directly from Discord. 

#### you might be wondering...
Why not just use the minecraft server's RCON protocol?
- RCON isn't secure and *no one* recommends exposing this to the internet.
- I wanted a safe way to allow my friends (and their friends) to interact with the servers console.

Ok, why don't you just make some trusted friends operators?
- granting operator to users grants more permissions than whats often required
- setting up custom operator levels/permissions on the MC server is cumbersome and more work
- still places the burden of operator on a few people and makes the experience less "self service"

There are mods like DiscordSRV, Fabricord, or Discord Integration Fabric already. why use this?
- I didn't actually know about these when developing this bot, oops :P
- It also seems like those mods require specific frameworks like Spigot, Fabric, etc., while this bot is agnostic to that. This only requires that your MC server be ran with pterodactyl, and that your MC server supports console commands via the panel.
- there are projects on github similar to this one, but they seem more generalized

Takeaway: using this bot allows me to *only expose the console commands that I choose* while having Discord handle the actual access control. This means that access to the bot/server commands can now be controlled via Discord's permission system, which offers more granularity and control than vanilla minecraft's operator system. Since this bot was built to be ran inside your pterodactyl panel next to your existing minecraft server, it will be simpler to set up than other solutions. And the python code is simple enough to easily extend/customize it to your needs.

## Features

-   **View Server Logs:** Display recent lines from the server console (`/log`).
-   **Check Connection Status:** Show the status of the WebSocket connection to the Pterodactyl server (`/status`).
-   **List Online Players:** Display the current online player count and list their usernames (`/list`).
-   **Manage Whitelist:** Add or remove players from the Minecraft server whitelist (`/whitelist`).
-   **WebSocket Integration:** Connects directly to the Pterodactyl server's console WebSocket for real-time interaction.
-   **Configuration:** Easily configured using environment variables (`.env` file).
-   **Slash Commands:** User-friendly interaction through Discord slash commands.

## Requirements

-   Python 3.8+
-   A Discord Bot Token with Server Members Intent enabled.
-   Pterodactyl panel account with API access.
-   A Minecraft server hosted on the Pterodactyl panel.
-   Access to the MC server panel's WebSocket (usually enabled by default with appropriate API key permissions).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pnivek/pteroCraft
    cd pteroCraft
    ```

2.  **Set up a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate the environment
    # Windows (CMD/PowerShell):
    .\venv\Scripts\activate
    # Linux/macOS:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create `.env` file:**
    Copy the example file:
    ```bash
    cp .env.example .env
    ```
    Then, edit `.env` with your specific credentials.

## Configuration (`.env` File)

Fill in the `.env` file with the following details:

```dotenv
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token     # Your Discord bot's secret token
DISCORD_GUILD_ID=your_discord_server_id  # ID of the Discord server where commands are registered

# Pterodactyl Panel Configuration
PTERODACTYL_URL=https://your.pterodactyl.panel # Base URL of your Pterodactyl panel (e.g., https://panel.example.com)
PTERODACTYL_API_KEY=your_client_api_key     # Pterodactyl *Client* API Key (Account API, NOT Application API)
PTERODACTYL_SERVER_ID=your_server_short_id  # The short ID of your Minecraft server (e.g., a1b2c3d4)
```

**Important:**
*   The `PTERODACTYL_API_KEY` must be a **Client API Key** generated from your Pterodactyl account settings, **not** an Application API key. It needs permissions to access the server console/WebSocket.
*   The `PTERODACTYL_SERVER_ID` is the short identifier found in the server's URL (e.g., `https://your.pterodactyl.panel/server/a1b2c3d4`, the ID is `a1b2c3d4`).

## Usage

There are two primary ways to run the bot:

1.  **Directly with Python:**
    Make sure your virtual environment is activated.
    ```bash
    python bot.py
    ```

2.  **Using the start script (Recommended for Linux/macOS):**
    This script handles environment activation, requirement installation, and automatic restarts.
    ```bash
    chmod +x startbot.sh # Make executable (first time only)
    ./startbot.sh
    ```
    *(Note: `startbot.sh` will need adjustments for Windows environments.)*

## Commands

The bot uses slash commands within your specified Discord server (`DISCORD_GUILD_ID`):

-   `/log [N]` - Shows the last *N* lines from the server console log (default: 10, max: 20).
-   `/status` - Displays the current connection status to the Pterodactyl WebSocket.
-   `/list` - Lists the players currently online on the Minecraft server.
-   `/whitelist <add|remove> <username>` - Adds or removes the specified Minecraft username from the server whitelist.

## Setting Up a Discord Bot

1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Create a "New Application".
3.  Go to the "Bot" tab:
    *   Click "Add Bot", confirm.
    *   **Copy the Token** and paste it into `DISCORD_TOKEN` in your `.env` file.
    *   Enable **SERVER MEMBERS INTENT** under Privileged Gateway Intents.
4.  Go to the "OAuth2" -> "General" tab:
    *   Under "Default Authorization Link", select "In-app Authorization".
    *   Select Scopes: `bot` and `applications.commands`.
    *   Select Bot Permissions: `Send Messages`, `Use Application Commands` (and any others you might need).
5.  Go to "OAuth2" -> "URL Generator":
    *   Select Scopes: `bot` and `applications.commands`.
    *   Select Bot Permissions: `Send Messages`, `Use Application Commands`.
    *   Copy the generated URL and paste it into your browser.
    *   Select your server and authorize the bot.
6.  Enable Developer Mode in Discord (User Settings -> Advanced -> Developer Mode). Right-click your server name and select "Copy Server ID". Paste this into `DISCORD_GUILD_ID` in your `.env` file.

## Getting Pterodactyl API Credentials

1.  Log in to your Pterodactyl panel.
2.  Click your account avatar/icon in the top right -> "API Credentials".
3.  Under "Client API Keys", create a new key.
    *   Give it a description (e.g., "Discord Bot").
    *   Leave "Allowed IPs" blank unless you have specific security needs.
    *   **Copy the generated API Key** and paste it into `PTERODACTYL_API_KEY` in your `.env` file. **Save this key securely, it won't be shown again.**
4.  Find your server ID: Navigate to your server's page. The URL will look like `https://your.pterodactyl.panel/server/xxxxxxxx`. The `xxxxxxxx` part is your `PTERODACTYL_SERVER_ID`.
