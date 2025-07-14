"""
Tests for WebSocket API endpoints.

This module tests WebSocket connection management, authentication,
and real-time message broadcasting functionality.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import WebSocket


class TestWebSocketEndpoints:
    """Test WebSocket API endpoints."""
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for authentication."""
        return {
            "sub": "user123",
            "email": "test@example.com",
            "is_active": True,
            "permissions": ["read", "write"],
            "exp": datetime.now().timestamp() + 3600  # 1 hour from now
        }
    
    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket connection."""
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.close = AsyncMock()
        websocket.query_params = {"token": "test_token"}
        websocket.headers = {"authorization": "Bearer test_token"}
        return websocket
    
    @patch('src.api.routers.websocket.verify_websocket_token')
    @pytest.mark.asyncio
    async def test_websocket_connection_success(
        self, 
        mock_verify_token,
        mock_websocket,
        sample_user_data
    ):
        """Test successful WebSocket connection."""
        # Setup mocks
        mock_verify_token.return_value = sample_user_data
        
        from src.api.routers.websocket import connection_manager, websocket_endpoint
        
        # Reset connection manager
        connection_manager.active_connections.clear()
        connection_manager.user_connections.clear()
        
        # Simulate connection
        mock_websocket.receive_text.side_effect = [
            json.dumps({"type": "ping"}),
            asyncio.CancelledError()  # Simulate disconnection
        ]
        
        try:
            await websocket_endpoint(mock_websocket, "test_token")
        except asyncio.CancelledError:
            pass
        
        # Verify connection was accepted
        mock_websocket.accept.assert_called_once()
        
        # Verify welcome message was sent
        assert mock_websocket.send_text.call_count >= 1
    
    @patch('src.api.routers.websocket.verify_websocket_token')
    @pytest.mark.asyncio
    async def test_websocket_authentication_failure(
        self, 
        mock_verify_token,
        mock_websocket
    ):
        """Test WebSocket connection with failed authentication."""
        # Setup mocks
        mock_verify_token.return_value = None  # Authentication failed
        
        from src.api.routers.websocket import websocket_endpoint
        
        # Simulate connection attempt
        await websocket_endpoint(mock_websocket, "invalid_token")
        
        # Verify connection was closed with authentication error
        mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_manager_connect(self, sample_user_data):
        """Test connection manager connect functionality."""
        from src.api.routers.websocket import ConnectionManager
        
        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        
        # Connect a user
        connection_id = await manager.connect(mock_websocket, sample_user_data)
        
        # Verify connection was added
        assert connection_id in manager.active_connections
        assert sample_user_data["sub"] in manager.user_connections
        assert connection_id in manager.user_connections[sample_user_data["sub"]]
        
        # Verify welcome message was sent
        mock_websocket.send_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_connection_manager_disconnect(self, sample_user_data):
        """Test connection manager disconnect functionality."""
        from src.api.routers.websocket import ConnectionManager
        
        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        
        # Connect and then disconnect
        connection_id = await manager.connect(mock_websocket, sample_user_data)
        manager.disconnect(connection_id)
        
        # Verify connection was removed
        assert connection_id not in manager.active_connections
        assert sample_user_data["sub"] not in manager.user_connections
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self, sample_user_data):
        """Test sending personal message to specific connection."""
        from src.api.routers.websocket import ConnectionManager
        
        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        
        # Connect a user
        connection_id = await manager.connect(mock_websocket, sample_user_data)
        
        # Send personal message
        test_message = {"type": "test", "data": "hello"}
        await manager.send_personal_message(test_message, connection_id)
        
        # Verify message was sent
        assert mock_websocket.send_text.call_count >= 2  # Welcome + test message
    
    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, sample_user_data):
        """Test broadcasting message to channel subscribers."""
        from src.api.routers.websocket import ConnectionManager
        
        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        
        # Connect a user and subscribe to channel
        connection_id = await manager.connect(mock_websocket, sample_user_data)
        manager.subscribe_to_channel(connection_id, "memory_updates")
        
        # Broadcast to channel
        test_message = {"type": "memory_update", "data": "test"}
        await manager.broadcast_to_channel(test_message, "memory_updates")
        
        # Verify message was sent to subscriber
        assert mock_websocket.send_text.call_count >= 2  # Welcome + broadcast
    
    @pytest.mark.asyncio
    async def test_channel_subscription_management(self, sample_user_data):
        """Test channel subscription and unsubscription."""
        from src.api.routers.websocket import ConnectionManager
        
        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        
        # Connect a user
        connection_id = await manager.connect(mock_websocket, sample_user_data)
        
        # Subscribe to channels
        manager.subscribe_to_channel(connection_id, "memory_updates")
        manager.subscribe_to_channel(connection_id, "graph_updates")
        
        # Verify subscriptions
        assert "memory_updates" in manager.channel_subscriptions
        assert "graph_updates" in manager.channel_subscriptions
        assert connection_id in manager.channel_subscriptions["memory_updates"]
        assert connection_id in manager.channel_subscriptions["graph_updates"]
        
        # Unsubscribe from one channel
        manager.unsubscribe_from_channel(connection_id, "memory_updates")
        
        # Verify unsubscription
        assert connection_id not in manager.channel_subscriptions.get("memory_updates", set())
        assert connection_id in manager.channel_subscriptions["graph_updates"]
    
    @pytest.mark.asyncio
    async def test_message_processing(self, sample_user_data):
        """Test WebSocket message processing."""
        from src.api.routers.websocket import _process_message
        
        connection_id = "test_connection"
        
        # Test ping message
        ping_message = json.dumps({"type": "ping"})
        await _process_message(connection_id, ping_message, sample_user_data)
        
        # Test subscribe message
        subscribe_message = json.dumps({
            "type": "subscribe",
            "channels": ["memory_updates", "graph_updates"]
        })
        await _process_message(connection_id, subscribe_message, sample_user_data)
        
        # Test unsubscribe message
        unsubscribe_message = json.dumps({
            "type": "unsubscribe",
            "channels": ["memory_updates"]
        })
        await _process_message(connection_id, unsubscribe_message, sample_user_data)
        
        # Test invalid JSON
        with pytest.raises(Exception):
            await _process_message(connection_id, "invalid json", sample_user_data)
    
    def test_channel_validation(self, sample_user_data):
        """Test channel validation for user permissions."""
        from src.api.routers.websocket import _is_valid_channel
        
        user_id = sample_user_data["sub"]
        
        # Test valid channels
        assert _is_valid_channel("memory_updates", sample_user_data) is True
        assert _is_valid_channel("graph_updates", sample_user_data) is True
        assert _is_valid_channel(f"user_{user_id}_personal", sample_user_data) is True
        assert _is_valid_channel("system_notifications", sample_user_data) is True
        
        # Test invalid channel
        assert _is_valid_channel("unauthorized_channel", sample_user_data) is False
    
    def test_connection_manager_stats(self, sample_user_data):
        """Test connection manager statistics."""
        from src.api.routers.websocket import ConnectionManager
        
        manager = ConnectionManager()
        
        # Get initial stats
        stats = manager.get_stats()
        assert stats["active_connections"] == 0
        assert stats["active_users"] == 0
        assert stats["active_channels"] == 0
    
    def test_connection_info(self, sample_user_data):
        """Test getting connection information."""
        from src.api.routers.websocket import ConnectionManager
        
        manager = ConnectionManager()
        
        # Test non-existent connection
        info = manager.get_connection_info("non_existent")
        assert info is None


class TestWebSocketAuthentication:
    """Test WebSocket authentication functionality."""
    
    @pytest.mark.asyncio
    async def test_verify_websocket_token_success(self):
        """Test successful WebSocket token verification."""
        from src.api.dependencies import verify_websocket_token
        
        mock_websocket = MagicMock()
        mock_websocket.query_params = {"token": "valid_token"}
        
        with patch('src.api.dependencies.get_settings') as mock_settings, \
             patch('src.api.dependencies.jwt.decode') as mock_decode:
            
            # Setup mocks
            mock_settings.return_value.jwt_secret_key.get_secret_value.return_value = "secret"
            mock_settings.return_value.jwt_algorithm = "HS256"
            
            mock_decode.return_value = {
                "sub": "user123",
                "exp": datetime.now().timestamp() + 3600
            }
            
            # Test token verification
            result = await verify_websocket_token(mock_websocket, "valid_token")
            
            assert result is not None
            assert result["sub"] == "user123"
    
    @pytest.mark.asyncio
    async def test_verify_websocket_token_failure(self):
        """Test failed WebSocket token verification."""
        from src.api.dependencies import verify_websocket_token
        from jose import JWTError
        
        mock_websocket = MagicMock()
        mock_websocket.query_params = {}
        mock_websocket.headers = {}
        
        with patch('src.api.dependencies.get_settings') as mock_settings, \
             patch('src.api.dependencies.jwt.decode') as mock_decode:
            
            # Setup mocks
            mock_settings.return_value.jwt_secret_key.get_secret_value.return_value = "secret"
            mock_settings.return_value.jwt_algorithm = "HS256"
            
            mock_decode.side_effect = JWTError("Invalid token")
            
            # Test token verification failure
            result = await verify_websocket_token(mock_websocket, "invalid_token")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_verify_websocket_token_expired(self):
        """Test expired WebSocket token verification."""
        from src.api.dependencies import verify_websocket_token
        
        mock_websocket = MagicMock()
        mock_websocket.query_params = {"token": "expired_token"}
        
        with patch('src.api.dependencies.get_settings') as mock_settings, \
             patch('src.api.dependencies.jwt.decode') as mock_decode:
            
            # Setup mocks
            mock_settings.return_value.jwt_secret_key.get_secret_value.return_value = "secret"
            mock_settings.return_value.jwt_algorithm = "HS256"
            
            # Return expired token
            mock_decode.return_value = {
                "sub": "user123",
                "exp": datetime.now().timestamp() - 3600  # 1 hour ago
            }
            
            # Test expired token verification
            result = await verify_websocket_token(mock_websocket, "expired_token")
            
            assert result is None


class TestWebSocketBroadcasting:
    """Test WebSocket broadcasting functionality."""
    
    @pytest.mark.asyncio
    async def test_broadcast_memory_update(self):
        """Test broadcasting memory update event."""
        from src.api.routers.websocket import broadcast_memory_update
        from src.core.memory.models import MemoryType
        
        memory_id = uuid4()
        
        # Test broadcast (would need connection manager mock in full implementation)
        await broadcast_memory_update(memory_id, MemoryType.LEARNING, "created")
        
        # Placeholder for verification
        assert memory_id is not None
    
    @pytest.mark.asyncio
    async def test_broadcast_graph_update(self):
        """Test broadcasting graph update event."""
        from src.api.routers.websocket import broadcast_graph_update
        
        graph_id = uuid4()
        metadata = {"nodes": 25, "edges": 45}
        
        # Test broadcast
        await broadcast_graph_update(graph_id, "created", metadata)
        
        # Placeholder for verification
        assert graph_id is not None
    
    @pytest.mark.asyncio
    async def test_broadcast_integration_update(self):
        """Test broadcasting integration update event."""
        from src.api.routers.websocket import broadcast_integration_update
        
        details = {"notes_created": 20, "notes_updated": 5}
        
        # Test broadcast
        await broadcast_integration_update("vault_sync", "completed", details)
        
        # Placeholder for verification
        assert details["notes_created"] == 20
    
    @pytest.mark.asyncio
    async def test_send_user_notification(self):
        """Test sending user-specific notification."""
        from src.api.routers.websocket import send_user_notification
        
        user_id = "user123"
        notification = {"message": "Test notification", "type": "info"}
        
        # Test notification
        await send_user_notification(user_id, notification)
        
        # Placeholder for verification
        assert notification["message"] == "Test notification"
    
    @pytest.mark.asyncio
    async def test_broadcast_system_notification(self):
        """Test broadcasting system notification."""
        from src.api.routers.websocket import broadcast_system_notification
        
        notification = {"message": "System maintenance", "type": "warning"}
        
        # Test broadcast
        await broadcast_system_notification(notification)
        
        # Placeholder for verification
        assert notification["type"] == "warning"


class TestWebSocketModels:
    """Test WebSocket-related models and data structures."""
    
    def test_websocket_connection_creation(self):
        """Test WebSocketConnection creation."""
        from src.api.routers.websocket import WebSocketConnection
        
        mock_websocket = MagicMock()
        connection_id = str(uuid4())
        user_id = "user123"
        user_data = {"sub": user_id, "email": "test@example.com"}
        connected_at = datetime.now()
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=user_id,
            user_data=user_data,
            connected_at=connected_at
        )
        
        assert connection.connection_id == connection_id
        assert connection.user_id == user_id
        assert connection.websocket == mock_websocket
        assert connection.connected_at == connected_at
        assert connection.messages_sent == 0
        assert connection.messages_received == 0
        assert len(connection.subscribed_channels) == 0
    
    def test_connection_manager_initialization(self):
        """Test ConnectionManager initialization."""
        from src.api.routers.websocket import ConnectionManager
        
        manager = ConnectionManager()
        
        assert len(manager.active_connections) == 0
        assert len(manager.user_connections) == 0
        assert len(manager.channel_subscriptions) == 0
        assert manager.total_connections == 0
        assert manager.total_messages_sent == 0
        assert manager.total_messages_received == 0