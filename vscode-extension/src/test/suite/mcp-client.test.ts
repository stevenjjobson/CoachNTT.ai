import * as assert from 'assert';
import * as sinon from 'sinon';
import { WebSocket } from 'ws';
import { MCPClient } from '../../services/mcp-client';
import { MCPEventEmitter } from '../../events/mcp-events';
import { 
    MCPConnectionMessage, 
    MCPMemoryUpdate,
    MCPMessage 
} from '../../types/mcp.types';

// Mock WebSocket for testing
class MockWebSocket {
    public readyState: number = WebSocket.CONNECTING;
    public listeners: Map<string, Function[]> = new Map();
    
    constructor(public url: string, public options?: any) {
        // Simulate connection after a delay
        setTimeout(() => {
            this.readyState = WebSocket.OPEN;
            this.emit('open');
            
            // Send connection established message
            const connectionMsg: MCPConnectionMessage = {
                type: 'connection_established',
                connection_id: 'test-conn-123',
                user_id: 'test-user',
                server_time: new Date().toISOString(),
                timestamp: new Date().toISOString(),
                message: 'Connected'
            };
            this.emit('message', Buffer.from(JSON.stringify(connectionMsg)));
        }, 10);
    }
    
    on(event: string, handler: Function): void {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event)!.push(handler);
    }
    
    emit(event: string, ...args: any[]): void {
        const handlers = this.listeners.get(event) || [];
        handlers.forEach(handler => handler(...args));
    }
    
    send(data: string): void {
        // Simulate echo or response
        const message = JSON.parse(data);
        if (message.type === 'subscribe') {
            setTimeout(() => {
                this.emit('message', Buffer.from(JSON.stringify({
                    type: 'subscription_confirmed',
                    channels: message.channels,
                    timestamp: new Date().toISOString()
                })));
            }, 5);
        }
    }
    
    close(code?: number, reason?: string): void {
        this.readyState = WebSocket.CLOSED;
        this.emit('close', code || 1000, Buffer.from(reason || 'Normal closure'));
    }
    
    removeAllListeners(): void {
        this.listeners.clear();
    }
    
    pong(): void {
        // Mock pong
    }
}

suite('MCP Client Test Suite', () => {
    let sandbox: sinon.SinonSandbox;
    let originalWebSocket: any;

    setup(() => {
        sandbox = sinon.createSandbox();
        
        // Replace WebSocket with mock
        originalWebSocket = (global as any).WebSocket;
        (global as any).WebSocket = MockWebSocket;
    });

    teardown(() => {
        sandbox.restore();
        (global as any).WebSocket = originalWebSocket;
    });

    test('MCPClient singleton pattern', () => {
        const client1 = MCPClient.getInstance();
        const client2 = MCPClient.getInstance();
        assert.strictEqual(client1, client2, 'Should return same instance');
    });

    test('Connect to MCP server', async () => {
        const client = MCPClient.getInstance();
        
        await client.connect('test-token');
        
        const state = client.getState();
        assert.strictEqual(state.connected, true, 'Should be connected');
        assert.strictEqual(state.userId, 'test-user', 'Should have user ID');
        assert.ok(state.connectionId, 'Should have connection ID');
        
        client.disconnect();
    });

    test('Handle connection failure', async () => {
        const client = MCPClient.getInstance();
        
        // Override WebSocket to simulate failure
        (global as any).WebSocket = class FailingWebSocket extends MockWebSocket {
            constructor(url: string, options?: any) {
                super(url, options);
                setTimeout(() => {
                    this.emit('error', new Error('Connection failed'));
                    this.emit('close', 1006, Buffer.from('Abnormal closure'));
                }, 5);
            }
        };
        
        try {
            await client.connect('test-token');
            assert.fail('Should have thrown error');
        } catch (error) {
            assert.ok(error, 'Should throw error on connection failure');
        }
        
        const state = client.getState();
        assert.strictEqual(state.connected, false, 'Should not be connected');
    });

    test('Subscribe to channels', async () => {
        const client = MCPClient.getInstance();
        
        await client.connect('test-token');
        await client.subscribe(['memory_updates', 'graph_updates']);
        
        const state = client.getState();
        assert.strictEqual(state.channels.size, 2, 'Should have 2 channels');
        assert.ok(state.channels.has('memory_updates'), 'Should have memory_updates channel');
        assert.ok(state.channels.has('graph_updates'), 'Should have graph_updates channel');
        
        client.disconnect();
    });

    test('Event emitter processes messages', async () => {
        const client = MCPClient.getInstance();
        const eventEmitter = client.getEventEmitter();
        
        let memoryUpdateReceived = false;
        eventEmitter.on('memory_update', (update) => {
            memoryUpdateReceived = true;
            assert.strictEqual(update.data.memory_id, 'test-memory-123');
            assert.strictEqual(update.data.action, 'created');
        });
        
        await client.connect('test-token');
        
        // Simulate memory update message
        const memoryUpdate: MCPMemoryUpdate = {
            type: 'memory_update',
            timestamp: new Date().toISOString(),
            data: {
                memory_id: 'test-memory-123',
                memory_type: 'learning',
                action: 'created',
                timestamp: new Date().toISOString()
            }
        };
        
        const ws = (client as any).ws as MockWebSocket;
        ws.emit('message', Buffer.from(JSON.stringify(memoryUpdate)));
        
        // Give time for async processing
        await new Promise(resolve => setTimeout(resolve, 10));
        
        assert.ok(memoryUpdateReceived, 'Should receive memory update event');
        
        client.disconnect();
    });

    test('Heartbeat mechanism', async () => {
        const client = MCPClient.getInstance();
        client.updateOptions({ heartbeatInterval: 50 }); // Fast heartbeat for testing
        
        await client.connect('test-token');
        
        const ws = (client as any).ws as MockWebSocket;
        let pingReceived = false;
        
        // Override send to detect ping
        const originalSend = ws.send.bind(ws);
        ws.send = (data: string) => {
            const message = JSON.parse(data);
            if (message.type === 'ping') {
                pingReceived = true;
            }
            originalSend(data);
        };
        
        // Wait for heartbeat
        await new Promise(resolve => setTimeout(resolve, 100));
        
        assert.ok(pingReceived, 'Should send heartbeat ping');
        
        client.disconnect();
    });

    test('Reconnection with exponential backoff', async () => {
        const client = MCPClient.getInstance();
        client.updateOptions({ 
            autoReconnect: true, 
            reconnectInterval: 10,
            maxReconnectAttempts: 3 
        });
        
        let reconnectAttempts = 0;
        const eventEmitter = client.getEventEmitter();
        
        eventEmitter.on('reconnecting', (attempt) => {
            reconnectAttempts = attempt;
        });
        
        // Connect successfully first
        await client.connect('test-token');
        
        // Simulate unexpected disconnect
        const ws = (client as any).ws as MockWebSocket;
        ws.emit('close', 1006, Buffer.from('Abnormal closure'));
        
        // Wait for reconnection attempts
        await new Promise(resolve => setTimeout(resolve, 100));
        
        assert.ok(reconnectAttempts > 0, 'Should attempt reconnection');
        
        client.disconnect();
    });

    test('Message queueing when disconnected', async () => {
        const client = MCPClient.getInstance();
        
        // Try to send without connection
        try {
            await client.send({ type: 'test', timestamp: new Date().toISOString() });
            assert.fail('Should throw error');
        } catch (error: any) {
            assert.strictEqual(error.message, 'WebSocket not connected');
        }
        
        // Check message was queued
        const queue = (client as any).messageQueue;
        assert.strictEqual(queue.length, 1, 'Should queue message');
        
        // Connect and verify queue is processed
        await client.connect('test-token');
        
        // Give time for queue processing
        await new Promise(resolve => setTimeout(resolve, 20));
        
        assert.strictEqual(queue.length, 0, 'Should process queued messages');
        
        client.disconnect();
    });
});