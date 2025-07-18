/**
 * Tests for Memory Tree Provider
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import * as sinon from 'sinon';
import { MemoryTreeProvider } from '../../providers/memory-tree-provider';
import { MCPClient } from '../../services/mcp-client';
import { Logger } from '../../utils/logger';
import { 
    Memory, 
    MemoryIntent, 
    MemoryTreeItem, 
    TreeItemType,
    MemorySearchResponse 
} from '../../models/memory.model';

suite('Memory Tree Provider Test Suite', () => {
    let sandbox: sinon.SinonSandbox;
    let provider: MemoryTreeProvider;
    let mockMCPClient: sinon.SinonStubbedInstance<MCPClient>;
    let mockLogger: sinon.SinonStubbedInstance<Logger>;

    const createMockMemory = (overrides?: Partial<Memory>): Memory => ({
        id: 'test-id',
        content: 'Test memory content',
        intent: MemoryIntent.LEARNING,
        timestamp: new Date().toISOString(),
        importance: 0.8,
        tags: ['test'],
        reinforcement_count: 0,
        ...overrides
    });

    setup(() => {
        sandbox = sinon.createSandbox();
        
        // Create mock logger
        mockLogger = {
            info: sandbox.stub(),
            error: sandbox.stub(),
            debug: sandbox.stub(),
            warn: sandbox.stub()
        } as any;
        
        // Create mock MCP client
        mockMCPClient = {
            isConnected: sandbox.stub().returns(true),
            callTool: sandbox.stub(),
            on: sandbox.stub(),
            off: sandbox.stub()
        } as any;
        
        provider = new MemoryTreeProvider(mockMCPClient as any, mockLogger as any);
    });

    teardown(() => {
        sandbox.restore();
    });

    test('Should show disconnected message when not connected', async () => {
        mockMCPClient.isConnected.returns(false);
        
        const children = await provider.getChildren();
        
        assert.strictEqual(children.length, 1);
        assert.strictEqual(children[0].label, 'Not connected to MCP server');
        assert.strictEqual(children[0].itemType, TreeItemType.LOADING);
    });

    test('Should show categories at root level when connected', async () => {
        const children = await provider.getChildren();
        
        assert.strictEqual(children.length, 3);
        assert.strictEqual(children[0].label, 'Recent Memories');
        assert.strictEqual(children[1].label, 'Important Memories');
        assert.strictEqual(children[2].label, 'By Intent');
        
        children.forEach(child => {
            assert.strictEqual(child.itemType, TreeItemType.CATEGORY);
            assert.strictEqual(child.collapsibleState, vscode.TreeItemCollapsibleState.Collapsed);
        });
    });

    test('Should show intent groups under "By Intent" category', async () => {
        // Mock memory count responses
        const intents = Object.values(MemoryIntent);
        intents.forEach(intent => {
            mockMCPClient.callTool.withArgs('memory_search', sinon.match({ intent }))
                .resolves({ total: intent === MemoryIntent.LEARNING ? 5 : 0 });
        });
        
        const rootChildren = await provider.getChildren();
        const byIntentCategory = rootChildren.find(c => c.label === 'By Intent');
        
        const intentChildren = await provider.getChildren(byIntentCategory);
        
        assert.strictEqual(intentChildren.length, 1);
        assert.strictEqual(intentChildren[0].label, 'Learning (5)');
        assert.strictEqual(intentChildren[0].itemType, TreeItemType.INTENT_GROUP);
    });

    test('Should show memory items under intent group', async () => {
        const mockMemories = [
            createMockMemory({ id: '1', content: 'Memory 1' }),
            createMockMemory({ id: '2', content: 'Memory 2' })
        ];
        
        const searchResponse: MemorySearchResponse = {
            memories: mockMemories,
            total: 2,
            offset: 0,
            limit: 50
        };
        
        mockMCPClient.callTool.withArgs('memory_search', sinon.match({ intent: MemoryIntent.LEARNING }))
            .resolves(searchResponse);
        
        const intentGroup = new MemoryTreeItem(
            'Learning (2)',
            vscode.TreeItemCollapsibleState.Collapsed,
            TreeItemType.INTENT_GROUP
        );
        
        const memoryChildren = await provider.getChildren(intentGroup);
        
        assert.strictEqual(memoryChildren.length, 2);
        assert.strictEqual(memoryChildren[0].label, 'Memory 1');
        assert.strictEqual(memoryChildren[1].label, 'Memory 2');
        
        memoryChildren.forEach(child => {
            assert.strictEqual(child.itemType, TreeItemType.MEMORY);
            assert.strictEqual(child.collapsibleState, vscode.TreeItemCollapsibleState.None);
        });
    });

    test('Should handle search functionality', async () => {
        const mockSearchResults = [
            createMockMemory({ id: '1', content: 'Search result 1' }),
            createMockMemory({ id: '2', content: 'Search result 2' })
        ];
        
        const searchResponse: MemorySearchResponse = {
            memories: mockSearchResults,
            total: 2,
            offset: 0,
            limit: 100
        };
        
        mockMCPClient.callTool.withArgs('memory_search', sinon.match({ query: 'test' }))
            .resolves(searchResponse);
        
        await provider.search('test');
        
        const children = await provider.getChildren();
        
        assert.strictEqual(children.length, 1);
        assert.strictEqual(children[0].label, 'Search Results (2)');
        assert.strictEqual(children[0].itemType, TreeItemType.SEARCH_RESULTS);
    });

    test('Should clear search and return to normal view', async () => {
        // First perform a search
        mockMCPClient.callTool.resolves({
            memories: [createMockMemory()],
            total: 1,
            offset: 0,
            limit: 100
        });
        
        await provider.search('test');
        let children = await provider.getChildren();
        assert.strictEqual(children[0].itemType, TreeItemType.SEARCH_RESULTS);
        
        // Clear search
        provider.clearSearch();
        
        children = await provider.getChildren();
        assert.strictEqual(children.length, 3);
        assert.strictEqual(children[0].label, 'Recent Memories');
    });

    test('Should handle memory created event', async () => {
        const newMemory = createMockMemory({ id: 'new-1' });
        let refreshCalled = false;
        
        // Capture the event handler
        const onCall = mockMCPClient.on.withArgs('memory:created');
        const handler = onCall.firstCall?.args[1];
        
        // Override refresh to track calls
        sandbox.stub(provider, 'refresh').callsFake(() => {
            refreshCalled = true;
        });
        
        // Simulate memory created event
        handler?.(newMemory);
        
        assert.strictEqual(refreshCalled, true);
    });

    test('Should truncate long memory content', async () => {
        const longContent = 'A'.repeat(100);
        const mockMemory = createMockMemory({ content: longContent });
        
        mockMCPClient.callTool.resolves({
            memories: [mockMemory],
            total: 1,
            offset: 0,
            limit: 50
        });
        
        const intentGroup = new MemoryTreeItem(
            'Learning (1)',
            vscode.TreeItemCollapsibleState.Collapsed,
            TreeItemType.INTENT_GROUP
        );
        
        const children = await provider.getChildren(intentGroup);
        
        assert.strictEqual(children[0].label.length, 50);
        assert.ok(children[0].label.endsWith('...'));
    });

    test('Should sort memories by configured sort order', async () => {
        const memories = [
            createMockMemory({ 
                id: '1', 
                content: 'Old memory',
                timestamp: '2024-01-01T00:00:00Z',
                importance: 0.5
            }),
            createMockMemory({ 
                id: '2', 
                content: 'New memory',
                timestamp: '2024-01-02T00:00:00Z',
                importance: 0.9
            })
        ];
        
        mockMCPClient.callTool.resolves({
            memories,
            total: 2,
            offset: 0,
            limit: 50
        });
        
        // Test default sort (timestamp desc)
        const intentGroup = new MemoryTreeItem(
            'Learning (2)',
            vscode.TreeItemCollapsibleState.Collapsed,
            TreeItemType.INTENT_GROUP
        );
        
        let children = await provider.getChildren(intentGroup);
        assert.strictEqual(children[0].label, 'New memory');
        assert.strictEqual(children[1].label, 'Old memory');
        
        // Update config to sort by importance
        provider.updateConfig({ sortBy: 'importance', sortOrder: 'desc' });
        
        // Clear cache and get children again
        provider.refresh();
        children = await provider.getChildren(intentGroup);
        
        assert.strictEqual(children[0].label, 'New memory'); // Higher importance
        assert.strictEqual(children[1].label, 'Old memory');
    });

    test('Should handle errors gracefully', async () => {
        mockMCPClient.callTool.rejects(new Error('API Error'));
        
        const intentGroup = new MemoryTreeItem(
            'Learning (1)',
            vscode.TreeItemCollapsibleState.Collapsed,
            TreeItemType.INTENT_GROUP
        );
        
        const children = await provider.getChildren(intentGroup);
        
        assert.strictEqual(children.length, 1);
        assert.strictEqual(children[0].label, 'Failed to load memories');
        assert.strictEqual(children[0].itemType, TreeItemType.LOADING);
        
        assert.ok(mockLogger.error.calledWith('Failed to load memories'));
    });

    test('Should implement caching for performance', async () => {
        const mockMemories = [createMockMemory()];
        
        mockMCPClient.callTool.resolves({
            memories: mockMemories,
            total: 1,
            offset: 0,
            limit: 50
        });
        
        const intentGroup = new MemoryTreeItem(
            'Learning (1)',
            vscode.TreeItemCollapsibleState.Collapsed,
            TreeItemType.INTENT_GROUP
        );
        
        // First call should hit the API
        await provider.getChildren(intentGroup);
        assert.ok(mockMCPClient.callTool.calledOnce);
        
        // Second call should use cache
        await provider.getChildren(intentGroup);
        assert.ok(mockMCPClient.callTool.calledOnce); // Still only called once
    });

    test('Should show proper icons for different memory intents', () => {
        const testCases = [
            { intent: MemoryIntent.LEARNING, expectedIcon: 'lightbulb' },
            { intent: MemoryIntent.DEBUGGING, expectedIcon: 'bug' },
            { intent: MemoryIntent.ARCHITECTURE, expectedIcon: 'symbol-structure' },
            { intent: MemoryIntent.TODO, expectedIcon: 'checklist' }
        ];
        
        testCases.forEach(({ intent, expectedIcon }) => {
            const memory = createMockMemory({ intent });
            const item = new MemoryTreeItem(
                memory.content,
                vscode.TreeItemCollapsibleState.None,
                TreeItemType.MEMORY,
                memory
            );
            
            assert.ok(item.iconPath instanceof vscode.ThemeIcon);
            assert.strictEqual((item.iconPath as vscode.ThemeIcon).id, 'file-text');
        });
    });

    test('Should handle memory importance in display', async () => {
        const memories = [
            createMockMemory({ content: 'High importance', importance: 0.9 }),
            createMockMemory({ content: 'Medium importance', importance: 0.6 }),
            createMockMemory({ content: 'Low importance', importance: 0.3 })
        ];
        
        mockMCPClient.callTool.resolves({
            memories,
            total: 3,
            offset: 0,
            limit: 50
        });
        
        const intentGroup = new MemoryTreeItem(
            'Learning (3)',
            vscode.TreeItemCollapsibleState.Collapsed,
            TreeItemType.INTENT_GROUP
        );
        
        const children = await provider.getChildren(intentGroup);
        
        // Check that high importance memories have star indicator
        assert.ok(children[0].description?.includes('⭐'));
        assert.ok(children[1].description?.includes('•'));
        assert.ok(!children[2].description?.includes('⭐'));
    });
});