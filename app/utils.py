from app.db import redis_conn
from sqlalchemy.orm import Session
from typing import Any, Optional

import hashlib
import base64



def shorten_text(text):
    # Create hash
    hash_object = hashlib.sha256(text.encode())
    hash_bytes = hash_object.digest()

    # Convert to Base64 and trim
    short_code = base64.urlsafe_b64encode(hash_bytes).decode()[:6]

    return short_code

class RedisCache:
    def __init__(self):
        self.redis_conn = redis_conn

    def set(self, key, value, ex=None):
        self.redis_conn.set(key, value, ex=ex)

    def get(self, key):
        return self.redis_conn.get(key)
    

def get_record_by_field(db: Session, model: Any, field: str, value: Any) -> Optional[Any]:
    """
    Generic utility to fetch a record from the database by a given field and value.
    Example: get_record_by_field(db, URLModel, 'long_url', long_url)
    """
    return db.query(model).filter(getattr(model, field) == value).first()