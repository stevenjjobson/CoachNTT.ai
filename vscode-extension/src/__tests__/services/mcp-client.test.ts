import { MCPClient } from '../../services/mcp-client';
import { ConnectionManager } from '../../services/connection-manager';
import { MCPEventEmitter } from '../../events/mcp-events';
import { MockWebSocket, waitFor, createDeferred } from '../utils/test-helpers';
import * as vscode from 'vscode';

// Mock WebSocket globally
(global as any).WebSocket = MockWebSocket;

// Mock dependencies
jest.mock('../../services/connection-manager');

describe('MCPClient', () => {
  let mcpClient: MCPClient;
  let mockConnectionManager: jest.Mocked<ConnectionManager>;
  let mockSecrets: any;
  let mockWebSocket: MockWebSocket;

  beforeEach(() => {
    // Reset singleton
    (MCPClient as any).instance = null;
    
    // Setup mocks
    mockSecrets = {
      get: jest.fn().mockResolvedValue('mock-jwt-token'),
      store: jest.fn().mockResolvedValue(undefined),
      delete: jest.fn().mockResolvedValue(undefined)
    };
    
    (vscode as any).testContext.secrets = mockSecrets;
    
    // Mock connection manager
    mockConnectionManager = {
      connect: jest.fn(),
      disconnect: jest.fn(),
      reconnect: jest.fn(),
      send: jest.fn(),
      onConnected: jest.fn(),
      onDisconnected: jest.fn(),
      onMessage: jest.fn(),
      onError: jest.fn(),
      isConnected: jest.fn().mockReturnValue(false),
      getWebSocket: jest.fn()
    } as any;
    
    (ConnectionManager as jest.Mock).mockImplementation(() => mockConnectionManager);
    
    // Get instance
    mcpClient = MCPClient.getInstance();
    
    // Create mock WebSocket
    mockWebSocket = new MockWebSocket('ws://localhost:8000/ws');
    mockConnectionManager.getWebSocket.mockReturnValue(mockWebSocket);
  });

  afterEach(() => {
    mcpClient.dispose();
    jest.clearAllMocks();
  });

  describe('Singleton Pattern', () => {
    it('should return the same instance', () => {
      const instance1 = MCPClient.getInstance();
      const instance2 = MCPClient.getInstance();
      
      expect(instance1).toBe(instance2);
    });
  });

  describe('Connection Management', () => {
    it('should connect with authentication', async () => {
      mockConnectionManager.connect.mockImplementation(async () => {
        mockConnectionManager.isConnected.mockReturnValue(true);
        
        // Simulate connection success
        const onConnectedCallback = mockConnectionManager.onConnected.mock.calls[0][0];
        onConnectedCallback();
      });
      
      await mcpClient.connect();
      
      expect(mockConnectionManager.connect).toHaveBeenCalledWith(
        expect.stringContaining('ws://'),
        expect.objectContaining({
          Authorization: 'Bearer mock-jwt-token'
        })
      );
      expect(mcpClient.isConnected()).toBe(true);
    });

    it('should handle connection without stored token', async () => {
      mockSecrets.get.mockResolvedValue(undefined);
      
      // Mock input box for token
      (vscode.window.showInputBox as jest.Mock).mockResolvedValue('user-provided-token');
      
      mockConnectionManager.connect.mockImplementation(async () => {
        mockConnectionManager.isConnected.mockReturnValue(true);
        const onConnectedCallback = mockConnectionManager.onConnected.mock.calls[0][0];
        onConnectedCallback();
      });
      
      await mcpClient.connect();
      
      expect(vscode.window.showInputBox).toHaveBeenCalled();
      expect(mockSecrets.store).toHaveBeenCalledWith('authToken', 'user-provided-token');
      expect(mockConnectionManager.connect).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          Authorization: 'Bearer user-provided-token'
        })
      );
    });

    it('should handle connection cancellation', async () => {
      mockSecrets.get.mockResolvedValue(undefined);
      (vscode.window.showInputBox as jest.Mock).mockResolvedValue(undefined);
      
      await mcpClient.connect();
      
      expect(mockConnectionManager.connect).not.toHaveBeenCalled();
      expect(mcpClient.isConnected()).toBe(false);
    });

    it('should disconnect properly', async () => {
      mockConnectionManager.isConnected.mockReturnValue(true);
      
      await mcpClient.disconnect();
      
      expect(mockConnectionManager.disconnect).toHaveBeenCalled();
    });

    it('should handle reconnection', async () => {
      await mcpClient.reconnect();
      
      expect(mockConnectionManager.reconnect).toHaveBeenCalled();
    });
  });

  describe('Message Handling', () => {
    beforeEach(async () => {
      // Setup connected state
      mockConnectionManager.connect.mockImplementation(async () => {
        mockConnectionManager.isConnected.mockReturnValue(true);
        const onConnectedCallback = mockConnectionManager.onConnected.mock.calls[0][0];
        onConnectedCallback();
      });
      
      await mcpClient.connect();
    });

    it('should send messages with proper format', async () => {
      const testData = { test: 'data' };
      
      await mcpClient.send('test_message', testData);
      
      expect(mockConnectionManager.send).toHaveBeenCalledWith({
        type: 'test_message',
        data: testData,
        timestamp: expect.any(String)
      });
    });

    it('should handle incoming messages', async () => {
      const messageDeferred = createDeferred<any>();
      
      mcpClient.on('memory_created', (data) => {
        messageDeferred.resolve(data);
      });
      
      // Get the message handler
      const onMessageCallback = mockConnectionManager.onMessage.mock.calls[0][0];
      
      // Simulate incoming message
      const testMessage = {
        type: 'memory_created',
        data: { id: 'test-memory', content: 'Test content' }
      };
      
      onMessageCallback(testMessage);
      
      const receivedData = await messageDeferred.promise;
      expect(receivedData).toEqual(testMessage.data);
    });

    it('should handle channel-specific messages', async () => {
      const memoryUpdateDeferred = createDeferred<any>();
      const graphUpdateDeferred = createDeferred<any>();
      
      mcpClient.subscribe('memory_updates', (data) => {
        memoryUpdateDeferred.resolve(data);
      });
      
      mcpClient.subscribe('graph_updates', (data) => {
        graphUpdateDeferred.resolve(data);
      });
      
      const onMessageCallback = mockConnectionManager.onMessage.mock.calls[0][0];
      
      // Send to memory channel
      onMessageCallback({
        type: 'channel_message',
        channel: 'memory_updates',
        data: { update: 'memory' }
      });
      
      // Send to graph channel
      onMessageCallback({
        type: 'channel_message',
        channel: 'graph_updates',
        data: { update: 'graph' }
      });
      
      const memoryData = await memoryUpdateDeferred.promise;
      const graphData = await graphUpdateDeferred.promise;
      
      expect(memoryData).toEqual({ update: 'memory' });
      expect(graphData).toEqual({ update: 'graph' });
    });

    it('should handle subscription and unsubscription', () => {
      let messageCount = 0;
      const handler = () => messageCount++;
      
      const disposable = mcpClient.subscribe('test_channel', handler);
      
      const onMessageCallback = mockConnectionManager.onMessage.mock.calls[0][0];
      
      // Send message
      onMessageCallback({
        type: 'channel_message',
        channel: 'test_channel',
        data: {}
      });
      
      expect(messageCount).toBe(1);
      
      // Unsubscribe
      disposable.dispose();
      
      // Send another message
      onMessageCallback({
        type: 'channel_message',
        channel: 'test_channel',
        data: {}
      });
      
      expect(messageCount).toBe(1); // Should not increase
    });
  });

  describe('Tool Calls', () => {
    beforeEach(async () => {
      mockConnectionManager.connect.mockImplementation(async () => {
        mockConnectionManager.isConnected.mockReturnValue(true);
        const onConnectedCallback = mockConnectionManager.onConnected.mock.calls[0][0];
        onConnectedCallback();
      });
      
      await mcpClient.connect();
    });

    it('should make tool calls and return results', async () => {
      const toolResult = { result: 'success' };
      
      // Mock the response
      mockConnectionManager.send.mockImplementation(async (message: any) => {
        // Simulate server response
        setTimeout(() => {
          const onMessageCallback = mockConnectionManager.onMessage.mock.calls[0][0];
          onMessageCallback({
            type: 'tool_result',
            request_id: message.request_id,
            data: toolResult
          });
        }, 10);
      });
      
      const result = await mcpClient.callTool('test_tool', { param: 'value' });
      
      expect(result).toEqual(toolResult);
      expect(mockConnectionManager.send).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'tool_call',
          tool: 'test_tool',
          params: { param: 'value' },
          request_id: expect.any(String)
        })
      );
    });

    it('should timeout tool calls', async () => {
      // Don't send response
      mockConnectionManager.send.mockResolvedValue(undefined);
      
      await expect(
        mcpClient.callTool('test_tool', {}, 100) // 100ms timeout
      ).rejects.toThrow('Tool call timed out');
    });

    it('should handle tool call errors', async () => {
      mockConnectionManager.send.mockImplementation(async (message: any) => {
        setTimeout(() => {
          const onMessageCallback = mockConnectionManager.onMessage.mock.calls[0][0];
          onMessageCallback({
            type: 'tool_error',
            request_id: message.request_id,
            error: 'Tool execution failed'
          });
        }, 10);
      });
      
      await expect(
        mcpClient.callTool('failing_tool', {})
      ).rejects.toThrow('Tool execution failed');
    });
  });

  describe('Memory Operations', () => {
    beforeEach(async () => {
      mockConnectionManager.connect.mockImplementation(async () => {
        mockConnectionManager.isConnected.mockReturnValue(true);
        const onConnectedCallback = mockConnectionManager.onConnected.mock.calls[0][0];
        onConnectedCallback();
      });
      
      await mcpClient.connect();
      
      // Setup tool call responses
      mockConnectionManager.send.mockImplementation(async (message: any) => {
        if (message.type === 'tool_call') {
          setTimeout(() => {
            const onMessageCallback = mockConnectionManager.onMessage.mock.calls[0][0];
            onMessageCallback({
              type: 'tool_result',
              request_id: message.request_id,
              data: { success: true, memory: { id: 'test-id' } }
            });
          }, 10);
        }
      });
    });

    it('should create memory', async () => {
      const result = await mcpClient.createMemory({
        content: 'Test memory',
        intent: { type: 'learn' }
      });
      
      expect(result).toEqual({ success: true, memory: { id: 'test-id' } });
      expect(mockConnectionManager.send).toHaveBeenCalledWith(
        expect.objectContaining({
          tool: 'create_memory',
          params: expect.objectContaining({
            content: 'Test memory'
          })
        })
      );
    });

    it('should search memories', async () => {
      const searchResults = [{ id: '1', content: 'Result 1' }];
      
      mockConnectionManager.send.mockImplementation(async (message: any) => {
        if (message.tool === 'search_memories') {
          setTimeout(() => {
            const onMessageCallback = mockConnectionManager.onMessage.mock.calls[0][0];
            onMessageCallback({
              type: 'tool_result',
              request_id: message.request_id,
              data: searchResults
            });
          }, 10);
        }
      });
      
      const results = await mcpClient.searchMemories('test query');
      
      expect(results).toEqual(searchResults);
    });
  });

  describe('Audio Operations', () => {
    beforeEach(async () => {
      mockConnectionManager.connect.mockImplementation(async () => {
        mockConnectionManager.isConnected.mockReturnValue(true);
        const onConnectedCallback = mockConnectionManager.onConnected.mock.calls[0][0];
        onConnectedCallback();
      });
      
      await mcpClient.connect();
    });

    it('should synthesize audio', async () => {
      const audioResponse = {
        audio_data: 'base64-audio',
        format: 'wav',
        duration_ms: 1000
      };
      
      mockConnectionManager.send.mockImplementation(async (message: any) => {
        if (message.tool === 'synthesize_audio') {
          setTimeout(() => {
            const onMessageCallback = mockConnectionManager.onMessage.mock.calls[0][0];
            onMessageCallback({
              type: 'tool_result',
              request_id: message.request_id,
              data: audioResponse
            });
          }, 10);
        }
      });
      
      const result = await mcpClient.synthesizeAudio('Test text');
      
      expect(result).toEqual(audioResponse);
    });

    it('should transcribe audio', async () => {
      const transcription = {
        text: 'Transcribed text',
        confidence: 0.95
      };
      
      mockConnectionManager.send.mockImplementation(async (message: any) => {
        if (message.tool === 'transcribe_audio') {
          setTimeout(() => {
            const onMessageCallback = mockConnectionManager.onMessage.mock.calls[0][0];
            onMessageCallback({
              type: 'tool_result',
              request_id: message.request_id,
              data: transcription
            });
          }, 10);
        }
      });
      
      const audioBuffer = new ArrayBuffer(100);
      const result = await mcpClient.transcribeAudio(audioBuffer);
      
      expect(result).toEqual(transcription);
    });
  });

  describe('Error Handling', () => {
    it('should handle connection errors', async () => {
      const error = new Error('Connection failed');
      mockConnectionManager.connect.mockRejectedValue(error);
      
      await expect(mcpClient.connect()).rejects.toThrow('Connection failed');
    });

    it('should emit error events', async () => {
      const errorDeferred = createDeferred<Error>();
      
      mcpClient.on('error', (error) => {
        errorDeferred.resolve(error);
      });
      
      // Setup error handler
      mockConnectionManager.connect.mockImplementation(async () => {
        const onErrorCallback = mockConnectionManager.onError.mock.calls[0][0];
        onErrorCallback(new Error('Test error'));
      });
      
      await mcpClient.connect().catch(() => {});
      
      const receivedError = await errorDeferred.promise;
      expect(receivedError.message).toBe('Test error');
    });

    it('should handle malformed messages gracefully', async () => {
      mockConnectionManager.connect.mockImplementation(async () => {
        mockConnectionManager.isConnected.mockReturnValue(true);
        const onConnectedCallback = mockConnectionManager.onConnected.mock.calls[0][0];
        onConnectedCallback();
      });
      
      await mcpClient.connect();
      
      const onMessageCallback = mockConnectionManager.onMessage.mock.calls[0][0];
      
      // Should not throw
      expect(() => {
        onMessageCallback({ invalid: 'message' });
        onMessageCallback(null);
        onMessageCallback('string message');
      }).not.toThrow();
    });
  });

  describe('Lifecycle Events', () => {
    it('should emit connected event', async () => {
      const connectedDeferred = createDeferred<void>();
      
      mcpClient.on('connected', () => {
        connectedDeferred.resolve();
      });
      
      mockConnectionManager.connect.mockImplementation(async () => {
        mockConnectionManager.isConnected.mockReturnValue(true);
        const onConnectedCallback = mockConnectionManager.onConnected.mock.calls[0][0];
        onConnectedCallback();
      });
      
      await mcpClient.connect();
      
      await expect(connectedDeferred.promise).resolves.toBeUndefined();
    });

    it('should emit disconnected event', async () => {
      const disconnectedDeferred = createDeferred<void>();
      
      mcpClient.on('disconnected', () => {
        disconnectedDeferred.resolve();
      });
      
      mockConnectionManager.connect.mockImplementation(async () => {
        mockConnectionManager.isConnected.mockReturnValue(true);
        const onDisconnectedCallback = mockConnectionManager.onDisconnected.mock.calls[0][0];
        onDisconnectedCallback('Connection closed');
      });
      
      await mcpClient.connect();
      
      await expect(disconnectedDeferred.promise).resolves.toBeUndefined();
    });
  });

  describe('Disposal', () => {
    it('should clean up resources', async () => {
      await mcpClient.connect();
      
      mcpClient.dispose();
      
      expect(mockConnectionManager.disconnect).toHaveBeenCalled();
    });

    it('should remove all listeners', () => {
      let eventCount = 0;
      mcpClient.on('test_event', () => eventCount++);
      
      mcpClient.dispose();
      
      // Try to emit after disposal
      (mcpClient as any).eventEmitter.emit('test_event', {});
      
      expect(eventCount).toBe(0);
    });
  });
});