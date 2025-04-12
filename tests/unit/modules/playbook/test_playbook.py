import pytest
from unittest.mock import Mock, AsyncMock, patch, PropertyMock
from typing import Dict, Any

from src.modules.playbook.playbook import Playbook
from src.modules.playbook.config import PlaybookConfig
from src.modules.logging import BaseLogger
from src.modules.playbook.variables import VariableManager
from src.modules.playbook.template_renderer import TemplateRenderer
from src.modules.playbook.managers.config_renderer import ConfigRenderer
from src.modules.playbook.managers.checkpoint_manager import CheckpointManager
from src.modules.playbook.managers.session_manager import SessionManager
from src.modules.playbook.managers.observer_manager import ObserverManager
from src.modules.request.client_factory import ResilientHttpClientFactory
from src.modules.session.session_store import SessionStore

@pytest.fixture
def mock_logger():
    return Mock(spec=BaseLogger)

@pytest.fixture
def mock_config():
    config = Mock(spec=PlaybookConfig)
    config.sessions = []
    config.phases = []
    config.incremental = Mock(enabled=False)
    config.metrics = Mock(enabled=False)
    return config

@pytest.fixture
def mock_variables():
    variables = Mock(spec=VariableManager)
    variables.get_all.return_value = {}
    variables.has.return_value = True
    variables.get.return_value = []
    return variables

@pytest.fixture
def mock_renderer():
    return Mock(spec=TemplateRenderer)

@pytest.fixture
def mock_config_renderer():
    return Mock(spec=ConfigRenderer)

@pytest.fixture
def mock_checkpoint_manager():
    return Mock(spec=CheckpointManager)

@pytest.fixture
def mock_session_manager():
    return Mock(spec=SessionManager)

@pytest.fixture
def mock_observer_manager():
    return Mock(spec=ObserverManager)

@pytest.fixture
def mock_client_factory():
    return Mock(spec=ResilientHttpClientFactory)

@pytest.fixture
def mock_session_store():
    return Mock(spec=SessionStore)

@pytest.fixture
def playbook(
    mock_config,
    mock_logger,
    mock_variables,
    mock_renderer,
    mock_config_renderer,
    mock_checkpoint_manager,
    mock_session_manager,
    mock_observer_manager,
    mock_client_factory
):
    return Playbook(
        config=mock_config,
        logger=mock_logger,
        variables=mock_variables,
        renderer=mock_renderer,
        config_renderer=mock_config_renderer,
        checkpoint_manager=mock_checkpoint_manager,
        session_manager=mock_session_manager,
        observer_manager=mock_observer_manager,
        client_factory=mock_client_factory
    )

class TestPlaybook:
    def test_initialization(self, playbook, mock_config, mock_logger):
        """Test that Playbook is initialized with correct dependencies."""
        assert playbook.config == mock_config
        assert playbook.logger == mock_logger
        assert isinstance(playbook.variables, Mock)
        assert isinstance(playbook.renderer, Mock)
        assert isinstance(playbook.config_renderer, Mock)
        assert isinstance(playbook.checkpoint_manager, Mock)
        assert isinstance(playbook.session_manager, Mock)
        assert isinstance(playbook.observer_manager, Mock)
        assert isinstance(playbook.client_factory, Mock)

    def test_create_factory_method(self, mock_config, mock_logger):
        """Test the create factory method creates a Playbook with default dependencies."""
        playbook = Playbook.create(mock_config, mock_logger)
        
        assert isinstance(playbook, Playbook)
        assert playbook.config == mock_config
        assert playbook.logger == mock_logger
        assert isinstance(playbook.variables, VariableManager)
        assert isinstance(playbook.renderer, TemplateRenderer)
        assert isinstance(playbook.config_renderer, ConfigRenderer)
        assert isinstance(playbook.checkpoint_manager, CheckpointManager)
        assert isinstance(playbook.session_manager, SessionManager)
        assert isinstance(playbook.observer_manager, ObserverManager)
        assert isinstance(playbook.client_factory, ResilientHttpClientFactory)

    @pytest.mark.asyncio
    async def test_execute_playbook(self, playbook, mock_session_store):
        """Test the execute method of Playbook."""
        # Setup mocks
        playbook.checkpoint_manager.load_checkpoint = AsyncMock(return_value=None)
        playbook.checkpoint_manager.clear_checkpoint = AsyncMock()
        playbook.session_manager.initialize_temp_sessions = Mock()
        playbook.session_manager.clear_temp_sessions = Mock()
        playbook.observer_manager.notify = Mock()
        playbook.observer_manager.cleanup = Mock()
        
        # Execute playbook
        await playbook.execute(mock_session_store)
        
        # Verify calls
        playbook.observer_manager.notify.assert_called()
        playbook.session_manager.initialize_temp_sessions.assert_called_once_with([])
        playbook.checkpoint_manager.load_checkpoint.assert_called_once()
        playbook.checkpoint_manager.clear_checkpoint.assert_called_once()
        playbook.session_manager.clear_temp_sessions.assert_called_once()
        playbook.observer_manager.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_playbook_with_error(self, playbook, mock_session_store):
        """Test error handling during playbook execution."""
        # Setup mocks
        playbook.checkpoint_manager.load_checkpoint = AsyncMock(return_value=None)
        playbook.session_manager.initialize_temp_sessions = Mock(side_effect=Exception("Test error"))
        playbook.observer_manager.notify = Mock()
        playbook.observer_manager.cleanup = Mock()
        
        # Execute playbook and expect error
        with pytest.raises(Exception) as exc_info:
            await playbook.execute(mock_session_store)
        
        assert str(exc_info.value) == "Test error"
        playbook.observer_manager.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_playbook_with_checkpoint(self, playbook, mock_session_store):
        """Test playbook execution with checkpoint handling."""
        # Setup mocks
        checkpoint = Mock(
            phase_index=1,
            step_index=2,
            variables={"test": "value"}
        )
        playbook.checkpoint_manager.load_checkpoint = AsyncMock(return_value=checkpoint)
        playbook.checkpoint_manager.clear_checkpoint = AsyncMock()
        playbook.session_manager.initialize_temp_sessions = Mock()
        playbook.session_manager.clear_temp_sessions = Mock()
        playbook.observer_manager.notify = Mock()
        playbook.observer_manager.cleanup = Mock()
        playbook.variables.set_all = Mock()
        
        # Mock config with phases
        playbook.config.phases = [
            Mock(index=0, steps=[Mock()]),
            Mock(index=1, steps=[Mock(), Mock(), Mock()]),
            Mock(index=2, steps=[Mock()])
        ]
        
        # Execute playbook
        await playbook.execute(mock_session_store)
        
        # Verify checkpoint handling
        playbook.checkpoint_manager.load_checkpoint.assert_called_once()
        playbook.variables.set_all.assert_called_once_with(checkpoint.variables)
        playbook.checkpoint_manager.clear_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_step_with_retry(self, playbook, mock_session_store):
        """Test step execution with retry logic."""
        # Setup mocks
        request_config = Mock()
        request_config.endpoint = "http://test.com"
        request_config.method = Mock(value="GET")
        request_config.headers = {}
        request_config.data = {}
        request_config.params = {}
        
        step_config = Mock(
            retry=Mock(count=2, delay=0.1),
            on_error="ignore",
            session="test_session",
            iterate=None,
            request=request_config,
            store=None,
            parallel=False,
            model_copy=Mock(return_value=Mock(
                request=request_config,
                store=None
            ))
        )
        phase_context = Mock(id="phase1", index=0)
        step_index = 0
        
        # Mock session
        session = Mock()
        playbook.session_manager.get_session.return_value = session
        
        # Mock client to fail twice then succeed
        client = Mock()
        client.execute_request = AsyncMock(
            side_effect=[
                Exception("First failure"),
                Exception("Second failure"),
                Mock(
                    status=200,
                    json=AsyncMock(return_value={"result": "success"}),
                    text=AsyncMock(return_value="success")
                )
            ]
        )
        client.close = AsyncMock()
        
        # Create metadata object with all required attributes
        metadata = Mock()
        metadata.status_code = 200
        metadata.duration = 0.1
        metadata.retries = 2
        metadata.error = None
        metadata.success = True
        metadata.errors = []
        client.get_last_request_execution_metadata = Mock(return_value=metadata)
        
        playbook.client_factory.create_client.return_value = client
        
        # Mock config renderer
        playbook.config_renderer.render_request_config.return_value = request_config
        
        # Mock variables
        playbook.variables.get_all.return_value = {}
        
        # Execute step
        await playbook._execute_step(step_config, phase_context.id, step_index, mock_session_store)
        
        # Verify retry behavior
        assert client.execute_request.call_count == 1
        playbook.observer_manager.notify.assert_called()
        client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_management(self, playbook, mock_session_store):
        """Test session management during playbook execution."""
        # Setup mocks
        session_name = "test_session"
        session = Mock()
        mock_session_store.get_session.return_value = session
        
        # Mock config with session
        playbook.config.sessions = [{"name": session_name}]
        playbook.config.phases = [Mock(steps=[Mock(session=session_name)])]
        
        # Setup other mocks
        playbook.checkpoint_manager.load_checkpoint = AsyncMock(return_value=None)
        playbook.checkpoint_manager.clear_checkpoint = AsyncMock()
        playbook.session_manager.initialize_temp_sessions = Mock()
        playbook.session_manager.clear_temp_sessions = Mock()
        playbook.observer_manager.notify = Mock()
        playbook.observer_manager.cleanup = Mock()
        playbook.session_manager.get_session.return_value = session
        
        # Mock step execution
        async def mock_execute_step(*args, **kwargs):
            playbook.session_manager.get_session.assert_called_with(session_name, mock_session_store)
        
        playbook._execute_step = AsyncMock(side_effect=mock_execute_step)
        
        # Execute playbook
        await playbook.execute(mock_session_store)
        
        # Verify session management
        playbook.session_manager.initialize_temp_sessions.assert_called_once_with([{"name": session_name}])
        playbook.session_manager.clear_temp_sessions.assert_called_once()

    def test_to_dict(self, playbook, mock_config):
        """Test the to_dict method returns the config as a dictionary."""
        expected_dict = {"test": "value"}
        mock_config.model_dump.return_value = expected_dict
        
        result = playbook.to_dict()
        
        assert result == expected_dict
        mock_config.model_dump.assert_called_once() 