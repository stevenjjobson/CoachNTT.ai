/**
 * Memory-related commands for CoachNTT.ai VSCode Extension
 */

import * as vscode from 'vscode';
import { MCPClient } from '../services/mcp-client';
import { MemoryTreeProvider } from '../providers/memory-tree-provider';
import { Memory, MemoryTreeItem, TreeItemType } from '../models/memory.model';
import { Logger } from '../utils/logger';

export class MemoryCommands {
    constructor(
        private mcpClient: MCPClient,
        private treeProvider: MemoryTreeProvider,
        private logger: Logger
    ) {}
    
    /**
     * Register all memory-related commands
     */
    registerCommands(context: vscode.ExtensionContext): void {
        // Tree view commands
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.refreshMemories', () => this.refreshMemories()),
            vscode.commands.registerCommand('coachntt.searchMemories', () => this.searchMemories()),
            vscode.commands.registerCommand('coachntt.clearSearch', () => this.clearSearch()),
            
            // Memory operations
            vscode.commands.registerCommand('coachntt.createMemory', () => this.createMemory()),
            vscode.commands.registerCommand('coachntt.createMemoryFromSelection', () => this.createMemoryFromSelection()),
            vscode.commands.registerCommand('coachntt.viewMemory', (item: MemoryTreeItem) => this.viewMemory(item)),
            vscode.commands.registerCommand('coachntt.editMemory', (item: MemoryTreeItem) => this.editMemory(item)),
            vscode.commands.registerCommand('coachntt.deleteMemory', (item: MemoryTreeItem) => this.deleteMemory(item)),
            vscode.commands.registerCommand('coachntt.reinforceMemory', (item: MemoryTreeItem) => this.reinforceMemory(item)),
            
            // Bulk operations
            vscode.commands.registerCommand('coachntt.exportMemories', () => this.exportMemories()),
            vscode.commands.registerCommand('coachntt.importMemories', () => this.importMemories()),
            
            // Settings
            vscode.commands.registerCommand('coachntt.configureMemoryView', () => this.configureMemoryView())
        );
    }
    
    /**
     * Refresh memory tree
     */
    private refreshMemories(): void {
        this.treeProvider.refresh();
        vscode.window.showInformationMessage('Memory tree refreshed');
    }
    
    /**
     * Search memories
     */
    private async searchMemories(): Promise<void> {
        const query = await vscode.window.showInputBox({
            prompt: 'Enter search query',
            placeHolder: 'Search memories by content, tags, or intent...',
            validateInput: (value) => {
                if (!value || value.trim().length < 2) {
                    return 'Search query must be at least 2 characters';
                }
                return null;
            }
        });
        
        if (query) {
            await this.treeProvider.search(query);
        }
    }
    
    /**
     * Clear search results
     */
    private clearSearch(): void {
        this.treeProvider.clearSearch();
    }
    
    /**
     * Create a new memory
     */
    private async createMemory(): Promise<void> {
        const content = await vscode.window.showInputBox({
            prompt: 'Enter memory content',
            placeHolder: 'What would you like to remember?',
            validateInput: (value) => {
                if (!value || value.trim().length === 0) {
                    return 'Memory content cannot be empty';
                }
                return null;
            }
        });
        
        if (!content) {
            return;
        }
        
        try {
            const memory = await this.mcpClient.callTool('memory_create', {
                content: content.trim()
            });
            
            vscode.window.showInformationMessage(`Memory created successfully`);
            this.treeProvider.refresh();
            
        } catch (error) {
            this.logger.error('Failed to create memory', error);
            vscode.window.showErrorMessage('Failed to create memory: ' + (error as Error).message);
        }
    }
    
    /**
     * Create memory from current selection
     */
    private async createMemoryFromSelection(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }
        
        const selection = editor.selection;
        const text = editor.document.getText(selection);
        
        if (!text) {
            vscode.window.showWarningMessage('No text selected');
            return;
        }
        
        // Get additional context
        const fileName = vscode.workspace.asRelativePath(editor.document.fileName);
        const language = editor.document.languageId;
        const lineNumber = selection.start.line + 1;
        
        // Build memory content with context
        const memoryContent = `Code from ${fileName}:${lineNumber}\n\`\`\`${language}\n${text}\n\`\`\``;
        
        try {
            await this.mcpClient.callTool('memory_create', {
                content: memoryContent,
                metadata: {
                    source: fileName,
                    language: language,
                    line_number: lineNumber
                }
            });
            
            vscode.window.showInformationMessage('Memory created from selection');
            this.treeProvider.refresh();
            
        } catch (error) {
            this.logger.error('Failed to create memory from selection', error);
            vscode.window.showErrorMessage('Failed to create memory: ' + (error as Error).message);
        }
    }
    
    /**
     * View memory details
     */
    private async viewMemory(item: MemoryTreeItem): Promise<void> {
        if (item.itemType !== TreeItemType.MEMORY || !item.memory) {
            return;
        }
        
        const memory = item.memory;
        
        // Create a virtual document to display the memory
        const uri = vscode.Uri.parse(`coachntt-memory:Memory/${memory.id}.md`);
        const doc = await vscode.workspace.openTextDocument(uri);
        await vscode.window.showTextDocument(doc, { preview: true });
    }
    
    /**
     * Edit a memory
     */
    private async editMemory(item: MemoryTreeItem): Promise<void> {
        if (item.itemType !== TreeItemType.MEMORY || !item.memory) {
            return;
        }
        
        const memory = item.memory;
        
        const newContent = await vscode.window.showInputBox({
            prompt: 'Edit memory content',
            value: memory.content,
            validateInput: (value) => {
                if (!value || value.trim().length === 0) {
                    return 'Memory content cannot be empty';
                }
                return null;
            }
        });
        
        if (!newContent || newContent === memory.content) {
            return;
        }
        
        try {
            await this.mcpClient.callTool('memory_update', {
                id: memory.id,
                content: newContent.trim()
            });
            
            vscode.window.showInformationMessage('Memory updated successfully');
            this.treeProvider.refresh();
            
        } catch (error) {
            this.logger.error('Failed to update memory', error);
            vscode.window.showErrorMessage('Failed to update memory: ' + (error as Error).message);
        }
    }
    
    /**
     * Delete a memory
     */
    private async deleteMemory(item: MemoryTreeItem): Promise<void> {
        if (item.itemType !== TreeItemType.MEMORY || !item.memory) {
            return;
        }
        
        const memory = item.memory;
        
        const confirm = await vscode.window.showWarningMessage(
            `Are you sure you want to delete this memory?`,
            'Delete',
            'Cancel'
        );
        
        if (confirm !== 'Delete') {
            return;
        }
        
        try {
            await this.mcpClient.callTool('memory_delete', {
                id: memory.id
            });
            
            vscode.window.showInformationMessage('Memory deleted successfully');
            this.treeProvider.refresh();
            
        } catch (error) {
            this.logger.error('Failed to delete memory', error);
            vscode.window.showErrorMessage('Failed to delete memory: ' + (error as Error).message);
        }
    }
    
    /**
     * Reinforce a memory
     */
    private async reinforceMemory(item: MemoryTreeItem): Promise<void> {
        if (item.itemType !== TreeItemType.MEMORY || !item.memory) {
            return;
        }
        
        const memory = item.memory;
        
        try {
            await this.mcpClient.callTool('memory_reinforce', {
                id: memory.id
            });
            
            vscode.window.showInformationMessage('Memory reinforced');
            this.treeProvider.refreshNode(item);
            
        } catch (error) {
            this.logger.error('Failed to reinforce memory', error);
            vscode.window.showErrorMessage('Failed to reinforce memory: ' + (error as Error).message);
        }
    }
    
    /**
     * Export memories
     */
    private async exportMemories(): Promise<void> {
        const uri = await vscode.window.showSaveDialog({
            defaultUri: vscode.Uri.file('memories.json'),
            filters: {
                'JSON files': ['json'],
                'All files': ['*']
            }
        });
        
        if (!uri) {
            return;
        }
        
        try {
            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'Exporting memories...',
                cancellable: false
            }, async (progress) => {
                progress.report({ increment: 0 });
                
                // Fetch all memories
                const response = await this.mcpClient.callTool('memory_search', {
                    limit: 1000
                });
                
                progress.report({ increment: 50 });
                
                // Write to file
                const content = JSON.stringify(response.memories, null, 2);
                await vscode.workspace.fs.writeFile(uri, Buffer.from(content));
                
                progress.report({ increment: 100 });
                
                vscode.window.showInformationMessage(`Exported ${response.memories.length} memories`);
            });
            
        } catch (error) {
            this.logger.error('Failed to export memories', error);
            vscode.window.showErrorMessage('Failed to export memories: ' + (error as Error).message);
        }
    }
    
    /**
     * Import memories
     */
    private async importMemories(): Promise<void> {
        const uris = await vscode.window.showOpenDialog({
            canSelectFiles: true,
            canSelectFolders: false,
            canSelectMany: false,
            filters: {
                'JSON files': ['json'],
                'All files': ['*']
            }
        });
        
        if (!uris || uris.length === 0) {
            return;
        }
        
        try {
            const content = await vscode.workspace.fs.readFile(uris[0]);
            const memories = JSON.parse(content.toString()) as Memory[];
            
            if (!Array.isArray(memories)) {
                throw new Error('Invalid memory format');
            }
            
            const confirm = await vscode.window.showInformationMessage(
                `Import ${memories.length} memories?`,
                'Import',
                'Cancel'
            );
            
            if (confirm !== 'Import') {
                return;
            }
            
            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'Importing memories...',
                cancellable: false
            }, async (progress) => {
                let imported = 0;
                
                for (const memory of memories) {
                    try {
                        await this.mcpClient.callTool('memory_create', {
                            content: memory.content,
                            metadata: memory.metadata
                        });
                        imported++;
                    } catch (error) {
                        this.logger.error(`Failed to import memory: ${memory.id}`, error);
                    }
                    
                    progress.report({ 
                        increment: (100 / memories.length),
                        message: `${imported}/${memories.length}`
                    });
                }
                
                vscode.window.showInformationMessage(`Imported ${imported} memories`);
                this.treeProvider.refresh();
            });
            
        } catch (error) {
            this.logger.error('Failed to import memories', error);
            vscode.window.showErrorMessage('Failed to import memories: ' + (error as Error).message);
        }
    }
    
    /**
     * Configure memory view settings
     */
    private async configureMemoryView(): Promise<void> {
        const config = vscode.workspace.getConfiguration('coachntt.memoryView');
        
        const choice = await vscode.window.showQuickPick([
            { label: 'Group by Intent', picked: config.get('groupByIntent', true) },
            { label: 'Show Archived', picked: config.get('showArchived', false) },
            { label: 'Sort by Timestamp', picked: config.get('sortBy') === 'timestamp' },
            { label: 'Sort by Importance', picked: config.get('sortBy') === 'importance' },
            { label: 'Sort by Reinforcement', picked: config.get('sortBy') === 'reinforcement' }
        ], {
            canPickMany: true,
            placeHolder: 'Configure memory view settings'
        });
        
        if (!choice) {
            return;
        }
        
        // Update configuration based on selection
        const updates: Array<{ key: string; value: any }> = [];
        
        if (choice.some(c => c.label === 'Group by Intent')) {
            updates.push({ key: 'groupByIntent', value: true });
        } else {
            updates.push({ key: 'groupByIntent', value: false });
        }
        
        if (choice.some(c => c.label === 'Show Archived')) {
            updates.push({ key: 'showArchived', value: true });
        } else {
            updates.push({ key: 'showArchived', value: false });
        }
        
        // Determine sort by
        if (choice.some(c => c.label === 'Sort by Importance')) {
            updates.push({ key: 'sortBy', value: 'importance' });
        } else if (choice.some(c => c.label === 'Sort by Reinforcement')) {
            updates.push({ key: 'sortBy', value: 'reinforcement' });
        } else {
            updates.push({ key: 'sortBy', value: 'timestamp' });
        }
        
        // Apply updates
        for (const update of updates) {
            await config.update(update.key, update.value, vscode.ConfigurationTarget.Global);
        }
        
        // Update tree provider config
        this.treeProvider.updateConfig({
            groupByIntent: config.get('groupByIntent', true),
            showArchived: config.get('showArchived', false),
            sortBy: config.get('sortBy', 'timestamp') as any,
            sortOrder: config.get('sortOrder', 'desc') as any,
            pageSize: config.get('pageSize', 50)
        });
    }
}