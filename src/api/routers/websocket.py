"""
WebSocket API endpoints.

This module provides WebSocket endpoints for real-time memory and graph updates
with safety-first design and JWT authentication.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from ..dependencies import verify_websocket_token
from ...core.memory.models import MemoryType

logger = logging.getLogger(__name__)

router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections with authentication and broadcasting."""
    
    def __init__(self):
        # Active connections: {connection_id: WebSocketConnection}
        self.active_connections: Dict[str, "WebSocketConnection"] = {}
        # User subscriptions: {user_id: set of connection_ids}
        self.user_connections: Dict[str, Set[str]] = {}
        # Channel subscriptions: {channel: set of connection_ids}
        self.channel_subscriptions: Dict[str, Set[str]] = {}
        
        # Statistics
        self.total_connections = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0
        
    async def connect(self, websocket: WebSocket, user_data: Dict[str, Any]) -> str:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        connection_id = str(uuid4())
        user_id = user_data.get("sub", "anonymous")
        
        # Create connection object
        connection = WebSocketConnection(
            connection_id=connection_id,
            websocket=websocket,
            user_id=user_id,
            user_data=user_data,
            connected_at=datetime.now()
        )
        
        # Store connection
        self.active_connections[connection_id] = connection
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        self.total_connections += 1
        
        logger.info(f"WebSocket connection established: {connection_id} for user {user_id}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "user_id": user_id,
            "server_time": datetime.now().isoformat(),
            "message": "WebSocket connection established successfully"
        }, connection_id)
        
        return connection_id
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            user_id = connection.user_id
            
            # Remove from active connections
            del self.active_connections[connection_id]
            
            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove from channel subscriptions
            for channel, subscribers in self.channel_subscriptions.items():
                subscribers.discard(connection_id)
            
            logger.info(f"WebSocket connection disconnected: {connection_id} for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            try:
                await connection.websocket.send_text(json.dumps(message))
                self.total_messages_sent += 1
                connection.messages_sent += 1
            except (ConnectionClosedOK, ConnectionClosedError):
                logger.warning(f"Connection {connection_id} already closed")
                self.disconnect(connection_id)
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Send a message to all connections for a specific user."""
        if user_id in self.user_connections:
            connection_ids = self.user_connections[user_id].copy()
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_channel(self, message: Dict[str, Any], channel: str):
        """Broadcast a message to all subscribers of a channel."""
        if channel in self.channel_subscriptions:
            connection_ids = self.channel_subscriptions[channel].copy()
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast a message to all active connections."""
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_personal_message(message, connection_id)
    
    def subscribe_to_channel(self, connection_id: str, channel: str):
        """Subscribe a connection to a channel."""
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()
        
        self.channel_subscriptions[channel].add(connection_id)
        
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            connection.subscribed_channels.add(channel)
            
        logger.debug(f"Connection {connection_id} subscribed to channel {channel}")
    
    def unsubscribe_from_channel(self, connection_id: str, channel: str):
        """Unsubscribe a connection from a channel."""
        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].discard(connection_id)
            
            if not self.channel_subscriptions[channel]:
                del self.channel_subscriptions[channel]
        
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            connection.subscribed_channels.discard(channel)
            
        logger.debug(f"Connection {connection_id} unsubscribed from channel {channel}")
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific connection."""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            return {
                "connection_id": connection_id,
                "user_id": connection.user_id,
                "connected_at": connection.connected_at.isoformat(),
                "messages_sent": connection.messages_sent,
                "messages_received": connection.messages_received,
                "last_activity": connection.last_activity.isoformat(),
                "subscribed_channels": list(connection.subscribed_channels)
            }
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics."""
        return {
            "active_connections": len(self.active_connections),
            "total_connections": self.total_connections,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "active_users": len(self.user_connections),
            "active_channels": len(self.channel_subscriptions),
            "channels": {
                channel: len(subscribers) 
                for channel, subscribers in self.channel_subscriptions.items()
            }
        }


class WebSocketConnection:
    """Represents a single WebSocket connection."""
    
    def __init__(
        self,
        connection_id: str,
        websocket: WebSocket,
        user_id: str,
        user_data: Dict[str, Any],
        connected_at: datetime
    ):
        self.connection_id = connection_id
        self.websocket = websocket
        self.user_id = user_id
        self.user_data = user_data
        self.connected_at = connected_at
        self.last_activity = connected_at
        self.messages_sent = 0
        self.messages_received = 0
        self.subscribed_channels: Set[str] = set()


# Global connection manager
connection_manager = ConnectionManager()


@router.websocket("/realtime")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None
):
    """WebSocket endpoint for real-time updates."""
    connection_id = None
    
    try:
        # Authenticate the connection
        user_data = await verify_websocket_token(websocket, token)
        if not user_data:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            return
        
        # Connect to the manager
        connection_id = await connection_manager.connect(websocket, user_data)
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(connection_id, websocket)
        )
        
        # Message handling loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                connection_manager.total_messages_received += 1
                
                if connection_id in connection_manager.active_connections:
                    connection = connection_manager.active_connections[connection_id]
                    connection.messages_received += 1
                    connection.last_activity = datetime.now()
                
                # Process the message
                await _process_message(connection_id, data, user_data)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {connection_id}")
                break
            except (ConnectionClosedOK, ConnectionClosedError):
                logger.info(f"WebSocket connection closed: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket message loop for {connection_id}: {e}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": datetime.now().isoformat()
                }, connection_id)
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        
    finally:
        # Clean up
        if connection_id:
            connection_manager.disconnect(connection_id)
        
        # Cancel heartbeat task
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()


async def _process_message(connection_id: str, data: str, user_data: Dict[str, Any]):
    """Process incoming WebSocket message."""
    try:
        message = json.loads(data)
        message_type = message.get("type")
        
        if message_type == "subscribe":
            # Subscribe to channels
            channels = message.get("channels", [])
            for channel in channels:
                if _is_valid_channel(channel, user_data):
                    connection_manager.subscribe_to_channel(connection_id, channel)
            
            await connection_manager.send_personal_message({
                "type": "subscription_confirmed",
                "channels": channels,
                "timestamp": datetime.now().isoformat()
            }, connection_id)
            
        elif message_type == "unsubscribe":
            # Unsubscribe from channels
            channels = message.get("channels", [])
            for channel in channels:
                connection_manager.unsubscribe_from_channel(connection_id, channel)
            
            await connection_manager.send_personal_message({
                "type": "unsubscription_confirmed",
                "channels": channels,
                "timestamp": datetime.now().isoformat()
            }, connection_id)
            
        elif message_type == "ping":
            # Respond to ping
            await connection_manager.send_personal_message({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }, connection_id)
            
        elif message_type == "get_info":
            # Send connection info
            info = connection_manager.get_connection_info(connection_id)
            await connection_manager.send_personal_message({
                "type": "connection_info",
                "data": info,
                "timestamp": datetime.now().isoformat()
            }, connection_id)
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await connection_manager.send_personal_message({
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": datetime.now().isoformat()
            }, connection_id)
            
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON received from {connection_id}")
        await connection_manager.send_personal_message({
            "type": "error",
            "message": "Invalid JSON format",
            "timestamp": datetime.now().isoformat()
        }, connection_id)
    except Exception as e:
        logger.error(f"Error processing message from {connection_id}: {e}")
        await connection_manager.send_personal_message({
            "type": "error",
            "message": "Error processing message",
            "timestamp": datetime.now().isoformat()
        }, connection_id)


def _is_valid_channel(channel: str, user_data: Dict[str, Any]) -> bool:
    """Validate if user can subscribe to a channel."""
    user_id = user_data.get("sub", "")
    
    # Define allowed channels
    allowed_channels = [
        "memory_updates",
        "graph_updates",
        "integration_updates",
        f"user_{user_id}_personal",  # Personal channel for user
        "system_notifications"
    ]
    
    return channel in allowed_channels


async def _heartbeat_loop(connection_id: str, websocket: WebSocket):
    """Send periodic heartbeat messages."""
    try:
        while True:
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            
            if connection_id in connection_manager.active_connections:
                await connection_manager.send_personal_message({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }, connection_id)
            else:
                break
                
    except asyncio.CancelledError:
        logger.debug(f"Heartbeat cancelled for {connection_id}")
    except Exception as e:
        logger.error(f"Heartbeat error for {connection_id}: {e}")


# API endpoints for WebSocket management
@router.get("/connections")
async def get_connections(
    user_data: Dict[str, Any] = Depends(verify_websocket_token)
) -> Dict[str, Any]:
    """Get information about WebSocket connections."""
    return connection_manager.get_stats()


@router.post("/broadcast")
async def broadcast_message(
    message: Dict[str, Any],
    channel: Optional[str] = None,
    user_data: Dict[str, Any] = Depends(verify_websocket_token)
) -> Dict[str, str]:
    """Broadcast a message to WebSocket connections."""
    try:
        # Add metadata to message
        broadcast_message = {
            **message,
            "timestamp": datetime.now().isoformat(),
            "broadcast_id": str(uuid4())
        }
        
        if channel:
            await connection_manager.broadcast_to_channel(broadcast_message, channel)
            target = f"channel '{channel}'"
        else:
            await connection_manager.broadcast_to_all(broadcast_message)
            target = "all connections"
        
        logger.info(f"Broadcast message sent to {target}")
        
        return {
            "message": f"Message broadcast to {target}",
            "broadcast_id": broadcast_message["broadcast_id"]
        }
        
    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast message"
        )


# Event broadcasting functions for other modules to use
async def broadcast_memory_update(memory_id: UUID, memory_type: MemoryType, action: str):
    """Broadcast a memory update event."""
    message = {
        "type": "memory_update",
        "data": {
            "memory_id": str(memory_id),
            "memory_type": memory_type.value,
            "action": action,  # "created", "updated", "deleted"
            "timestamp": datetime.now().isoformat()
        }
    }
    
    await connection_manager.broadcast_to_channel(message, "memory_updates")
    logger.debug(f"Broadcast memory {action}: {memory_id}")


async def broadcast_graph_update(graph_id: UUID, action: str, metadata: Optional[Dict[str, Any]] = None):
    """Broadcast a graph update event."""
    message = {
        "type": "graph_update",
        "data": {
            "graph_id": str(graph_id),
            "action": action,  # "created", "updated", "deleted", "exported"
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
    }
    
    await connection_manager.broadcast_to_channel(message, "graph_updates")
    logger.debug(f"Broadcast graph {action}: {graph_id}")


async def broadcast_integration_update(integration_type: str, status: str, details: Optional[Dict[str, Any]] = None):
    """Broadcast an integration update event."""
    message = {
        "type": "integration_update",
        "data": {
            "integration_type": integration_type,  # "vault_sync", "docs_generation", etc.
            "status": status,  # "started", "completed", "failed"
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
    }
    
    await connection_manager.broadcast_to_channel(message, "integration_updates")
    logger.debug(f"Broadcast integration {integration_type} {status}")


async def send_user_notification(user_id: str, notification: Dict[str, Any]):
    """Send a personal notification to a specific user."""
    message = {
        "type": "user_notification",
        "data": {
            **notification,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    await connection_manager.send_to_user(message, user_id)
    logger.debug(f"Sent notification to user {user_id}")


async def broadcast_system_notification(notification: Dict[str, Any]):
    """Broadcast a system-wide notification."""
    message = {
        "type": "system_notification",
        "data": {
            **notification,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    await connection_manager.broadcast_to_channel(message, "system_notifications")
    logger.info("Broadcast system notification")


# Helper function to get connection manager instance
def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return connection_manager