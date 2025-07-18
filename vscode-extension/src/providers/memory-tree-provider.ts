/**
 * Memory Tree Provider for CoachNTT.ai VSCode Extension
 * Implements a three-tier hierarchical view: Category -> Intent -> Memories
 */

import * as vscode from 'vscode';
import { MCPClient } from '../services/mcp-client';
import { 
    Memory, 
    MemoryTreeItem, 
    TreeItemType, 
    MemoryIntent,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryTreeConfig,
    DEFAULT_TREE_CONFIG
} from '../models/memory.model';
import { Logger } from '../utils/logger';

export class MemoryTreeProvider implements vscode.TreeDataProvider<MemoryTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<MemoryTreeItem | undefined | null | void> = new vscode.EventEmitter<MemoryTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<MemoryTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;
    
    private memories: Map<string, Memory[]> = new Map();
    private searchResults: Memory[] = [];
    private isSearchMode: boolean = false;
    private config: MemoryTreeConfig = DEFAULT_TREE_CONFIG;
    private loadingStates: Map<string, boolean> = new Map();
    private cache: Map<string, { data: Memory[], timestamp: number }> = new Map();
    private readonly CACHE_TTL = 60000; // 60 seconds
    
    constructor(
        private mcpClient: MCPClient,
        private logger: Logger
    ) {
        // Subscribe to MCP events for real-time updates
        this.mcpClient.on('memory:created', (memory: Memory) => {
            this.handleMemoryCreated(memory);
        });
        
        this.mcpClient.on('memory:updated', (memory: Memory) => {
            this.handleMemoryUpdated(memory);
        });
        
        this.mcpClient.on('memory:deleted', (memoryId: string) => {
            this.handleMemoryDeleted(memoryId);
        });
    }
    
    /**
     * Get tree item for display
     */
    getTreeItem(element: MemoryTreeItem): vscode.TreeItem {
        return element;
    }
    
    /**
     * Get children for tree item
     */
    async getChildren(element?: MemoryTreeItem): Promise<MemoryTreeItem[]> {
        if (!this.mcpClient.isConnected()) {
            return [new MemoryTreeItem(
                'Not connected to MCP server',
                vscode.TreeItemCollapsibleState.None,
                TreeItemType.LOADING
            )];
        }
        
        // Root level - show categories or search results
        if (!element) {
            if (this.isSearchMode) {
                return this.getSearchResultItems();
            }
            return this.getCategoryItems();
        }
        
        // Category level - show intent groups
        if (element.itemType === TreeItemType.CATEGORY) {
            return this.getIntentGroupItems();
        }
        
        // Intent group level - show memories
        if (element.itemType === TreeItemType.INTENT_GROUP) {
            return this.getMemoryItems(element.label);
        }
        
        return [];
    }
    
    /**
     * Get category items (top level)
     */
    private getCategoryItems(): MemoryTreeItem[] {
        const categories = [
            { label: 'Recent Memories', icon: 'history' },
            { label: 'Important Memories', icon: 'star' },
            { label: 'By Intent', icon: 'list-tree' }
        ];
        
        return categories.map(cat => new MemoryTreeItem(
            cat.label,
            vscode.TreeItemCollapsibleState.Collapsed,
            TreeItemType.CATEGORY
        ));
    }
    
    /**
     * Get intent group items
     */
    private async getIntentGroupItems(): Promise<MemoryTreeItem[]> {
        const intents = Object.values(MemoryIntent);
        const items: MemoryTreeItem[] = [];
        
        for (const intent of intents) {
            const count = await this.getMemoryCountByIntent(intent);
            if (count > 0) {
                const label = this.formatIntentLabel(intent);
                const item = new MemoryTreeItem(
                    `${label} (${count})`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    TreeItemType.INTENT_GROUP
                );
                items.push(item);
            }
        }
        
        return items;
    }
    
    /**
     * Get memory items for a specific intent
     */
    private async getMemoryItems(intentLabel: string): Promise<MemoryTreeItem[]> {
        const intent = this.parseIntentFromLabel(intentLabel);
        const cacheKey = `memories_${intent}`;
        
        // Check cache first
        const cached = this.cache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < this.CACHE_TTL) {
            return this.createMemoryTreeItems(cached.data);
        }
        
        // Show loading state
        const loadingKey = `loading_${intent}`;
        if (this.loadingStates.get(loadingKey)) {
            return [new MemoryTreeItem(
                'Loading memories...',
                vscode.TreeItemCollapsibleState.None,
                TreeItemType.LOADING
            )];
        }
        
        try {
            this.loadingStates.set(loadingKey, true);
            
            const searchRequest: MemorySearchRequest = {
                intent: intent as MemoryIntent,
                limit: this.config.pageSize,
                offset: 0
            };
            
            const response = await this.searchMemories(searchRequest);
            
            // Cache the results
            this.cache.set(cacheKey, {
                data: response.memories,
                timestamp: Date.now()
            });
            
            return this.createMemoryTreeItems(response.memories);
            
        } catch (error) {
            this.logger.error('Failed to load memories', error);
            return [new MemoryTreeItem(
                'Failed to load memories',
                vscode.TreeItemCollapsibleState.None,
                TreeItemType.LOADING
            )];
        } finally {
            this.loadingStates.set(loadingKey, false);
        }
    }
    
    /**
     * Get search result items
     */
    private getSearchResultItems(): MemoryTreeItem[] {
        if (this.searchResults.length === 0) {
            return [new MemoryTreeItem(
                'No search results',
                vscode.TreeItemCollapsibleState.None,
                TreeItemType.LOADING
            )];
        }
        
        const resultsItem = new MemoryTreeItem(
            `Search Results (${this.searchResults.length})`,
            vscode.TreeItemCollapsibleState.Expanded,
            TreeItemType.SEARCH_RESULTS
        );
        
        resultsItem.children = this.createMemoryTreeItems(this.searchResults);
        return [resultsItem];
    }
    
    /**
     * Create tree items from memories
     */
    private createMemoryTreeItems(memories: Memory[]): MemoryTreeItem[] {
        // Sort memories based on config
        const sorted = this.sortMemories(memories);
        
        return sorted.map(memory => {
            const label = this.truncateContent(memory.content, 50);
            return new MemoryTreeItem(
                label,
                vscode.TreeItemCollapsibleState.None,
                TreeItemType.MEMORY,
                memory
            );
        });
    }
    
    /**
     * Search memories
     */
    async search(query: string): Promise<void> {
        try {
            const searchRequest: MemorySearchRequest = {
                query,
                limit: 100
            };
            
            const response = await this.searchMemories(searchRequest);
            this.searchResults = response.memories;
            this.isSearchMode = true;
            this.refresh();
            
        } catch (error) {
            this.logger.error('Search failed', error);
            vscode.window.showErrorMessage('Failed to search memories');
        }
    }
    
    /**
     * Clear search and return to normal view
     */
    clearSearch(): void {
        this.searchResults = [];
        this.isSearchMode = false;
        this.refresh();
    }
    
    /**
     * Refresh the tree view
     */
    refresh(): void {
        this.cache.clear();
        this._onDidChangeTreeData.fire();
    }
    
    /**
     * Refresh a specific node
     */
    refreshNode(node: MemoryTreeItem): void {
        this._onDidChangeTreeData.fire(node);
    }
    
    /**
     * Update tree configuration
     */
    updateConfig(config: Partial<MemoryTreeConfig>): void {
        this.config = { ...this.config, ...config };
        this.refresh();
    }
    
    /**
     * Get memory by ID
     */
    async getMemory(id: string): Promise<Memory | undefined> {
        try {
            const response = await this.mcpClient.callTool('memory_get', { id });
            return response.memory;
        } catch (error) {
            this.logger.error('Failed to get memory', error);
            return undefined;
        }
    }
    
    /**
     * Private helper methods
     */
    
    private async searchMemories(request: MemorySearchRequest): Promise<MemorySearchResponse> {
        const response = await this.mcpClient.callTool('memory_search', request);
        return response;
    }
    
    private async getMemoryCountByIntent(intent: MemoryIntent): Promise<number> {
        try {
            const response = await this.searchMemories({
                intent,
                limit: 1
            });
            return response.total;
        } catch {
            return 0;
        }
    }
    
    private formatIntentLabel(intent: string): string {
        return intent.split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
    }
    
    private parseIntentFromLabel(label: string): string {
        const match = label.match(/^(.*?)\s*\(\d+\)$/);
        const cleanLabel = match ? match[1] : label;
        return cleanLabel.toLowerCase().replace(/\s+/g, '_');
    }
    
    private truncateContent(content: string, maxLength: number): string {
        if (content.length <= maxLength) {
            return content;
        }
        return content.substring(0, maxLength - 3) + '...';
    }
    
    private sortMemories(memories: Memory[]): Memory[] {
        return [...memories].sort((a, b) => {
            let comparison = 0;
            
            switch (this.config.sortBy) {
                case 'timestamp':
                    comparison = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
                    break;
                case 'importance':
                    comparison = a.importance - b.importance;
                    break;
                case 'reinforcement':
                    comparison = (a.reinforcement_count || 0) - (b.reinforcement_count || 0);
                    break;
            }
            
            return this.config.sortOrder === 'asc' ? comparison : -comparison;
        });
    }
    
    /**
     * Real-time update handlers
     */
    
    private handleMemoryCreated(memory: Memory): void {
        // Invalidate relevant caches
        this.cache.delete(`memories_${memory.intent}`);
        
        // Refresh the tree
        this.refresh();
        
        // Show notification
        vscode.window.showInformationMessage(`New memory created: ${this.truncateContent(memory.content, 30)}`);
    }
    
    private handleMemoryUpdated(memory: Memory): void {
        // Invalidate relevant caches
        this.cache.delete(`memories_${memory.intent}`);
        
        // Update search results if necessary
        if (this.isSearchMode) {
            const index = this.searchResults.findIndex(m => m.id === memory.id);
            if (index !== -1) {
                this.searchResults[index] = memory;
            }
        }
        
        // Refresh the tree
        this.refresh();
    }
    
    private handleMemoryDeleted(memoryId: string): void {
        // Clear all caches as we don't know which intent it belonged to
        this.cache.clear();
        
        // Remove from search results if necessary
        if (this.isSearchMode) {
            this.searchResults = this.searchResults.filter(m => m.id !== memoryId);
        }
        
        // Refresh the tree
        this.refresh();
    }
    
    /**
     * Dispose resources
     */
    dispose(): void {
        this._onDidChangeTreeData.dispose();
    }
}