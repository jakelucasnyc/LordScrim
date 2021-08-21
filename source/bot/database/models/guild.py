import sqlalchemy
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from bot.database import tableBase

class Guild(tableBase):

    __tablename__ = 'guild'

    guild_id = Column(String(20), primary_key=True)
    team_1_channel_id = Column(String(20))
    team_2_channel_id = Column(String(20))
    general_channel_id = Column(String(20))
    teams_message_id = Column(String(20))
    team_1_emoji_text = Column(String(50))
    team_2_emoji_text = Column(String(50))
    players = relationship('ScrimPlayer')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.team_1_emoji_text = ':one:'
        self.team_2_emoji_text = ':two:'
