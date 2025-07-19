import * as vscode from 'vscode';
import * as path from 'path';
import { LivingDocument } from '../types/living-document.types';
import { DocumentAbstractor } from '../services/document-abstractor';

/**
 * Living Document Preview Panel
 * Provides rich visualization of abstracted documents with real-time updates
 */
export class LivingDocumentPreview {
    private static panels: Map<string, vscode.WebviewPanel> = new Map();
    private static abstractor = DocumentAbstractor.getInstance();

    /**
     * Create or show preview panel for a document
     */
    public static async createOrShow(
        document: LivingDocument,
        extensionUri: vscode.Uri
    ): Promise<void> {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        // Check if panel already exists
        const existingPanel = this.panels.get(document.id);
        
        if (existingPanel) {
            existingPanel.reveal(column);
            await this.updateContent(existingPanel, document);
            return;
        }

        // Create new panel
        const panel = vscode.window.createWebviewPanel(
            'livingDocPreview',
            `Preview: ${document.title}`,
            column || vscode.ViewColumn.Beside,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [
                    vscode.Uri.joinPath(extensionUri, 'media'),
                    vscode.Uri.joinPath(extensionUri, 'resources')
                ]
            }
        );

        // Store panel reference
        this.panels.set(document.id, panel);

        // Set initial content
        panel.webview.html = await this.getWebviewContent(panel.webview, document, extensionUri);

        // Handle panel disposal
        panel.onDidDispose(() => {
            this.panels.delete(document.id);
        });

        // Handle messages from webview
        panel.webview.onDidReceiveMessage(
            async message => {
                switch (message.command) {
                    case 'showOriginal':
                        await this.showOriginalReference(message.reference);
                        break;
                    case 'copyAbstracted':
                        await vscode.env.clipboard.writeText(message.text);
                        vscode.window.showInformationMessage('Abstracted reference copied to clipboard');
                        break;
                    case 'openDocument':
                        const doc = await vscode.workspace.openTextDocument(document.uri);
                        await vscode.window.showTextDocument(doc);
                        break;
                    case 'changeCompactionStrategy':
                        await this.handleCompactionChange(document, message.strategy);
                        break;
                }
            }
        );

        // Watch for document changes
        const changeListener = vscode.workspace.onDidChangeTextDocument(async e => {
            if (e.document.uri.toString() === document.uri.toString()) {
                // Re-abstract the content
                const newContent = e.document.getText();
                const abstracted = await this.abstractor.abstractDocument(newContent);
                
                // Update the preview
                panel.webview.postMessage({
                    type: 'contentUpdate',
                    content: abstracted.abstractedContent,
                    stats: {
                        totalAbstractions: abstracted.statistics.totalAbstractions,
                        safetyScore: abstracted.safetyScore
                    }
                });
            }
        });

        // Clean up listener on dispose
        panel.onDidDispose(() => {
            changeListener.dispose();
        });
    }

    /**
     * Update content for existing panel
     */
    private static async updateContent(
        panel: vscode.WebviewPanel,
        document: LivingDocument
    ): Promise<void> {
        panel.webview.postMessage({
            type: 'fullUpdate',
            document: {
                title: document.title,
                content: document.abstractedContent,
                stage: document.stage,
                safetyScore: document.safetyMetadata.safetyScore,
                totalAbstractions: document.safetyMetadata.abstractedElements.length,
                compactionLevel: document.compactionMetadata.currentLevel,
                lastModified: document.temporalMetadata.lastModified
            }
        });
    }

    /**
     * Generate webview HTML content
     */
    private static async getWebviewContent(
        webview: vscode.Webview,
        document: LivingDocument,
        extensionUri: vscode.Uri
    ): Promise<string> {
        // Get resource URIs
        const styleUri = webview.asWebviewUri(
            vscode.Uri.joinPath(extensionUri, 'media', 'document-preview.css')
        );
        const scriptUri = webview.asWebviewUri(
            vscode.Uri.joinPath(extensionUri, 'media', 'document-preview.js')
        );

        // Process content with syntax highlighting
        const highlightedContent = this.highlightAbstractions(document.abstractedContent);

        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>${document.title} - Living Document Preview</title>
            <link href="${styleUri}" rel="stylesheet">
            <style>
                body {
                    font-family: var(--vscode-font-family);
                    font-size: var(--vscode-font-size);
                    color: var(--vscode-foreground);
                    background-color: var(--vscode-editor-background);
                    padding: 20px;
                    line-height: 1.6;
                }
                
                .header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid var(--vscode-widget-border);
                }
                
                .title {
                    font-size: 1.5em;
                    font-weight: bold;
                }
                
                .stats {
                    display: flex;
                    gap: 20px;
                    font-size: 0.9em;
                    color: var(--vscode-descriptionForeground);
                }
                
                .stat-item {
                    display: flex;
                    align-items: center;
                    gap: 5px;
                }
                
                .safety-score {
                    padding: 2px 8px;
                    border-radius: 12px;
                    background: var(--vscode-badge-background);
                    color: var(--vscode-badge-foreground);
                }
                
                .safety-high { background: #4CAF50; }
                .safety-medium { background: #FF9800; }
                .safety-low { background: #F44336; }
                
                .abstracted {
                    color: var(--vscode-symbolIcon-variableForeground);
                    font-weight: 600;
                    cursor: help;
                    text-decoration: underline;
                    text-decoration-style: dotted;
                    text-underline-offset: 2px;
                }
                
                .abstracted:hover {
                    background: var(--vscode-editor-selectionBackground);
                    border-radius: 3px;
                    padding: 0 2px;
                }
                
                .evolution-indicator {
                    font-size: 0.8em;
                    color: var(--vscode-editorLineNumber-foreground);
                    vertical-align: super;
                }
                
                .content {
                    white-space: pre-wrap;
                    font-family: var(--vscode-editor-font-family);
                }
                
                .toolbar {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    display: flex;
                    gap: 10px;
                }
                
                .button {
                    padding: 5px 10px;
                    background: var(--vscode-button-background);
                    color: var(--vscode-button-foreground);
                    border: none;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 12px;
                }
                
                .button:hover {
                    background: var(--vscode-button-hoverBackground);
                }
                
                .compaction-selector {
                    display: flex;
                    align-items: center;
                    gap: 5px;
                    background: var(--vscode-dropdown-background);
                    padding: 5px;
                    border-radius: 3px;
                }
                
                select {
                    background: var(--vscode-dropdown-background);
                    color: var(--vscode-dropdown-foreground);
                    border: 1px solid var(--vscode-dropdown-border);
                    padding: 3px;
                    border-radius: 3px;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">${document.title}</div>
                <div class="stats">
                    <div class="stat-item">
                        <span>Stage:</span>
                        <span>${document.stage}</span>
                    </div>
                    <div class="stat-item">
                        <span>Abstractions:</span>
                        <span>${document.safetyMetadata.abstractedElements.length}</span>
                    </div>
                    <div class="stat-item">
                        <span>Safety:</span>
                        <span class="safety-score ${this.getSafetyClass(document.safetyMetadata.safetyScore)}">
                            ${(document.safetyMetadata.safetyScore * 100).toFixed(0)}%
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="toolbar">
                <div class="compaction-selector">
                    <label for="compaction">Compaction:</label>
                    <select id="compaction" onchange="changeCompaction(this.value)">
                        <option value="aggressive" ${document.compactionMetadata.strategy === 'aggressive' ? 'selected' : ''}>
                            Aggressive
                        </option>
                        <option value="balanced" ${document.compactionMetadata.strategy === 'balanced' ? 'selected' : ''}>
                            Balanced
                        </option>
                        <option value="conservative" ${document.compactionMetadata.strategy === 'conservative' ? 'selected' : ''}>
                            Conservative
                        </option>
                    </select>
                </div>
                <button class="button" onclick="openInEditor()">
                    Open in Editor
                </button>
            </div>
            
            <div class="content" id="content">
                ${highlightedContent}
            </div>
            
            <script>
                const vscode = acquireVsCodeApi();
                
                // Handle abstracted element clicks
                document.addEventListener('click', (e) => {
                    if (e.target.classList.contains('abstracted')) {
                        const original = e.target.getAttribute('data-original');
                        if (original) {
                            vscode.postMessage({
                                command: 'showOriginal',
                                reference: original
                            });
                        }
                    }
                });
                
                // Handle real-time updates
                window.addEventListener('message', event => {
                    const message = event.data;
                    switch (message.type) {
                        case 'contentUpdate':
                            document.getElementById('content').innerHTML = message.content;
                            updateStats(message.stats);
                            break;
                        case 'fullUpdate':
                            updateDocument(message.document);
                            break;
                    }
                });
                
                function changeCompaction(strategy) {
                    vscode.postMessage({
                        command: 'changeCompactionStrategy',
                        strategy: strategy
                    });
                }
                
                function openInEditor() {
                    vscode.postMessage({
                        command: 'openDocument'
                    });
                }
                
                function updateStats(stats) {
                    // Update statistics in header
                    const statsElements = document.querySelectorAll('.stat-item span:last-child');
                    if (statsElements[1]) {
                        statsElements[1].textContent = stats.totalAbstractions;
                    }
                    if (statsElements[2]) {
                        const score = stats.safetyScore * 100;
                        statsElements[2].textContent = score.toFixed(0) + '%';
                        statsElements[2].className = 'safety-score ' + 
                            (score >= 80 ? 'safety-high' : score >= 60 ? 'safety-medium' : 'safety-low');
                    }
                }
                
                function updateDocument(doc) {
                    document.querySelector('.title').textContent = doc.title;
                    document.getElementById('content').innerHTML = doc.content;
                    // Update other UI elements as needed
                }
            </script>
        </body>
        </html>`;
    }

    /**
     * Highlight abstracted elements in content
     */
    private static highlightAbstractions(content: string): string {
        // Common abstraction patterns to highlight
        const patterns = [
            { pattern: /<project>/g, original: 'project root' },
            { pattern: /<api>/g, original: 'API endpoint' },
            { pattern: /<home>/g, original: 'home directory' },
            { pattern: /<config>/g, original: 'configuration' },
            { pattern: /<credentials>/g, original: 'credentials' },
            { pattern: /<token:[^>]+>/g, original: 'token' }
        ];

        let highlighted = content;
        
        patterns.forEach(({ pattern, original }) => {
            highlighted = highlighted.replace(pattern, (match) => {
                return `<span class="abstracted" data-original="${original}" title="Abstracted ${original}">${match}</span>`;
            });
        });

        // Add evolution indicators where applicable
        highlighted = highlighted.replace(/(\w+)\.(\w+)⁺/g, (match, p1, p2) => {
            return `${p1}.${p2}<span class="evolution-indicator" title="This reference has evolved">⁺</span>`;
        });

        return highlighted;
    }

    /**
     * Get safety score CSS class
     */
    private static getSafetyClass(score: number): string {
        if (score >= 0.8) return 'safety-high';
        if (score >= 0.6) return 'safety-medium';
        return 'safety-low';
    }

    /**
     * Show original reference in tooltip
     */
    private static async showOriginalReference(reference: string): Promise<void> {
        await vscode.window.showInformationMessage(
            `Original reference: ${reference}`,
            'Copy'
        ).then(selection => {
            if (selection === 'Copy') {
                vscode.env.clipboard.writeText(reference);
            }
        });
    }

    /**
     * Handle compaction strategy change
     */
    private static async handleCompactionChange(
        document: LivingDocument,
        strategy: string
    ): Promise<void> {
        // This would trigger re-compaction with new strategy
        vscode.commands.executeCommand('coachntt.compactDocument', {
            documentId: document.id,
            strategy
        });
    }
}