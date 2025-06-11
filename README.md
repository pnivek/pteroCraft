# pteroCraft

A Discord bot that bridges your Discord server with a Minecraft server hosted on Pterodactyl. Instead of relying on insecure RCON or complex server mods, pteroCraft connects directly to your Pterodactyl panel's WebSocket API to provide safe, granular control over server management.

## Why pteroCraft?

**🔒 Security First**
- **Why not RCON?** RCON is inherently insecure and should never be exposed to the internet. pteroCraft uses Pterodactyl's secure WebSocket API instead.
- **Why not make friends operators?** Minecraft's operator system is all-or-nothing. pteroCraft lets you expose only the specific commands you choose.

**🎯 Better Control**
- **Discord-based permissions:** Leverage Discord's robust permission system instead of managing complex Minecraft operator levels.
- **Self-service:** Friends can manage whitelist and check server status without bothering admins.
- **Audit trail:** All commands are logged and attributable to Discord users.

**⚡ Simple Setup**
- **Server-agnostic:** Works with any Minecraft server (Vanilla, Fabric, Forge, etc.) as long as it runs on Pterodactyl.
- **No mods required:** Unlike DiscordSRV, Fabricord, or Discord Integration Fabric, pteroCraft doesn't require specific server frameworks.
- **Lightweight:** Just a Python bot that can run alongside your existing server infrastructure.

## Core Features

-   **📋 View Server Logs:** Display recent console output (`/log`)
-   **🔍 Connection Status:** Monitor WebSocket connection health (`/status`)  
-   **👥 Player Management:** List online players (`/list`)
-   **✅ Whitelist Control:** Add/remove players from whitelist (`/whitelist`)
-   **🔐 Permission-based:** Control access through Discord roles and permissions

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
