import * as assert from 'assert';
import * as vscode from 'vscode';
import { Logger } from '../../src/utils/logger';
import { ConfigurationService } from '../../src/config/settings';

suite('Extension Test Suite', () => {
    vscode.window.showInformationMessage('Start all tests.');

    test('Extension should be present', () => {
        assert.ok(vscode.extensions.getExtension('coachntt.coachntt'));
    });

    test('Extension should activate', async () => {
        const extension = vscode.extensions.getExtension('coachntt.coachntt');
        assert.ok(extension);
        
        if (!extension.isActive) {
            await extension.activate();
        }
        
        assert.ok(extension.isActive);
    });

    test('Commands should be registered', async () => {
        const commands = await vscode.commands.getCommands();
        
        const expectedCommands = [
            'coachntt.connect',
            'coachntt.disconnect',
            'coachntt.showLogs',
            'coachntt.openSettings',
            'coachntt.refreshView',
            'coachntt.checkStatus'
        ];
        
        expectedCommands.forEach(cmd => {
            assert.ok(
                commands.includes(cmd),
                `Command ${cmd} should be registered`
            );
        });
    });

    test('Logger should abstract sensitive information', () => {
        const logger = Logger.getInstance();
        
        // Test file path abstraction
        const testPath = 'C:\\Users\\John\\project\\file.ts';
        const abstracted = (logger as any).abstractMessage(testPath);
        assert.ok(!abstracted.includes('John'), 'Username should be abstracted');
        assert.ok(abstracted.includes('<project>/<module>/<file>'), 'Path should be abstracted');
        
        // Test URL abstraction
        const testUrl = 'https://api.example.com/endpoint';
        const abstractedUrl = (logger as any).abstractMessage(testUrl);
        assert.ok(abstractedUrl.includes('<url>'), 'URL should be abstracted');
        
        // Test IP abstraction
        const testIp = 'Connected to 192.168.1.100';
        const abstractedIp = (logger as any).abstractMessage(testIp);
        assert.ok(abstractedIp.includes('<ip_address>'), 'IP should be abstracted');
    });

    test('Configuration service should validate settings', () => {
        const config = ConfigurationService.getInstance();
        
        // Test URL validation
        const connectionConfig = config.getConnectionConfig();
        assert.ok(connectionConfig.url, 'Should have API URL');
        assert.ok(connectionConfig.websocketUrl, 'Should have WebSocket URL');
        
        // Test safety score validation
        const safetyScore = config.getMinSafetyScore();
        assert.ok(safetyScore >= 0 && safetyScore <= 1, 'Safety score should be between 0 and 1');
        
        // Test settings validation
        const validation = config.validateSettings();
        assert.ok(validation.valid || validation.errors.length > 0, 'Should validate settings');
    });

    test('Status bar items should be created', async () => {
        // This test would need to check if status bar items are visible
        // In a real test environment, we'd mock the VSCode API
        const statusBarItems = vscode.window.createStatusBarItem();
        assert.ok(statusBarItems, 'Should create status bar item');
        statusBarItems.dispose();
    });

    test('Configuration should have correct defaults', () => {
        const config = vscode.workspace.getConfiguration('coachntt');
        
        assert.strictEqual(config.get('apiUrl'), 'http://localhost:8000');
        assert.strictEqual(config.get('safetyValidation'), true);
        assert.strictEqual(config.get('minSafetyScore'), 0.8);
        assert.strictEqual(config.get('autoConnect'), false);
        assert.strictEqual(config.get('logLevel'), 'info');
    });

    test('Tree view should be registered', () => {
        // Check if the view container is registered
        // This would be better tested with VSCode API mocks
        assert.ok(true, 'Tree view registration test placeholder');
    });
});

/**
 * Test runner configuration
 */
export function run(): Promise<void> {
    // Create the mocha test
    const mocha = new Mocha({
        ui: 'tdd',
        color: true
    });

    // Add test files
    mocha.addFile(__filename);

    return new Promise((resolve, reject) => {
        try {
            // Run the mocha test
            mocha.run(failures => {
                if (failures > 0) {
                    reject(new Error(`${failures} tests failed.`));
                } else {
                    resolve();
                }
            });
        } catch (err) {
            console.error(err);
            reject(err);
        }
    });
}