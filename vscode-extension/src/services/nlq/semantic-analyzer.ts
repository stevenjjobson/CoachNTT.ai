import { NLQuery, QueryTarget } from './nlq-parser';
import { Logger } from '../../utils/logger';

export interface SemanticConcept {
    name: string;
    type: 'action' | 'entity' | 'attribute' | 'relationship';
    synonyms: string[];
    relatedConcepts: string[];
    codePatterns: string[];
}

export interface SearchConstraint {
    type: 'must' | 'should' | 'mustNot';
    field: 'name' | 'type' | 'content' | 'comment';
    value: string | RegExp;
    weight: number;
}

export interface SemanticQuery {
    concepts: SemanticConcept[];
    constraints: SearchConstraint[];
    contextRequirements: ContextRequirement[];
    searchScope: SearchScope;
}

export interface ContextRequirement {
    type: 'hasParent' | 'hasChild' | 'hasSibling' | 'inScope';
    nodeType?: string;
    pattern?: string;
}

export interface SearchScope {
    includeImports: boolean;
    includeExports: boolean;
    includePrivate: boolean;
    includeComments: boolean;
    maxDepth: number;
}

export class SemanticAnalyzer {
    private logger: Logger;
    private conceptDatabase: Map<string, SemanticConcept>;
    
    constructor() {
        this.logger = Logger.getInstance();
        this.conceptDatabase = this.initializeConceptDatabase();
    }
    
    public analyze(query: NLQuery): SemanticQuery {
        this.logger.debug(`Analyzing query semantically: ${query.normalized}`);
        
        // Extract semantic concepts from targets
        const concepts = this.extractConcepts(query);
        
        // Build search constraints
        const constraints = this.buildConstraints(query, concepts);
        
        // Determine context requirements
        const contextRequirements = this.analyzeContextRequirements(query);
        
        // Define search scope
        const searchScope = this.determineSearchScope(query);
        
        const semanticQuery: SemanticQuery = {
            concepts,
            constraints,
            contextRequirements,
            searchScope
        };
        
        this.logger.info(`Semantic analysis complete: ${JSON.stringify(semanticQuery)}`);
        return semanticQuery;
    }
    
    private extractConcepts(query: NLQuery): SemanticConcept[] {
        const concepts: SemanticConcept[] = [];
        
        // Convert targets to concepts
        for (const target of query.targets) {
            const concept = this.targetToConcept(target);
            if (concept) {
                concepts.push(concept);
            }
        }
        
        // Extract action concepts from intent
        const actionConcept = this.intentToActionConcept(query.intent);
        if (actionConcept) {
            concepts.push(actionConcept);
        }
        
        // Look for implicit concepts in the query text
        const implicitConcepts = this.findImplicitConcepts(query.normalized);
        concepts.push(...implicitConcepts);
        
        return this.deduplicateConcepts(concepts);
    }
    
    private buildConstraints(query: NLQuery, concepts: SemanticConcept[]): SearchConstraint[] {
        const constraints: SearchConstraint[] = [];
        
        // Add constraints for each concept
        for (const concept of concepts) {
            // Name constraints
            if (concept.type === 'entity') {
                constraints.push({
                    type: 'should',
                    field: 'name',
                    value: new RegExp(concept.name, 'i'),
                    weight: 2.0
                });
                
                // Add synonym constraints
                for (const synonym of concept.synonyms) {
                    constraints.push({
                        type: 'should',
                        field: 'name',
                        value: new RegExp(synonym, 'i'),
                        weight: 1.5
                    });
                }
            }
            
            // Pattern constraints
            for (const pattern of concept.codePatterns) {
                constraints.push({
                    type: 'should',
                    field: 'content',
                    value: new RegExp(pattern, 'i'),
                    weight: 1.0
                });
            }
        }
        
        // Add filter constraints
        for (const filter of query.filters) {
            const constraint = this.filterToConstraint(filter);
            if (constraint) {
                constraints.push(constraint);
            }
        }
        
        // Add specific name constraints from targets
        for (const target of query.targets) {
            if (target.name) {
                constraints.push({
                    type: 'must',
                    field: 'name',
                    value: target.name,
                    weight: 3.0
                });
            }
        }
        
        return constraints;
    }
    
    private analyzeContextRequirements(query: NLQuery): ContextRequirement[] {
        const requirements: ContextRequirement[] = [];
        
        // Analyze for parent-child relationships
        if (query.normalized.includes('in class') || query.normalized.includes('inside')) {
            requirements.push({
                type: 'hasParent',
                nodeType: 'class'
            });
        }
        
        if (query.normalized.includes('that extends') || query.normalized.includes('inherits')) {
            requirements.push({
                type: 'hasParent',
                pattern: 'extends'
            });
        }
        
        if (query.normalized.includes('that implements')) {
            requirements.push({
                type: 'hasParent',
                pattern: 'implements'
            });
        }
        
        return requirements;
    }
    
    private determineSearchScope(query: NLQuery): SearchScope {
        const scope: SearchScope = {
            includeImports: true,
            includeExports: true,
            includePrivate: query.normalized.includes('private') || !query.normalized.includes('public'),
            includeComments: query.normalized.includes('comment') || query.normalized.includes('todo'),
            maxDepth: 5
        };
        
        // Adjust based on query type
        if (query.intent.type === 'explain') {
            scope.includeComments = true;
            scope.maxDepth = 10;
        }
        
        return scope;
    }
    
    private targetToConcept(target: QueryTarget): SemanticConcept | null {
        const existing = this.conceptDatabase.get(target.name || target.pattern || '');
        if (existing) {
            return existing;
        }
        
        // Create new concept for the target
        return {
            name: target.name || target.pattern || '',
            type: 'entity',
            synonyms: this.generateSynonyms(target),
            relatedConcepts: [],
            codePatterns: this.generatePatterns(target)
        };
    }
    
    private intentToActionConcept(intent: any): SemanticConcept | null {
        const actionMappings: Record<string, SemanticConcept> = {
            'find': {
                name: 'search',
                type: 'action',
                synonyms: ['locate', 'discover', 'identify'],
                relatedConcepts: ['filter', 'match'],
                codePatterns: []
            },
            'explain': {
                name: 'analyze',
                type: 'action',
                synonyms: ['describe', 'document', 'clarify'],
                relatedConcepts: ['understand', 'interpret'],
                codePatterns: []
            }
        };
        
        return actionMappings[intent.type] || null;
    }
    
    private findImplicitConcepts(text: string): SemanticConcept[] {
        const concepts: SemanticConcept[] = [];
        
        // Check for relationship indicators
        if (text.includes('connect') || text.includes('call') || text.includes('use')) {
            concepts.push(this.conceptDatabase.get('relationship') || this.createRelationshipConcept());
        }
        
        // Check for modification indicators
        if (text.includes('change') || text.includes('modify') || text.includes('update')) {
            concepts.push(this.conceptDatabase.get('modification') || this.createModificationConcept());
        }
        
        return concepts;
    }
    
    private filterToConstraint(filter: any): SearchConstraint | null {
        switch (filter.type) {
            case 'file':
                return {
                    type: 'must',
                    field: 'name',
                    value: filter.value,
                    weight: 2.0
                };
            case 'extension':
                return {
                    type: 'must',
                    field: 'name',
                    value: new RegExp(`\\.${filter.value}$`),
                    weight: 1.0
                };
            default:
                return null;
        }
    }
    
    private generateSynonyms(target: QueryTarget): string[] {
        const synonymMap: Record<string, string[]> = {
            'function': ['func', 'fn', 'method', 'procedure'],
            'class': ['cls', 'type', 'object'],
            'variable': ['var', 'const', 'let', 'field', 'property'],
            'interface': ['iface', 'contract', 'api'],
            'authentication': ['auth', 'login', 'signin', 'security'],
            'connection': ['conn', 'link', 'socket', 'client']
        };
        
        return synonymMap[target.name || ''] || [];
    }
    
    private generatePatterns(target: QueryTarget): string[] {
        const patterns: string[] = [];
        
        switch (target.type) {
            case 'function':
                patterns.push(`function\\s+${target.pattern}`, `const\\s+${target.pattern}\\s*=\\s*\\(`);
                break;
            case 'class':
                patterns.push(`class\\s+${target.pattern}`, `export\\s+class\\s+${target.pattern}`);
                break;
            case 'interface':
                patterns.push(`interface\\s+${target.pattern}`, `export\\s+interface\\s+${target.pattern}`);
                break;
        }
        
        return patterns;
    }
    
    private deduplicateConcepts(concepts: SemanticConcept[]): SemanticConcept[] {
        const seen = new Set<string>();
        return concepts.filter(concept => {
            if (seen.has(concept.name)) {
                return false;
            }
            seen.add(concept.name);
            return true;
        });
    }
    
    private initializeConceptDatabase(): Map<string, SemanticConcept> {
        const db = new Map<string, SemanticConcept>();
        
        // Common programming concepts
        db.set('authentication', {
            name: 'authentication',
            type: 'entity',
            synonyms: ['auth', 'login', 'signin', 'security', 'credential'],
            relatedConcepts: ['user', 'token', 'session', 'permission'],
            codePatterns: ['auth', 'login', 'authenticate', 'credential', 'token']
        });
        
        db.set('error-handling', {
            name: 'error-handling',
            type: 'entity',
            synonyms: ['exception', 'error', 'catch', 'try'],
            relatedConcepts: ['validation', 'logging', 'recovery'],
            codePatterns: ['try', 'catch', 'throw', 'Error', 'Exception']
        });
        
        db.set('async', {
            name: 'asynchronous',
            type: 'attribute',
            synonyms: ['async', 'await', 'promise', 'concurrent'],
            relatedConcepts: ['callback', 'future', 'observable'],
            codePatterns: ['async', 'await', 'Promise', 'then', 'catch']
        });
        
        return db;
    }
    
    private createRelationshipConcept(): SemanticConcept {
        return {
            name: 'relationship',
            type: 'relationship',
            synonyms: ['connection', 'link', 'association', 'dependency'],
            relatedConcepts: ['coupling', 'interface', 'contract'],
            codePatterns: ['import', 'require', 'extends', 'implements']
        };
    }
    
    private createModificationConcept(): SemanticConcept {
        return {
            name: 'modification',
            type: 'action',
            synonyms: ['change', 'update', 'alter', 'modify'],
            relatedConcepts: ['refactor', 'edit', 'transform'],
            codePatterns: ['set', 'update', 'modify', 'change']
        };
    }
    
    public expandConcept(concept: string): string[] {
        const dbConcept = this.conceptDatabase.get(concept);
        if (!dbConcept) {
            return [concept];
        }
        
        return [concept, ...dbConcept.synonyms, ...dbConcept.relatedConcepts];
    }
}