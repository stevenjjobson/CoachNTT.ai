import * as assert from 'assert';
import * as sinon from 'sinon';
import * as vscode from 'vscode';
import { ConnectionManager } from '../../services/connection-manager';
import { MCPClient } from '../../services/mcp-client';
import { ConfigurationService } from '../../config/settings';

suite('Connection Manager Test Suite', () => {
    let sandbox: sinon.SinonSandbox;
    let mockContext: vscode.ExtensionContext;
    let mockSecrets: vscode.SecretStorage;
    let mockWorkspaceState: vscode.Memento;
    let showInformationMessageStub: sinon.SinonStub;
    let showErrorMessageStub: sinon.SinonStub;
    let showInputBoxStub: sinon.SinonStub;
    let executeCommandStub: sinon.SinonStub;

    setup(() => {
        sandbox = sinon.createSandbox();
        
        // Mock VSCode APIs
        showInformationMessageStub = sandbox.stub(vscode.window, 'showInformationMessage');
        showErrorMessageStub = sandbox.stub(vscode.window, 'showErrorMessage');
        showInputBoxStub = sandbox.stub(vscode.window, 'showInputBox');
        executeCommandStub = sandbox.stub(vscode.commands, 'executeCommand');
        
        // Mock secrets storage
        mockSecrets = {
            get: sandbox.stub().resolves(undefined),
            store: sandbox.stub().resolves(),
            delete: sandbox.stub().resolves(),
            onDidChange: new vscode.EventEmitter<vscode.SecretStorageChangeEvent>().event
        } as any;
        
        // Mock workspace state
        mockWorkspaceState = {
            get: sandbox.stub().returns(undefined),
            update: sandbox.stub().resolves(),
            keys: () => []
        } as any;
        
        // Mock extension context
        mockContext = {
            secrets: mockSecrets,
            workspaceState: mockWorkspaceState,
            subscriptions: [],
            extensionUri: vscode.Uri.file('/test'),
            extensionPath: '/test',
            globalState: mockWorkspaceState,
            storagePath: '/test/storage',
            globalStoragePath: '/test/global',
            logPath: '/test/logs',
            extensionMode: vscode.ExtensionMode.Test,
            asAbsolutePath: (path: string) => path
        } as any;
    });

    teardown(() => {
        sandbox.restore();
    });

    test('ConnectionManager singleton pattern', () => {
        const manager1 = ConnectionManager.getInstance();
        const manager2 = ConnectionManager.getInstance();
        assert.strictEqual(manager1, manager2, 'Should return same instance');
    });

    test('Initialize with auto-connect disabled', () => {
        const manager = ConnectionManager.getInstance();
        const configStub = sandbox.stub(ConfigurationService.prototype, 'getAutoConnect').returns(false);
        
        manager.initialize(mockContext);
        
        // Should not attempt to connect
        assert.ok(configStub.called, 'Should check auto-connect setting');
        assert.ok(showInformationMessageStub.notCalled, 'Should not show connection message');
    });

    test('Initialize with auto-connect and saved connection', async () => {
        const manager = ConnectionManager.getInstance();
        const configStub = sandbox.stub(ConfigurationService.prototype, 'getAutoConnect').returns(true);
        const connectStub = sandbox.stub(manager as any, 'connect').resolves();
        
        // Mock previous connection state
        (mockWorkspaceState.get as sinon.SinonStub).withArgs('mcp.connected').returns(true);
        
        manager.initialize(mockContext);
        
        // Give time for async operations
        await new Promise(resolve => setTimeout(resolve, 10));
        
        assert.ok(connectStub.called, 'Should attempt to restore connection');
    });

    test('Connect with token prompt', async () => {
        const manager = ConnectionManager.getInstance();
        const mcpClientStub = sandbox.stub(MCPClient.prototype, 'connect').resolves();
        const subscribeStub = sandbox.stub(MCPClient.prototype, 'subscribe').resolves();
        const getStateStub = sandbox.stub(MCPClient.prototype, 'getState').returns({
            connected: true,
            userId: 'test-user',
            channels: new Set(),
            reconnectAttempts: 0
        });
        
        // Setup token prompt
        showInputBoxStub.resolves('test-jwt-token');
        
        manager.initialize(mockContext);
        await manager.connect();
        
        // Verify token was saved
        assert.ok((mockSecrets.store as sinon.SinonStub).calledWith('coachntt.authToken', 'test-jwt-token'));
        
        // Verify connection was established
        assert.ok(mcpClientStub.calledWith('test-jwt-token'));
        
        // Verify UI updates
        assert.ok(executeCommandStub.calledWith('setContext', 'coachntt.connected', true));
        assert.ok(showInformationMessageStub.calledWith('Connected to CoachNTT backend'));
        
        // Verify default channels subscription
        assert.ok(subscribeStub.called);
    });

    test('Connect with saved token', async () => {
        const manager = ConnectionManager.getInstance();
        const mcpClientStub = sandbox.stub(MCPClient.prototype, 'connect').resolves();
        const getStateStub = sandbox.stub(MCPClient.prototype, 'getState').returns({
            connected: true,
            userId: 'test-user',
            channels: new Set(),
            reconnectAttempts: 0
        });
        
        // Mock saved token
        (mockSecrets.get as sinon.SinonStub).withArgs('coachntt.authToken').resolves('saved-token');
        
        manager.initialize(mockContext);
        await manager.connect();
        
        // Should not prompt for token
        assert.ok(showInputBoxStub.notCalled);
        
        // Should use saved token
        assert.ok(mcpClientStub.calledWith('saved-token'));
    });

    test('Connect with retry on failure', async () => {
        const manager = ConnectionManager.getInstance();
        let attempts = 0;
        
        // Fail first 2 attempts, succeed on 3rd
        const mcpClientStub = sandbox.stub(MCPClient.prototype, 'connect').callsFake(async () => {
            attempts++;
            if (attempts < 3) {
                throw new Error('Connection failed');
            }
        });
        
        const getStateStub = sandbox.stub(MCPClient.prototype, 'getState').returns({
            connected: true,
            userId: 'test-user',
            channels: new Set(),
            reconnectAttempts: 0
        });
        
        showInputBoxStub.resolves('test-token');
        
        manager.initialize(mockContext);
        await manager.connect();
        
        assert.strictEqual(attempts, 3, 'Should retry 3 times');
        assert.ok(showInformationMessageStub.calledWith('Connected to CoachNTT backend'));
    });

    test('Disconnect updates state correctly', async () => {
        const manager = ConnectionManager.getInstance();
        const mcpDisconnectStub = sandbox.stub(MCPClient.prototype, 'disconnect');
        
        manager.initialize(mockContext);
        await manager.disconnect();
        
        // Verify disconnection
        assert.ok(mcpDisconnectStub.called);
        
        // Verify state updates
        assert.ok((mockWorkspaceState.update as sinon.SinonStub).calledWith('mcp.connected', false));
        assert.ok(executeCommandStub.calledWith('setContext', 'coachntt.connected', false));
        
        // Verify UI update
        assert.ok(showInformationMessageStub.calledWith('Disconnected from CoachNTT backend'));
    });

    test('Handle notifications', async () => {
        const manager = ConnectionManager.getInstance();
        const eventEmitter = MCPClient.getInstance().getEventEmitter();
        
        manager.initialize(mockContext);
        
        // Emit different notification levels
        eventEmitter.emit('user_notification', {
            type: 'user_notification',
            timestamp: new Date().toISOString(),
            data: {
                title: 'Test Info',
                message: 'Info message',
                level: 'info',
                timestamp: new Date().toISOString()
            }
        });
        
        eventEmitter.emit('user_notification', {
            type: 'user_notification',
            timestamp: new Date().toISOString(),
            data: {
                title: 'Test Warning',
                message: 'Warning message',
                level: 'warning',
                timestamp: new Date().toISOString()
            }
        });
        
        eventEmitter.emit('user_notification', {
            type: 'user_notification',
            timestamp: new Date().toISOString(),
            data: {
                title: 'Test Error',
                message: 'Error message',
                level: 'error',
                timestamp: new Date().toISOString()
            }
        });
        
        // Verify notifications shown
        assert.ok(showInformationMessageStub.calledWith('Test Info: Info message'));
        assert.ok(vscode.window.showWarningMessage);
        assert.ok(showErrorMessageStub.calledWith('Test Error: Error message'));
    });

    test('Channel subscription management', async () => {
        const manager = ConnectionManager.getInstance();
        const subscribeStub = sandbox.stub(MCPClient.prototype, 'subscribe').resolves();
        const unsubscribeStub = sandbox.stub(MCPClient.prototype, 'unsubscribe').resolves();
        
        await manager.subscribe(['memory_updates', 'graph_updates']);
        assert.ok(subscribeStub.calledWith(['memory_updates', 'graph_updates']));
        
        await manager.unsubscribe(['memory_updates']);
        assert.ok(unsubscribeStub.calledWith(['memory_updates']));
    });

    test('State retrieval', () => {
        const manager = ConnectionManager.getInstance();
        const mockState = {
            connected: true,
            connectionId: 'test-123',
            userId: 'user-123',
            channels: new Set(['memory_updates']),
            reconnectAttempts: 0
        };
        
        sandbox.stub(MCPClient.prototype, 'getState').returns(mockState);
        
        const state = manager.getState();
        assert.deepStrictEqual(state, mockState);
    });
});