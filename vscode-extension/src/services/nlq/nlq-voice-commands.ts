import * as vscode from 'vscode';
import { VoiceCommandRegistry } from '../voice-command/voice-command-registry';
import { VoiceFeedbackService } from '../voice-command/voice-feedback-service';
import { NLQParser } from './nlq-parser';
import { SemanticAnalyzer } from './semantic-analyzer';
import { CodeSearchEngine } from './code-search-engine';
import { QueryResultManager } from './query-result-manager';
import { Logger } from '../../utils/logger';

export class NLQVoiceCommands {
    private static instance: NLQVoiceCommands;
    private logger: Logger;
    private registry: VoiceCommandRegistry;
    private feedback: VoiceFeedbackService;
    private nlqParser: NLQParser;
    private semanticAnalyzer: SemanticAnalyzer;
    private searchEngine: CodeSearchEngine;
    private resultManager: QueryResultManager;
    private isSearching = false;
    
    private constructor() {
        this.logger = Logger.getInstance();
        this.registry = VoiceCommandRegistry.getInstance();
        this.feedback = VoiceFeedbackService.getInstance();
        this.nlqParser = new NLQParser();
        this.semanticAnalyzer = new SemanticAnalyzer();
        this.searchEngine = new CodeSearchEngine();
        this.resultManager = new QueryResultManager();
    }
    
    public static getInstance(): NLQVoiceCommands {
        if (!NLQVoiceCommands.instance) {
            NLQVoiceCommands.instance = new NLQVoiceCommands();
        }
        return NLQVoiceCommands.instance;
    }
    
    public registerCommands(): void {
        // Register NLQ command patterns
        this.registry.registerCommand({
            id: 'nlq.search',
            name: 'Natural Language Search',
            category: 'search',
            patterns: [
                /^(?:find|show|where|what|search)/i
            ],
            handler: this.handleNLQSearch.bind(this),
            contextValidation: () => true,
            description: 'Search code using natural language'
        });
        
        this.registry.registerCommand({
            id: 'nlq.showResults',
            name: 'Show Search Results',
            category: 'search',
            patterns: [
                /show results/i,
                /list results/i,
                /show all results/i
            ],
            handler: this.handleShowResults.bind(this),
            contextValidation: () => this.resultManager['currentResults'].length > 0,
            description: 'Show all search results in quick pick'
        });
        
        this.registry.registerCommand({
            id: 'nlq.nextResult',
            name: 'Next Search Result',
            category: 'search',
            patterns: [
                /next result/i,
                /next/i,
                /go to next/i
            ],
            handler: this.handleNextResult.bind(this),
            contextValidation: () => this.resultManager['currentResults'].length > 0,
            description: 'Navigate to next search result'
        });
        
        this.registry.registerCommand({
            id: 'nlq.previousResult',
            name: 'Previous Search Result',
            category: 'search',
            patterns: [
                /previous result/i,
                /previous/i,
                /go to previous/i,
                /back/i
            ],
            handler: this.handlePreviousResult.bind(this),
            contextValidation: () => this.resultManager['currentResults'].length > 0,
            description: 'Navigate to previous search result'
        });
        
        this.registry.registerCommand({
            id: 'nlq.explainCode',
            name: 'Explain Code',
            category: 'search',
            patterns: [
                /explain (.+)/i,
                /what does (.+) do/i,
                /how does (.+) work/i
            ],
            handler: this.handleExplainCode.bind(this),
            contextValidation: () => true,
            description: 'Explain code functionality'
        });
        
        this.logger.info('NLQ voice commands registered');
    }
    
    private async handleNLQSearch(command: any): Promise<void> {
        if (this.isSearching) {
            await this.feedback.provideFeedback({
                message: 'Search already in progress',
                type: 'warning',
                visual: 'notification'
            });
            return;
        }
        
        this.isSearching = true;
        
        try {
            // Parse the natural language query
            const nlQuery = await this.nlqParser.parse(command.raw, {
                currentFile: vscode.window.activeTextEditor?.document.uri.fsPath,
                selectedText: vscode.window.activeTextEditor?.document.getText(
                    vscode.window.activeTextEditor.selection
                )
            });
            
            if (!nlQuery) {
                await this.feedback.provideFeedback({
                    message: 'Could not understand the query',
                    type: 'error',
                    speak: true
                });
                return;
            }
            
            // Provide initial feedback
            await this.feedback.provideFeedback({
                message: `Searching for: ${nlQuery.normalized}`,
                type: 'info',
                visual: 'status',
                speak: true
            });
            
            // Analyze semantically
            const semanticQuery = this.semanticAnalyzer.analyze(nlQuery);
            
            // Perform search
            const results = await this.searchEngine.search(semanticQuery);
            
            // Process results
            const grouped = this.resultManager.processResults(results, nlQuery.raw);
            const presentation = this.resultManager.createPresentation(results, grouped);
            
            // Provide feedback
            await this.feedback.provideFeedback({
                message: presentation.voiceResponse,
                type: results.length > 0 ? 'success' : 'warning',
                speak: true,
                visual: 'notification'
            });
            
            // Navigate to first result if found
            if (results.length > 0) {
                await this.resultManager.navigateToResult(results[0]);
            }
            
        } catch (error) {
            this.logger.error('NLQ search failed', error);
            await this.feedback.provideFeedback({
                message: 'Search failed. Please try again.',
                type: 'error',
                speak: true
            });
        } finally {
            this.isSearching = false;
        }
    }
    
    private async handleShowResults(): Promise<void> {
        try {
            const selected = await this.resultManager.showQuickPick();
            if (selected) {
                await this.feedback.provideFeedback({
                    message: `Navigated to ${selected.name}`,
                    type: 'success',
                    speak: true
                });
            }
        } catch (error) {
            this.logger.error('Failed to show results', error);
            await this.feedback.provideFeedback({
                message: 'Failed to show results',
                type: 'error',
                speak: true
            });
        }
    }
    
    private async handleNextResult(): Promise<void> {
        try {
            await this.resultManager.navigateNext();
            await this.feedback.provideFeedback({
                message: 'Next result',
                type: 'info',
                visual: 'status'
            });
        } catch (error) {
            this.logger.error('Failed to navigate to next result', error);
            await this.feedback.provideFeedback({
                message: 'Failed to navigate to next result',
                type: 'error',
                speak: true
            });
        }
    }
    
    private async handlePreviousResult(): Promise<void> {
        try {
            await this.resultManager.navigatePrevious();
            await this.feedback.provideFeedback({
                message: 'Previous result',
                type: 'info',
                visual: 'status'
            });
        } catch (error) {
            this.logger.error('Failed to navigate to previous result', error);
            await this.feedback.provideFeedback({
                message: 'Failed to navigate to previous result',
                type: 'error',
                speak: true
            });
        }
    }
    
    private async handleExplainCode(command: any): Promise<void> {
        // For now, redirect to search with explain intent
        const explainQuery = `explain ${command.parameters.query || command.raw}`;
        await this.handleNLQSearch({
            ...command,
            raw: explainQuery
        });
    }
    
    public dispose(): void {
        this.resultManager.dispose();
    }
}