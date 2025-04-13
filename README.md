# Minecraft Server Discord Bot

A Discord bot that interfaces with a Minecraft server hosted on the Pterodactyl panel. Manage your server's whitelist and send announcements directly from Discord.

## Features

- Manage server whitelist (add/remove players)
- Send server-wide announcements
- Easy to set up and use with slash commands

## Requirements

- Python 3.8+
- Discord bot token
- Pterodactyl panel with API access
- A Minecraft server hosted on the Pterodactyl panel

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/minecraft-discord-bot.git
   cd minecraft-discord-bot
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on the provided `.env.example`:
   ```
   cp .env.example .env
   ```

4. Edit the `.env` file with your credentials:
   ```
   # Discord Bot Configuration
   DISCORD_TOKEN=your_discord_bot_token
   DISCORD_GUILD_ID=your_guild_id

   # Pterodactyl Panel Configuration
   PTERODACTYL_URL=https://your-pterodactyl-panel-url.com
   PTERODACTYL_API_KEY=your_pterodactyl_api_key
   PTERODACTYL_SERVER_ID=your_minecraft_server_id
   ```

## Usage

Run the bot:
```
python bot.py
```

### Commands

The bot provides the following slash commands:

- `/whitelist add <username>` - Add a player to the whitelist
- `/whitelist remove <username>` - Remove a player from the whitelist
- `/say <message>` - Send a server-wide announcement

## Setting Up a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Navigate to the "Bot" tab and click "Add Bot"
4. Copy the token and add it to your `.env` file
5. Enable the "SERVER MEMBERS INTENT" under Privileged Gateway Intents
6. Go to the "OAuth2" tab and select the following scopes:
   - bot
   - applications.commands
7. Select the following bot permissions:
   - Send Messages
   - Use Slash Commands
8. Use the generated URL to invite the bot to your server

## Getting Pterodactyl API Credentials

1. Log in to your Pterodactyl panel
2. Go to Account Settings > API Credentials
3. Create a new API key with appropriate permissions
4. Copy the API key to your `.env` file
5. Find your server ID in the URL when viewing your server (or via the API)

## License

[MIT License](LICENSE)

## Contributing

Contributions, issues, and feature requests are welcome!
