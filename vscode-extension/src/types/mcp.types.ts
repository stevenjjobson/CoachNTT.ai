/**
 * MCP (Model Context Protocol) type definitions
 * 
 * This module defines all types for MCP communication between
 * the VSCode extension and the backend WebSocket server.
 */

/**
 * Base message structure for all MCP communications
 */
export interface MCPMessage {
    type: string;
    data?: any;
    timestamp: string;
    broadcast_id?: string;
    error?: string;
    message?: string;
}

/**
 * Connection established message
 */
export interface MCPConnectionMessage extends MCPMessage {
    type: 'connection_established';
    connection_id: string;
    user_id: string;
    server_time: string;
}

/**
 * Subscription messages
 */
export interface MCPSubscriptionMessage extends MCPMessage {
    type: 'subscribe' | 'unsubscribe' | 'subscription_confirmed' | 'unsubscription_confirmed';
    channels: string[];
}

/**
 * Heartbeat messages
 */
export interface MCPHeartbeatMessage extends MCPMessage {
    type: 'heartbeat' | 'ping' | 'pong';
}

/**
 * Connection info message
 */
export interface MCPConnectionInfo extends MCPMessage {
    type: 'connection_info';
    data: {
        connection_id: string;
        user_id: string;
        connected_at: string;
        messages_sent: number;
        messages_received: number;
        last_activity: string;
        subscribed_channels: string[];
    };
}

/**
 * Memory update event
 */
export interface MCPMemoryUpdate extends MCPMessage {
    type: 'memory_update';
    data: {
        memory_id: string;
        memory_type: 'learning' | 'decision' | 'checkpoint';
        action: 'created' | 'updated' | 'deleted';
        timestamp: string;
    };
}

/**
 * Graph update event
 */
export interface MCPGraphUpdate extends MCPMessage {
    type: 'graph_update';
    data: {
        graph_id: string;
        action: 'created' | 'updated' | 'deleted' | 'exported';
        metadata?: Record<string, any>;
        timestamp: string;
    };
}

/**
 * Integration update event
 */
export interface MCPIntegrationUpdate extends MCPMessage {
    type: 'integration_update';
    data: {
        integration_type: 'vault_sync' | 'docs_generation' | 'checkpoint';
        status: 'started' | 'completed' | 'failed';
        details?: Record<string, any>;
        timestamp: string;
    };
}

/**
 * User notification
 */
export interface MCPUserNotification extends MCPMessage {
    type: 'user_notification';
    data: {
        title: string;
        message: string;
        level: 'info' | 'warning' | 'error' | 'success';
        timestamp: string;
        [key: string]: any;
    };
}

/**
 * System notification
 */
export interface MCPSystemNotification extends MCPMessage {
    type: 'system_notification';
    data: {
        title: string;
        message: string;
        level: 'info' | 'warning' | 'error' | 'critical';
        timestamp: string;
        [key: string]: any;
    };
}

/**
 * Error message
 */
export interface MCPErrorMessage extends MCPMessage {
    type: 'error';
    message: string;
    details?: any;
}

/**
 * Available channel types
 */
export type MCPChannel = 
    | 'memory_updates'
    | 'graph_updates'
    | 'integration_updates'
    | 'system_notifications'
    | `user_${string}_personal`;

/**
 * Connection state
 */
export interface MCPConnectionState {
    connected: boolean;
    connectionId?: string;
    userId?: string;
    channels: Set<MCPChannel>;
    lastActivity?: Date;
    reconnectAttempts: number;
    error?: Error;
}

/**
 * Connection options
 */
export interface MCPConnectionOptions {
    url: string;
    token?: string;
    autoReconnect?: boolean;
    reconnectInterval?: number;
    maxReconnectAttempts?: number;
    heartbeatInterval?: number;
    headers?: Record<string, string>;
}

/**
 * Event map for typed event emitter
 */
export interface MCPEventMap {
    // Connection events
    connected: (info: MCPConnectionMessage) => void;
    disconnected: (reason: string) => void;
    reconnecting: (attempt: number) => void;
    error: (error: Error) => void;
    
    // Message events
    memory_update: (update: MCPMemoryUpdate) => void;
    graph_update: (update: MCPGraphUpdate) => void;
    integration_update: (update: MCPIntegrationUpdate) => void;
    user_notification: (notification: MCPUserNotification) => void;
    system_notification: (notification: MCPSystemNotification) => void;
    
    // Channel events
    subscribed: (channels: string[]) => void;
    unsubscribed: (channels: string[]) => void;
    
    // Raw message event
    message: (message: MCPMessage) => void;
}

/**
 * Type guard functions
 */
export function isMCPConnectionMessage(msg: MCPMessage): msg is MCPConnectionMessage {
    return msg.type === 'connection_established';
}

export function isMCPMemoryUpdate(msg: MCPMessage): msg is MCPMemoryUpdate {
    return msg.type === 'memory_update';
}

export function isMCPGraphUpdate(msg: MCPMessage): msg is MCPGraphUpdate {
    return msg.type === 'graph_update';
}

export function isMCPIntegrationUpdate(msg: MCPMessage): msg is MCPIntegrationUpdate {
    return msg.type === 'integration_update';
}

export function isMCPUserNotification(msg: MCPMessage): msg is MCPUserNotification {
    return msg.type === 'user_notification';
}

export function isMCPSystemNotification(msg: MCPMessage): msg is MCPSystemNotification {
    return msg.type === 'system_notification';
}

export function isMCPError(msg: MCPMessage): msg is MCPErrorMessage {
    return msg.type === 'error';
}