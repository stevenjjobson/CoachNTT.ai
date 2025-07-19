import { CommandParser } from '../command-parser';

describe('CommandParser', () => {
    let parser: CommandParser;

    beforeEach(() => {
        parser = new CommandParser();
    });

    describe('Navigation Commands', () => {
        test('should parse go to line commands', async () => {
            const testCases = [
                { input: 'go to line 42', expected: { action: 'goToLine', line: '42' } },
                { input: 'jump to line 100', expected: { action: 'goToLine', line: '100' } },
                { input: 'line 25', expected: { action: 'goToLine', line: '25' } },
                { input: 'go 15', expected: { action: 'goToLine', line: '15' } }
            ];

            for (const { input, expected } of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('navigate');
                expect(result!.action).toBe(expected.action);
                expect(result!.parameters).toEqual({ line: expected.line });
                expect(result!.confidence).toBeGreaterThan(0.7);
            }
        });

        test('should parse go to function commands', async () => {
            const testCases = [
                { input: 'go to function handleConnect', expected: { function: 'handleConnect' } },
                { input: 'find method processData', expected: { function: 'processData' } },
                { input: 'function initialize', expected: { function: 'initialize' } }
            ];

            for (const { input, expected } of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('navigate');
                expect(result!.action).toBe('goToFunction');
                expect(result!.parameters).toEqual(expected);
            }
        });
    });

    describe('File Operations', () => {
        test('should parse open file commands', async () => {
            const testCases = [
                { input: 'open file test.ts', expected: { file: 'test.ts' } },
                { input: 'open extension.ts', expected: { file: 'extension.ts' } },
                { input: 'show file config.json', expected: { file: 'config.json' } }
            ];

            for (const { input, expected } of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('file');
                expect(result!.action).toBe('open');
                expect(result!.parameters).toEqual(expected);
            }
        });

        test('should parse save commands', async () => {
            const testCases = [
                'save file',
                'save',
                'save current'
            ];

            for (const input of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('file');
                expect(result!.action).toBe('save');
                expect(result!.parameters).toEqual({});
            }
        });
    });

    describe('Selection Commands', () => {
        test('should parse select line commands', async () => {
            const result = await parser.parse('select line 10');
            expect(result).not.toBeNull();
            expect(result!.intent).toBe('selection');
            expect(result!.action).toBe('selectLine');
            expect(result!.parameters).toEqual({ line: '10' });
        });

        test('should parse select word commands', async () => {
            const testCases = [
                'select word',
                'select current word',
                'highlight word'
            ];

            for (const input of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('selection');
                expect(result!.action).toBe('selectWord');
            }
        });
    });

    describe('Editing Commands', () => {
        test('should parse comment commands', async () => {
            const testCases = [
                'comment line',
                'comment',
                'add comment',
                'comment this'
            ];

            for (const input of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('edit');
                expect(result!.action).toBe('comment');
            }
        });

        test('should parse format commands', async () => {
            const testCases = [
                'format document',
                'format file',
                'beautify',
                'prettify'
            ];

            for (const input of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('edit');
                expect(result!.action).toBe('format');
            }
        });

        test('should parse replace commands', async () => {
            const testCases = [
                { input: 'replace foo with bar', expected: { find: 'foo', replace: 'bar' } },
                { input: 'change old to new', expected: { find: 'old', replace: 'new' } }
            ];

            for (const { input, expected } of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('edit');
                expect(result!.action).toBe('replace');
                expect(result!.parameters).toEqual(expected);
            }
        });
    });

    describe('Search Commands', () => {
        test('should parse find commands', async () => {
            const testCases = [
                { input: 'find handleConnect', expected: { query: 'handleConnect' } },
                { input: 'search for TODO', expected: { query: 'TODO' } },
                { input: 'look for error handling', expected: { query: 'error handling' } }
            ];

            for (const { input, expected } of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('search');
                expect(result!.action).toBe('find');
                expect(result!.parameters).toEqual(expected);
            }
        });
    });

    describe('Extension Commands', () => {
        test('should parse connect backend command', async () => {
            const testCases = [
                'connect to backend',
                'connect backend',
                'start connection'
            ];

            for (const input of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('extension');
                expect(result!.action).toBe('connect');
            }
        });

        test('should parse show memories command', async () => {
            const testCases = [
                'show memories',
                'open memories',
                'list memories'
            ];

            for (const input of testCases) {
                const result = await parser.parse(input);
                expect(result).not.toBeNull();
                expect(result!.intent).toBe('extension');
                expect(result!.action).toBe('showMemories');
            }
        });
    });

    describe('Confidence Scoring', () => {
        test('should have high confidence for exact matches', async () => {
            const result = await parser.parse('go to line 42');
            expect(result).not.toBeNull();
            expect(result!.confidence).toBeGreaterThan(0.8);
        });

        test('should have lower confidence for partial matches', async () => {
            const result = await parser.parse('maybe go somewhere around line 42 please');
            expect(result).not.toBeNull();
            expect(result!.confidence).toBeLessThan(0.8);
        });
    });

    describe('Fuzzy Matching', () => {
        test('should handle variations with fuzzy matching', async () => {
            const result = await parser.parse('jump line twenty');
            expect(result).not.toBeNull();
            expect(result!.confidence).toBeGreaterThan(0.5);
        });

        test('should extract action keywords from unclear commands', async () => {
            const result = await parser.parse('I want to save this');
            expect(result).not.toBeNull();
            expect(result!.action).toBe('save');
            expect(result!.confidence).toBeGreaterThan(0.5);
        });
    });

    describe('Edge Cases', () => {
        test('should handle empty input', async () => {
            const result = await parser.parse('');
            expect(result).toBeNull();
        });

        test('should handle unrecognized commands', async () => {
            const result = await parser.parse('do something random');
            expect(result).toBeNull();
        });

        test('should normalize text properly', async () => {
            const result = await parser.parse('  GO   TO   LINE   42!!!  ');
            expect(result).not.toBeNull();
            expect(result!.action).toBe('goToLine');
            expect(result!.parameters).toEqual({ line: '42' });
        });

        test('should handle commands with special characters', async () => {
            const result = await parser.parse('open file test-file_2.ts');
            expect(result).not.toBeNull();
            expect(result!.parameters).toEqual({ file: 'test-file_2.ts' });
        });
    });

    describe('Command Discovery', () => {
        test('should return supported commands', () => {
            const commands = parser.getSupportedCommands();
            expect(commands).toBeInstanceOf(Array);
            expect(commands.length).toBeGreaterThan(10);
            expect(commands).toContain(expect.stringContaining('go.*line'));
        });
    });
});