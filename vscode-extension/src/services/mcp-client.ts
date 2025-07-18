import * as vscode from 'vscode';
import { WebSocket } from 'ws';
import { 
    MCPConnectionOptions, 
    MCPConnectionState, 
    MCPMessage,
    MCPChannel,
    MCPSubscriptionMessage
} from '../types/mcp.types';
import { MCPEventEmitter } from '../events/mcp-events';
import { Logger } from '../utils/logger';
import { ConfigurationService } from '../config/settings';

/**
 * MCP WebSocket Client
 * 
 * Manages WebSocket communication with the backend MCP server
 * including authentication, message handling, and channel subscriptions.
 */
export class MCPClient {
    private static instance: MCPClient;
    
    private ws: WebSocket | null = null;
    private logger: Logger;
    private config: ConfigurationService;
    private eventEmitter: MCPEventEmitter;
    private state: MCPConnectionState;
    private options: MCPConnectionOptions;
    private heartbeatInterval: NodeJS.Timeout | null = null;
    private reconnectTimeout: NodeJS.Timeout | null = null;
    private messageQueue: MCPMessage[] = [];

    private constructor() {
        this.logger = Logger.getInstance();
        this.config = ConfigurationService.getInstance();
        this.eventEmitter = new MCPEventEmitter();
        
        this.state = {
            connected: false,
            channels: new Set(),
            reconnectAttempts: 0
        };

        // Initialize default options
        const connectionConfig = this.config.getConnectionConfig();
        this.options = {
            url: connectionConfig.websocketUrl.replace('/ws', '/ws/realtime'),
            autoReconnect: true,
            reconnectInterval: 1000,
            maxReconnectAttempts: 10,
            heartbeatInterval: 30000,
            headers: connectionConfig.headers
        };
    }

    /**
     * Get singleton instance
     */
    public static getInstance(): MCPClient {
        if (!MCPClient.instance) {
            MCPClient.instance = new MCPClient();
        }
        return MCPClient.instance;
    }

    /**
     * Connect to MCP server
     */
    public async connect(token?: string): Promise<void> {
        if (this.state.connected) {
            this.logger.info('Already connected to MCP server');
            return;
        }

        this.logger.info('Connecting to MCP server...');
        
        // Update token if provided
        if (token) {
            this.options.token = token;
        }

        // Get token from options or secure storage
        const authToken = this.options.token || await this.getStoredToken();
        if (!authToken) {
            throw new Error('No authentication token available');
        }

        return new Promise((resolve, reject) => {
            try {
                // Construct WebSocket URL with token
                const wsUrl = new URL(this.options.url);
                wsUrl.searchParams.set('token', authToken);

                // Create WebSocket connection
                this.ws = new WebSocket(wsUrl.toString(), {
                    headers: this.options.headers
                });

                // Set up event handlers
                this.setupEventHandlers(resolve, reject);

            } catch (error) {
                this.logger.error('Failed to create WebSocket connection', error);
                reject(error);
            }
        });
    }

    /**
     * Disconnect from MCP server
     */
    public disconnect(): void {
        this.logger.info('Disconnecting from MCP server');
        
        // Clear timers
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }

        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }

        // Close WebSocket
        if (this.ws) {
            this.ws.removeAllListeners();
            if (this.ws.readyState === WebSocket.OPEN) {
                this.ws.close(1000, 'Client disconnect');
            }
            this.ws = null;
        }

        // Update state
        this.state.connected = false;
        this.state.connectionId = undefined;
        this.state.userId = undefined;
        this.state.channels.clear();
        this.state.lastActivity = undefined;
        this.state.reconnectAttempts = 0;

        this.eventEmitter.emit('disconnected', 'Client disconnected');
    }

    /**
     * Subscribe to channels
     */
    public async subscribe(channels: MCPChannel[]): Promise<void> {
        if (!this.state.connected) {
            throw new Error('Not connected to MCP server');
        }

        const message: MCPSubscriptionMessage = {
            type: 'subscribe',
            channels: channels,
            timestamp: new Date().toISOString()
        };

        await this.send(message);
        
        // Update local state
        channels.forEach(channel => this.state.channels.add(channel));
    }

    /**
     * Unsubscribe from channels
     */
    public async unsubscribe(channels: MCPChannel[]): Promise<void> {
        if (!this.state.connected) {
            throw new Error('Not connected to MCP server');
        }

        const message: MCPSubscriptionMessage = {
            type: 'unsubscribe',
            channels: channels,
            timestamp: new Date().toISOString()
        };

        await this.send(message);
        
        // Update local state
        channels.forEach(channel => this.state.channels.delete(channel));
    }

    /**
     * Send a message to the server
     */
    public async send(message: MCPMessage): Promise<void> {
        if (!this.state.connected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            // Queue message if not connected
            this.messageQueue.push(message);
            throw new Error('WebSocket not connected');
        }

        try {
            const data = JSON.stringify(message);
            this.ws.send(data);
            this.state.lastActivity = new Date();
        } catch (error) {
            this.logger.error('Failed to send message', error);
            throw error;
        }
    }

    /**
     * Get current connection state
     */
    public getState(): Readonly<MCPConnectionState> {
        return { ...this.state, channels: new Set(this.state.channels) };
    }

    /**
     * Get event emitter for subscribing to events
     */
    public getEventEmitter(): MCPEventEmitter {
        return this.eventEmitter;
    }

    /**
     * Set up WebSocket event handlers
     */
    private setupEventHandlers(
        connectResolve: () => void,
        connectReject: (error: Error) => void
    ): void {
        if (!this.ws) return;

        let resolved = false;

        this.ws.on('open', () => {
            this.logger.info('WebSocket connection opened');
            this.state.connected = true;
            this.state.reconnectAttempts = 0;
            
            // Start heartbeat
            this.startHeartbeat();
            
            // Don't resolve yet - wait for connection_established message
        });

        this.ws.on('message', (data: Buffer) => {
            try {
                const message = JSON.parse(data.toString()) as MCPMessage;
                
                // Handle connection established
                if (message.type === 'connection_established') {
                    const connMsg = message as any;
                    this.state.connectionId = connMsg.connection_id;
                    this.state.userId = connMsg.user_id;
                    this.state.lastActivity = new Date();
                    
                    if (!resolved) {
                        resolved = true;
                        connectResolve();
                    }
                    
                    // Process queued messages
                    this.processQueuedMessages();
                }
                
                // Process all messages through event emitter
                this.eventEmitter.processMessage(message);
                
            } catch (error) {
                this.logger.error('Failed to parse WebSocket message', error);
            }
        });

        this.ws.on('close', (code: number, reason: Buffer) => {
            const reasonStr = reason.toString();
            this.logger.info(`WebSocket closed: ${code} - ${reasonStr}`);
            
            this.state.connected = false;
            this.stopHeartbeat();
            
            if (!resolved) {
                resolved = true;
                connectReject(new Error(`Connection closed: ${reasonStr}`));
            }
            
            this.eventEmitter.emit('disconnected', reasonStr);
            
            // Attempt reconnection if enabled
            if (this.options.autoReconnect && code !== 1000) {
                this.scheduleReconnect();
            }
        });

        this.ws.on('error', (error: Error) => {
            this.logger.error('WebSocket error', error);
            this.state.error = error;
            
            if (!resolved) {
                resolved = true;
                connectReject(error);
            }
            
            this.eventEmitter.emit('error', error);
        });

        this.ws.on('ping', () => {
            this.logger.debug('Received ping from server');
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.pong();
            }
        });
    }

    /**
     * Start heartbeat timer
     */
    private startHeartbeat(): void {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }

        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.send({
                    type: 'ping',
                    timestamp: new Date().toISOString()
                }).catch(error => {
                    this.logger.error('Heartbeat failed', error);
                });
            }
        }, this.options.heartbeatInterval || 30000);
    }

    /**
     * Stop heartbeat timer
     */
    private stopHeartbeat(): void {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Schedule reconnection attempt
     */
    private scheduleReconnect(): void {
        if (this.state.reconnectAttempts >= (this.options.maxReconnectAttempts || 10)) {
            this.logger.error('Max reconnection attempts reached');
            return;
        }

        const delay = this.calculateReconnectDelay();
        this.state.reconnectAttempts++;
        
        this.logger.info(`Scheduling reconnect attempt ${this.state.reconnectAttempts} in ${delay}ms`);
        this.eventEmitter.emit('reconnecting', this.state.reconnectAttempts);

        this.reconnectTimeout = setTimeout(() => {
            this.connect().catch(error => {
                this.logger.error('Reconnection failed', error);
            });
        }, delay);
    }

    /**
     * Calculate exponential backoff delay
     */
    private calculateReconnectDelay(): number {
        const baseDelay = this.options.reconnectInterval || 1000;
        const attempt = this.state.reconnectAttempts;
        const maxDelay = 30000; // 30 seconds max
        
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s, 30s...
        const delay = Math.min(baseDelay * Math.pow(2, attempt), maxDelay);
        
        // Add jitter (±10%)
        const jitter = delay * 0.1 * (Math.random() * 2 - 1);
        
        return Math.round(delay + jitter);
    }

    /**
     * Process queued messages
     */
    private processQueuedMessages(): void {
        if (this.messageQueue.length === 0) return;

        this.logger.info(`Processing ${this.messageQueue.length} queued messages`);
        
        const messages = [...this.messageQueue];
        this.messageQueue = [];
        
        messages.forEach(message => {
            this.send(message).catch(error => {
                this.logger.error('Failed to send queued message', error);
            });
        });
    }

    /**
     * Get stored authentication token
     */
    private async getStoredToken(): Promise<string | undefined> {
        try {
            const secrets = vscode.workspace.getConfiguration('coachntt').get<string>('authToken');
            return secrets;
        } catch (error) {
            this.logger.error('Failed to retrieve stored token', error);
            return undefined;
        }
    }

    /**
     * Update connection options
     */
    public updateOptions(options: Partial<MCPConnectionOptions>): void {
        this.options = { ...this.options, ...options };
        
        // Update URL from config if not specified
        if (!options.url) {
            const connectionConfig = this.config.getConnectionConfig();
            this.options.url = connectionConfig.websocketUrl.replace('/ws', '/ws/realtime');
        }
    }

    /**
     * Dispose the client
     */
    public dispose(): void {
        this.disconnect();
        this.eventEmitter.dispose();
        this.messageQueue = [];
    }
}