import * as vscode from 'vscode';
import * as path from 'path';
import { LivingDocument, DocumentRelevance } from '../types/living-document.types';
import { ContextWindowManager } from './context-window-manager';

/**
 * Session-aware document manager for intelligent loading
 * Selects relevant documents based on current coding context
 */
export class DocumentSessionManager {
    private allDocuments: Map<string, LivingDocument> = new Map();
    private contextWindowManager: ContextWindowManager;
    private relevanceCache: Map<string, RelevanceScore> = new Map();
    private lastContextUpdate: Date = new Date();

    constructor(
        private contextBudget: number = 0.3 // 30% of context window for documents
    ) {
        this.contextWindowManager = new ContextWindowManager();
        this.setupFileWatchers();
    }

    /**
     * Get documents most relevant to current workspace context
     */
    async getRelevantDocuments(
        maxDocuments: number = 5
    ): Promise<LivingDocument[]> {
        const context = await this.getCurrentWorkspaceContext();
        
        // Score all documents by relevance
        const scoredDocs = await Promise.all(
            Array.from(this.allDocuments.values()).map(async doc => ({
                doc,
                score: await this.calculateRelevance(doc, context)
            }))
        );

        // Sort by score and filter by context budget
        const sorted = scoredDocs.sort((a, b) => b.score - a.score);
        
        return this.selectOptimalDocuments(sorted, maxDocuments);
    }

    /**
     * Add or update a document in the session
     */
    async addDocument(document: LivingDocument): Promise<void> {
        this.allDocuments.set(document.id, document);
        
        // Clear relevance cache for this document
        this.relevanceCache.delete(document.id);
        
        // Check if we need to update loaded documents
        if (await this.shouldUpdateLoadedDocuments(document)) {
            vscode.commands.executeCommand('coachntt.refreshDocumentContext');
        }
    }

    /**
     * Get documents related to specific files
     */
    async getDocumentsForFiles(filePaths: string[]): Promise<LivingDocument[]> {
        const relevantDocs: LivingDocument[] = [];
        
        for (const doc of this.allDocuments.values()) {
            // Check if document references any of the files
            const references = this.extractFileReferences(doc.content);
            const hasRelevantRef = references.some(ref => 
                filePaths.some(filePath => this.isRelatedPath(ref, filePath))
            );
            
            if (hasRelevantRef) {
                relevantDocs.push(doc);
            }
        }
        
        return relevantDocs;
    }

    /**
     * Get documents by category for current context
     */
    async getDocumentsByCategory(
        category: string
    ): Promise<LivingDocument[]> {
        const context = await this.getCurrentWorkspaceContext();
        
        return Array.from(this.allDocuments.values())
            .filter(doc => {
                // Check document metadata for category
                const frontmatter = this.parseFrontmatter(doc.content);
                return frontmatter.category === category ||
                       frontmatter.tags?.includes(category);
            })
            .sort((a, b) => {
                // Sort by relevance to current context
                const scoreA = this.quickRelevanceScore(a, context);
                const scoreB = this.quickRelevanceScore(b, context);
                return scoreB - scoreA;
            });
    }

    // Private methods

    private async getCurrentWorkspaceContext(): Promise<WorkspaceContext> {
        const activeEditor = vscode.window.activeTextEditor;
        const recentFiles = await this.getRecentlyEditedFiles();
        const gitBranch = await this.getCurrentGitBranch();
        const activeSymbols = await this.getActiveSymbols();
        
        return {
            currentFile: activeEditor?.document.fileName,
            recentFiles,
            gitBranch,
            activeSymbols,
            workspaceFolder: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
            timestamp: new Date()
        };
    }

    private async calculateRelevance(
        document: LivingDocument,
        context: WorkspaceContext
    ): Promise<number> {
        // Check cache first
        const cacheKey = `${document.id}-${context.timestamp.getTime()}`;
        if (this.relevanceCache.has(cacheKey)) {
            return this.relevanceCache.get(cacheKey)!.score;
        }

        let score = 0;
        const weights = {
            currentFile: 0.4,
            recentFiles: 0.3,
            symbols: 0.2,
            branch: 0.1
        };

        // Current file relevance
        if (context.currentFile) {
            const fileRefs = this.extractFileReferences(document.content);
            if (fileRefs.some(ref => this.isRelatedPath(ref, context.currentFile!))) {
                score += weights.currentFile;
            }
        }

        // Recent files relevance
        const recentRelevance = context.recentFiles.reduce((acc, file) => {
            const fileRefs = this.extractFileReferences(document.content);
            return acc + (fileRefs.some(ref => this.isRelatedPath(ref, file.path)) ? 1 : 0);
        }, 0) / Math.max(context.recentFiles.length, 1);
        score += recentRelevance * weights.recentFiles;

        // Symbol relevance
        const symbolMatches = context.activeSymbols.filter(symbol =>
            document.content.includes(symbol)
        ).length;
        score += (symbolMatches / Math.max(context.activeSymbols.length, 1)) * weights.symbols;

        // Git branch relevance
        if (context.gitBranch && document.content.includes(context.gitBranch)) {
            score += weights.branch;
        }

        // Boost score based on document metadata
        score *= this.getDocumentBoost(document);

        // Cache the result
        this.relevanceCache.set(cacheKey, { score, timestamp: new Date() });

        return score;
    }

    private selectOptimalDocuments(
        scoredDocs: Array<{ doc: LivingDocument; score: number }>,
        maxDocuments: number
    ): LivingDocument[] {
        const selected: LivingDocument[] = [];
        let currentTokens = 0;
        const maxTokens = this.contextWindowManager.getAvailableTokens() * this.contextBudget;

        for (const { doc, score } of scoredDocs) {
            if (selected.length >= maxDocuments) break;
            
            const docTokens = this.estimateTokens(doc.abstractedContent);
            if (currentTokens + docTokens <= maxTokens) {
                selected.push(doc);
                currentTokens += docTokens;
            }
        }

        return selected;
    }

    private async getRecentlyEditedFiles(
        limit: number = 10
    ): Promise<Array<{ path: string; timestamp: Date }>> {
        // Get recently opened files from VSCode
        const recentFiles: Array<{ path: string; timestamp: Date }> = [];
        
        // This would integrate with VSCode's recently opened files API
        // For now, we'll use workspace text documents
        vscode.workspace.textDocuments.forEach(doc => {
            if (!doc.isUntitled && doc.isDirty) {
                recentFiles.push({
                    path: doc.fileName,
                    timestamp: new Date() // Would use actual modification time
                });
            }
        });

        return recentFiles.slice(0, limit);
    }

    private async getCurrentGitBranch(): Promise<string | null> {
        try {
            const gitExtension = vscode.extensions.getExtension('vscode.git')?.exports;
            if (!gitExtension) return null;
            
            const api = gitExtension.getAPI(1);
            const repo = api.repositories[0];
            
            return repo?.state?.HEAD?.name || null;
        } catch {
            return null;
        }
    }

    private async getActiveSymbols(): Promise<string[]> {
        const symbols: string[] = [];
        const activeEditor = vscode.window.activeTextEditor;
        
        if (!activeEditor) return symbols;

        try {
            const documentSymbols = await vscode.commands.executeCommand<vscode.DocumentSymbol[]>(
                'vscode.executeDocumentSymbolProvider',
                activeEditor.document.uri
            );

            if (documentSymbols) {
                this.extractSymbolNames(documentSymbols, symbols);
            }
        } catch {
            // Symbol provider not available
        }

        return symbols;
    }

    private extractSymbolNames(
        symbols: vscode.DocumentSymbol[],
        result: string[]
    ): void {
        for (const symbol of symbols) {
            result.push(symbol.name);
            if (symbol.children) {
                this.extractSymbolNames(symbol.children, result);
            }
        }
    }

    private extractFileReferences(content: string): string[] {
        const references: string[] = [];
        
        // Match common file path patterns
        const patterns = [
            /<project>\/([^>\s]+)/g,
            /\[([^\]]+)\]\(([^)]+)\)/g, // Markdown links
            /(?:from|import)\s+['"]([^'"]+)['"]/g, // Import statements
            /(?:src|href)=["']([^"']+)["']/g // HTML attributes
        ];

        patterns.forEach(pattern => {
            let match;
            while ((match = pattern.exec(content)) !== null) {
                references.push(match[1] || match[2]);
            }
        });

        return [...new Set(references)];
    }

    private isRelatedPath(ref: string, filePath: string): boolean {
        // Normalize paths for comparison
        const normalizedRef = path.normalize(ref).toLowerCase();
        const normalizedPath = path.normalize(filePath).toLowerCase();
        
        // Check if paths are related
        return normalizedPath.includes(normalizedRef) ||
               normalizedRef.includes(path.basename(normalizedPath)) ||
               this.haveSimilarComponents(normalizedRef, normalizedPath);
    }

    private haveSimilarComponents(path1: string, path2: string): boolean {
        const parts1 = path1.split(/[\/\\]/).filter(p => p);
        const parts2 = path2.split(/[\/\\]/).filter(p => p);
        
        // Count matching components
        const matches = parts1.filter(part => parts2.includes(part)).length;
        
        // Consider related if more than 50% of components match
        return matches > Math.min(parts1.length, parts2.length) * 0.5;
    }

    private parseFrontmatter(content: string): any {
        const match = content.match(/^---\n([\s\S]*?)\n---/);
        if (!match) return {};
        
        try {
            // Simple YAML parsing (would use proper YAML parser in production)
            const frontmatter: any = {};
            const lines = match[1].split('\n');
            
            lines.forEach(line => {
                const [key, ...valueParts] = line.split(':');
                if (key && valueParts.length) {
                    const value = valueParts.join(':').trim();
                    frontmatter[key.trim()] = value.replace(/^["']|["']$/g, '');
                }
            });
            
            return frontmatter;
        } catch {
            return {};
        }
    }

    private getDocumentBoost(document: LivingDocument): number {
        let boost = 1.0;
        
        // Boost recently updated documents
        const daysSinceUpdate = (Date.now() - document.updatedAt.getTime()) / (1000 * 60 * 60 * 24);
        if (daysSinceUpdate < 1) boost *= 1.5;
        else if (daysSinceUpdate < 7) boost *= 1.2;
        
        // Boost frequently accessed documents
        if (document.accessCount > 10) boost *= 1.3;
        else if (document.accessCount > 5) boost *= 1.1;
        
        // Boost based on stage
        if (document.stage === 'active') boost *= 1.2;
        else if (document.stage === 'archived') boost *= 0.5;
        
        return boost;
    }

    private quickRelevanceScore(
        document: LivingDocument,
        context: WorkspaceContext
    ): number {
        // Quick scoring without full calculation
        let score = 0;
        
        if (context.currentFile && document.content.includes(path.basename(context.currentFile))) {
            score += 0.5;
        }
        
        if (document.stage === 'active') score += 0.2;
        if (document.accessCount > 5) score += 0.1;
        
        const daysSinceUpdate = (Date.now() - document.updatedAt.getTime()) / (1000 * 60 * 60 * 24);
        if (daysSinceUpdate < 7) score += 0.2;
        
        return score;
    }

    private estimateTokens(content: string): number {
        // Rough estimation: 1 token ≈ 4 characters
        return Math.ceil(content.length / 4);
    }

    private async shouldUpdateLoadedDocuments(
        newDoc: LivingDocument
    ): Promise<boolean> {
        const context = await this.getCurrentWorkspaceContext();
        const relevance = await this.calculateRelevance(newDoc, context);
        
        // Check if this document is more relevant than currently loaded ones
        const currentDocs = await this.getRelevantDocuments();
        const lowestScore = currentDocs.length > 0
            ? Math.min(...await Promise.all(
                currentDocs.map(d => this.calculateRelevance(d, context))
              ))
            : 0;
        
        return relevance > lowestScore;
    }

    private setupFileWatchers(): void {
        // Watch for .CoachNTT file changes
        const watcher = vscode.workspace.createFileSystemWatcher('**/*.CoachNTT');
        
        watcher.onDidCreate(uri => {
            vscode.commands.executeCommand('coachntt.loadDocument', uri);
        });
        
        watcher.onDidChange(uri => {
            vscode.commands.executeCommand('coachntt.reloadDocument', uri);
        });
        
        watcher.onDidDelete(uri => {
            // Remove from session
            const docId = this.getDocumentIdFromUri(uri);
            if (docId) {
                this.allDocuments.delete(docId);
            }
        });
    }

    private getDocumentIdFromUri(uri: vscode.Uri): string | null {
        for (const [id, doc] of this.allDocuments) {
            if (doc.uri.toString() === uri.toString()) {
                return id;
            }
        }
        return null;
    }
}

interface WorkspaceContext {
    currentFile?: string;
    recentFiles: Array<{ path: string; timestamp: Date }>;
    gitBranch: string | null;
    activeSymbols: string[];
    workspaceFolder?: string;
    timestamp: Date;
}

interface RelevanceScore {
    score: number;
    timestamp: Date;
}