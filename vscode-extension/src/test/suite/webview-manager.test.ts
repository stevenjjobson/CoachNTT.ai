/**
 * WebView Manager Tests
 * 
 * Tests for WebView panel lifecycle, message protocol, and security
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import * as sinon from 'sinon';
import { WebViewManager, ManagedWebViewPanel } from '../../webview/webview-manager';
import { MessageProtocol } from '../../webview/message-protocol';
import { BaseTemplate } from '../../webview/templates/base-template';
import { Logger } from '../../utils/logger';

// Mock WebView Panel
class MockWebViewPanel extends ManagedWebViewPanel {
    private state: any = {};
    
    protected handleMessage(message: any): void {
        // Mock implementation
    }
    
    protected getPanelState(): any {
        return this.state;
    }
    
    public restoreState(state: any): void {
        this.state = state;
    }
}

suite('WebView Manager Test Suite', () => {
    let sandbox: sinon.SinonSandbox;
    let context: vscode.ExtensionContext;
    let webViewManager: WebViewManager;
    
    setup(() => {
        sandbox = sinon.createSandbox();
        
        // Mock extension context
        context = {
            extensionUri: vscode.Uri.file('/test/extension'),
            workspaceState: {
                get: sandbox.stub().returns({}),
                update: sandbox.stub().resolves()
            },
            subscriptions: []
        } as any;
    });
    
    teardown(() => {
        sandbox.restore();
        webViewManager?.dispose();
    });
    
    test('WebView Manager singleton creation', () => {
        webViewManager = WebViewManager.getInstance(context);
        const instance2 = WebViewManager.getInstance(context);
        
        assert.strictEqual(webViewManager, instance2, 'Should return same instance');
    });
    
    test('Create WebView panel', () => {
        webViewManager = WebViewManager.getInstance(context);
        
        // Mock vscode.window.createWebviewPanel
        const mockPanel = {
            webview: {
                html: '',
                postMessage: sandbox.stub().resolves(true),
                asWebviewUri: (uri: vscode.Uri) => uri
            },
            onDidDispose: sandbox.stub(),
            onDidChangeViewState: sandbox.stub(),
            dispose: sandbox.stub()
        };
        
        sandbox.stub(vscode.window, 'createWebviewPanel').returns(mockPanel as any);
        
        const panel = webViewManager.createOrShowPanel(
            'test-panel',
            {
                viewType: 'test.panel',
                title: 'Test Panel'
            },
            (p) => new MockWebViewPanel(p, context, Logger.getInstance())
        );
        
        assert.ok(panel, 'Panel should be created');
        assert.strictEqual(webViewManager.getPanel('test-panel'), panel, 'Should retrieve panel by ID');
    });
    
    test('Panel state persistence', () => {
        webViewManager = WebViewManager.getInstance(context);
        
        const mockPanel = {
            webview: {
                html: '',
                postMessage: sandbox.stub().resolves(true),
                asWebviewUri: (uri: vscode.Uri) => uri
            },
            viewType: 'test.panel',
            title: 'Test Panel',
            viewColumn: vscode.ViewColumn.One,
            active: true,
            visible: true,
            onDidDispose: sandbox.stub(),
            onDidChangeViewState: sandbox.stub(),
            dispose: sandbox.stub()
        };
        
        sandbox.stub(vscode.window, 'createWebviewPanel').returns(mockPanel as any);
        
        const panel = webViewManager.createOrShowPanel(
            'test-panel',
            {
                viewType: 'test.panel',
                title: 'Test Panel'
            },
            (p) => new MockWebViewPanel(p, context, Logger.getInstance())
        );
        
        // Verify state is saved
        const updateStub = context.workspaceState.update as sinon.SinonStub;
        assert.ok(updateStub.called, 'State should be saved');
    });
    
    test('Close panel', () => {
        webViewManager = WebViewManager.getInstance(context);
        
        const mockPanel = {
            webview: {
                html: '',
                postMessage: sandbox.stub().resolves(true),
                asWebviewUri: (uri: vscode.Uri) => uri
            },
            onDidDispose: sandbox.stub(),
            onDidChangeViewState: sandbox.stub(),
            dispose: sandbox.stub()
        };
        
        sandbox.stub(vscode.window, 'createWebviewPanel').returns(mockPanel as any);
        
        webViewManager.createOrShowPanel(
            'test-panel',
            {
                viewType: 'test.panel',
                title: 'Test Panel'
            },
            (p) => new MockWebViewPanel(p, context, Logger.getInstance())
        );
        
        webViewManager.closePanel('test-panel');
        
        assert.ok(mockPanel.dispose.called, 'Panel should be disposed');
        assert.strictEqual(webViewManager.getPanel('test-panel'), undefined, 'Panel should be removed');
    });
    
    test('Message Protocol - Request/Response', async () => {
        const postMessage = sandbox.stub().resolves(true);
        const abstractContent = (content: string) => content.replace(/[A-Za-z0-9]{32,}/g, '<token>');
        
        const protocol = new MessageProtocol(postMessage, abstractContent);
        
        // Register request handler
        protocol.onRequest('test', async (params) => {
            return { result: `Hello ${params.name}` };
        });
        
        // Simulate incoming request
        const request = {
            id: 'req_1',
            type: 'request',
            method: 'test',
            params: { name: 'World' },
            timestamp: Date.now()
        };
        
        await protocol.handleMessage(request);
        
        // Verify response was sent
        assert.ok(postMessage.called, 'Response should be sent');
        const response = postMessage.firstCall.args[0];
        assert.strictEqual(response.type, 'response');
        assert.strictEqual(response.success, true);
        assert.deepStrictEqual(response.result, { result: 'Hello World' });
    });
    
    test('Message Protocol - Event handling', () => {
        const postMessage = sandbox.stub().resolves(true);
        const abstractContent = (content: string) => content;
        
        const protocol = new MessageProtocol(postMessage, abstractContent);
        
        let eventReceived = false;
        protocol.on('testEvent', (data) => {
            eventReceived = true;
            assert.strictEqual(data.message, 'Hello');
        });
        
        // Send event
        protocol.sendEvent('testEvent', { message: 'Hello' });
        
        // Simulate receiving the event
        const event = postMessage.firstCall.args[0];
        protocol.handleMessage(event);
        
        assert.ok(eventReceived, 'Event should be received');
    });
    
    test('Base Template - CSP generation', () => {
        const nonce = 'test-nonce-123';
        const csp = BaseTemplate.generateCSP(nonce);
        
        assert.ok(csp.includes(`script-src 'nonce-${nonce}'`), 'CSP should include nonce');
        assert.ok(csp.includes(`default-src 'none'`), 'CSP should have secure defaults');
        assert.ok(!csp.includes('unsafe-inline'), 'CSP should not allow unsafe-inline');
    });
    
    test('Base Template - HTML generation', () => {
        const options = {
            title: 'Test Page',
            nonce: 'test-nonce',
            styleUris: [],
            scriptUris: [],
            bodyContent: '<div>Test Content</div>'
        };
        
        const html = BaseTemplate.generateHTML(options);
        
        assert.ok(html.includes('<!DOCTYPE html>'), 'Should be valid HTML');
        assert.ok(html.includes(options.title), 'Should include title');
        assert.ok(html.includes(options.nonce), 'Should include nonce');
        assert.ok(html.includes(options.bodyContent), 'Should include body content');
        assert.ok(html.includes('Content-Security-Policy'), 'Should include CSP meta tag');
    });
    
    test('Base Template - Theme detection', () => {
        // Mock active color theme
        sandbox.stub(vscode.window, 'activeColorTheme').value({
            kind: vscode.ColorThemeKind.Dark
        });
        
        const theme = BaseTemplate.getThemeConfig();
        
        assert.strictEqual(theme.kind, vscode.ColorThemeKind.Dark);
        assert.strictEqual(theme.cssClass, 'vscode-dark');
    });
    
    test('Security - Content abstraction', () => {
        const postMessage = sandbox.stub().resolves(true);
        const abstractContent = (content: string) => {
            return content
                .replace(/[A-Za-z0-9]{32,}/g, '<token>')
                .replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '<ip_address>');
        };
        
        const protocol = new MessageProtocol(postMessage, abstractContent);
        
        // Send event with sensitive data
        protocol.sendEvent('test', {
            token: 'abcdef1234567890abcdef1234567890',
            ip: '192.168.1.1',
            safe: 'This is safe content'
        });
        
        const message = postMessage.firstCall.args[0];
        assert.strictEqual(message.data.token, '<token>', 'Token should be abstracted');
        assert.strictEqual(message.data.ip, '<ip_address>', 'IP should be abstracted');
        assert.strictEqual(message.data.safe, 'This is safe content', 'Safe content should remain');
    });
});