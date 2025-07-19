import { Logger } from '../../utils/logger';

export interface NLQIntent {
    type: 'find' | 'explain' | 'show' | 'search' | 'navigate';
    action: string;
    confidence: number;
}

export interface QueryTarget {
    type: 'function' | 'class' | 'variable' | 'interface' | 'type' | 'method' | 'property' | 'concept';
    name?: string;
    pattern?: string;
    modifiers?: string[];
}

export interface QueryFilter {
    type: 'file' | 'directory' | 'extension' | 'scope' | 'visibility';
    value: string;
    operator: 'includes' | 'excludes' | 'equals' | 'matches';
}

export interface NLQuery {
    raw: string;
    normalized: string;
    intent: NLQIntent;
    targets: QueryTarget[];
    filters: QueryFilter[];
    context?: {
        currentFile?: string;
        selectedText?: string;
        cursorPosition?: { line: number; character: number };
    };
    confidence: number;
}

export class NLQParser {
    private logger: Logger;
    
    // Intent patterns
    private readonly intentPatterns = new Map<string, RegExp[]>([
        ['find', [
            /(?:find|locate|search for|look for|where (?:is|are))(?: all)? (.+)/i,
            /show me(?: all)? (.+)/i,
            /(?:what|which) (.+) (?:handle|implement|use|call|contain)/i
        ]],
        ['explain', [
            /(?:explain|what (?:is|does)|how (?:does|do)) (.+)/i,
            /tell me about (.+)/i,
            /describe (.+)/i
        ]],
        ['show', [
            /(?:show|display|list)(?: me)?(?: all)? (.+)/i,
            /(?:open|go to|jump to) (.+)/i,
            /navigate to (.+)/i
        ]],
        ['search', [
            /search(?: for)? (.+)/i,
            /grep (.+)/i,
            /find text (.+)/i
        ]]
    ]);
    
    // Target patterns
    private readonly targetPatterns = new Map<string, RegExp[]>([
        ['function', [
            /functions?\s+(?:named\s+|called\s+)?(\w+)/i,
            /(\w+)\s+functions?/i,
            /functions?\s+that\s+(\w+)/i
        ]],
        ['class', [
            /class(?:es)?\s+(?:named\s+|called\s+)?(\w+)/i,
            /(\w+)\s+class(?:es)?/i,
            /class(?:es)?\s+that\s+(\w+)/i
        ]],
        ['method', [
            /methods?\s+(?:named\s+|called\s+)?(\w+)/i,
            /(\w+)\s+methods?/i,
            /methods?\s+that\s+(\w+)/i
        ]],
        ['variable', [
            /variables?\s+(?:named\s+|called\s+)?(\w+)/i,
            /(\w+)\s+variables?/i,
            /(?:const|let|var)\s+(\w+)/i
        ]],
        ['interface', [
            /interfaces?\s+(?:named\s+|called\s+)?(\w+)/i,
            /(\w+)\s+interfaces?/i
        ]],
        ['type', [
            /types?\s+(?:named\s+|called\s+)?(\w+)/i,
            /(\w+)\s+types?/i
        ]]
    ]);
    
    // Concept mappings
    private readonly conceptMappings = new Map<string, string[]>([
        ['authentication', ['auth', 'login', 'signin', 'authenticate', 'credential', 'token', 'jwt']],
        ['connection', ['connect', 'websocket', 'socket', 'client', 'server', 'network']],
        ['memory', ['memory', 'cache', 'store', 'storage', 'persist']],
        ['validation', ['validate', 'verify', 'check', 'ensure', 'assert', 'test']],
        ['error', ['error', 'exception', 'catch', 'throw', 'fail', 'reject']],
        ['async', ['async', 'await', 'promise', 'then', 'callback', 'subscribe']],
        ['initialization', ['init', 'initialize', 'setup', 'start', 'begin', 'create']],
        ['cleanup', ['cleanup', 'dispose', 'destroy', 'close', 'end', 'terminate']]
    ]);
    
    constructor() {
        this.logger = Logger.getInstance();
    }
    
    public async parse(text: string, context?: any): Promise<NLQuery | null> {
        const normalized = this.normalizeQuery(text);
        this.logger.debug(`Parsing NLQ: "${normalized}"`);
        
        // Extract intent
        const intent = this.extractIntent(normalized);
        if (!intent) {
            this.logger.warn(`No intent found in query: "${text}"`);
            return null;
        }
        
        // Extract targets
        const targets = this.extractTargets(normalized);
        
        // Extract filters
        const filters = this.extractFilters(normalized);
        
        // Calculate overall confidence
        const confidence = this.calculateConfidence(intent, targets, filters);
        
        const query: NLQuery = {
            raw: text,
            normalized,
            intent,
            targets,
            filters,
            context,
            confidence
        };
        
        this.logger.info(`Parsed NLQ: ${JSON.stringify(query)}`);
        return query;
    }
    
    private normalizeQuery(text: string): string {
        return text
            .toLowerCase()
            .trim()
            .replace(/[?!.,;:]/g, '')
            .replace(/\s+/g, ' ')
            .replace(/'/g, '');
    }
    
    private extractIntent(text: string): NLQIntent | null {
        let bestMatch: NLQIntent | null = null;
        let highestConfidence = 0;
        
        for (const [type, patterns] of this.intentPatterns) {
            for (const pattern of patterns) {
                const match = text.match(pattern);
                if (match) {
                    const confidence = this.calculatePatternConfidence(text, match[0]);
                    if (confidence > highestConfidence) {
                        bestMatch = {
                            type: type as any,
                            action: this.getActionFromIntent(type, match[1] || ''),
                            confidence
                        };
                        highestConfidence = confidence;
                    }
                }
            }
        }
        
        // Fallback to 'find' intent if keywords suggest search
        if (!bestMatch && this.hasSearchKeywords(text)) {
            bestMatch = {
                type: 'find',
                action: 'search',
                confidence: 0.6
            };
        }
        
        return bestMatch;
    }
    
    private extractTargets(text: string): QueryTarget[] {
        const targets: QueryTarget[] = [];
        
        // Extract specific code element targets
        for (const [type, patterns] of this.targetPatterns) {
            for (const pattern of patterns) {
                const matches = text.matchAll(new RegExp(pattern, 'gi'));
                for (const match of matches) {
                    if (match[1]) {
                        targets.push({
                            type: type as any,
                            name: match[1],
                            pattern: match[1]
                        });
                    }
                }
            }
        }
        
        // Extract concept-based targets
        for (const [concept, keywords] of this.conceptMappings) {
            for (const keyword of keywords) {
                if (text.includes(keyword)) {
                    targets.push({
                        type: 'concept',
                        name: concept,
                        pattern: keyword
                    });
                    break;
                }
            }
        }
        
        // Extract generic patterns
        const genericPatterns = [
            /that (\w+) (.+)/i,
            /(?:handle|implement|use|call|contain) (.+)/i,
            /for (.+) (?:functionality|feature|logic)/i
        ];
        
        for (const pattern of genericPatterns) {
            const match = text.match(pattern);
            if (match && match[1]) {
                const words = match[1].split(' ').filter(w => w.length > 2);
                for (const word of words) {
                    if (!this.isStopWord(word)) {
                        targets.push({
                            type: 'concept',
                            pattern: word
                        });
                    }
                }
            }
        }
        
        // Deduplicate targets
        return this.deduplicateTargets(targets);
    }
    
    private extractFilters(text: string): QueryFilter[] {
        const filters: QueryFilter[] = [];
        
        // File filters
        const filePattern = /in (?:file|files?) (\S+)/i;
        const fileMatch = text.match(filePattern);
        if (fileMatch) {
            filters.push({
                type: 'file',
                value: fileMatch[1],
                operator: 'includes'
            });
        }
        
        // Directory filters
        const dirPattern = /in (?:folder|directory|dir) (\S+)/i;
        const dirMatch = text.match(dirPattern);
        if (dirMatch) {
            filters.push({
                type: 'directory',
                value: dirMatch[1],
                operator: 'includes'
            });
        }
        
        // Extension filters
        const extPattern = /(?:typescript|javascript|ts|js|tsx|jsx) files?/i;
        const extMatch = text.match(extPattern);
        if (extMatch) {
            const ext = extMatch[0].includes('typescript') || extMatch[0].includes('ts') ? 'ts' : 'js';
            filters.push({
                type: 'extension',
                value: ext,
                operator: 'equals'
            });
        }
        
        // Visibility filters
        const visibilityPattern = /(?:public|private|protected) (\w+)/i;
        const visMatch = text.match(visibilityPattern);
        if (visMatch) {
            filters.push({
                type: 'visibility',
                value: visMatch[0].split(' ')[0],
                operator: 'equals'
            });
        }
        
        return filters;
    }
    
    private calculatePatternConfidence(text: string, matched: string): number {
        const ratio = matched.length / text.length;
        let confidence = ratio;
        
        // Boost if match is at the beginning
        if (text.startsWith(matched)) {
            confidence += 0.2;
        }
        
        // Boost for exact intent keywords
        if (text.includes('find') || text.includes('show') || text.includes('search')) {
            confidence += 0.1;
        }
        
        return Math.min(1, confidence);
    }
    
    private calculateConfidence(intent: NLQIntent, targets: QueryTarget[], filters: QueryFilter[]): number {
        let confidence = intent.confidence;
        
        // Boost for specific targets
        if (targets.length > 0) {
            confidence += 0.1 * Math.min(targets.length, 3);
        }
        
        // Boost for filters
        if (filters.length > 0) {
            confidence += 0.05 * filters.length;
        }
        
        return Math.min(1, confidence);
    }
    
    private getActionFromIntent(intent: string, captured: string): string {
        switch (intent) {
            case 'find':
                return captured.includes('all') ? 'findAll' : 'findOne';
            case 'explain':
                return 'explain';
            case 'show':
                return 'navigate';
            case 'search':
                return 'textSearch';
            default:
                return 'search';
        }
    }
    
    private hasSearchKeywords(text: string): boolean {
        const keywords = ['where', 'what', 'which', 'how', 'find', 'search', 'show', 'locate'];
        return keywords.some(keyword => text.includes(keyword));
    }
    
    private isStopWord(word: string): boolean {
        const stopWords = new Set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their'
        ]);
        return stopWords.has(word.toLowerCase());
    }
    
    private deduplicateTargets(targets: QueryTarget[]): QueryTarget[] {
        const seen = new Set<string>();
        return targets.filter(target => {
            const key = `${target.type}-${target.name || target.pattern}`;
            if (seen.has(key)) {
                return false;
            }
            seen.add(key);
            return true;
        });
    }
    
    public getSupportedIntents(): string[] {
        return Array.from(this.intentPatterns.keys());
    }
    
    public getSupportedTargets(): string[] {
        return Array.from(this.targetPatterns.keys());
    }
    
    public getConceptKeywords(concept: string): string[] {
        return this.conceptMappings.get(concept) || [];
    }
}