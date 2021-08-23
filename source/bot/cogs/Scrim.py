from discord.ext import commands
import discord
from bot import bot
import logging
import sqlalchemy
from sqlalchemy import select, update, delete, text
from sqlalchemy.dialects.mysql import insert
from bot.database import DBConn
from bot.database.models.scrimPlayer import ScrimPlayer
from bot.database.models.guild import Guild
from emoji import emojize, demojize
import asyncio
import sys


class Scrim(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        #logging
        self._logger = logging.getLogger('ScrimCog')
        self._logger.setLevel(logging.INFO)
        self._handler = logging.StreamHandler(sys.stdout)
        self._handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self._logger.addHandler(self._handler)

        #database
        self._dbConn = DBConn()
        self._engine = self._dbConn.engine
        self._session = self._dbConn.session

    def isRegisteredGuild(self, conn, guildId:str):
        record = conn.execute(select(Guild.guild_id).where(Guild.guild_id == str(guildId))).first()
        if record is None:
            return False
        else:
            return True 

    def isBot(self, member):
        return member.bot

    @commands.command()
    @commands.guild_only()
    async def teams(self, ctx):

        with self._engine.connect() as conn:

            guildRecord = conn.execute(select(Guild).where(Guild.guild_id == str(ctx.guild.id))).first()
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

            stmt = insert(Guild).values(guild_id=str(ctx.guild.id), teams_message_id=pollMessageId)
            onDuplicateStmt = stmt.on_duplicate_key_update(teams_message_id=pollMessageId)
            conn.execute(onDuplicateStmt)
            # conn.commit()

            

            self._logger.debug('teams command successful')

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
    @commands.guild_only()
    async def on_reaction_add(self, reaction, member):
        # member = payload.member
        # channel = self.bot.get_channel(payload.channel_id)
        # message = await channel.fetch_message(payload.message_id)
        
        #checking if the reactor is a bot
        if self.isBot(member):
            self._logger.debug('Bot is reacting. Not responding to this added reaction.')
            return
        guildId = reaction.message.guild.id
        with self._engine.connect() as conn:
            #checking if the guild is in the database. If not, then the teams poll has never been run and reactions shouldn't be reacted to
            if not self.isRegisteredGuild(conn, str(guildId)):
                self._logger.debug('Not a registered guild. Not responding to this added reaction.')
                return

            #querying the guild to get necessary information
            teamsMessageId ,= conn.execute(select(Guild.teams_message_id).where(Guild.guild_id == str(guildId))).first()
            #if no teams message is valid
            if teamsMessageId != str(reaction.message.id): 
                self._logger.debug('No teams poll registered. Not responsding to this added reaction.')
                return

        #removing previous reactions to other teams
        for reactionItem in reaction.message.reactions:
            for user in await reactionItem.users().flatten():
                if user.id == member.id and reaction != reactionItem: 

                    with self._engine.connect() as conn:
                        #writing into the database that the reaction is being removed automatically so that the on_reaction_remove handler doesn't act meaningfully
                        conn.execute(update(ScrimPlayer).where(ScrimPlayer.member_id == str(member.id)).values(autoReactionRemoval=True))
                        await reactionItem.remove(member)
                        #waiting for a short duration so that the on_reaction_remove handler runs before this continues
                        await asyncio.sleep(0.1)
                        
        with self._engine.begin() as conn:
            team_1_emoji_text, team_2_emoji_text = conn.execute(select(Guild.team_1_emoji_text, Guild.team_2_emoji_text).where(Guild.guild_id == str(guildId))).first()

            #setting sides based on the type of emoji that was reacted
            team1Emoji = emojize(team_1_emoji_text, use_aliases=True)
            team2Emoji = emojize(team_2_emoji_text, use_aliases=True)
            if reaction.emoji == team1Emoji:
                side = 1
            elif reaction.emoji == team2Emoji:
                side = 2

        await self.addPlayer(member, reaction.message, side)
            

    async def addPlayer(self, member, message, side):
        guildId = str(member.guild.id)
        with self._engine.begin() as conn:

            #adding player to database
            stmt = insert(ScrimPlayer).values(member_id=str(member.id), display_name=member.display_name, guild_id=str(guildId), side=side).on_duplicate_key_update(display_name=member.display_name, guild_id=str(guildId), side=side)
            conn.execute(stmt)

            #getting a list of players to be used in the updated message
            players = conn.execute(select(ScrimPlayer.display_name, ScrimPlayer.side).where(ScrimPlayer.guild_id == str(guildId))).all()
            await self.updateTeamsMessage(message, players)
            self._logger.debug('updateTeamsMessage in reaction_add')


    @commands.Cog.listener()
    @commands.guild_only()
    async def on_reaction_remove(self, reaction, member):
        #checking if the reactor is a bot
        if self.isBot(member):
            self._logger.debug('Bot is reacting. Not responding to this removed reaction.')
            return
        guildId = reaction.message.guild.id
        with self._engine.connect() as conn:
            #checking if the guild is in the database. If not, then the teams poll has never been run and reactions shouldn't be reacted to
            if not self.isRegisteredGuild(conn, str(guildId)):
                self._logger.debug('Not a registered guild. Not responding to this removed reaction.')
                return

            #querying the database for a poll message evoked by the "teams" command
            teamsMessageId ,= conn.execute(select(Guild.teams_message_id).where(Guild.guild_id == str(guildId))).first()
            #if no teams message is valid
            if teamsMessageId != str(reaction.message.id): 
                self._logger.debug('No teams poll registered. Not responsding to this removed reaction.')
                return

            #checking if this event was caused by an automatic reaction removal
            autoReactionRemovalRecord ,= conn.execute(select(ScrimPlayer.autoReactionRemoval).where(ScrimPlayer.member_id == str(member.id))).first()
            if autoReactionRemovalRecord == True:
                conn.execute(update(ScrimPlayer).where(ScrimPlayer.member_id == str(member.id)).values(autoReactionRemoval=False))
                self._logger.debug('Automatically removed reaction.')
                return

            await self.removePlayer(member, reaction.message)


    async def removePlayer(self, member, message):
        guildId = str(member.guild.id)
        with self._engine.begin() as conn:
            #querying the player to delete them from the database
            player = conn.execute(select(ScrimPlayer.member_id).where(ScrimPlayer.member_id == str(member.id))).first()
            if player is None:
                self._logger.warning('Player "{member.display_name}" is removing a reaction from the teams , but is not registered in the database')
                return
            conn.execute(delete(ScrimPlayer).where(ScrimPlayer.member_id == str(member.id)))

            #updating the teams poll to accommodate the changes to the roster
            players = conn.execute(select(ScrimPlayer.display_name, ScrimPlayer.side).where(ScrimPlayer.guild_id == str(guildId))).all()
            await self.updateTeamsMessage(message, players)
            self._logger.debug('updateTeamsMessage in reaction_remove')

    @commands.command()
    @commands.guild_only()
    async def scrim(self, ctx):
        #if teams aren't set up yet
        with self._engine.connect() as conn:
            selectGuildStmt = select(Guild).where(Guild.guild_id == str(ctx.guild.id)) 
            guildRecord = conn.execute(selectGuildStmt).first()
            if guildRecord is None:
                await ctx.send('This server is unregistered. Please use the register command to register this server.') 
                return
            if guildRecord['teams_message_id'] is None:
                await ctx.send("Teams haven't been picked yet. Please use the teams command to pick teams for the scrim.")
                return
            if guildRecord['team_1_channel_id'] is None:
                await ctx.send("Team 1 voice channel has not been set. Please use the setChannel1 command to choose a team 1 voice channel.")
                return
            if guildRecord['team_2_channel_id'] is None:
                await ctx.send("Team 1 voice channel has not been set. Please use the setChannel2 command to choose a team 1 voice channel.")
                return
            if guildRecord['general_channel_id'] is None:
                await ctx.send("General voice channel has not been set. Please use the setChannelGeneral command to choose a team 1 voice channel.")
                return

            team1Channel = self.bot.get_channel(int(guildRecord['team_1_channel_id']))
            team2Channel = self.bot.get_channel(int(guildRecord['team_2_channel_id']))

            selectPlayersStmt = select(ScrimPlayer.member_id, ScrimPlayer.side).where(ScrimPlayer.guild_id == str(ctx.guild.id))
            players = conn.execute(selectPlayersStmt).all()
            # print(players)


            try:
                for player in players:
                    member = ctx.guild.get_member(int(player[0]))
                    if player[1] == 1:
                        await member.move_to(team1Channel, reason='The scrim is starting.')
                    elif player[1] == 2:
                        await member.move_to(team2Channel, reason='The scrim is starting.')
                    await asyncio.sleep(0.5)

            except discord.errors.HTTPException as e:
                await ctx.send('Everyone scrimming, please join a voice channel before starting the scrim.')
                self._logger.error('Not all scrim members in voice chat during scrim command. Aborting...')
            else:
                await ctx.send('Game on! Happy Scrimming!')
                self._logger.debug('scrim command successful')


    @commands.command()
    @commands.guild_only()
    async def disband(self, ctx):
        with self._engine.connect() as conn:
            stmt = update(Guild).where(Guild.guild_id == str(ctx.guild.id)).values(teams_message_id=sqlalchemy.null())
            conn.execute(stmt)
        await ctx.send('Teams disbanded.')

    @commands.command(name='return')
    @commands.guild_only()
    async def return_(self, ctx):

        with self._engine.connect() as conn:

            selectChannelsStmt = select(Guild.team_1_channel_id, Guild.team_2_channel_id, Guild.general_channel_id).where(Guild.guild_id == str(ctx.guild.id))
            team1Id, team2Id, generalId = conn.execute(selectChannelsStmt).first()
        team1Channel = self.bot.get_channel(int(team1Id))
        team2Channel = self.bot.get_channel(int(team2Id))
        generalChannel = self.bot.get_channel(int(generalId))

        players = team1Channel.members + team2Channel.members

        for player in players:
            await player.move_to(generalChannel, reason='Scrimming is over')
        
        await ctx.send('Scrim Over!...for now ;)')
        self._logger.debug('return command successful')

    @commands.command()
    # @commands.guild_only()
    async def addPlayerToTeam1(self, ctx, member: discord.Member):
        side = 1

        with self._engine.connect() as conn:
            selectGuildStmt = select(Guild).where(Guild.guild_id == str(ctx.guild.id)) 
            guildRecord = conn.execute(selectGuildStmt).first()
            if guildRecord is None:
                await ctx.send('This server is unregistered. Please use the register command to register this server.') 
                return
            if guildRecord['teams_message_id'] is None:
                await ctx.send("Teams haven't been picked yet. Please use the teams command to pick teams for the scrim.")
                return
            message = await ctx.channel.fetch_message(int(guildRecord['teams_message_id']))
            await self.addPlayer(member, message, side)
        
        await ctx.send(f'Player "{member.display_name}" has been added to team 1.')

    @commands.command()
    # @commands.guild_only()
    async def addPlayerToTeam2(self, ctx, member: discord.Member):
        side = 2

        with self._engine.connect() as conn:
            selectGuildStmt = select(Guild).where(Guild.guild_id == str(ctx.guild.id)) 
            guildRecord = conn.execute(selectGuildStmt).first()
            if guildRecord is None:
                await ctx.send('This server is unregistered. Please use the register command to register this server.') 
                return
            if guildRecord['teams_message_id'] is None:
                await ctx.send("Teams haven't been picked yet. Please use the teams command to pick teams for the scrim.")
                return
            message = await ctx.channel.fetch_message(int(guildRecord['teams_message_id']))
            await self.addPlayer(member, message, side)
        await ctx.send(f'Player "{member.display_name}" has been added to team 2.')

    @commands.command(name='removePlayer')
    @commands.guild_only()
    async def removePlayerCommand(self, ctx, member: discord.Member):
        with self._engine.connect() as conn:
            selectGuildStmt = select(Guild).where(Guild.guild_id == str(ctx.guild.id)) 
            guildRecord = conn.execute(selectGuildStmt).first()
            if guildRecord is None:
                await ctx.send('This server is unregistered. Please use the register command to register this server.') 
                return
            if guildRecord['teams_message_id'] is None:
                await ctx.send("Teams haven't been picked yet. Please use the teams command to pick teams for the scrim.")
                return
            message = await ctx.channel.fetch_message(int(guildRecord['teams_message_id']))
            await self.removePlayer(member, message)
        await ctx.send(f'Player "{member.display_name}" has been removed from their team.')


def setup(bot):
    bot.add_cog(Scrim(bot))
