/**
 * Memory models and interfaces for CoachNTT.ai VSCode Extension
 * Follows the safety-first abstraction principles
 */

import * as vscode from 'vscode';

/**
 * Memory intent types - matching backend intent classification
 */
export enum MemoryIntent {
    LEARNING = 'learning',
    DEBUGGING = 'debugging',
    ARCHITECTURE = 'architecture',
    CONFIGURATION = 'configuration',
    ERROR_PATTERN = 'error_pattern',
    BEST_PRACTICE = 'best_practice',
    CODE_PATTERN = 'code_pattern',
    TODO = 'todo',
    WORKFLOW = 'workflow',
    REFERENCE = 'reference',
    DECISION = 'decision',
    LIVING_DOCUMENT = 'living_document',
    UNKNOWN = 'unknown'
}

/**
 * Memory status for tracking state
 */
export enum MemoryStatus {
    ACTIVE = 'active',
    ARCHIVED = 'archived',
    PENDING = 'pending',
    PROCESSING = 'processing'
}

/**
 * Core memory model - matching backend API response
 */
export interface Memory {
    id: string;
    content: string;
    intent: MemoryIntent;
    timestamp: string;
    importance: number;
    tags: string[];
    metadata?: MemoryMetadata;
    status?: MemoryStatus;
    reinforcement_count?: number;
    last_accessed?: string;
    similarity_score?: number;
}

/**
 * Memory metadata for additional context
 */
export interface MemoryMetadata {
    source?: string;
    language?: string;
    framework?: string;
    file_type?: string;
    abstraction_score?: number;
    word_count?: number;
    embedding_cached?: boolean;
    [key: string]: any;
}

/**
 * Tree view item types for hierarchical display
 */
export enum TreeItemType {
    CATEGORY = 'category',
    INTENT_GROUP = 'intent_group',
    MEMORY = 'memory',
    SEARCH_RESULTS = 'search_results',
    LOADING = 'loading'
}

/**
 * Extended tree item for memory display
 */
export class MemoryTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly itemType: TreeItemType,
        public readonly memory?: Memory,
        public readonly children?: MemoryTreeItem[]
    ) {
        super(label, collapsibleState);
        
        // Set context value for menu actions
        this.contextValue = itemType;
        
        // Set tooltip
        if (memory) {
            this.tooltip = this.createTooltip();
        }
        
        // Set icon based on type
        this.iconPath = this.getIcon();
        
        // Set description for additional info
        if (itemType === TreeItemType.MEMORY && memory) {
            this.description = this.getDescription();
        }
    }
    
    private createTooltip(): string {
        if (!this.memory) return '';
        
        const lines = [
            `Memory ID: ${this.memory.id}`,
            `Intent: ${this.memory.intent}`,
            `Importance: ${this.memory.importance.toFixed(2)}`,
            `Created: ${new Date(this.memory.timestamp).toLocaleString()}`,
            `Tags: ${this.memory.tags.join(', ') || 'None'}`
        ];
        
        if (this.memory.reinforcement_count) {
            lines.push(`Reinforcements: ${this.memory.reinforcement_count}`);
        }
        
        return lines.join('\n');
    }
    
    private getIcon(): vscode.ThemeIcon | undefined {
        switch (this.itemType) {
            case TreeItemType.CATEGORY:
                return new vscode.ThemeIcon('folder');
            case TreeItemType.INTENT_GROUP:
                return this.getIntentIcon();
            case TreeItemType.MEMORY:
                return new vscode.ThemeIcon('file-text');
            case TreeItemType.SEARCH_RESULTS:
                return new vscode.ThemeIcon('search');
            case TreeItemType.LOADING:
                return new vscode.ThemeIcon('loading~spin');
            default:
                return undefined;
        }
    }
    
    private getIntentIcon(): vscode.ThemeIcon {
        if (!this.label) return new vscode.ThemeIcon('folder');
        
        const intentIconMap: Record<string, string> = {
            [MemoryIntent.LEARNING]: 'lightbulb',
            [MemoryIntent.DEBUGGING]: 'bug',
            [MemoryIntent.ARCHITECTURE]: 'symbol-structure',
            [MemoryIntent.CONFIGURATION]: 'settings-gear',
            [MemoryIntent.ERROR_PATTERN]: 'warning',
            [MemoryIntent.BEST_PRACTICE]: 'star',
            [MemoryIntent.CODE_PATTERN]: 'symbol-method',
            [MemoryIntent.TODO]: 'checklist',
            [MemoryIntent.WORKFLOW]: 'run-all',
            [MemoryIntent.REFERENCE]: 'book',
            [MemoryIntent.DECISION]: 'question',
            [MemoryIntent.UNKNOWN]: 'circle-outline'
        };
        
        const intent = this.label.toLowerCase().replace(' ', '_');
        const iconName = intentIconMap[intent] || 'folder';
        return new vscode.ThemeIcon(iconName);
    }
    
    private getDescription(): string {
        if (!this.memory) return '';
        
        const parts = [];
        
        // Add importance indicator
        const importance = this.memory.importance;
        if (importance >= 0.8) {
            parts.push('⭐');
        } else if (importance >= 0.6) {
            parts.push('•');
        }
        
        // Add reinforcement indicator
        if (this.memory.reinforcement_count && this.memory.reinforcement_count > 0) {
            parts.push(`↑${this.memory.reinforcement_count}`);
        }
        
        // Add time ago
        parts.push(this.getTimeAgo(this.memory.timestamp));
        
        return parts.join(' ');
    }
    
    private getTimeAgo(timestamp: string): string {
        const now = new Date();
        const then = new Date(timestamp);
        const seconds = Math.floor((now.getTime() - then.getTime()) / 1000);
        
        if (seconds < 60) return 'just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
        return then.toLocaleDateString();
    }
}

/**
 * Memory search request
 */
export interface MemorySearchRequest {
    query?: string;
    intent?: MemoryIntent;
    tags?: string[];
    start_date?: string;
    end_date?: string;
    min_importance?: number;
    limit?: number;
    offset?: number;
}

/**
 * Memory search response
 */
export interface MemorySearchResponse {
    memories: Memory[];
    total: number;
    offset: number;
    limit: number;
}

/**
 * Memory statistics for display
 */
export interface MemoryStatistics {
    total_memories: number;
    memories_by_intent: Record<MemoryIntent, number>;
    average_importance: number;
    most_used_tags: Array<{ tag: string; count: number }>;
    memory_growth: Array<{ date: string; count: number }>;
}

/**
 * Memory tree configuration
 */
export interface MemoryTreeConfig {
    groupByIntent: boolean;
    showArchived: boolean;
    sortBy: 'timestamp' | 'importance' | 'reinforcement';
    sortOrder: 'asc' | 'desc';
    pageSize: number;
}

/**
 * Default tree configuration
 */
export const DEFAULT_TREE_CONFIG: MemoryTreeConfig = {
    groupByIntent: true,
    showArchived: false,
    sortBy: 'timestamp',
    sortOrder: 'desc',
    pageSize: 50
};