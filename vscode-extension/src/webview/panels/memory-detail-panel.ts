/**
 * Memory Detail Panel - WebView for displaying memory details
 * 
 * Shows rich, formatted memory content with:
 * - Syntax highlighting for code
 * - Metadata display
 * - Real-time updates
 * - Action buttons
 */

import * as vscode from 'vscode';
import { ManagedWebViewPanel } from '../webview-manager';
import { MessageProtocol } from '../message-protocol';
import { BaseTemplate } from '../templates/base-template';
import { Memory } from '../../models/memory.model';
import { MCPClient } from '../../services/mcp-client';
import { Logger } from '../../utils/logger';

/**
 * Memory detail panel state
 */
interface MemoryDetailPanelState {
    memoryId: string;
    memory?: Memory;
    lastUpdated?: number;
}

/**
 * Memory Detail WebView Panel
 */
export class MemoryDetailPanel extends ManagedWebViewPanel {
    private protocol: MessageProtocol;
    private memory: Memory | undefined;
    private mcpClient: MCPClient;
    
    constructor(
        panel: vscode.WebviewPanel,
        context: vscode.ExtensionContext,
        logger: Logger,
        mcpClient: MCPClient,
        initialMemory?: Memory
    ) {
        super(panel, context, logger);
        this.mcpClient = mcpClient;
        this.memory = initialMemory;
        
        // Initialize message protocol
        this.protocol = new MessageProtocol(
            message => this.panel.webview.postMessage(message),
            content => this.abstractContent(content)
        );
        
        // Set up protocol handlers
        this.setupProtocolHandlers();
        
        // Set up MCP event listeners
        this.setupMCPListeners();
        
        // Initial render
        this.render();
    }
    
    /**
     * Abstract content for safety
     */
    private abstractContent(content: string): string {
        // Use the same abstraction logic as the logger
        content = content.replace(/([A-Za-z]:)?[\/\\][\w\s-]+[\/\\][\w\s-]+\.(ts|js|json|py|md)/g, '<project>/<module>/<file>');
        content = content.replace(/([A-Za-z]:)?[\/\\][\w\s-]+[\/\\]/g, '<directory>/');
        content = content.replace(/https?:\/\/[^\s]+/g, '<url>');
        content = content.replace(/ws:\/\/[^\s]+/g, '<websocket_url>');
        content = content.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '<ip_address>');
        content = content.replace(/[A-Za-z0-9]{32,}/g, '<token>');
        content = content.replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, '<uuid>');
        return content;
    }
    
    /**
     * Set up message protocol handlers
     */
    private setupProtocolHandlers(): void {
        // Handle refresh request
        this.protocol.onRequest('refresh', async () => {
            if (this.memory) {
                await this.loadMemory(this.memory.id);
            }
        });
        
        // Handle edit request
        this.protocol.onRequest('edit', async () => {
            if (this.memory) {
                vscode.commands.executeCommand('coachntt.editMemory', this.memory);
            }
        });
        
        // Handle delete request
        this.protocol.onRequest('delete', async () => {
            if (this.memory) {
                vscode.commands.executeCommand('coachntt.deleteMemory', this.memory);
            }
        });
        
        // Handle reinforce request
        this.protocol.onRequest('reinforce', async () => {
            if (this.memory) {
                vscode.commands.executeCommand('coachntt.reinforceMemory', this.memory);
            }
        });
        
        // Handle copy content
        this.protocol.onRequest('copyContent', async () => {
            if (this.memory) {
                await vscode.env.clipboard.writeText(this.memory.content);
                vscode.window.showInformationMessage('Memory content copied to clipboard');
            }
        });
    }
    
    /**
     * Set up MCP event listeners
     */
    private setupMCPListeners(): void {
        // Listen for memory updates
        this.mcpClient.on('memory:updated', (updatedMemory: Memory) => {
            if (this.memory && updatedMemory.id === this.memory.id) {
                this.memory = updatedMemory;
                this.render();
                this.protocol.sendEvent('memoryUpdated', updatedMemory);
            }
        });
        
        // Listen for memory deletion
        this.mcpClient.on('memory:deleted', (memoryId: string) => {
            if (this.memory && memoryId === this.memory.id) {
                this.panel.dispose();
            }
        });
    }
    
    /**
     * Load memory from backend
     */
    public async loadMemory(memoryId: string): Promise<void> {
        try {
            this.protocol.sendEvent('loading', true);
            
            const response = await this.mcpClient.callTool('memory_get', { id: memoryId });
            if (response.memory) {
                this.memory = response.memory;
                this.render();
                this.protocol.sendEvent('loading', false);
            } else {
                throw new Error('Memory not found');
            }
        } catch (error) {
            this.logger.error('Failed to load memory', error);
            this.protocol.sendEvent('error', 'Failed to load memory');
            this.protocol.sendEvent('loading', false);
        }
    }
    
    /**
     * Render the WebView content
     */
    private render(): void {
        if (!this.memory) {
            this.updateContent(BaseTemplate.generateErrorPage(this.nonce, 'No memory loaded'));
            return;
        }
        
        const styleUri = this.getResourceUri('media/memory-detail.css');
        const scriptUri = this.getResourceUri('media/memory-detail.js');
        
        const html = BaseTemplate.generateHTML({
            title: `Memory: ${this.truncateText(this.memory.content, 50)}`,
            nonce: this.nonce,
            styleUris: [styleUri],
            scriptUris: [scriptUri],
            inlineStyles: this.getInlineStyles(),
            bodyContent: this.getBodyContent(),
            initialState: {
                memoryId: this.memory.id,
                memory: this.sanitizeMemory(this.memory)
            }
        });
        
        this.updateContent(html);
    }
    
    /**
     * Get inline styles
     */
    private getInlineStyles(): string {
        return `
            .memory-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding-bottom: 20px;
                border-bottom: 1px solid var(--vscode-panel-border);
                margin-bottom: 20px;
            }
            
            .memory-actions {
                display: flex;
                gap: 10px;
            }
            
            .memory-metadata {
                display: grid;
                grid-template-columns: 150px 1fr;
                gap: 10px;
                margin-bottom: 20px;
                padding: 15px;
                background-color: var(--vscode-editor-background);
                border-radius: 5px;
            }
            
            .metadata-label {
                font-weight: bold;
                color: var(--vscode-descriptionForeground);
            }
            
            .memory-content {
                padding: 20px;
                background-color: var(--vscode-editor-background);
                border-radius: 5px;
                white-space: pre-wrap;
                font-family: var(--vscode-editor-font-family);
                line-height: 1.5;
            }
            
            .memory-tags {
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                margin-top: 20px;
            }
            
            .tag {
                background-color: var(--vscode-badge-background);
                color: var(--vscode-badge-foreground);
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.9em;
            }
            
            .importance-bar {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .importance-progress {
                flex: 1;
                height: 8px;
                background-color: var(--vscode-progressBar-background);
                border-radius: 4px;
                overflow: hidden;
            }
            
            .importance-fill {
                height: 100%;
                background-color: var(--vscode-progressBar-foreground);
                transition: width 0.3s ease;
            }
            
            .reinforcement-badge {
                display: inline-flex;
                align-items: center;
                gap: 5px;
                padding: 5px 10px;
                background-color: var(--vscode-editorWarning-background);
                color: var(--vscode-editorWarning-foreground);
                border-radius: 5px;
            }
        `;
    }
    
    /**
     * Get body content
     */
    private getBodyContent(): string {
        if (!this.memory) return '';
        
        const safeMemory = this.sanitizeMemory(this.memory);
        const timestamp = new Date(safeMemory.timestamp).toLocaleString();
        const importancePercent = Math.round(safeMemory.importance * 100);
        
        return `
            <div class="container">
                <div class="memory-header">
                    <h1>${this.formatIntent(safeMemory.intent)} Memory</h1>
                    <div class="memory-actions">
                        <button onclick="handleAction('refresh')" title="Refresh">
                            <span class="codicon codicon-refresh"></span> Refresh
                        </button>
                        <button onclick="handleAction('edit')" title="Edit">
                            <span class="codicon codicon-edit"></span> Edit
                        </button>
                        <button onclick="handleAction('reinforce')" title="Reinforce">
                            <span class="codicon codicon-star"></span> Reinforce
                        </button>
                        <button onclick="handleAction('copyContent')" title="Copy Content">
                            <span class="codicon codicon-copy"></span> Copy
                        </button>
                        <button onclick="handleAction('delete')" title="Delete" style="color: var(--vscode-errorForeground);">
                            <span class="codicon codicon-trash"></span> Delete
                        </button>
                    </div>
                </div>
                
                <div class="memory-metadata">
                    <div class="metadata-label">ID:</div>
                    <div><code>${safeMemory.id}</code></div>
                    
                    <div class="metadata-label">Created:</div>
                    <div>${timestamp}</div>
                    
                    <div class="metadata-label">Intent:</div>
                    <div><span class="badge">${this.formatIntent(safeMemory.intent)}</span></div>
                    
                    <div class="metadata-label">Importance:</div>
                    <div class="importance-bar">
                        <div class="importance-progress">
                            <div class="importance-fill" style="width: ${importancePercent}%"></div>
                        </div>
                        <span>${importancePercent}%</span>
                    </div>
                    
                    ${safeMemory.reinforcement_count ? `
                    <div class="metadata-label">Reinforcements:</div>
                    <div class="reinforcement-badge">
                        <span class="codicon codicon-arrow-up"></span>
                        ${safeMemory.reinforcement_count}
                    </div>
                    ` : ''}
                    
                    ${safeMemory.metadata?.abstraction_score !== undefined ? `
                    <div class="metadata-label">Safety Score:</div>
                    <div>${(safeMemory.metadata.abstraction_score * 100).toFixed(1)}%</div>
                    ` : ''}
                </div>
                
                <div class="memory-content">
                    ${BaseTemplate.escapeHtml(safeMemory.content)}
                </div>
                
                ${safeMemory.tags && safeMemory.tags.length > 0 ? `
                <div class="memory-tags">
                    ${safeMemory.tags.map(tag => `<span class="tag">${BaseTemplate.escapeHtml(tag)}</span>`).join('')}
                </div>
                ` : ''}
            </div>
            
            <script nonce="${this.nonce}">
                // Handle action buttons
                async function handleAction(action) {
                    const message = {
                        id: Date.now().toString(),
                        type: 'request',
                        method: action,
                        timestamp: Date.now()
                    };
                    
                    window.postMessage(message);
                }
                
                // Handle incoming messages
                window.handleMessage = function(message) {
                    switch (message.type) {
                        case 'event':
                            if (message.event === 'loading') {
                                // TODO: Show/hide loading state
                            } else if (message.event === 'error') {
                                // TODO: Show error message
                            } else if (message.event === 'memoryUpdated') {
                                // TODO: Update UI with new memory data
                            }
                            break;
                    }
                };
            </script>
        `;
    }
    
    /**
     * Sanitize memory for display
     */
    private sanitizeMemory(memory: Memory): Memory {
        return {
            ...memory,
            content: this.abstractContent(memory.content),
            tags: memory.tags.map(tag => this.abstractContent(tag))
        };
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
     * Truncate text
     */
    private truncateText(text: string, maxLength: number): string {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }
    
    /**
     * Handle incoming messages
     */
    protected handleMessage(message: any): void {
        this.protocol.handleMessage(message);
    }
    
    /**
     * Get panel state for persistence
     */
    protected getPanelState(): MemoryDetailPanelState {
        return {
            memoryId: this.memory?.id || '',
            memory: this.memory,
            lastUpdated: Date.now()
        };
    }
    
    /**
     * Restore panel state
     */
    public restoreState(state: MemoryDetailPanelState): void {
        if (state.memoryId) {
            this.loadMemory(state.memoryId);
        }
    }
    
    /**
     * Dispose resources
     */
    public dispose(): void {
        this.protocol.dispose();
        super.dispose();
    }
}