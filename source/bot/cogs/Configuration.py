import discord
from discord.ext import commands
from bot import bot

class Configuration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def setTeamChannels(self, ctx):
        pass

    @commands.command()
    async def setGeneralChannel(self, ctx):
        pass

    @commands.command()
    async def setSideEmojis(self, ctx):
        pass

    
def setup(bot):
    bot.add_cog(Configuration(bot))