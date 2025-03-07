import os
import uuid


class Session:
    def __init__(self, name: str, base_url: str, token: str | None = None, id: str | None = None):
        self.name = name
        self.base_url = base_url
        self.token = token
        self.id = id or str(uuid.uuid4())

    def to_dict(self):
        """Convert the Session instance to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "token": self.token
        }

    @classmethod
    def from_dict(cls, name, data):
        """Create a Session instance from a dictionary."""
        session = cls(name, data.get("base_url"), data.get("token"), data.get("id"))
        return session
