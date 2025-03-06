import yaml
import os
from .session import Session

SESSIONS_FILE = os.path.expanduser("~/.restbook/sessions.yml")

class SessionStore:
    def __init__(self, file_path=SESSIONS_FILE):
        self.file_path = file_path
        self.sessions = {}  # id -> Session
        self.name_to_id = {}  # name -> id
        self._load_sessions()

    def _load_sessions(self):
        """Load sessions from the YAML file and return a dict of Session objects."""
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                data = yaml.safe_load(f) or {}
            for _, details in data.items():
                session = Session.from_dict(details["name"], details)
                self.sessions[session.id] = session
                self.name_to_id[session.name] = session.id

    def _save_sessions(self):
        """Save the current sessions to the YAML file."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        # Save using IDs as keys for consistency with internal structure
        data = {session_id: session.to_dict() for session_id, session in self.sessions.items()}
        with open(self.file_path, "w") as f:
            yaml.dump(data, f)

    def create_session(self, name: str, base_url: str, token: str | None = None):
        """Create a new session and persist it."""
        if name in self.name_to_id:
            raise ValueError(f"Session '{name}' already exists.")
        session = Session(name, base_url, token)
        self.sessions[session.id] = session
        self.name_to_id[name] = session.id
        self._save_sessions()
        return session

    def list_sessions(self):
        """Return a dictionary of all sessions."""
        return {name: self.sessions[id] for name, id in self.name_to_id.items()}

    def update_session(self, name, base_url=None, token=None):
        """Update an existing session and persist the changes."""
        if name not in self.name_to_id:
            raise ValueError(f"Session '{name}' does not exist.")
        session = self.sessions[self.name_to_id[name]]
        if base_url:
            session.base_url = base_url
        if token:
            session.token = token
        self._save_sessions()
        return session

    def delete_session(self, name):
        """Delete a session and persist the changes."""
        if name not in self.name_to_id:
            raise ValueError(f"Session '{name}' does not exist.")
        session_id = self.name_to_id[name]
        del self.sessions[session_id]
        del self.name_to_id[name]
        self._save_sessions()