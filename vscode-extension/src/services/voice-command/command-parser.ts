import { ParsedCommand } from './voice-command-service';
import { Logger } from '../../utils/logger';

export interface IntentPattern {
    intent: string;
    action: string;
    patterns: RegExp[];
    parameterExtractor?: (match: RegExpMatchArray) => Record<string, any>;
}

export class CommandParser {
    private logger: Logger;
    private intents: IntentPattern[] = [];
    private stopWords = new Set(['the', 'a', 'an', 'to', 'in', 'at', 'on', 'for', 'with']);

    constructor() {
        this.logger = Logger.getInstance();
        this.initializeIntents();
    }

    private initializeIntents(): void {
        // Navigation intents
        this.addIntent({
            intent: 'navigate',
            action: 'goToLine',
            patterns: [
                /(?:go|jump|navigate) to line (\d+)/i,
                /line (\d+)/i,
                /(?:go|jump) (\d+)/i
            ],
            parameterExtractor: (match) => ({ line: match[1] })
        });

        this.addIntent({
            intent: 'navigate',
            action: 'goToFunction',
            patterns: [
                /(?:go|jump|navigate) to (?:function|method) ([\w]+)/i,
                /find (?:function|method) ([\w]+)/i,
                /function ([\w]+)/i
            ],
            parameterExtractor: (match) => ({ function: match[1] })
        });

        // File operations
        this.addIntent({
            intent: 'file',
            action: 'open',
            patterns: [
                /open (?:file )?(.+?)(?:\.|$)/i,
                /show (?:file )?(.+?)(?:\.|$)/i
            ],
            parameterExtractor: (match) => ({ file: match[1].trim() })
        });

        this.addIntent({
            intent: 'file',
            action: 'save',
            patterns: [
                /save(?: file)?/i,
                /save current/i
            ]
        });

        // Selection intents
        this.addIntent({
            intent: 'selection',
            action: 'selectLine',
            patterns: [
                /select line (\d+)/i,
                /highlight line (\d+)/i
            ],
            parameterExtractor: (match) => ({ line: match[1] })
        });

        this.addIntent({
            intent: 'selection',
            action: 'selectWord',
            patterns: [
                /select (?:current )?word/i,
                /highlight (?:current )?word/i
            ]
        });

        // Editing intents
        this.addIntent({
            intent: 'edit',
            action: 'comment',
            patterns: [
                /comment(?: line)?/i,
                /add comment/i,
                /comment (?:this|current)/i
            ]
        });

        this.addIntent({
            intent: 'edit',
            action: 'uncomment',
            patterns: [
                /uncomment(?: line)?/i,
                /remove comment/i,
                /uncomment (?:this|current)/i
            ]
        });

        this.addIntent({
            intent: 'edit',
            action: 'format',
            patterns: [
                /format (?:document|file|code)/i,
                /beautify/i,
                /prettify/i
            ]
        });

        // Search and replace
        this.addIntent({
            intent: 'search',
            action: 'find',
            patterns: [
                /(?:find|search)(?: for)? (.+)/i,
                /look for (.+)/i
            ],
            parameterExtractor: (match) => ({ query: match[1] })
        });

        this.addIntent({
            intent: 'edit',
            action: 'replace',
            patterns: [
                /replace (.+?) with (.+)/i,
                /change (.+?) to (.+)/i
            ],
            parameterExtractor: (match) => ({ find: match[1], replace: match[2] })
        });

        // Extension specific
        this.addIntent({
            intent: 'extension',
            action: 'connect',
            patterns: [
                /connect(?: to)? backend/i,
                /start connection/i
            ]
        });

        this.addIntent({
            intent: 'extension',
            action: 'showMemories',
            patterns: [
                /show memories/i,
                /open memories/i,
                /list memories/i
            ]
        });
    }

    private addIntent(pattern: IntentPattern): void {
        this.intents.push(pattern);
    }

    public async parse(text: string): Promise<ParsedCommand | null> {
        const normalizedText = this.normalizeText(text);
        this.logger.debug(`Parsing normalized text: "${normalizedText}"`);

        let bestMatch: ParsedCommand | null = null;
        let highestConfidence = 0;

        for (const intent of this.intents) {
            for (const pattern of intent.patterns) {
                const match = normalizedText.match(pattern);
                if (match) {
                    const confidence = this.calculateConfidence(text, match[0]);
                    
                    if (confidence > highestConfidence) {
                        const parameters = intent.parameterExtractor ? 
                            intent.parameterExtractor(match) : {};
                        
                        bestMatch = {
                            intent: intent.intent,
                            action: intent.action,
                            parameters,
                            confidence,
                            raw: text
                        };
                        highestConfidence = confidence;
                    }
                }
            }
        }

        // If no exact match, try fuzzy matching
        if (!bestMatch && normalizedText.length > 3) {
            bestMatch = this.fuzzyMatch(normalizedText);
        }

        if (bestMatch) {
            this.logger.info(`Parsed command: ${JSON.stringify(bestMatch)}`);
        } else {
            this.logger.warn(`No command match found for: "${text}"`);
        }

        return bestMatch;
    }

    private normalizeText(text: string): string {
        return text
            .toLowerCase()
            .trim()
            .replace(/[^\w\s]/g, ' ')
            .replace(/\s+/g, ' ');
    }

    private calculateConfidence(original: string, matched: string): number {
        const originalLength = original.trim().length;
        const matchedLength = matched.length;
        const ratio = matchedLength / originalLength;
        
        // Base confidence on how much of the input was matched
        let confidence = ratio;
        
        // Boost confidence if the match is at the beginning
        if (original.toLowerCase().trim().startsWith(matched.toLowerCase())) {
            confidence += 0.2;
        }
        
        // Normalize to 0-1 range
        return Math.min(1, confidence);
    }

    private fuzzyMatch(text: string): ParsedCommand | null {
        const words = text.split(' ').filter(w => !this.stopWords.has(w));
        
        // Look for action keywords
        const actionKeywords = {
            'go': 'navigate',
            'jump': 'navigate',
            'open': 'file',
            'save': 'file',
            'find': 'search',
            'search': 'search',
            'select': 'selection',
            'comment': 'edit',
            'format': 'edit',
            'connect': 'extension'
        };

        for (const word of words) {
            for (const [keyword, intent] of Object.entries(actionKeywords)) {
                if (word.includes(keyword) || keyword.includes(word)) {
                    // Try to extract additional context
                    const remainingText = text.replace(word, '').trim();
                    
                    return {
                        intent,
                        action: keyword,
                        parameters: { query: remainingText },
                        confidence: 0.6,
                        raw: text
                    };
                }
            }
        }

        return null;
    }

    public getSupportedCommands(): string[] {
        const commands: string[] = [];
        for (const intent of this.intents) {
            for (const pattern of intent.patterns) {
                commands.push(pattern.source);
            }
        }
        return commands;
    }
}