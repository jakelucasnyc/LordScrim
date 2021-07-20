import logging
from discord.ext import commands 
import discord
from emoji import emojize, demojize

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='../discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)



#intents
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot('/', intents=intents)

pollMessageId = None
channels = ['commands', 'general']

oneEmoji = emojize(':one:', use_aliases=True)
twoEmoji = emojize(':two:', use_aliases=True)

team1Name = 'Team 1'
team2Name = 'Team 2'
generalName = 'General'

@bot.event
async def on_ready():
    print('Bot Ready')

@bot.command()
async def test(ctx):
    await ctx.send('Test Successful')
    logger.info('!test command successful')

@bot.command()
async def teams(ctx):
    pollMessage = await ctx.send('Choose your side!')

    # print(f'{oneEmoji=}')
    # print(f'{twoEmoji=}')

    await pollMessage.add_reaction(oneEmoji)
    await pollMessage.add_reaction(twoEmoji)
    global pollMessageId
    pollMessageId = pollMessage.id
    logger.info('!teams command successful')

@bot.command()
async def scrim(ctx):
    #if teams aren't set up yet
    if pollMessageId is None:
        await ctx.send("Teams haven't been picked yet. Type '!teams' to create the team poll")
        return

    #fetching poll message
    pollMessage = await ctx.fetch_message(pollMessageId)
    #getting the ids of the channels needed
    # team1Id = [channel.id for channel in ctx.guild.channels if channel.name == team1Name][0]
    # team2Id = [channel.id for channel in ctx.guild.channels if channel.name == team2Name][0]
    # team1Channel = bot.get_channel(team1Id)
    # team2Channel = bot.get_channel(team2Id)
    team1Channel = bot.get_channel(848235185384325181)
    team2Channel = bot.get_channel(799472682545709056)

    reactions = pollMessage.reactions
    # print(f'{reactions=}')
    users = {}
    #getting users who used each reaction
    for reaction in reactions:
        eachReactUser = await reaction.users().flatten()
        eachReactUser = [user for user in eachReactUser if not user.bot]
        # print(f'\n\n{eachReactUser=}\n\n')
        users.update({reaction.emoji: eachReactUser})
        # print('Appended')

    #checking to see if no one is on more than one team
    listIntersection = list(set(users[oneEmoji]) & set(users[twoEmoji]))
    # print(f'{listIntersection=}')
    if listIntersection:
        await ctx.send("Someone is on both sides at the same time! Please redo or fix the poll.")
        logger.error('Someone was on more than one team during the !teams command. Aborting...')
        return

    #putting users into their voice channels
    try:
        for key, userList in users.items():
            if key == oneEmoji:
                for user in userList:
                    await user.move_to(team1Channel, reason='The scrim is starting') 
            
            elif key == twoEmoji:
                for user in userList:
                    await user.move_to(team2Channel, reason='The scrim is starting')
    except discord.errors.HTTPException as e:
        await ctx.send('Everyone scrimming, please join a voice channel before starting the scrim.')
        logger.error('Not all scrim members in voice chat during !scrim command. Aborting...')

    else:
        await ctx.send('Game on! Happy Scrimming!')
        logger.info('!scrim command successful')
    

@bot.command()
async def disband(ctx):
    global pollMessageId
    pollMessageId = None

    await ctx.send('Team Disbanded!')
    logger.info('!disband command successful')

@bot.command(aliases=['return'])
async def return_(ctx):

    # team1Id = [channel.id for channel in ctx.guild.channels if channel.name == team1Name][0]
    # team2Id = [channel.id for channel in ctx.guild.channels if channel.name == team2Name][0]
    # generalId = [channel.id for channel in ctx.guild.channels if channel.name == generalName][0]
    # team1Channel = bot.get_channel(team1Id)
    # team2Channel = bot.get_channel(team2Id)
    # generalChannel = bot.get_channel(generalId)
    team1Channel = bot.get_channel(848235185384325181)
    team2Channel = bot.get_channel(799472682545709056)
    generalChannel = bot.get_channel(788006982534692864)

    players = team1Channel.members + team2Channel.members

    for player in players:
        await player.move_to(generalChannel, reason='Scrimming is over')
    
    await ctx.send('Scrim Over!...for now ;)')
    logger.info('!return command successful')


