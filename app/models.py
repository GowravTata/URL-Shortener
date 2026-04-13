from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# -----------------------
# MODEL
# -----------------------
class URLModel(Base):
    __tablename__ = "url_shortener"

    id = Column(Integer, primary_key=True, autoincrement=True)
    long_url = Column(Text, nullable=False)
    short_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
