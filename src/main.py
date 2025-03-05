import click
from src.models.session.session_store import SessionStore

# Instantiate the session store (this could be injected for tests)
session_store = SessionStore()

@click.group()
def cli():
    """RestBook CLI Tool: Declarative API interactions."""
    pass

@cli.group()
def session():
    """Manage API sessions (create, list, update, delete)."""
    pass

@session.command()
@click.argument("name")
@click.option("--base-url", prompt="Base URL", help="The API base URL.")
@click.option("--token", help="Authentication token for the API.", default=None)
def create(name, base_url, token):
    """Create a new session."""
    try:
        new_session = session_store.create_session(name, base_url, token)
        click.echo(f"Session '{name}' created successfully:\n{new_session.to_dict()}")
    except ValueError as err:
        click.echo(str(err), err=True)

@session.command(name="list")
def list_sessions():
    """List all available sessions."""
    sessions = session_store.list_sessions()
    if not sessions:
        click.echo("No sessions found.")
    else:
        for session in sessions.values():
            click.echo(f"{session.to_dict()}")

@session.command()
@click.argument("name")
@click.option("--base-url", help="New API base URL.", default=None)
@click.option("--token", help="New authentication token.", default=None)
def update(name, base_url, token):
    """Update an existing session."""
    try:
        updated_session = session_store.update_session(name, base_url, token)
        click.echo(f"Session '{name}' updated successfully:\n{updated_session.to_dict()}")
    except ValueError as err:
        click.echo(str(err), err=True)

@session.command()
@click.argument("name")
def delete(name):
    """Delete an existing session."""
    try:
        session_store.delete_session(name)
        click.echo(f"Session '{name}' deleted successfully.")
    except ValueError as err:
        click.echo(str(err), err=True)

def main():
    cli()

if __name__ == '__main__':
    main()
