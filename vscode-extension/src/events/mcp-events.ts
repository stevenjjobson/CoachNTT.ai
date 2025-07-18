import { EventEmitter } from 'eventemitter3';
import { 
    MCPEventMap, 
    MCPMessage,
    MCPConnectionMessage,
    MCPMemoryUpdate,
    MCPGraphUpdate,
    MCPIntegrationUpdate,
    MCPUserNotification,
    MCPSystemNotification,
    isMCPConnectionMessage,
    isMCPMemoryUpdate,
    isMCPGraphUpdate,
    isMCPIntegrationUpdate,
    isMCPUserNotification,
    isMCPSystemNotification
} from '../types/mcp.types';
import { Logger } from '../utils/logger';

/**
 * MCP Event Emitter
 * 
 * Provides a typed event system for MCP communications with
 * automatic message routing and filtering.
 */
export class MCPEventEmitter extends EventEmitter<MCPEventMap> {
    private logger: Logger;
    private messageCount: number = 0;
    private eventStats: Map<string, number>;

    constructor() {
        super();
        this.logger = Logger.getInstance();
        this.eventStats = new Map();
        
        // Set up internal logging
        this.on('error', (error) => {
            this.logger.error('MCP Event Error', error);
        });
    }

    /**
     * Process an incoming MCP message and emit appropriate events
     */
    public processMessage(message: MCPMessage): void {
        this.messageCount++;
        this.updateStats(message.type);
        
        // Emit raw message event
        this.emit('message', message);
        
        // Route to specific event handlers
        this.routeMessage(message);
    }

    /**
     * Route message to specific event handlers based on type
     */
    private routeMessage(message: MCPMessage): void {
        try {
            // Connection messages
            if (isMCPConnectionMessage(message)) {
                this.emit('connected', message);
                return;
            }

            // Memory updates
            if (isMCPMemoryUpdate(message)) {
                this.emit('memory_update', message);
                return;
            }

            // Graph updates
            if (isMCPGraphUpdate(message)) {
                this.emit('graph_update', message);
                return;
            }

            // Integration updates
            if (isMCPIntegrationUpdate(message)) {
                this.emit('integration_update', message);
                return;
            }

            // User notifications
            if (isMCPUserNotification(message)) {
                this.emit('user_notification', message);
                return;
            }

            // System notifications
            if (isMCPSystemNotification(message)) {
                this.emit('system_notification', message);
                return;
            }

            // Handle subscription confirmations
            if (message.type === 'subscription_confirmed') {
                const channels = (message as any).channels || [];
                this.emit('subscribed', channels);
                return;
            }

            if (message.type === 'unsubscription_confirmed') {
                const channels = (message as any).channels || [];
                this.emit('unsubscribed', channels);
                return;
            }

            // Log unhandled message types
            this.logger.debug(`Unhandled MCP message type: ${message.type}`);
            
        } catch (error) {
            this.logger.error('Error routing MCP message', error);
            this.emit('error', error as Error);
        }
    }

    /**
     * Update event statistics
     */
    private updateStats(eventType: string): void {
        const count = this.eventStats.get(eventType) || 0;
        this.eventStats.set(eventType, count + 1);
    }

    /**
     * Get event statistics
     */
    public getStats(): {
        totalMessages: number;
        eventCounts: Record<string, number>;
        listeners: Record<string, number>;
    } {
        const eventCounts: Record<string, number> = {};
        this.eventStats.forEach((count, type) => {
            eventCounts[type] = count;
        });

        const listeners: Record<string, number> = {};
        for (const event of this.eventNames()) {
            listeners[event as string] = this.listenerCount(event);
        }

        return {
            totalMessages: this.messageCount,
            eventCounts,
            listeners
        };
    }

    /**
     * Reset statistics
     */
    public resetStats(): void {
        this.messageCount = 0;
        this.eventStats.clear();
    }

    /**
     * Subscribe to memory updates for a specific type
     */
    public onMemoryUpdate(
        memoryType: 'learning' | 'decision' | 'checkpoint' | 'all',
        callback: (update: MCPMemoryUpdate) => void
    ): () => void {
        const wrappedCallback = (update: MCPMemoryUpdate) => {
            if (memoryType === 'all' || update.data.memory_type === memoryType) {
                callback(update);
            }
        };

        this.on('memory_update', wrappedCallback);
        
        // Return unsubscribe function
        return () => {
            this.off('memory_update', wrappedCallback);
        };
    }

    /**
     * Subscribe to graph updates for specific actions
     */
    public onGraphUpdate(
        action: 'created' | 'updated' | 'deleted' | 'exported' | 'all',
        callback: (update: MCPGraphUpdate) => void
    ): () => void {
        const wrappedCallback = (update: MCPGraphUpdate) => {
            if (action === 'all' || update.data.action === action) {
                callback(update);
            }
        };

        this.on('graph_update', wrappedCallback);
        
        // Return unsubscribe function
        return () => {
            this.off('graph_update', wrappedCallback);
        };
    }

    /**
     * Subscribe to integration updates for specific types
     */
    public onIntegrationUpdate(
        integrationType: 'vault_sync' | 'docs_generation' | 'checkpoint' | 'all',
        callback: (update: MCPIntegrationUpdate) => void
    ): () => void {
        const wrappedCallback = (update: MCPIntegrationUpdate) => {
            if (integrationType === 'all' || update.data.integration_type === integrationType) {
                callback(update);
            }
        };

        this.on('integration_update', wrappedCallback);
        
        // Return unsubscribe function
        return () => {
            this.off('integration_update', wrappedCallback);
        };
    }

    /**
     * Subscribe to notifications with level filtering
     */
    public onNotification(
        level: 'info' | 'warning' | 'error' | 'success' | 'all',
        callback: (notification: MCPUserNotification | MCPSystemNotification) => void
    ): () => void {
        const userCallback = (notification: MCPUserNotification) => {
            if (level === 'all' || notification.data.level === level) {
                callback(notification);
            }
        };

        const systemCallback = (notification: MCPSystemNotification) => {
            if (level === 'all' || notification.data.level === level) {
                callback(notification);
            }
        };

        this.on('user_notification', userCallback);
        this.on('system_notification', systemCallback);
        
        // Return unsubscribe function
        return () => {
            this.off('user_notification', userCallback);
            this.off('system_notification', systemCallback);
        };
    }

    /**
     * Clean up all listeners
     */
    public dispose(): void {
        this.removeAllListeners();
        this.resetStats();
        this.logger.debug('MCP Event Emitter disposed');
    }
}