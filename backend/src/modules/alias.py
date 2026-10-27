import hashlib
import hmac
import uuid

from src.core.config import get_settings


def display_alias(auction_id: uuid.UUID, user_id: uuid.UUID, role: str) -> str:
    prefix = "Seller-" if role == "SELLER" else "Bidder-"
    msg = f"{auction_id}:{user_id}".encode()
    digest = hmac.new(get_settings().alias_secret.encode(), msg, hashlib.sha256).hexdigest()
    return prefix + digest[:8]
