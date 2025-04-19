import asyncio
import signal
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
        
    def _read_playbook_content(self, playbook_file: Optional[TextIO]) -> str:
        """Read playbook content from file or stdin."""
        if playbook_file is None:
            if sys.stdin.isatty():
                raise ValueError("Please provide a playbook file or pipe YAML content")
            return sys.stdin.read()
        
        content = playbook_file.read()
        playbook_file.seek(0)  # Reset file pointer for potential reuse
        return content

    def _configure_playbook(self, playbook: Playbook, no_resume: bool) -> None:
        """Configure playbook settings based on command options."""
        if no_resume and playbook.config.incremental and playbook.config.incremental.enabled:
            playbook.config.incremental.enabled = False
            self.logger.log_info("Checkpoint resume disabled")

    def _log_execution_timing(self, execution_start: datetime) -> None:
        """Log execution timing information."""
        execution_time = (datetime.now() - execution_start).total_seconds()
        self.logger.log_info(f"Execution completed in {execution_time:.2f} seconds")

    def _check_schedule_drift(self, next_run: datetime) -> None:
        """Check and log if we're running behind schedule."""
        current_time = datetime.now()
        if current_time > next_run:
            time_behind = (current_time - next_run).total_seconds()
            self.logger.log_warning(
                f"Execution is running {time_behind:.2f} seconds behind schedule. "
                "Consider adjusting the cron schedule to allow more time between runs."
            )

    def _wait_until_next_run(self, next_run: datetime) -> None:
        """Sleep until the next scheduled run time."""
        sleep_time = max(0, (next_run - datetime.now()).total_seconds())
        if sleep_time > 0:
            self.logger.log_info(f"Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

    def execute_playbook(self, playbook_file: Optional[TextIO], no_resume: bool):
        """Execute a playbook from a file or stdin."""
        try:
            # Read and parse the playbook
            content = self._read_playbook_content(playbook_file)
            playbook = Playbook.from_yaml(content, self.logger, self.session_store)
            
            # Configure playbook settings
            self._configure_playbook(playbook, no_resume)
            # Execute the playbook
            asyncio.run(playbook.execute())
        except ValueError as err:
            self.logger.log_error(f"Playbook error: {str(err)}")
        except requests.exceptions.RequestException as err:
            self.logger.log_error(f"Request failed: {str(err)}")
        except KeyboardInterrupt:
            self.logger.log_info("Execution interrupted by user")
        except Exception as err:
            self.logger.log_error(f"Unexpected error during playbook execution: {str(err)}")
            raise

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
                    
                    # Wait for next run time
                    self._wait_until_next_run(next_run)
                    
                    # Check if we're running behind schedule
                    self._check_schedule_drift(next_run)
                    
                    try:
                        execution_start = datetime.now()
                        self.logger.log_info("Starting playbook execution")
                        self.execute_playbook(playbook_file, no_resume)
                        self._log_execution_timing(execution_start)
                    except Exception as e:
                        self.logger.log_error(f"Error in scheduled execution: {str(e)}")
                        # Continue to next scheduled run despite errors
                        
            except ImportError:
                self.logger.log_error("croniter package is required for cron functionality. Install with: pip install croniter")
                sys.exit(1)
            except KeyboardInterrupt:
                self.logger.log_info("Cron scheduler stopped by user")
                return
        else:
            self.execute_playbook(playbook_file, no_resume) 