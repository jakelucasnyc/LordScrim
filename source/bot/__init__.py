import logging
from discord.ext import commands 
import discord
import os

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='../discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


#intents
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot('scrim.', intents=intents, case_insensitive=True)

@bot.event
async def on_ready():
    print('Bot Ready')

@bot.command()
async def test(ctx):
    await ctx.send('Test Successful.')
    logger.info('test command successful')

@bot.command()
async def reload(ctx, extension:str=''):
    if extension == '':
        await ctx.send('Please specify an extension to reload.')
        return
    try:
        bot.unload_extension(f'bot.cogs.{extension}')
            
        bot.load_extension(f'bot.cogs.{extension}')
    except Exception as e:
        await ctx.send(str(e))
        raise e
    else:
        await ctx.send('Reload Successful.')

for filename in os.listdir('./bot/cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'bot.cogs.{filename[:-3]}')

