import { NLQParser } from '../nlq-parser';

describe('NLQParser', () => {
    let parser: NLQParser;
    
    beforeEach(() => {
        parser = new NLQParser();
    });
    
    describe('Intent Extraction', () => {
        it('should extract find intent', async () => {
            const queries = [
                'find all functions that handle authentication',
                'where is the connection logic',
                'show me the login function',
                'locate the error handler'
            ];
            
            for (const query of queries) {
                const result = await parser.parse(query);
                expect(result).not.toBeNull();
                expect(result!.intent.type).toBe('find');
            }
        });
        
        it('should extract explain intent', async () => {
            const queries = [
                'explain how authentication works',
                'what does the connection manager do',
                'tell me about the memory service'
            ];
            
            for (const query of queries) {
                const result = await parser.parse(query);
                expect(result).not.toBeNull();
                expect(result!.intent.type).toBe('explain');
            }
        });
        
        it('should extract show intent', async () => {
            const queries = [
                'show me all classes',
                'display the interface definitions',
                'go to the main function'
            ];
            
            for (const query of queries) {
                const result = await parser.parse(query);
                expect(result).not.toBeNull();
                expect(result!.intent.type).toBe('show');
            }
        });
    });
    
    describe('Target Extraction', () => {
        it('should extract function targets', async () => {
            const query = 'find functions named connect';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.targets).toHaveLength(1);
            expect(result!.targets[0]).toMatchObject({
                type: 'function',
                name: 'connect'
            });
        });
        
        it('should extract class targets', async () => {
            const query = 'show me the MCPClient class';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.targets.some(t => 
                t.type === 'class' && t.name === 'MCPClient'
            )).toBe(true);
        });
        
        it('should extract concept targets', async () => {
            const query = 'find all authentication logic';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.targets.some(t => 
                t.type === 'concept' && t.name === 'authentication'
            )).toBe(true);
        });
        
        it('should extract multiple targets', async () => {
            const query = 'find functions and classes that handle memory validation';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.targets.length).toBeGreaterThan(1);
            expect(result!.targets.some(t => t.type === 'function')).toBe(true);
            expect(result!.targets.some(t => t.type === 'class')).toBe(true);
        });
    });
    
    describe('Filter Extraction', () => {
        it('should extract file filters', async () => {
            const query = 'find connect function in file mcp-client.ts';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.filters).toContainEqual({
                type: 'file',
                value: 'mcp-client.ts',
                operator: 'includes'
            });
        });
        
        it('should extract directory filters', async () => {
            const query = 'show all classes in folder services';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.filters).toContainEqual({
                type: 'directory',
                value: 'services',
                operator: 'includes'
            });
        });
        
        it('should extract visibility filters', async () => {
            const query = 'find all private methods';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.filters).toContainEqual({
                type: 'visibility',
                value: 'private',
                operator: 'equals'
            });
        });
    });
    
    describe('Complex Queries', () => {
        it('should parse complex queries with multiple elements', async () => {
            const query = 'find all public functions that handle authentication in services folder';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.intent.type).toBe('find');
            expect(result!.targets.some(t => t.type === 'function')).toBe(true);
            expect(result!.targets.some(t => t.name === 'authentication')).toBe(true);
            expect(result!.filters.some(f => f.type === 'visibility' && f.value === 'public')).toBe(true);
            expect(result!.filters.some(f => f.type === 'directory' && f.value === 'services')).toBe(true);
        });
        
        it('should handle queries with context', async () => {
            const context = {
                currentFile: '/src/services/mcp-client.ts',
                selectedText: 'connect'
            };
            
            const query = 'explain this';
            const result = await parser.parse(query, context);
            
            expect(result).not.toBeNull();
            expect(result!.context).toEqual(context);
        });
    });
    
    describe('Confidence Scoring', () => {
        it('should have high confidence for clear queries', async () => {
            const query = 'find function handleConnect';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.confidence).toBeGreaterThan(0.8);
        });
        
        it('should have lower confidence for ambiguous queries', async () => {
            const query = 'something about connections';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.confidence).toBeLessThan(0.7);
        });
    });
    
    describe('Edge Cases', () => {
        it('should handle empty queries', async () => {
            const result = await parser.parse('');
            expect(result).toBeNull();
        });
        
        it('should handle queries with special characters', async () => {
            const query = 'find function $handleConnect!';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.targets.some(t => t.name === 'handleConnect')).toBe(true);
        });
        
        it('should handle very long queries', async () => {
            const query = 'find all functions and methods and classes that handle authentication ' +
                         'and validation and also connect to the backend API and process memory data';
            const result = await parser.parse(query);
            
            expect(result).not.toBeNull();
            expect(result!.targets.length).toBeGreaterThan(0);
        });
    });
});