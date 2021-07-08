import logging
from discord.ext import commands 

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)


bot = commands.Bot('!')
channels = ['commands']

@bot.event
async def on_ready():
    print('Bot Ready')

@bot.command()
async def test(ctx):
    await ctx.send('Test Successful')
