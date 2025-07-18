import * as vscode from 'vscode';
import * as path from 'path';
import {
    LivingDocument,
    DocumentStage,
    DocumentCategory,
    DocumentTreeItem,
    DocumentUpdateEvent
} from '../types/living-document.types';
import { Logger } from '../utils/logger';

/**
 * Tree data provider for Living Documents
 */
export class DocumentTreeProvider implements vscode.TreeDataProvider<DocumentTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<DocumentTreeItem | undefined | null | void> = 
        new vscode.EventEmitter<DocumentTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<DocumentTreeItem | undefined | null | void> = 
        this._onDidChangeTreeData.event;
    
    private logger: Logger;
    private documents: Map<string, LivingDocument>;
    private categories: Map<DocumentCategory, LivingDocument[]>;
    private showArchived: boolean = false;
    
    constructor() {
        this.logger = Logger.getInstance();
        this.documents = new Map();
        this.categories = new Map();
        
        // Initialize categories
        Object.values(DocumentCategory).forEach(category => {
            this.categories.set(category as DocumentCategory, []);
        });
    }
    
    /**
     * Refresh the tree view
     */
    public refresh(element?: DocumentTreeItem): void {
        this._onDidChangeTreeData.fire(element);
    }
    
    /**
     * Get tree item
     */
    public getTreeItem(element: DocumentTreeItem): vscode.TreeItem {
        return element;
    }
    
    /**
     * Get children for tree item
     */
    public async getChildren(element?: DocumentTreeItem): Promise<DocumentTreeItem[]> {
        if (!element) {
            // Root level - show categories
            return this.getCategoryNodes();
        }
        
        if (element.contextValue === 'category') {
            // Show documents in category
            const category = element.label as DocumentCategory;
            return this.getDocumentNodes(category);
        }
        
        return [];
    }
    
    /**
     * Get parent for tree item
     */
    public getParent(element: DocumentTreeItem): vscode.TreeItem | undefined {
        if (element.contextValue === 'document' && element.document) {
            // Find category parent
            const category = element.document.metadata.category;
            return this.createCategoryNode(category);
        }
        return undefined;
    }
    
    /**
     * Create category nodes
     */
    private getCategoryNodes(): DocumentTreeItem[] {
        const nodes: DocumentTreeItem[] = [];
        
        // Active categories
        this.categories.forEach((documents, category) => {
            const activeDocuments = documents.filter(d => 
                d.stage !== DocumentStage.Archived || this.showArchived
            );
            
            if (activeDocuments.length > 0) {
                nodes.push(this.createCategoryNode(category, activeDocuments.length));
            }
        });
        
        // Add archived category if showing archived
        if (this.showArchived) {
            const archivedCount = Array.from(this.documents.values())
                .filter(d => d.stage === DocumentStage.Archived).length;
            
            if (archivedCount > 0) {
                const archivedNode: DocumentTreeItem = {
                    label: 'Archived',
                    collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
                    contextValue: 'archived',
                    iconPath: new vscode.ThemeIcon('archive'),
                    description: `${archivedCount} documents`,
                    document: undefined as any
                };
                nodes.push(archivedNode);
            }
        }
        
        return nodes;
    }
    
    /**
     * Create a category node
     */
    private createCategoryNode(category: DocumentCategory, count?: number): DocumentTreeItem {
        const iconMap: Record<DocumentCategory, string> = {
            [DocumentCategory.Architecture]: 'symbol-structure',
            [DocumentCategory.API]: 'symbol-interface',
            [DocumentCategory.Tutorial]: 'book',
            [DocumentCategory.Reference]: 'references',
            [DocumentCategory.Planning]: 'checklist',
            [DocumentCategory.Notes]: 'note',
            [DocumentCategory.Other]: 'file-text'
        };
        
        const node: DocumentTreeItem = {
            label: category,
            collapsibleState: vscode.TreeItemCollapsibleState.Collapsed,
            contextValue: 'category',
            iconPath: new vscode.ThemeIcon(iconMap[category] || 'folder'),
            description: count !== undefined ? `${count} documents` : undefined,
            document: undefined as any
        };
        
        return node;
    }
    
    /**
     * Get document nodes for a category
     */
    private getDocumentNodes(category: DocumentCategory): DocumentTreeItem[] {
        const documents = this.categories.get(category) || [];
        
        return documents
            .filter(doc => doc.stage !== DocumentStage.Archived || this.showArchived)
            .sort((a, b) => b.relevanceScore - a.relevanceScore)
            .map(doc => this.createDocumentNode(doc));
    }
    
    /**
     * Create a document node
     */
    private createDocumentNode(document: LivingDocument): DocumentTreeItem {
        const label = document.title || path.basename(document.uri.fsPath);
        
        // Status indicators
        let description = '';
        if (document.stage === DocumentStage.Compacting) {
            description = '(compacting...)';
        } else if (document.compactionRatio < 0.8) {
            description = `(${Math.round(document.compactionRatio * 100)}% size)`;
        }
        
        // Icon based on stage and safety
        let icon = 'file-text';
        if (document.stage === DocumentStage.Archived) {
            icon = 'archive';
        } else if (document.safetyScore < 0.8) {
            icon = 'warning';
        } else if (document.stage === DocumentStage.Compacting) {
            icon = 'sync~spin';
        }
        
        const node: DocumentTreeItem = {
            label,
            description,
            tooltip: this.createDocumentTooltip(document),
            collapsibleState: vscode.TreeItemCollapsibleState.None,
            contextValue: 'document',
            iconPath: new vscode.ThemeIcon(icon),
            command: {
                command: 'coachntt.openLivingDocument',
                title: 'Open Document',
                arguments: [document]
            },
            document
        };
        
        // Add resource URI for theme icon colors
        if (document.safetyScore < 0.8) {
            node.resourceUri = vscode.Uri.parse('unsafe:' + document.id);
        }
        
        return node;
    }
    
    /**
     * Create tooltip for document
     */
    private createDocumentTooltip(document: LivingDocument): vscode.MarkdownString {
        const tooltip = new vscode.MarkdownString();
        
        tooltip.appendMarkdown(`**${document.title}**\n\n`);
        tooltip.appendMarkdown(`📁 ${document.uri.fsPath}\n\n`);
        tooltip.appendMarkdown(`**Safety Score**: ${(document.safetyScore * 100).toFixed(0)}%\n\n`);
        tooltip.appendMarkdown(`**Relevance**: ${(document.relevanceScore * 100).toFixed(0)}%\n\n`);
        tooltip.appendMarkdown(`**Size**: ${document.currentSize} / ${document.originalSize} tokens `);
        tooltip.appendMarkdown(`(${(document.compactionRatio * 100).toFixed(0)}%)\n\n`);
        tooltip.appendMarkdown(`**Last Accessed**: ${this.formatRelativeTime(document.lastAccessed)}\n\n`);
        
        if (document.metadata.tags.length > 0) {
            tooltip.appendMarkdown(`**Tags**: ${document.metadata.tags.join(', ')}\n\n`);
        }
        
        tooltip.isTrusted = true;
        return tooltip;
    }
    
    /**
     * Format relative time
     */
    private formatRelativeTime(date: Date): string {
        const now = Date.now();
        const diff = now - date.getTime();
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        return `${days}d ago`;
    }
    
    /**
     * Add or update a document
     */
    public addDocument(document: LivingDocument): void {
        this.documents.set(document.id, document);
        
        // Update category mapping
        const categoryDocs = this.categories.get(document.metadata.category) || [];
        const existingIndex = categoryDocs.findIndex(d => d.id === document.id);
        
        if (existingIndex >= 0) {
            categoryDocs[existingIndex] = document;
        } else {
            categoryDocs.push(document);
        }
        
        this.categories.set(document.metadata.category, categoryDocs);
        this.refresh();
    }
    
    /**
     * Remove a document
     */
    public removeDocument(documentId: string): void {
        const document = this.documents.get(documentId);
        if (!document) return;
        
        this.documents.delete(documentId);
        
        // Update category mapping
        const categoryDocs = this.categories.get(document.metadata.category) || [];
        const filtered = categoryDocs.filter(d => d.id !== documentId);
        this.categories.set(document.metadata.category, filtered);
        
        this.refresh();
    }
    
    /**
     * Update document
     */
    public updateDocument(event: DocumentUpdateEvent): void {
        const document = this.documents.get(event.documentId);
        if (!document) return;
        
        // Update specific fields based on event type
        switch (event.type) {
            case 'compacted':
                if (event.changes?.compaction) {
                    document.compactionHistory.push(event.changes.compaction);
                    document.compactionRatio = event.changes.compaction.sizeAfter / 
                                              document.originalSize;
                }
                break;
                
            case 'archived':
                document.stage = DocumentStage.Archived;
                break;
                
            case 'updated':
                document.updatedAt = new Date();
                break;
        }
        
        this.refresh();
    }
    
    /**
     * Toggle showing archived documents
     */
    public toggleShowArchived(): void {
        this.showArchived = !this.showArchived;
        this.refresh();
    }
    
    /**
     * Get all documents
     */
    public getAllDocuments(): LivingDocument[] {
        return Array.from(this.documents.values());
    }
    
    /**
     * Get documents by category
     */
    public getDocumentsByCategory(category: DocumentCategory): LivingDocument[] {
        return this.categories.get(category) || [];
    }
    
    /**
     * Search documents
     */
    public searchDocuments(query: string): LivingDocument[] {
        const lowercaseQuery = query.toLowerCase();
        
        return Array.from(this.documents.values()).filter(doc => {
            return doc.title.toLowerCase().includes(lowercaseQuery) ||
                   doc.abstractedContent.toLowerCase().includes(lowercaseQuery) ||
                   doc.metadata.tags.some(tag => tag.toLowerCase().includes(lowercaseQuery));
        });
    }
    
    /**
     * Get document by ID
     */
    public getDocument(documentId: string): LivingDocument | undefined {
        return this.documents.get(documentId);
    }
    
    /**
     * Clear all documents
     */
    public clear(): void {
        this.documents.clear();
        this.categories.forEach(category => category.length = 0);
        this.refresh();
    }
}