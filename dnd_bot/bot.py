import discord
import os

# It's recommended to load the token from an environment variable for security
# For example, create a .env file with: BOT_TOKEN="YOUR_TOKEN_HERE"
# and use a library like python-dotenv to load it.
BOT_TOKEN = os.environ.get("DND_BOT_TOKEN", "YOUR_TOKEN_HERE") 

# Set up intents. The default intents are fine for slash commands.
intents = discord.Intents.default()

# Create the bot instance
class DndBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        # The tree is where slash commands are registered
        self.tree = discord.app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    # This is required to sync the commands to a specific guild (server)
    # for instant updates during development.
    async def setup_hook(self):
        # Replace YOUR_GUILD_ID_HERE with the integer ID of your test server
        guild_id = 1234567890 # <-- IMPORTANT: REPLACE WITH YOUR TEST SERVER ID
        guild = discord.Object(id=guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


bot = DndBot(intents=intents)

@bot.tree.command()
async def hello(interaction: discord.Interaction):
    """Says hello!"""
    await interaction.response.send_message(f'Hello, {interaction.user.mention}!')

def main():
    if BOT_TOKEN == "YOUR_TOKEN_HERE":
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR: Bot token is not configured.      !!!")
        print("!!! Please set the DND_BOT_TOKEN environment !!!")
        print("!!! variable or replace the placeholder in   !!!")
        print("!!! gemini-bot.py.                                  !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return
        
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    main()
