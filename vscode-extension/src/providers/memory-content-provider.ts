/**
 * Memory Content Provider for virtual document display
 * Provides formatted memory content for viewing in VSCode
 */

import * as vscode from 'vscode';
import { Memory } from '../models/memory.model';
import { MCPClient } from '../services/mcp-client';
import { Logger } from '../utils/logger';

export class MemoryContentProvider implements vscode.TextDocumentContentProvider {
    private _onDidChange = new vscode.EventEmitter<vscode.Uri>();
    readonly onDidChange = this._onDidChange.event;
    
    constructor(
        private mcpClient: MCPClient,
        private logger: Logger
    ) {}
    
    /**
     * Provide text document content for memory URI
     */
    async provideTextDocumentContent(uri: vscode.Uri): Promise<string> {
        const memoryId = this.getMemoryIdFromUri(uri);
        if (!memoryId) {
            return '# Memory Not Found\n\nInvalid memory URI';
        }
        
        try {
            const response = await this.mcpClient.callTool('memory_get', { id: memoryId });
            const memory = response.memory as Memory;
            
            if (!memory) {
                return '# Memory Not Found\n\nThe requested memory could not be found.';
            }
            
            return this.formatMemoryContent(memory);
            
        } catch (error) {
            this.logger.error('Failed to load memory content', error);
            return `# Error Loading Memory\n\n${(error as Error).message}`;
        }
    }
    
    /**
     * Format memory as markdown document
     */
    private formatMemoryContent(memory: Memory): string {
        const lines: string[] = [];
        
        // Header
        lines.push(`# Memory Details`);
        lines.push('');
        
        // Metadata section
        lines.push('## Metadata');
        lines.push(`- **ID**: ${memory.id}`);
        lines.push(`- **Intent**: ${this.formatIntent(memory.intent)}`);
        lines.push(`- **Importance**: ${memory.importance.toFixed(2)}`);
        lines.push(`- **Created**: ${new Date(memory.timestamp).toLocaleString()}`);
        
        if (memory.reinforcement_count) {
            lines.push(`- **Reinforcements**: ${memory.reinforcement_count}`);
        }
        
        if (memory.last_accessed) {
            lines.push(`- **Last Accessed**: ${new Date(memory.last_accessed).toLocaleString()}`);
        }
        
        lines.push('');
        
        // Tags section
        if (memory.tags && memory.tags.length > 0) {
            lines.push('## Tags');
            lines.push(memory.tags.map(tag => `\`${tag}\``).join(' '));
            lines.push('');
        }
        
        // Content section
        lines.push('## Content');
        lines.push('');
        lines.push(memory.content);
        lines.push('');
        
        // Additional metadata
        if (memory.metadata) {
            lines.push('## Additional Information');
            
            if (memory.metadata.source) {
                lines.push(`- **Source**: ${memory.metadata.source}`);
            }
            
            if (memory.metadata.language) {
                lines.push(`- **Language**: ${memory.metadata.language}`);
            }
            
            if (memory.metadata.framework) {
                lines.push(`- **Framework**: ${memory.metadata.framework}`);
            }
            
            if (memory.metadata.abstraction_score !== undefined) {
                lines.push(`- **Abstraction Score**: ${memory.metadata.abstraction_score.toFixed(3)}`);
            }
            
            if (memory.metadata.word_count) {
                lines.push(`- **Word Count**: ${memory.metadata.word_count}`);
            }
            
            if (memory.metadata.embedding_cached !== undefined) {
                lines.push(`- **Embedding Cached**: ${memory.metadata.embedding_cached ? 'Yes' : 'No'}`);
            }
            
            lines.push('');
        }
        
        // Similarity score if available
        if (memory.similarity_score !== undefined) {
            lines.push('## Search Relevance');
            lines.push(`Similarity Score: ${(memory.similarity_score * 100).toFixed(1)}%`);
            lines.push('');
        }
        
        // Actions section
        lines.push('## Actions');
        lines.push('- Use `Ctrl+Shift+P` to open command palette');
        lines.push('- Run `CoachNTT: Edit Memory` to modify this memory');
        lines.push('- Run `CoachNTT: Reinforce Memory` to increase importance');
        lines.push('- Run `CoachNTT: Delete Memory` to remove this memory');
        
        return lines.join('\n');
    }
    
    /**
     * Format intent for display
     */
    private formatIntent(intent: string): string {
        return intent.split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
    }
    
    /**
     * Extract memory ID from URI
     */
    private getMemoryIdFromUri(uri: vscode.Uri): string | null {
        const match = uri.path.match(/Memory\/(.+)\.md$/);
        return match ? match[1] : null;
    }
    
    /**
     * Update document content
     */
    update(uri: vscode.Uri): void {
        this._onDidChange.fire(uri);
    }
    
    /**
     * Dispose resources
     */
    dispose(): void {
        this._onDidChange.dispose();
    }
}