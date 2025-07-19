import * as vscode from 'vscode';
import { SearchResult, NodeType } from './code-search-engine';
import { Logger } from '../../utils/logger';
import { EventEmitter } from 'events';

export interface GroupedResults {
    byFile: Map<string, SearchResult[]>;
    byType: Map<NodeType, SearchResult[]>;
    byScore: SearchResult[];
}

export interface ResultPresentation {
    summary: string;
    voiceResponse: string;
    quickPicks: vscode.QuickPickItem[];
    decorations: Map<string, vscode.TextEditorDecorationType[]>;
}

export interface NavigationHistory {
    query: string;
    timestamp: Date;
    results: SearchResult[];
    selectedIndex?: number;
}

export class QueryResultManager extends EventEmitter {
    private logger: Logger;
    private currentResults: SearchResult[];
    private navigationHistory: NavigationHistory[];
    private maxHistorySize = 50;
    private decorationType: vscode.TextEditorDecorationType;
    
    constructor() {
        super();
        this.logger = Logger.getInstance();
        this.currentResults = [];
        this.navigationHistory = [];
        
        // Create decoration type for highlighting results
        this.decorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: new vscode.ThemeColor('editor.findMatchHighlightBackground'),
            border: '1px solid',
            borderColor: new vscode.ThemeColor('editor.findMatchHighlightBorder'),
            overviewRulerColor: new vscode.ThemeColor('editorOverviewRuler.findMatchForeground'),
            overviewRulerLane: vscode.OverviewRulerLane.Center
        });
    }
    
    public processResults(results: SearchResult[], query: string): GroupedResults {
        this.currentResults = results;
        
        // Add to history
        this.addToHistory(query, results);
        
        // Group results
        const grouped = this.groupResults(results);
        
        // Emit event
        this.emit('resultsProcessed', { results, grouped });
        
        return grouped;
    }
    
    public async navigateToResult(result: SearchResult): Promise<void> {
        try {
            // Open the document
            const document = await vscode.workspace.openTextDocument(result.uri);
            const editor = await vscode.window.showTextDocument(document);
            
            // Set cursor position
            editor.selection = new vscode.Selection(result.range.start, result.range.start);
            editor.revealRange(result.range, vscode.TextEditorRevealType.InCenter);
            
            // Highlight the result
            this.highlightResult(editor, result);
            
            // Update history
            const currentHistory = this.navigationHistory[0];
            if (currentHistory) {
                currentHistory.selectedIndex = this.currentResults.indexOf(result);
            }
            
            this.emit('navigatedToResult', result);
            this.logger.info(`Navigated to ${result.name} at ${result.uri.fsPath}:${result.range.start.line}`);
            
        } catch (error) {
            this.logger.error('Failed to navigate to result', error);
            throw error;
        }
    }
    
    public async navigateNext(): Promise<void> {
        if (this.currentResults.length === 0) {
            return;
        }
        
        const currentHistory = this.navigationHistory[0];
        if (!currentHistory) {
            return;
        }
        
        const currentIndex = currentHistory.selectedIndex ?? -1;
        const nextIndex = (currentIndex + 1) % this.currentResults.length;
        
        await this.navigateToResult(this.currentResults[nextIndex]);
    }
    
    public async navigatePrevious(): Promise<void> {
        if (this.currentResults.length === 0) {
            return;
        }
        
        const currentHistory = this.navigationHistory[0];
        if (!currentHistory) {
            return;
        }
        
        const currentIndex = currentHistory.selectedIndex ?? 0;
        const prevIndex = currentIndex === 0 ? 
            this.currentResults.length - 1 : currentIndex - 1;
        
        await this.navigateToResult(this.currentResults[prevIndex]);
    }
    
    public createPresentation(
        results: SearchResult[],
        grouped: GroupedResults
    ): ResultPresentation {
        const summary = this.createSummary(results, grouped);
        const voiceResponse = this.createVoiceResponse(results, grouped);
        const quickPicks = this.createQuickPicks(results);
        const decorations = this.createDecorations(results);
        
        return {
            summary,
            voiceResponse,
            quickPicks,
            decorations
        };
    }
    
    public async showQuickPick(): Promise<SearchResult | undefined> {
        if (this.currentResults.length === 0) {
            vscode.window.showInformationMessage('No results to show');
            return undefined;
        }
        
        const presentation = this.createPresentation(
            this.currentResults,
            this.groupResults(this.currentResults)
        );
        
        const selected = await vscode.window.showQuickPick(presentation.quickPicks, {
            placeHolder: 'Select a result to navigate to',
            matchOnDescription: true,
            matchOnDetail: true
        });
        
        if (selected) {
            const index = presentation.quickPicks.indexOf(selected);
            const result = this.currentResults[index];
            await this.navigateToResult(result);
            return result;
        }
        
        return undefined;
    }
    
    private groupResults(results: SearchResult[]): GroupedResults {
        const byFile = new Map<string, SearchResult[]>();
        const byType = new Map<NodeType, SearchResult[]>();
        
        for (const result of results) {
            // Group by file
            const fileName = result.uri.fsPath;
            if (!byFile.has(fileName)) {
                byFile.set(fileName, []);
            }
            byFile.get(fileName)!.push(result);
            
            // Group by type
            if (!byType.has(result.type)) {
                byType.set(result.type, []);
            }
            byType.get(result.type)!.push(result);
        }
        
        // Sort by score
        const byScore = [...results].sort((a, b) => b.score - a.score);
        
        return { byFile, byType, byScore };
    }
    
    private createSummary(results: SearchResult[], grouped: GroupedResults): string {
        if (results.length === 0) {
            return 'No results found';
        }
        
        const lines: string[] = [];
        lines.push(`Found ${results.length} results in ${grouped.byFile.size} files`);
        
        // Type breakdown
        lines.push('\nBy type:');
        for (const [type, typeResults] of grouped.byType) {
            lines.push(`  ${type}: ${typeResults.length}`);
        }
        
        // Top results
        lines.push('\nTop results:');
        const topResults = grouped.byScore.slice(0, 5);
        for (const result of topResults) {
            const fileName = vscode.workspace.asRelativePath(result.uri);
            lines.push(`  ${result.name} (${result.type}) in ${fileName}:${result.range.start.line + 1}`);
        }
        
        return lines.join('\n');
    }
    
    private createVoiceResponse(results: SearchResult[], grouped: GroupedResults): string {
        if (results.length === 0) {
            return 'No results found for your query';
        }
        
        if (results.length === 1) {
            const result = results[0];
            const fileName = vscode.workspace.asRelativePath(result.uri);
            return `Found ${result.name} ${result.type} in ${fileName} at line ${result.range.start.line + 1}`;
        }
        
        const topResult = grouped.byScore[0];
        const fileName = vscode.workspace.asRelativePath(topResult.uri);
        
        return `Found ${results.length} results. The best match is ${topResult.name} ${topResult.type} ` +
               `in ${fileName} at line ${topResult.range.start.line + 1}. ` +
               `Say 'show results' to see all results or 'next' to navigate through them.`;
    }
    
    private createQuickPicks(results: SearchResult[]): vscode.QuickPickItem[] {
        return results.map((result, index) => {
            const fileName = vscode.workspace.asRelativePath(result.uri);
            const icon = this.getIconForType(result.type);
            
            return {
                label: `${icon} ${result.name}`,
                description: `${result.type} in ${fileName}`,
                detail: `Line ${result.range.start.line + 1} • Score: ${result.score.toFixed(2)}`,
                alwaysShow: index < 10
            };
        });
    }
    
    private createDecorations(results: SearchResult[]): Map<string, vscode.TextEditorDecorationType[]> {
        const decorations = new Map<string, vscode.TextEditorDecorationType[]>();
        
        // Group by file
        const byFile = new Map<string, SearchResult[]>();
        for (const result of results) {
            const key = result.uri.toString();
            if (!byFile.has(key)) {
                byFile.set(key, []);
            }
            byFile.get(key)!.push(result);
        }
        
        // Create decorations for each file
        for (const [fileUri, fileResults] of byFile) {
            const decos: vscode.TextEditorDecorationType[] = [];
            
            for (const result of fileResults) {
                const deco = vscode.window.createTextEditorDecorationType({
                    backgroundColor: new vscode.ThemeColor('editor.findMatchHighlightBackground'),
                    border: '1px solid',
                    borderColor: new vscode.ThemeColor('editor.findMatchHighlightBorder'),
                    overviewRulerColor: new vscode.ThemeColor('editorOverviewRuler.findMatchForeground'),
                    overviewRulerLane: vscode.OverviewRulerLane.Center,
                    after: {
                        contentText: ` [${result.type}: score ${result.score.toFixed(2)}]`,
                        color: new vscode.ThemeColor('editorCodeLens.foreground'),
                        fontStyle: 'italic'
                    }
                });
                decos.push(deco);
            }
            
            decorations.set(fileUri, decos);
        }
        
        return decorations;
    }
    
    private highlightResult(editor: vscode.TextEditor, result: SearchResult): void {
        // Clear previous decorations
        editor.setDecorations(this.decorationType, []);
        
        // Apply new decoration
        editor.setDecorations(this.decorationType, [result.range]);
        
        // Clear after 3 seconds
        setTimeout(() => {
            if (editor && !editor.document.isClosed) {
                editor.setDecorations(this.decorationType, []);
            }
        }, 3000);
    }
    
    private getIconForType(type: NodeType): string {
        const icons: Record<NodeType, string> = {
            'function': '𝑓',
            'class': '◆',
            'interface': '◇',
            'method': '→',
            'property': '•',
            'variable': '𝑥',
            'type': '𝑇',
            'enum': '∈',
            'import': '↓',
            'export': '↑'
        };
        
        return icons[type] || '○';
    }
    
    private addToHistory(query: string, results: SearchResult[]): void {
        const entry: NavigationHistory = {
            query,
            timestamp: new Date(),
            results: [...results]
        };
        
        this.navigationHistory.unshift(entry);
        
        // Limit history size
        if (this.navigationHistory.length > this.maxHistorySize) {
            this.navigationHistory = this.navigationHistory.slice(0, this.maxHistorySize);
        }
    }
    
    public getHistory(): NavigationHistory[] {
        return [...this.navigationHistory];
    }
    
    public clearHistory(): void {
        this.navigationHistory = [];
        this.currentResults = [];
    }
    
    public dispose(): void {
        this.decorationType.dispose();
        this.removeAllListeners();
    }
}