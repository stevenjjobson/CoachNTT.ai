/**
 * WebView Manager for CoachNTT.ai VSCode Extension
 * 
 * Central service for managing WebView panel lifecycle, including:
 * - Panel creation and disposal
 * - State persistence and recovery
 * - Resource URI handling
 * - Theme management
 */

import * as vscode from 'vscode';
import * as crypto from 'crypto';
import { Logger } from '../utils/logger';
import { BaseTemplate } from './templates/base-template';

/**
 * WebView panel configuration
 */
export interface WebViewPanelConfig {
    viewType: string;
    title: string;
    showOptions?: vscode.ViewColumn | { viewColumn: vscode.ViewColumn; preserveFocus?: boolean };
    options?: vscode.WebviewPanelOptions & vscode.WebviewOptions;
    iconPath?: vscode.Uri | { light: vscode.Uri; dark: vscode.Uri };
}

/**
 * WebView panel state for persistence
 */
export interface WebViewPanelState {
    viewType: string;
    title: string;
    viewColumn?: vscode.ViewColumn;
    active: boolean;
    visible: boolean;
    state?: any;
}

/**
 * Managed WebView panel with lifecycle hooks
 */
export abstract class ManagedWebViewPanel {
    protected panel: vscode.WebviewPanel;
    protected disposables: vscode.Disposable[] = [];
    protected isDisposed: boolean = false;
    protected nonce: string;
    
    constructor(
        panel: vscode.WebviewPanel,
        protected context: vscode.ExtensionContext,
        protected logger: Logger
    ) {
        this.panel = panel;
        this.nonce = this.generateNonce();
        this.setupPanel();
    }
    
    /**
     * Generate a nonce for Content Security Policy
     */
    private generateNonce(): string {
        return crypto.randomBytes(16).toString('base64');
    }
    
    /**
     * Set up panel event handlers
     */
    private setupPanel(): void {
        // Handle panel disposal
        this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
        
        // Handle messages from WebView
        this.panel.webview.onDidReceiveMessage(
            message => this.handleMessage(message),
            null,
            this.disposables
        );
        
        // Handle visibility changes
        this.panel.onDidChangeViewState(
            e => this.handleViewStateChange(e.webviewPanel.visible, e.webviewPanel.active),
            null,
            this.disposables
        );
    }
    
    /**
     * Get resource URI for WebView
     */
    protected getResourceUri(relativePath: string): vscode.Uri {
        const onDiskPath = vscode.Uri.joinPath(this.context.extensionUri, relativePath);
        return this.panel.webview.asWebviewUri(onDiskPath);
    }
    
    /**
     * Update panel HTML content
     */
    protected updateContent(content: string): void {
        if (!this.isDisposed) {
            this.panel.webview.html = content;
        }
    }
    
    /**
     * Send message to WebView
     */
    public postMessage(message: any): Thenable<boolean> {
        if (!this.isDisposed) {
            return this.panel.webview.postMessage(message);
        }
        return Promise.resolve(false);
    }
    
    /**
     * Handle messages from WebView
     */
    protected abstract handleMessage(message: any): void;
    
    /**
     * Handle view state changes
     */
    protected handleViewStateChange(visible: boolean, active: boolean): void {
        // Override in subclasses if needed
    }
    
    /**
     * Get panel state for persistence
     */
    public getState(): WebViewPanelState {
        return {
            viewType: this.panel.viewType,
            title: this.panel.title,
            viewColumn: this.panel.viewColumn,
            active: this.panel.active,
            visible: this.panel.visible,
            state: this.getPanelState()
        };
    }
    
    /**
     * Get panel-specific state for persistence
     */
    protected abstract getPanelState(): any;
    
    /**
     * Restore panel-specific state
     */
    public abstract restoreState(state: any): void;
    
    /**
     * Reveal the panel
     */
    public reveal(preserveFocus?: boolean): void {
        if (!this.isDisposed) {
            this.panel.reveal(undefined, preserveFocus);
        }
    }
    
    /**
     * Dispose the panel
     */
    public dispose(): void {
        if (this.isDisposed) {
            return;
        }
        
        this.isDisposed = true;
        
        // Clean up disposables
        while (this.disposables.length) {
            const disposable = this.disposables.pop();
            if (disposable) {
                disposable.dispose();
            }
        }
        
        // Dispose the panel
        this.panel.dispose();
    }
}

/**
 * WebView Manager - Singleton service for managing all WebView panels
 */
export class WebViewManager {
    private static instance: WebViewManager;
    private panels: Map<string, ManagedWebViewPanel> = new Map();
    private panelFactories: Map<string, (panel: vscode.WebviewPanel) => ManagedWebViewPanel> = new Map();
    private logger: Logger;
    
    private constructor(private context: vscode.ExtensionContext) {
        this.logger = Logger.getInstance();
        this.restorePanels();
    }
    
    /**
     * Get singleton instance
     */
    public static getInstance(context: vscode.ExtensionContext): WebViewManager {
        if (!WebViewManager.instance) {
            WebViewManager.instance = new WebViewManager(context);
        }
        return WebViewManager.instance;
    }
    
    /**
     * Register a panel factory for a view type
     */
    public registerPanelFactory(
        viewType: string, 
        factory: (panel: vscode.WebviewPanel) => ManagedWebViewPanel
    ): void {
        this.panelFactories.set(viewType, factory);
    }
    
    /**
     * Create or show a WebView panel
     */
    public createOrShowPanel(
        id: string,
        config: WebViewPanelConfig,
        factory: (panel: vscode.WebviewPanel) => ManagedWebViewPanel
    ): ManagedWebViewPanel {
        // Check if panel already exists
        const existing = this.panels.get(id);
        if (existing) {
            existing.reveal();
            return existing;
        }
        
        // Create panel options with secure defaults
        const options: vscode.WebviewPanelOptions & vscode.WebviewOptions = {
            enableScripts: true,
            localResourceRoots: [
                vscode.Uri.joinPath(this.context.extensionUri, 'media'),
                vscode.Uri.joinPath(this.context.extensionUri, 'dist')
            ],
            retainContextWhenHidden: true,
            ...config.options
        };
        
        // Create the panel
        const panel = vscode.window.createWebviewPanel(
            config.viewType,
            config.title,
            config.showOptions || vscode.ViewColumn.One,
            options
        );
        
        // Set icon if provided
        if (config.iconPath) {
            panel.iconPath = config.iconPath;
        }
        
        // Create managed panel instance
        const managedPanel = factory(panel);
        
        // Track the panel
        this.panels.set(id, managedPanel);
        
        // Handle disposal
        panel.onDidDispose(() => {
            this.panels.delete(id);
            this.savePanelStates();
        });
        
        // Save panel states on changes
        panel.onDidChangeViewState(() => {
            this.savePanelStates();
        });
        
        this.logger.info(`Created WebView panel: ${id}`);
        
        return managedPanel;
    }
    
    /**
     * Get a panel by ID
     */
    public getPanel(id: string): ManagedWebViewPanel | undefined {
        return this.panels.get(id);
    }
    
    /**
     * Get all panels
     */
    public getAllPanels(): Map<string, ManagedWebViewPanel> {
        return new Map(this.panels);
    }
    
    /**
     * Close a panel by ID
     */
    public closePanel(id: string): void {
        const panel = this.panels.get(id);
        if (panel) {
            panel.dispose();
        }
    }
    
    /**
     * Close all panels
     */
    public closeAllPanels(): void {
        this.panels.forEach(panel => panel.dispose());
        this.panels.clear();
    }
    
    /**
     * Save panel states for restoration
     */
    private savePanelStates(): void {
        const states: Record<string, WebViewPanelState> = {};
        
        this.panels.forEach((panel, id) => {
            states[id] = panel.getState();
        });
        
        this.context.workspaceState.update('coachntt.webviewPanels', states);
    }
    
    /**
     * Restore panels from saved state
     */
    private restorePanels(): void {
        const states = this.context.workspaceState.get<Record<string, WebViewPanelState>>('coachntt.webviewPanels');
        
        if (states) {
            // TODO: Implement panel restoration when view serializers are registered
            this.logger.debug('Panel states found for restoration', Object.keys(states));
        }
    }
    
    /**
     * Get resource URI helper
     */
    public getResourceUri(relativePath: string): vscode.Uri {
        const onDiskPath = vscode.Uri.joinPath(this.context.extensionUri, relativePath);
        // Use the first panel's webview for URI conversion, or create a temporary one
        const firstPanel = this.panels.values().next().value;
        if (firstPanel) {
            return firstPanel.panel.webview.asWebviewUri(onDiskPath);
        }
        
        // Fallback: return the on-disk path
        return onDiskPath;
    }
    
    /**
     * Dispose all resources
     */
    public dispose(): void {
        this.closeAllPanels();
    }
}