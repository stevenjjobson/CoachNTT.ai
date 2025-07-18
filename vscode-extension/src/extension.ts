import * as vscode from 'vscode';
import { Logger } from './utils/logger';
import { ConfigurationService } from './config/settings';
import { CommandRegistry } from './commands';
import { WelcomeViewProvider } from './providers/welcomeView';
import { MCPClient } from './services/mcp-client';
import { ConnectionManager } from './services/connection-manager';
import { MemoryTreeProvider } from './providers/memory-tree-provider';
import { MemoryCommands } from './commands/memory-commands';
import { MemoryContentProvider } from './providers/memory-content-provider';
import { WebViewManager } from './webview/webview-manager';
import { MemoryDetailPanel } from './webview/panels/memory-detail-panel';
import { AudioPlaybackService } from './services/audio-playback-service';
import { AudioPlayerPanel } from './webview/audio-player/audio-player-panel';

/**
 * Extension state management
 */
export class ExtensionState {
    private static instance: ExtensionState;
    private logger: Logger;
    private config: ConfigurationService;
    private commands: CommandRegistry;
    private welcomeViewProvider: WelcomeViewProvider | undefined;
    private memoryTreeProvider: MemoryTreeProvider | undefined;
    private memoryCommands: MemoryCommands | undefined;
    private memoryContentProvider: MemoryContentProvider | undefined;
    private mcpClient: MCPClient | undefined;
    private connectionManager: ConnectionManager | undefined;
    private webViewManager: WebViewManager | undefined;
    private audioService: AudioPlaybackService | undefined;
    private statusBarItems: Map<string, vscode.StatusBarItem>;
    private disposables: vscode.Disposable[];

    private constructor() {
        this.logger = Logger.getInstance();
        this.config = ConfigurationService.getInstance();
        this.commands = CommandRegistry.getInstance();
        this.statusBarItems = new Map();
        this.disposables = [];
    }

    public static getInstance(): ExtensionState {
        if (!ExtensionState.instance) {
            ExtensionState.instance = new ExtensionState();
        }
        return ExtensionState.instance;
    }

    /**
     * Initialize extension
     */
    public async initialize(context: vscode.ExtensionContext): Promise<void> {
        this.logger.info('CoachNTT extension activating...');
        
        try {
            // Initialize MCP client and connection manager first
            this.initializeMCPServices(context);
            
            // Initialize WebView manager
            this.webViewManager = WebViewManager.getInstance(context);
            
            // Initialize Audio service
            this.audioService = AudioPlaybackService.getInstance(context);
            
            // Set connection manager getter to avoid circular dependency
            this.commands.setConnectionManagerGetter(() => this.connectionManager);
            
            // Register commands
            this.commands.registerCommands(context);
            
            // Create status bar items
            this.createStatusBarItems(context);
            
            // Register views
            this.registerViews(context);
            
            // Register WebView commands
            this.registerWebViewCommands(context);
            
            // Register audio commands
            this.registerAudioCommands(context);
            
            // Create audio status bar item
            if (this.audioService) {
                const audioStatusBar = this.audioService.createStatusBarItem();
                context.subscriptions.push(audioStatusBar);
            }
            
            // Auto-connect if configured
            if (this.config.getAutoConnect()) {
                this.logger.info('Auto-connecting to backend...');
                await vscode.commands.executeCommand('coachntt.connect');
            }
            
            // Show welcome message
            this.showWelcomeMessage(context);
            
            this.logger.info('CoachNTT extension activated successfully');
            
        } catch (error) {
            this.logger.error('Failed to activate extension', error);
            throw error;
        }
    }

    /**
     * Create status bar items
     */
    private createStatusBarItems(context: vscode.ExtensionContext): void {
        // Connection status
        const connectionStatus = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );
        connectionStatus.text = '$(circle-slash) CoachNTT';
        connectionStatus.tooltip = 'Click to connect to CoachNTT backend';
        connectionStatus.command = 'coachntt.connect';
        connectionStatus.show();
        this.statusBarItems.set('connection', connectionStatus);
        context.subscriptions.push(connectionStatus);

        // Safety score indicator
        const safetyScore = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            99
        );
        safetyScore.text = '$(shield) 0.0';
        safetyScore.tooltip = 'Current safety score';
        safetyScore.hide(); // Hidden until connected
        this.statusBarItems.set('safety', safetyScore);
        context.subscriptions.push(safetyScore);

        // Quick actions
        const quickActions = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            98
        );
        quickActions.text = '$(gear)';
        quickActions.tooltip = 'CoachNTT Settings';
        quickActions.command = 'coachntt.openSettings';
        quickActions.show();
        this.statusBarItems.set('actions', quickActions);
        context.subscriptions.push(quickActions);

        // Listen for connection state changes
        context.subscriptions.push(
            vscode.workspace.onDidChangeConfiguration(e => {
                if (e.affectsConfiguration('coachntt')) {
                    this.updateStatusBarItems();
                }
            })
        );
    }

    /**
     * Update status bar items based on state
     */
    public updateStatusBarItems(isConnected: boolean = false, safetyScore: number = 0): void {
        const connectionStatus = this.statusBarItems.get('connection');
        const safetyIndicator = this.statusBarItems.get('safety');
        
        if (connectionStatus) {
            if (isConnected) {
                connectionStatus.text = '$(pass-filled) CoachNTT';
                connectionStatus.tooltip = 'Connected to CoachNTT backend (click to disconnect)';
                connectionStatus.command = 'coachntt.disconnect';
                connectionStatus.backgroundColor = undefined;
            } else {
                connectionStatus.text = '$(circle-slash) CoachNTT';
                connectionStatus.tooltip = 'Disconnected from CoachNTT backend (click to connect)';
                connectionStatus.command = 'coachntt.connect';
                connectionStatus.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
            }
        }
        
        if (safetyIndicator) {
            if (isConnected) {
                safetyIndicator.text = `$(shield) ${safetyScore.toFixed(1)}`;
                
                // Color based on safety score
                if (safetyScore >= this.config.getMinSafetyScore()) {
                    safetyIndicator.backgroundColor = undefined;
                    safetyIndicator.tooltip = `Safety score: ${safetyScore.toFixed(2)} (Good)`;
                } else {
                    safetyIndicator.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                    safetyIndicator.tooltip = `Safety score: ${safetyScore.toFixed(2)} (Below threshold)`;
                }
                
                safetyIndicator.show();
            } else {
                safetyIndicator.hide();
            }
        }
    }

    /**
     * Register views
     */
    private registerViews(context: vscode.ExtensionContext): void {
        // Create welcome view provider
        this.welcomeViewProvider = new WelcomeViewProvider();
        
        // Register tree data provider
        const welcomeTreeView = vscode.window.createTreeView('coachntt.welcome', {
            treeDataProvider: this.welcomeViewProvider,
            showCollapseAll: true
        });
        
        context.subscriptions.push(welcomeTreeView);
        
        // Register refresh command for the view
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.refreshView', () => {
                this.welcomeViewProvider?.refresh();
            })
        );
        
        // Register memory tree view if connected
        if (this.mcpClient && this.memoryTreeProvider) {
            const memoryTreeView = vscode.window.createTreeView('coachntt.memories', {
                treeDataProvider: this.memoryTreeProvider,
                showCollapseAll: true,
                canSelectMany: false
            });
            
            context.subscriptions.push(memoryTreeView);
            
            // Register memory content provider
            this.memoryContentProvider = new MemoryContentProvider(this.mcpClient, this.logger);
            const scheme = 'coachntt-memory';
            context.subscriptions.push(
                vscode.workspace.registerTextDocumentContentProvider(scheme, this.memoryContentProvider)
            );
            
            // Register memory commands
            this.memoryCommands = new MemoryCommands(this.mcpClient, this.memoryTreeProvider, this.logger);
            this.memoryCommands.registerCommands(context);
        }
    }

    /**
     * Show welcome message on first activation
     */
    private showWelcomeMessage(context: vscode.ExtensionContext): void {
        const key = 'coachntt.welcomed';
        const welcomed = context.globalState.get(key, false);
        
        if (!welcomed) {
            const message = 'Welcome to CoachNTT! Your AI coding assistant is ready.';
            const actions = ['Get Started', 'Settings', 'Documentation'];
            
            vscode.window.showInformationMessage(message, ...actions).then(selection => {
                switch (selection) {
                    case 'Get Started':
                        vscode.commands.executeCommand('coachntt.connect');
                        break;
                    case 'Settings':
                        vscode.commands.executeCommand('coachntt.openSettings');
                        break;
                    case 'Documentation':
                        vscode.env.openExternal(vscode.Uri.parse('https://github.com/coachntt/vscode-extension#readme'));
                        break;
                }
            });
            
            context.globalState.update(key, true);
        }
    }

    /**
     * Initialize MCP services
     */
    private initializeMCPServices(context: vscode.ExtensionContext): void {
        try {
            // Create MCP client
            this.mcpClient = new MCPClient(this.logger);
            
            // Create connection manager
            this.connectionManager = new ConnectionManager(this.mcpClient, this.logger);
            
            // Create memory tree provider
            this.memoryTreeProvider = new MemoryTreeProvider(this.mcpClient, this.logger);
            
            // Set up connection state change handler
            this.mcpClient.on('connected', () => {
                this.updateStatusBarItems(true, 0.95); // Default good safety score
                vscode.commands.executeCommand('setContext', 'coachntt.connected', true);
                
                // Register memory view if not already registered
                if (!this.memoryCommands) {
                    this.registerViews(context);
                }
            });
            
            this.mcpClient.on('disconnected', () => {
                this.updateStatusBarItems(false, 0);
                vscode.commands.executeCommand('setContext', 'coachntt.connected', false);
            });
            
            this.mcpClient.on('error', (error: Error) => {
                this.logger.error('MCP client error', error);
                vscode.window.showErrorMessage(`CoachNTT error: ${error.message}`);
            });
            
        } catch (error) {
            this.logger.error('Failed to initialize MCP services', error);
        }
    }
    
    /**
     * Get MCP client instance
     */
    public getMCPClient(): MCPClient | undefined {
        return this.mcpClient;
    }
    
    /**
     * Get connection manager instance
     */
    public getConnectionManager(): ConnectionManager | undefined {
        return this.connectionManager;
    }
    
    /**
     * Register WebView commands
     */
    private registerWebViewCommands(context: vscode.ExtensionContext): void {
        // Command to open memory detail in WebView
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.openMemoryWebView', async (memory: any) => {
                if (!this.webViewManager || !this.mcpClient) {
                    vscode.window.showErrorMessage('WebView manager not initialized');
                    return;
                }
                
                const panelId = `memory-detail-${memory.id}`;
                
                this.webViewManager.createOrShowPanel(
                    panelId,
                    {
                        viewType: 'coachntt.memoryDetail',
                        title: 'Memory Details',
                        showOptions: vscode.ViewColumn.Two,
                        options: {
                            enableScripts: true,
                            retainContextWhenHidden: true
                        }
                    },
                    (panel) => new MemoryDetailPanel(
                        panel,
                        context,
                        this.logger,
                        this.mcpClient!,
                        memory
                    )
                );
            })
        );
        
        // Command to open WebView panel test
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.testWebView', () => {
                if (!this.webViewManager) {
                    vscode.window.showErrorMessage('WebView manager not initialized');
                    return;
                }
                
                vscode.window.showInformationMessage('WebView foundation is ready!');
            })
        );
    }
    
    /**
     * Register audio commands
     */
    private registerAudioCommands(context: vscode.ExtensionContext): void {
        if (!this.audioService) return;
        
        // Toggle playback command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.togglePlayback', () => {
                if (!this.audioService) return;
                
                if (this.audioService.getState() === 'playing') {
                    this.audioService.pause();
                } else {
                    this.audioService.play();
                }
            })
        );
        
        // Open audio player command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.openAudioPlayer', () => {
                if (!this.webViewManager || !this.audioService) {
                    vscode.window.showErrorMessage('Audio service not initialized');
                    return;
                }
                
                this.webViewManager.createOrShowPanel(
                    'audio-player',
                    {
                        viewType: 'coachntt.audioPlayer',
                        title: 'Audio Player',
                        showOptions: vscode.ViewColumn.Two,
                        options: {
                            enableScripts: true,
                            retainContextWhenHidden: true
                        }
                    },
                    (panel) => new AudioPlayerPanel(
                        panel,
                        context,
                        this.logger,
                        this.audioService!
                    )
                );
            })
        );
        
        // Add to queue from selection command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.addSelectionToAudioQueue', async () => {
                const editor = vscode.window.activeTextEditor;
                if (!editor || !this.audioService) return;
                
                const selection = editor.selection;
                const text = editor.document.getText(selection);
                
                if (!text) {
                    vscode.window.showWarningMessage('No text selected');
                    return;
                }
                
                try {
                    await this.audioService.addToQueue(text, 'synthesis', {
                        metadata: {
                            source: vscode.workspace.asRelativePath(editor.document.fileName)
                        }
                    });
                    
                    vscode.window.showInformationMessage('Added to audio queue');
                } catch (error) {
                    this.logger.error('Failed to add to audio queue', error);
                    vscode.window.showErrorMessage('Failed to add to audio queue');
                }
            })
        );
        
        // Play/pause command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.audioPlay', () => {
                this.audioService?.play();
            })
        );
        
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.audioPause', () => {
                this.audioService?.pause();
            })
        );
        
        // Skip commands
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.audioNext', () => {
                this.audioService?.next();
            })
        );
        
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.audioPrevious', () => {
                this.audioService?.previous();
            })
        );
        
        // Volume commands
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.audioVolumeUp', () => {
                if (!this.audioService) return;
                const currentVolume = this.audioService.getVolume();
                this.audioService.setVolume(Math.min(100, currentVolume + 10));
            })
        );
        
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.audioVolumeDown', () => {
                if (!this.audioService) return;
                const currentVolume = this.audioService.getVolume();
                this.audioService.setVolume(Math.max(0, currentVolume - 10));
            })
        );
    }
    
    /**
     * Cleanup extension state
     */
    public dispose(): void {
        this.logger.info('CoachNTT extension deactivating...');
        
        // Dispose all disposables
        this.disposables.forEach(d => d.dispose());
        
        // Dispose status bar items
        this.statusBarItems.forEach(item => item.dispose());
        
        // Dispose services
        this.memoryContentProvider?.dispose();
        this.memoryTreeProvider?.dispose();
        this.audioService?.dispose();
        this.webViewManager?.dispose();
        this.connectionManager?.dispose();
        this.mcpClient?.disconnect();
        this.commands.dispose();
        this.config.dispose();
        this.logger.dispose();
        
        this.logger.info('CoachNTT extension deactivated');
    }
}

/**
 * Extension activation
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    const state = ExtensionState.getInstance();
    await state.initialize(context);
    
    // Update status bar when connection state changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('coachntt.connected')) {
                const isConnected = context.workspaceState.get<boolean>('connected', false);
                state.updateStatusBarItems(isConnected);
            }
        })
    );
}

/**
 * Extension deactivation
 */
export function deactivate(): void {
    const state = ExtensionState.getInstance();
    state.dispose();
}