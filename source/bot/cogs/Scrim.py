from discord.ext import commands
import discord
from bot import bot
import logging
import sqlalchemy
from sqlalchemy import select, insert, update, delete, text
from bot.database import DBConn
from bot.database.models.scrimPlayer import ScrimPlayer
from bot.database.models.guild import Guild
from emoji import emojize, demojize
import asyncio

import cProfile
import io
import pstats
import contextlib

@contextlib.contextmanager
def profiled():
    pr = cProfile.Profile()
    pr.enable()
    yield
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    # uncomment this to see who's calling what
    # ps.print_callers()
    print(s.getvalue())


class Scrim(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self._logger = logging.getLogger('ScrimCog')
        self._dbConn = DBConn()
        # self._engine = self._dbConn.engine
        self._session = self._dbConn.session

    def isRegisteredGuild(self, conn, guildId:str):
        record = conn.query(Guild.guild_id).filter_by(guild_id=str(guildId)).first()
        if record is None:
            return False
        else:
            return True 

    def isBot(self, member):
        return member.bot

    @commands.command()
    async def teams(self, ctx):
        with self._session.begin() as conn:

            guildRecord = conn.query(Guild).filter_by(guild_id=str(ctx.guild.id)).first()
            if guildRecord is None:
                guildRecord = Guild(guild_id=str(ctx.guild.id))
            
            # self._logger.info(f'Team 1 Emoji Text: {guildRecord.team_1_emoji_text}')

            oneEmoji = emojize(guildRecord.team_1_emoji_text, use_aliases=True)
            twoEmoji = emojize(guildRecord.team_2_emoji_text, use_aliases=True)

            #creating the message and adding initial reactions
            team1TextBlock = ''.join([" **__Team 1:__**\n",
                                      "``` ```"])
            team2TextBlock = ''.join([" **__Team 2:__**\n",
                                      "``` ```"])
            pollMessage = await ctx.send('\n'.join(['Choose your side!', team1TextBlock, team2TextBlock]))
            await pollMessage.add_reaction(oneEmoji)
            await pollMessage.add_reaction(twoEmoji)
            pollMessageId = pollMessage.id

            guildRecord.teams_message_id = pollMessageId
            conn.add(guildRecord)
            conn.commit()

            

            self._logger.info('teams command successful')

    async def updateTeamsMessage(self, message, players):
        ":param List[tuple] players: list of tuples with each tuple as (display_name, side)"

        team1List = []
        team2List = []
        for player in players:
            if player[1] == 1:
                team1List.append(player)
            elif player[1] == 2:
                team2List.append(player)

        team1TextBlock = ''.join([" **__Team 1:__**\n",
                            "``` ",
                            '\n'.join([player[0] for player in team1List]),
                            "```"])
        team2TextBlock = ''.join(["**__Team 2:__**\n",
                            "``` ",
                            '\n'.join([player[0] for player in team2List]),
                            "```"])

        await message.edit(content='\n'.join(['\nChoose your side!', team1TextBlock, team2TextBlock]))

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, member):
        # member = payload.member
        # channel = self.bot.get_channel(payload.channel_id)
        # message = await channel.fetch_message(payload.message_id)
        
        #checking if the reactor is a bot
        if self.isBot(member):
            self._logger.info('Bot is reacting. Not responding to this added reaction.')
            return
        guildId = reaction.message.guild.id
        with self._session.begin() as conn:
            #checking if the guild is in the database. If not, then the teams poll has never been run and reactions shouldn't be reacted to
            if not self.isRegisteredGuild(conn, str(guildId)):
                self._logger.info('Not a registered guild. Not responding to this added reaction.')
                return

            #querying the guild to get necessary information
            teamsMessageId ,= conn.query(Guild.teams_message_id).filter_by(guild_id=str(guildId)).first()
            # self._logger.info(teamsMessageId)
            #if no teams message is valid
            if teamsMessageId != str(reaction.message.id): 
                self._logger.info('No teams poll registered. Not responsding to this added reaction.')
                return

            #defining a checking function when waiting for the reaction_remove event
            # def checkCorrectReaction(innerReaction, innerMember):
            #     return innerMember.id == member.id and innerReaction == reactionItem

        #removing previous reactions to other teams
        for reactionItem in reaction.message.reactions:
            for user in await reactionItem.users().flatten():
                if user.id == member.id and reaction != reactionItem: 

                    with self._session.begin() as conn:
                        autoReactionRemovalRecord ,= conn.query(ScrimPlayer.autoReactionRemoval).filter_by(member_id=str(member.id)).first()
                        autoReactionRemovalRecord = True
                        conn.execute(update(ScrimPlayer).where(ScrimPlayer.member_id == str(member.id)).values(autoReactionRemoval=autoReactionRemovalRecord).execution_options(synchronize_session='fetch'))
                        conn.commit()

                    await reactionItem.remove(member)
                    # await self.bot.wait_for('reaction_remove', check=checkCorrectReaction)
                    #waiting for the on_reaction_remove function to complete
                    # await asyncio.sleep(2)
            
        with self._session.begin() as conn:
            team_1_emoji_text, team_2_emoji_text = conn.query(Guild.team_1_emoji_text, Guild.team_2_emoji_text).filter_by(guild_id=str(guildId)).first()

            #setting sides based on the type of emoji that was reacted
            team1Emoji = emojize(team_1_emoji_text, use_aliases=True)
            team2Emoji = emojize(team_2_emoji_text, use_aliases=True)
            if reaction.emoji == team1Emoji:
                side = 1
            elif reaction.emoji == team2Emoji:
                side = 2

            #querying the player if he/she is in the database already. If not, we create the entry and fill in the necessary information
            player = conn.query(ScrimPlayer).filter_by(member_id=str(member.id)).first()
            if player is None:
                player = ScrimPlayer(member_id=str(member.id))
            # conn.refresh(player)
            player.display_name = member.display_name
            player.guild_id = str(guildId) 
            player.side = side

            #adding player to database
            conn.add(player)
            conn.flush()

            #getting a list of players to be used in the updated message
            players = conn.query(ScrimPlayer.display_name, ScrimPlayer.side).filter_by(guild_id=str(guildId)).all()
            await self.updateTeamsMessage(reaction.message, players)
            self._logger.info('updateTeamsMessage in reaction_add')
            conn.commit()

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, member):
        #checking if the reactor is a bot
        if self.isBot(member):
            self._logger.info('Bot is reacting. Not responding to this removed reaction.')
            return
        guildId = reaction.message.guild.id
        with self._session.begin() as conn:
            #checking if the guild is in the database. If not, then the teams poll has never been run and reactions shouldn't be reacted to
            if not self.isRegisteredGuild(conn, str(guildId)):
                self._logger.info('Not a registered guild. Not responding to this removed reaction.')
                return

            teamsMessageId ,= conn.query(Guild.teams_message_id).filter_by(guild_id=str(guildId)).first()
            #if no teams message is valid
            if teamsMessageId != str(reaction.message.id): 
                self._logger.info('No teams poll registered. Not responsding to this removed reaction.')
                return

            autoReactionRemovalRecord ,= conn.query(ScrimPlayer.autoReactionRemoval).filter_by(member_id=str(member.id)).first()
            if autoReactionRemovalRecord == True:
                self._logger.info('Automatically removed reaction.')
                autoReactionRemovalRecord = False
                # conn.execute(update(ScrimPlayer, whereclause=text(f'scrim_player.member_id={member.id}'), values={'autoReactionRemoval': autoReactionRemovalRecord}))
                conn.execute(update(ScrimPlayer).where(ScrimPlayer.member_id == str(member.id)).values(autoReactionRemoval=autoReactionRemovalRecord).execution_options(synchronize_session='fetch'))
                conn.commit()
                return

        with self._session.begin() as conn:
            #querying the player to delete them from the database
            player = conn.query(ScrimPlayer).filter_by(member_id=str(member.id)).first()
            if player is None:
                self._logger.warning('Player "{member.display_name}" is removing a reaction from the teams , but is not registered in the database')
                return
            conn.delete(player)
            # conn.flush()

            #updating the teams poll to accommodate the changes to the roster
            players = conn.query(ScrimPlayer.display_name, ScrimPlayer.side).filter_by(guild_id=str(guildId)).all()
            await self.updateTeamsMessage(reaction.message, players)
            self._logger.info('updateTeamsMessage in reaction_remove')
            conn.commit()

            

    @commands.command()
    async def scrim(self, ctx):
        #if teams aren't set up yet
        if not ctx.guild in guildPollDict.keys():
            await ctx.send("Teams haven't been picked yet. Type '!teams' to create the team poll.")
            return

        pollMessageId = guildPollDict[ctx.guild]

        #fetching poll message
        pollMessage = await ctx.fetch_message(pollMessageId)
        #getting the ids of the channels needed
        # team1Id = [channel.id for channel in ctx.guild.channels if channel.name == team1Name][0]
        # team2Id = [channel.id for channel in ctx.guild.channels if channel.name == team2Name][0]
        # team1Channel = self.bot.get_channel(team1Id)
        # team2Channel = self.bot.get_channel(team2Id)
        team1Channel = self.bot.get_channel(848235185384325181)
        team2Channel = self.bot.get_channel(799472682545709056)

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
            await ctx.send("Someone is on self.both sides at the same time! Please redo or fix the poll.")
            self._logger.error('Someone was on more than one team during the !teams command. Aborting...')
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
            self._logger.error('Not all scrim members in voice chat during !scrim command. Aborting...')

        else:
            await ctx.send('Game on! Happy Scrimming!')
            self._logger.info('scrim command successful')
        

    @commands.command()
    async def disband(self, ctx):
        try:
            guildPollDict.pop(ctx.guild) 
        except KeyError as e:
            await ctx.send('No team was created.')
        else:
            await ctx.send('Team Disbanded.')
        finally:
            self._logger.info('disband command successful')

    @commands.command(name='return')
    async def return_(self, ctx):

        # team1Id = [channel.id for channel in ctx.guild.channels if channel.name == team1Name][0]
        # team2Id = [channel.id for channel in ctx.guild.channels if channel.name == team2Name][0]
        # generalId = [channel.id for channel in ctx.guild.channels if channel.name == generalName][0]
        # team1Channel = self.bot.get_channel(team1Id)
        # team2Channel = self.bot.get_channel(team2Id)
        # generalChannel = self.bot.get_channel(generalId)
        team1Channel = self.bot.get_channel(848235185384325181)
        team2Channel = self.bot.get_channel(799472682545709056)
        generalChannel = self.bot.get_channel(788006982534692864)

        players = team1Channel.members + team2Channel.members

        for player in players:
            await player.move_to(generalChannel, reason='Scrimming is over')
        
        await ctx.send('Scrim Over!...for now ;)')
        self._logger.info('return command successful')

def setup(bot):
    bot.add_cog(Scrim(bot))
