import * as vscode from 'vscode';
import { CodeSearchEngine } from '../code-search-engine';
import { SemanticQuery } from '../semantic-analyzer';

// Mock vscode
jest.mock('vscode');

describe('CodeSearchEngine', () => {
    let searchEngine: CodeSearchEngine;
    let mockDocument: vscode.TextDocument;
    
    beforeEach(() => {
        searchEngine = new CodeSearchEngine();
        
        // Mock document
        mockDocument = {
            getText: jest.fn().mockReturnValue('function testFunction() { return true; }'),
            lineAt: jest.fn().mockReturnValue({ text: 'test line' }),
            lineCount: 100,
            positionAt: jest.fn().mockImplementation((offset) => ({
                line: Math.floor(offset / 50),
                character: offset % 50
            }))
        } as any;
        
        // Mock workspace
        (vscode.workspace.openTextDocument as jest.Mock).mockResolvedValue(mockDocument);
        (vscode.workspace.findFiles as jest.Mock).mockResolvedValue([
            vscode.Uri.file('/test/file1.ts'),
            vscode.Uri.file('/test/file2.ts')
        ]);
    });
    
    afterEach(() => {
        jest.clearAllMocks();
    });
    
    describe('Search Execution', () => {
        it('should search files based on semantic query', async () => {
            const query: SemanticQuery = {
                concepts: [],
                constraints: [{
                    type: 'should',
                    field: 'name',
                    value: 'test',
                    weight: 1.0
                }],
                contextRequirements: [],
                searchScope: {
                    includeImports: true,
                    includeExports: true,
                    includePrivate: true,
                    includeComments: true,
                    maxDepth: 5
                }
            };
            
            const results = await searchEngine.search(query);
            
            expect(vscode.workspace.findFiles).toHaveBeenCalled();
            expect(vscode.workspace.openTextDocument).toHaveBeenCalled();
        });
        
        it('should limit results based on options', async () => {
            const query: SemanticQuery = {
                concepts: [],
                constraints: [{
                    type: 'should',
                    field: 'content',
                    value: /function/,
                    weight: 1.0
                }],
                contextRequirements: [],
                searchScope: {
                    includeImports: true,
                    includeExports: true,
                    includePrivate: true,
                    includeComments: false,
                    maxDepth: 3
                }
            };
            
            const options = {
                maxResults: 10,
                minScore: 0.5,
                includeSnippets: true,
                snippetLines: 3
            };
            
            const results = await searchEngine.search(query, options);
            
            expect(results.length).toBeLessThanOrEqual(options.maxResults);
            results.forEach(result => {
                expect(result.score).toBeGreaterThanOrEqual(options.minScore);
                if (options.includeSnippets) {
                    expect(result.snippet).toBeTruthy();
                }
            });
        });
    });
    
    describe('Constraint Application', () => {
        it('should respect must constraints', async () => {
            const query: SemanticQuery = {
                concepts: [],
                constraints: [{
                    type: 'must',
                    field: 'name',
                    value: 'nonexistent',
                    weight: 1.0
                }],
                contextRequirements: [],
                searchScope: {
                    includeImports: true,
                    includeExports: true,
                    includePrivate: true,
                    includeComments: true,
                    maxDepth: 5
                }
            };
            
            const results = await searchEngine.search(query);
            
            // Should find no results since 'nonexistent' is not in our mock
            expect(results.length).toBe(0);
        });
        
        it('should respect mustNot constraints', async () => {
            const query: SemanticQuery = {
                concepts: [],
                constraints: [
                    {
                        type: 'should',
                        field: 'content',
                        value: /function/,
                        weight: 1.0
                    },
                    {
                        type: 'mustNot',
                        field: 'name',
                        value: 'test',
                        weight: 1.0
                    }
                ],
                contextRequirements: [],
                searchScope: {
                    includeImports: true,
                    includeExports: true,
                    includePrivate: true,
                    includeComments: true,
                    maxDepth: 5
                }
            };
            
            const results = await searchEngine.search(query);
            
            // Results should not include items with 'test' in the name
            results.forEach(result => {
                expect(result.name).not.toContain('test');
            });
        });
    });
    
    describe('Snippet Extraction', () => {
        it('should extract code snippets with context', async () => {
            const mockLines = [
                'line 1',
                'line 2',
                'function testFunction() {',
                '    return true;',
                '}',
                'line 6',
                'line 7'
            ];
            
            mockDocument.lineAt = jest.fn().mockImplementation((line) => ({
                text: mockLines[line] || ''
            }));
            mockDocument.lineCount = mockLines.length;
            
            const query: SemanticQuery = {
                concepts: [],
                constraints: [{
                    type: 'should',
                    field: 'content',
                    value: /function/,
                    weight: 1.0
                }],
                contextRequirements: [],
                searchScope: {
                    includeImports: true,
                    includeExports: true,
                    includePrivate: true,
                    includeComments: true,
                    maxDepth: 5
                }
            };
            
            const options = {
                maxResults: 10,
                minScore: 0.1,
                includeSnippets: true,
                snippetLines: 5
            };
            
            const results = await searchEngine.search(query, options);
            
            if (results.length > 0) {
                expect(results[0].snippet).toContain('function');
                expect(results[0].snippet.split('\n').length).toBeLessThanOrEqual(options.snippetLines);
            }
        });
    });
    
    describe('Cache Management', () => {
        it('should clear cache when requested', () => {
            searchEngine.clearCache();
            // Cache should be cleared - no errors should occur
            expect(() => searchEngine.clearCache()).not.toThrow();
        });
    });
    
    describe('Error Handling', () => {
        it('should handle file read errors gracefully', async () => {
            (vscode.workspace.openTextDocument as jest.Mock).mockRejectedValue(
                new Error('File not found')
            );
            
            const query: SemanticQuery = {
                concepts: [],
                constraints: [{
                    type: 'should',
                    field: 'name',
                    value: 'test',
                    weight: 1.0
                }],
                contextRequirements: [],
                searchScope: {
                    includeImports: true,
                    includeExports: true,
                    includePrivate: true,
                    includeComments: true,
                    maxDepth: 5
                }
            };
            
            const results = await searchEngine.search(query);
            
            // Should return empty results instead of throwing
            expect(results).toEqual([]);
        });
    });
});