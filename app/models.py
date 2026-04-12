from dataclasses import dataclass

@dataclass
class URLModel:
    __tablename__ = 'url_shortener'
    id: int
    long_url: str
    short_url: str