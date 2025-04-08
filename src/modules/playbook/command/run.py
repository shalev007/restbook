import asyncio
import sys
import requests
from typing import Optional, TextIO
from ...logging import BaseLogger
from ...session.session_store import SessionStore
from ..playbook import Playbook
from croniter import croniter
import time
from datetime import datetime


class RunCommand:
    """Command class for handling playbook execution."""
    
    def __init__(
        self,
        logger: BaseLogger,
        session_store: SessionStore,
        timeout: int = 30,
        verify_ssl: bool = True,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        max_delay: Optional[int] = None
    ):
        """
        Initialize the run command.
        
        Args:
            logger: Logger instance
            session_store: Session store instance
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retries
            backoff_factor: Backoff factor for retries
            max_delay: Maximum delay between retries in seconds
        """
        self.logger = logger
        self.session_store = session_store
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay

    def execute_playbook(self, playbook_file: Optional[TextIO], no_resume: bool):
        """Execute a playbook from a file or stdin."""
        try:
            # Read from file or stdin
            if playbook_file is None:
                if sys.stdin.isatty():
                    raise ValueError("Please provide a playbook file or pipe YAML content")
                content = sys.stdin.read()
            else:
                content = playbook_file.read()
                playbook_file.seek(0)  # Reset file pointer for potential reuse

            # Parse the playbook
            playbook = Playbook.from_yaml(content, logger=self.logger)
            
            # Disable incremental execution if --no-resume is specified
            if no_resume and playbook.config.incremental and playbook.config.incremental.enabled:
                playbook.checkpoint_store = None
                playbook.content_hash = None
                self.logger.log_info("Checkpoint resume disabled")
                
            # Execute the playbook
            asyncio.run(playbook.execute(self.session_store))

        except ValueError as err:
            self.logger.log_error(str(err))
        except requests.exceptions.RequestException as err:
            self.logger.log_error(f"Request failed: {str(err)}")

    def run(self, playbook_file: Optional[TextIO], no_resume: bool, cron: Optional[str] = None):
        """
        Run the playbook command.
        
        Args:
            playbook_file: File containing the playbook YAML
            no_resume: Whether to disable checkpoint resume
            cron: Optional cron expression for scheduling
        """
        if cron:
            try:
                if not croniter.is_valid(cron):
                    raise ValueError(f"Invalid cron expression: {cron}")
                
                self.logger.log_info(f"Starting playbook in cron mode with schedule: {cron}")
                cron_iter = croniter(cron, datetime.now())
                
                while True:
                    next_run = cron_iter.get_next(datetime)
                    self.logger.log_info(f"Next run scheduled for: {next_run}")
                    
                    # Sleep until next run time
                    time.sleep(max(0, (next_run - datetime.now()).total_seconds()))
                    
                    try:
                        self.execute_playbook(playbook_file, no_resume)
                    except Exception as e:
                        self.logger.log_error(f"Error in scheduled execution: {str(e)}")
                        # Continue to next scheduled run despite errors
            except ImportError:
                self.logger.log_error("croniter package is required for cron functionality. Install with: pip install croniter")
                sys.exit(1)
        else:
            self.execute_playbook(playbook_file, no_resume) 