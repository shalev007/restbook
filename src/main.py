import click
from src.modules.session.session_store import SessionStore
from src.modules.session.commands import create_session_commands
from src.modules.playbook.commands import create_playbook_commands
from src.modules.request.commands import create_request_commands
from src.modules.logging import create_logger, BaseLogger


class RestbookContext:
    """Context object to store CLI state."""
    def __init__(self):
        self.logger = None
        self.session_store = SessionStore()

pass_context = click.make_pass_decorator(RestbookContext, ensure=True)

@click.group()
@click.option('--output', '-o',
              type=click.Choice(['colorful', 'plain', 'json']),
              default='colorful',
              help='Output format (colorful for CLI, plain for CI/file, json for machine parsing)',
              envvar='RESTBOOK_OUTPUT')
@click.option('--log-level', '-l',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
              default='INFO',
              help='Set the logging level',
              envvar='RESTBOOK_LOG_LEVEL')
@pass_context
def cli(ctx, output, log_level):
    """RestBook CLI Tool: Declarative API interactions."""
    ctx.logger = create_logger(output, log_level)

# Add commands
cli.add_command(create_session_commands())
cli.add_command(create_request_commands())
cli.add_command(create_playbook_commands())

def main():
    cli()

if __name__ == '__main__':
    main()
