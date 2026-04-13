import hashlib
import base64

def shorten_text(text):
    # Create hash
    hash_object = hashlib.sha256(text.encode())
    hash_bytes = hash_object.digest()

    # Convert to Base64 and trim
    short_code = base64.urlsafe_b64encode(hash_bytes).decode()[:6]

    return short_code