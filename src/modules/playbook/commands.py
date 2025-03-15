import asyncio
import click
import sys
import requests
from typing import Optional, TextIO
from ..logging import BaseLogger
from ..session.session_store import SessionStore
from .playbook import Playbook


def create_playbook_commands() -> click.Command:
    """Create the playbook command."""

    @click.group(name='playbook')
    @click.pass_context
    def playbook(ctx):
        """Manage and execute playbooks."""
        pass

    @playbook.command(name='run')
    @click.argument('playbook_file', type=click.File('r'), required=False)
    @click.option('--no-resume', is_flag=True, help='Do not resume from checkpoint')
    @click.pass_context
    def run(ctx, playbook_file: Optional[TextIO], no_resume: bool):
        """Execute a YAML playbook from a file or stdin.
        
        If no file is specified, reads from stdin.
        """
        logger: BaseLogger = ctx.obj.logger
        session_store: SessionStore = ctx.obj.session_store
        try:
            # Read from file or stdin
            if playbook_file is None:
                if sys.stdin.isatty():
                    raise click.UsageError("Please provide a playbook file or pipe YAML content")
                content = sys.stdin.read()
            else:
                content = playbook_file.read()

            # Parse the playbook
            playbook = Playbook.from_yaml(content, logger=logger)
            
            # Disable incremental execution if --no-resume is specified
            if no_resume and playbook.config.incremental and playbook.config.incremental.enabled:
                playbook.checkpoint_store = None
                playbook.content_hash = None
                logger.log_info("Checkpoint resume disabled")
                
            # Execute the playbook
            asyncio.run(playbook.execute(session_store))

        except ValueError as err:
            logger.log_error(str(err))
        except requests.exceptions.RequestException as err:
            logger.log_error(f"Request failed: {str(err)}")

    return playbook 