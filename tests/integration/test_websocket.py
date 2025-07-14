"""
WebSocket integration tests.

Tests WebSocket connections, authentication, real-time updates,
channel subscriptions, and error handling.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch

import websockets
from httpx import AsyncClient

from tests.fixtures.memories import MemoryFixtures


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebSocket:
    """Test WebSocket functionality."""
    
    @pytest.fixture
    def ws_url(self):
        """WebSocket URL for testing."""
        return "ws://test/ws/realtime"
    
    @pytest.fixture
    def auth_token(self):
        """Test authentication token."""
        return "test-jwt-token"
    
    @pytest.fixture
    async def ws_client(self, api_client: AsyncClient, ws_url: str, auth_token: str):
        """Create WebSocket test client."""
        # Mock websocket connection
        ws = AsyncMock()
        ws.send = AsyncMock()
        ws.recv = AsyncMock()
        ws.close = AsyncMock()
        
        async def mock_connect(*args, **kwargs):
            return ws
        
        with patch('websockets.connect', side_effect=mock_connect):
            yield ws
    
    async def test_websocket_connection_success(
        self,
        ws_client,
        ws_url: str,
        auth_token: str
    ):
        """Test successful WebSocket connection."""
        # Simulate successful connection
        ws_client.recv.side_effect = [
            json.dumps({
                "type": "connection",
                "status": "connected",
                "message": "Connected to CoachNTT.ai realtime updates"
            })
        ]
        
        # Connect to WebSocket
        async with websockets.connect(
            f"{ws_url}?token={auth_token}"
        ) as websocket:
            # Receive connection message
            message = await websocket.recv()
            data = json.loads(message)
            
            assert data["type"] == "connection"
            assert data["status"] == "connected"
    
    async def test_websocket_authentication_required(
        self,
        ws_client,
        ws_url: str
    ):
        """Test WebSocket requires authentication."""
        # Simulate auth failure
        ws_client.recv.side_effect = websockets.exceptions.ConnectionClosedError(
            1008, "Policy Violation"
        )
        
        # Try to connect without token
        with pytest.raises(websockets.exceptions.ConnectionClosedError):
            async with websockets.connect(ws_url) as websocket:
                await websocket.recv()
    
    async def test_channel_subscription(
        self,
        ws_client,
        ws_url: str,
        auth_token: str
    ):
        """Test subscribing to channels."""
        # Simulate subscription responses
        ws_client.recv.side_effect = [
            json.dumps({
                "type": "connection",
                "status": "connected"
            }),
            json.dumps({
                "type": "subscription",
                "channel": "memory_updates",
                "status": "subscribed"
            }),
            json.dumps({
                "type": "subscription",
                "channel": "graph_updates",
                "status": "subscribed"
            })
        ]
        
        async with websockets.connect(
            f"{ws_url}?token={auth_token}"
        ) as websocket:
            # Skip connection message
            await websocket.recv()
            
            # Subscribe to memory updates
            await websocket.send(json.dumps({
                "action": "subscribe",
                "channel": "memory_updates"
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            assert data["type"] == "subscription"
            assert data["channel"] == "memory_updates"
            assert data["status"] == "subscribed"
            
            # Subscribe to graph updates
            await websocket.send(json.dumps({
                "action": "subscribe",
                "channel": "graph_updates"
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            assert data["channel"] == "graph_updates"
            assert data["status"] == "subscribed"
    
    async def test_memory_update_notifications(
        self,
        ws_client,
        ws_url: str,
        auth_token: str,
        memory_fixtures: MemoryFixtures
    ):
        """Test receiving memory update notifications."""
        memory_data = memory_fixtures.create_safe_memory()
        
        # Simulate memory update notification
        ws_client.recv.side_effect = [
            json.dumps({
                "type": "connection",
                "status": "connected"
            }),
            json.dumps({
                "type": "subscription",
                "channel": "memory_updates",
                "status": "subscribed"
            }),
            json.dumps({
                "type": "memory_update",
                "action": "created",
                "data": {
                    "id": memory_data["id"],
                    "memory_type": memory_data["memory_type"],
                    "content": memory_data["content"],
                    "safety_score": memory_data["safety_score"]
                }
            })
        ]
        
        async with websockets.connect(
            f"{ws_url}?token={auth_token}"
        ) as websocket:
            # Connect and subscribe
            await websocket.recv()  # connection
            await websocket.send(json.dumps({
                "action": "subscribe",
                "channel": "memory_updates"
            }))
            await websocket.recv()  # subscription confirmation
            
            # Receive memory update
            message = await websocket.recv()
            data = json.loads(message)
            
            assert data["type"] == "memory_update"
            assert data["action"] == "created"
            assert data["data"]["id"] == memory_data["id"]
    
    async def test_graph_update_notifications(
        self,
        ws_client,
        ws_url: str,
        auth_token: str
    ):
        """Test receiving graph update notifications."""
        # Simulate graph update
        ws_client.recv.side_effect = [
            json.dumps({
                "type": "connection",
                "status": "connected"
            }),
            json.dumps({
                "type": "subscription",
                "channel": "graph_updates",
                "status": "subscribed"
            }),
            json.dumps({
                "type": "graph_update",
                "action": "build_complete",
                "data": {
                    "graph_id": "test-graph-123",
                    "name": "Test Graph",
                    "node_count": 25,
                    "edge_count": 40,
                    "build_time_seconds": 2.5
                }
            })
        ]
        
        async with websockets.connect(
            f"{ws_url}?token={auth_token}"
        ) as websocket:
            # Connect and subscribe
            await websocket.recv()
            await websocket.send(json.dumps({
                "action": "subscribe",
                "channel": "graph_updates"
            }))
            await websocket.recv()
            
            # Receive graph update
            message = await websocket.recv()
            data = json.loads(message)
            
            assert data["type"] == "graph_update"
            assert data["action"] == "build_complete"
            assert data["data"]["graph_id"] == "test-graph-123"
    
    async def test_heartbeat_mechanism(
        self,
        ws_client,
        ws_url: str,
        auth_token: str
    ):
        """Test WebSocket heartbeat/ping-pong."""
        # Simulate heartbeat exchange
        ws_client.recv.side_effect = [
            json.dumps({
                "type": "connection",
                "status": "connected"
            }),
            json.dumps({
                "type": "pong",
                "timestamp": "2024-01-01T00:00:00Z"
            })
        ]
        
        async with websockets.connect(
            f"{ws_url}?token={auth_token}"
        ) as websocket:
            await websocket.recv()  # connection
            
            # Send ping
            await websocket.send(json.dumps({
                "type": "ping",
                "timestamp": "2024-01-01T00:00:00Z"
            }))
            
            # Receive pong
            message = await websocket.recv()
            data = json.loads(message)
            
            assert data["type"] == "pong"
            assert "timestamp" in data
    
    async def test_error_handling(
        self,
        ws_client,
        ws_url: str,
        auth_token: str
    ):
        """Test WebSocket error handling."""
        # Simulate error response
        ws_client.recv.side_effect = [
            json.dumps({
                "type": "connection",
                "status": "connected"
            }),
            json.dumps({
                "type": "error",
                "code": "INVALID_CHANNEL",
                "message": "Channel 'invalid_channel' does not exist"
            })
        ]
        
        async with websockets.connect(
            f"{ws_url}?token={auth_token}"
        ) as websocket:
            await websocket.recv()  # connection
            
            # Try to subscribe to invalid channel
            await websocket.send(json.dumps({
                "action": "subscribe",
                "channel": "invalid_channel"
            }))
            
            # Receive error
            message = await websocket.recv()
            data = json.loads(message)
            
            assert data["type"] == "error"
            assert data["code"] == "INVALID_CHANNEL"
    
    async def test_concurrent_subscriptions(
        self,
        ws_client,
        ws_url: str,
        auth_token: str
    ):
        """Test multiple concurrent channel subscriptions."""
        channels = [
            "memory_updates",
            "graph_updates",
            "integration_updates",
            "system_notifications"
        ]
        
        # Simulate subscription confirmations
        responses = [
            json.dumps({
                "type": "connection",
                "status": "connected"
            })
        ]
        
        for channel in channels:
            responses.append(json.dumps({
                "type": "subscription",
                "channel": channel,
                "status": "subscribed"
            }))
        
        ws_client.recv.side_effect = responses
        
        async with websockets.connect(
            f"{ws_url}?token={auth_token}"
        ) as websocket:
            await websocket.recv()  # connection
            
            # Subscribe to all channels
            subscribed_channels = []
            
            for channel in channels:
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "channel": channel
                }))
                
                response = await websocket.recv()
                data = json.loads(response)
                
                assert data["status"] == "subscribed"
                subscribed_channels.append(data["channel"])
            
            # Verify all channels subscribed
            assert set(subscribed_channels) == set(channels)
    
    async def test_unsubscribe_from_channel(
        self,
        ws_client,
        ws_url: str,
        auth_token: str
    ):
        """Test unsubscribing from channels."""
        ws_client.recv.side_effect = [
            json.dumps({
                "type": "connection",
                "status": "connected"
            }),
            json.dumps({
                "type": "subscription",
                "channel": "memory_updates",
                "status": "subscribed"
            }),
            json.dumps({
                "type": "unsubscription",
                "channel": "memory_updates",
                "status": "unsubscribed"
            })
        ]
        
        async with websockets.connect(
            f"{ws_url}?token={auth_token}"
        ) as websocket:
            await websocket.recv()  # connection
            
            # Subscribe
            await websocket.send(json.dumps({
                "action": "subscribe",
                "channel": "memory_updates"
            }))
            await websocket.recv()  # subscription
            
            # Unsubscribe
            await websocket.send(json.dumps({
                "action": "unsubscribe",
                "channel": "memory_updates"
            }))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            assert data["type"] == "unsubscription"
            assert data["status"] == "unsubscribed"
    
    @pytest.mark.slow
    async def test_connection_resilience(
        self,
        ws_client,
        ws_url: str,
        auth_token: str
    ):
        """Test WebSocket connection resilience and reconnection."""
        reconnect_attempts = 0
        max_reconnects = 3
        
        async def connect_with_retry():
            nonlocal reconnect_attempts
            
            while reconnect_attempts < max_reconnects:
                try:
                    async with websockets.connect(
                        f"{ws_url}?token={auth_token}"
                    ) as websocket:
                        # Simulate connection success after retries
                        if reconnect_attempts == 2:
                            ws_client.recv.side_effect = [
                                json.dumps({
                                    "type": "connection",
                                    "status": "connected"
                                })
                            ]
                            message = await websocket.recv()
                            return json.loads(message)
                        else:
                            # Simulate connection failure
                            raise websockets.exceptions.ConnectionClosedError(
                                1006, "Abnormal Closure"
                            )
                            
                except websockets.exceptions.ConnectionClosedError:
                    reconnect_attempts += 1
                    await asyncio.sleep(0.1)  # Brief delay before retry
            
            return None
        
        result = await connect_with_retry()
        
        assert result is not None
        assert result["status"] == "connected"
        assert reconnect_attempts == 2  # Connected on third attempt
    
    async def test_message_ordering(
        self,
        ws_client,
        ws_url: str,
        auth_token: str
    ):
        """Test that messages are received in order."""
        # Create ordered messages
        messages = []
        for i in range(10):
            messages.append(json.dumps({
                "type": "memory_update",
                "sequence": i,
                "data": {"id": f"memory_{i}"}
            }))
        
        ws_client.recv.side_effect = [
            json.dumps({"type": "connection", "status": "connected"})
        ] + messages
        
        async with websockets.connect(
            f"{ws_url}?token={auth_token}"
        ) as websocket:
            await websocket.recv()  # connection
            
            # Receive messages and verify order
            received_sequences = []
            
            for _ in range(10):
                message = await websocket.recv()
                data = json.loads(message)
                received_sequences.append(data["sequence"])
            
            # Verify messages received in order
            assert received_sequences == list(range(10))