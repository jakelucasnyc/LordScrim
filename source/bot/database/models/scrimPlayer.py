from bot.database import tableBase
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer, ForeignKey, SmallInteger, Boolean 

class ScrimPlayer(tableBase):
    __tablename__ = 'scrim_player'

    member_id = Column(String(20), primary_key=True)
    display_name = Column(String(35), nullable=False)
    guild_id = Column(ForeignKey('guild.guild_id'), nullable=False)
    side = Column(SmallInteger, nullable=False)
    autoReactionRemoval = Column(Boolean)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.autoReactionRemoval = False