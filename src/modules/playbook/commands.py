import click
from typing import Optional, TextIO
from .command.run import RunCommand


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
    @click.option('--cron', type=str, help='Schedule playbook execution using cron syntax (e.g. "*/5 * * * *")')
    @click.pass_context
    def run(ctx, playbook_file: Optional[TextIO], no_resume: bool, cron: Optional[str]):
        """Execute a YAML playbook from a file or stdin.
        
        If no file is specified, reads from stdin.
        If --cron is specified, runs the playbook on a schedule using cron syntax.
        """
        command = RunCommand(
            logger=ctx.obj.logger,
            session_store=ctx.obj.session_store
        )
        command.run(playbook_file, no_resume, cron)

    return playbook 