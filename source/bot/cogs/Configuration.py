import discord
from sqlalchemy import select, update, delete
from sqlalchemy.dialects.mysql import insert
from discord.ext import commands
from bot import bot
from bot.database import DBConn
from bot.database.models.guild import Guild
from emoji import emojize, demojize
import logging
import sys

class Configuration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        #logging
        self._logger = logging.getLogger('ConfigurationCog')
        self._logger.setLevel(logging.INFO)
        self._handler = logging.StreamHandler()
        self._handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self._logger.addHandler(self._handler)

        #database
        self._dbConn = DBConn()
        self._engine = self._dbConn.engine

    def isRegisteredGuild(self, conn, guildId:str):
        record = conn.execute(select(Guild.guild_id).where(Guild.guild_id == str(guildId))).first()
        if record is None:
            return False
        else:
            return True 

    @commands.command()
    @commands.guild_only()
    async def register(self, ctx):
        with self._engine.connect() as conn:
            stmt = insert(Guild).values(guild_id=str(ctx.guild.id)).prefix_with('IGNORE')
            conn.execute(stmt)
        await ctx.send('Server registered successfully.')
            

    @commands.command(name='setChannel1')
    @commands.guild_only()
    async def setTeam1Channel(self, ctx, channel: discord.VoiceChannel):
        with self._engine.connect() as conn:
            if not self.isRegisteredGuild(conn, ctx.guild.id):
                await ctx.send('This server is unregistered. Please use the register command to register this server.') 
                return

            stmt = update(Guild).where(Guild.guild_id == str(ctx.guild.id)).values(team_1_channel_id=str(channel.id))
            conn.execute(stmt)

        await ctx.send(f'Set team 1 channel to "{channel.name}".')

    @commands.command(name='setChannel2')
    @commands.guild_only()
    async def setTeam2Channel(self, ctx, channel: discord.VoiceChannel):
        with self._engine.connect() as conn:
            if not self.isRegisteredGuild(conn, ctx.guild.id):
                await ctx.send('This server is unregistered. Please use the register command to register this server.') 
                return

            stmt = update(Guild).where(Guild.guild_id == str(ctx.guild.id)).values(team_2_channel_id=str(channel.id))
            conn.execute(stmt)

        await ctx.send(f'Set team 2 channel to "{channel.name}".')

    @commands.command(name='setChannelGeneral', aliases=['setGeneralChannel'])
    @commands.guild_only()
    async def setGeneralChannel(self, ctx, channel: discord.VoiceChannel):
        with self._engine.connect() as conn:
            if not self.isRegisteredGuild(conn, ctx.guild.id):
                await ctx.send('This server is unregistered. Please use the register command to register this server.') 
                return

            stmt = update(Guild).where(Guild.guild_id == str(ctx.guild.id)).values(general_channel_id=str(channel.id))
            conn.execute(stmt)

        await ctx.send(f'Set general channel to "{channel.name}".')

    @commands.command(name='setEmoji1')
    @commands.guild_only()
    async def setTeam1Emoji(self, ctx, emoji):
        emojiText = demojize(emoji, use_aliases=True)
        with self._engine.connect() as conn:
            if not self.isRegisteredGuild(conn, ctx.guild.id):
                await ctx.send('This server is unregistered. Please use the register command to register this server.') 
                return
            stmt = update(Guild).where(Guild.guild_id == str(ctx.guild.id)).values(team_1_emoji_text=emojiText)
            conn.execute(stmt)

        await ctx.send(f'Set team 1 emoji to {emojiText}.')

    @commands.command(name='setEmoji2')
    @commands.guild_only()
    async def setTeam2Emoji(self, ctx, emoji):
        emojiText = demojize(emoji, use_aliases=True)
        with self._engine.connect() as conn:
            if not self.isRegisteredGuild(conn, ctx.guild.id):
                await ctx.send('This server is unregistered. Please use the register command to register this server.') 
                return
            stmt = update(Guild).where(Guild.guild_id == str(ctx.guild.id)).values(team_2_emoji_text=emojiText)
            conn.execute(stmt)

        await ctx.send(f'Set team 2 emoji to {emojiText}.')

def setup(bot):
    bot.add_cog(Configuration(bot))