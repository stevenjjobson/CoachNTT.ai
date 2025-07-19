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
import { AudioCaptureService } from './services/audio-capture-service';
import { AudioSourceType } from './models/audio-queue';
import { VoiceInputPanel } from './webview/voice-input/voice-input-panel';
import { MonitoringService } from './services/monitoring-service';
import { MonitoringDashboard } from './webview/monitoring/monitoring-dashboard';
import { CodeAnalysisService } from './services/code-analysis-service';
import { ComplexityCodeLensProvider } from './providers/code-lens-provider';
import { CodeInsightsPanel } from './webview/code-insights/code-insights-panel';
import { LivingDocumentService } from './services/living-document-service';
import { DocumentTreeProvider } from './providers/document-tree-provider';

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
    private audioCaptureService: AudioCaptureService | undefined;
    private monitoringService: MonitoringService | undefined;
    private codeAnalysisService: CodeAnalysisService | undefined;
    private codeLensProvider: ComplexityCodeLensProvider | undefined;
    private livingDocumentService: LivingDocumentService | undefined;
    private documentTreeProvider: DocumentTreeProvider | undefined;
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
            
            // Initialize Audio services
            this.audioService = AudioPlaybackService.getInstance(context);
            this.audioCaptureService = AudioCaptureService.getInstance();
            
            // Initialize Monitoring service
            this.monitoringService = MonitoringService.getInstance();
            
            // Initialize Code Analysis service
            this.codeAnalysisService = CodeAnalysisService.getInstance();
            this.codeLensProvider = new ComplexityCodeLensProvider();
            
            // Initialize Living Documents (will be connected when MCP is ready)
            this.documentTreeProvider = new DocumentTreeProvider();
            
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
            
            // Register voice commands
            this.registerVoiceCommands(context);
            
            // Register monitoring commands
            this.registerMonitoringCommands(context);
            
            // Register code analysis commands
            this.registerCodeAnalysisCommands(context);
            
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
            // Get MCP client singleton
            this.mcpClient = MCPClient.getInstance();
            
            // Get connection manager singleton
            this.connectionManager = ConnectionManager.getInstance();
            
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
                
                // Initialize Living Document service when connected
                if (!this.livingDocumentService) {
                    this.livingDocumentService = LivingDocumentService.getInstance(this.mcpClient);
                    this.registerLivingDocumentCommands(context);
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
                    await this.audioService.addToQueue(text, AudioSourceType.SYNTHESIS, {
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
     * Register voice commands
     */
    private registerVoiceCommands(context: vscode.ExtensionContext): void {
        if (!this.audioCaptureService) return;
        
        // Open voice input panel command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.openVoiceInput', () => {
                if (!this.webViewManager || !this.audioCaptureService) {
                    vscode.window.showErrorMessage('Voice input service not initialized');
                    return;
                }
                
                this.webViewManager.createOrShowPanel(
                    'voice-input',
                    {
                        viewType: 'coachntt.voiceInput',
                        title: 'Voice Input',
                        showOptions: vscode.ViewColumn.Two,
                        options: {
                            enableScripts: true,
                            retainContextWhenHidden: true
                        }
                    },
                    (panel) => new VoiceInputPanel(panel, context, this.logger)
                );
            })
        );
        
        // Start voice recording command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.startVoiceRecording', async () => {
                if (!this.audioCaptureService) return;
                
                try {
                    const state = this.audioCaptureService.getState();
                    if (state === 'idle') {
                        await this.audioCaptureService.initialize();
                    }
                    this.audioCaptureService.startRecording();
                    vscode.window.showInformationMessage('Voice recording started');
                } catch (error) {
                    this.logger.error('Failed to start voice recording', error);
                    vscode.window.showErrorMessage('Failed to start voice recording');
                }
            })
        );
        
        // Stop voice recording command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.stopVoiceRecording', async () => {
                if (!this.audioCaptureService) return;
                
                try {
                    await this.audioCaptureService.stopRecording();
                    vscode.window.showInformationMessage('Voice recording stopped');
                } catch (error) {
                    this.logger.error('Failed to stop voice recording', error);
                    vscode.window.showErrorMessage('Failed to stop voice recording');
                }
            })
        );
        
        // Toggle push-to-talk command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.togglePushToTalk', () => {
                if (!this.audioCaptureService) return;
                
                // This command is meant to be used with keybindings
                // The actual push-to-talk logic is handled in the WebView
                vscode.commands.executeCommand('coachntt.openVoiceInput');
            })
        );
        
        // Toggle VAD command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.toggleVAD', () => {
                if (!this.audioCaptureService) return;
                
                // Toggle VAD state
                const vadEnabled = !this.audioCaptureService.vadEnabled;
                this.audioCaptureService.setVADEnabled(vadEnabled);
                
                vscode.window.showInformationMessage(
                    `Voice Activity Detection ${vadEnabled ? 'enabled' : 'disabled'}`
                );
            })
        );
    }
    
    /**
     * Register monitoring commands
     */
    private registerMonitoringCommands(context: vscode.ExtensionContext): void {
        if (!this.monitoringService) return;
        
        // Open monitoring dashboard command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.openMonitoringDashboard', () => {
                if (!this.webViewManager || !this.monitoringService) {
                    vscode.window.showErrorMessage('Monitoring service not initialized');
                    return;
                }
                
                this.webViewManager.createOrShowPanel(
                    'monitoring-dashboard',
                    {
                        viewType: 'coachntt.monitoringDashboard',
                        title: 'Monitoring Dashboard',
                        showOptions: vscode.ViewColumn.Two,
                        options: {
                            enableScripts: true,
                            retainContextWhenHidden: true
                        }
                    },
                    (panel) => new MonitoringDashboard(
                        panel,
                        context,
                        this.logger
                    )
                );
            })
        );
        
        // Update session count command (for testing)
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.updateSessionCount', async () => {
                const input = await vscode.window.showInputBox({
                    prompt: 'Enter number of active sessions',
                    value: '1',
                    validateInput: (value) => {
                        const num = parseInt(value);
                        if (isNaN(num) || num < 1 || num > 100) {
                            return 'Please enter a number between 1 and 100';
                        }
                        return null;
                    }
                });
                
                if (input) {
                    this.monitoringService?.updateSessionCount(parseInt(input));
                    vscode.window.showInformationMessage(`Session count updated to ${input}`);
                }
            })
        );
        
        // Show monitoring status bar item
        const monitoringStatus = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            97
        );
        monitoringStatus.text = '$(dashboard) Monitor';
        monitoringStatus.tooltip = 'Open Monitoring Dashboard';
        monitoringStatus.command = 'coachntt.openMonitoringDashboard';
        monitoringStatus.show();
        this.statusBarItems.set('monitoring', monitoringStatus);
        context.subscriptions.push(monitoringStatus);
    }
    
    /**
     * Register code analysis commands
     */
    private registerCodeAnalysisCommands(context: vscode.ExtensionContext): void {
        if (!this.codeAnalysisService) return;
        
        // Register CodeLens provider
        context.subscriptions.push(
            vscode.languages.registerCodeLensProvider(
                [
                    { language: 'typescript' },
                    { language: 'javascript' },
                    { language: 'typescriptreact' },
                    { language: 'javascriptreact' }
                ],
                this.codeLensProvider!
            )
        );
        
        // Open code insights panel
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.openCodeInsights', () => {
                if (!this.webViewManager || !this.codeAnalysisService) {
                    vscode.window.showErrorMessage('Code analysis service not initialized');
                    return;
                }
                
                this.webViewManager.createOrShowPanel(
                    'code-insights',
                    {
                        viewType: 'coachntt.codeInsights',
                        title: 'Code Insights',
                        showOptions: vscode.ViewColumn.Two,
                        options: {
                            enableScripts: true,
                            retainContextWhenHidden: true
                        }
                    },
                    (panel) => new CodeInsightsPanel(
                        panel,
                        context,
                        this.logger
                    )
                );
            })
        );
        
        // Analyze current file command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.analyzeCurrentFile', async () => {
                const editor = vscode.window.activeTextEditor;
                if (!editor) {
                    vscode.window.showWarningMessage('No active editor');
                    return;
                }
                
                try {
                    const result = await this.codeAnalysisService!.analyzeFile(editor.document.uri);
                    vscode.window.showInformationMessage(
                        `Analysis complete - Score: ${result.summary.score} (${result.summary.grade})`
                    );
                } catch (error) {
                    vscode.window.showErrorMessage('Analysis failed: ' + (error as Error).message);
                }
            })
        );
        
        // Show complexity details command (for CodeLens)
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.showComplexityDetails', 
                (uri: vscode.Uri, range: vscode.Range, metrics: any) => {
                    vscode.window.showInformationMessage(
                        `Complexity - Cyclomatic: ${metrics.cyclomatic}, Cognitive: ${metrics.cognitive}, Nesting: ${metrics.nestingDepth}`
                    );
                }
            )
        );
        
        // Show pattern details command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.showPatternDetails',
                (uri: vscode.Uri, pattern: any) => {
                    vscode.window.showInformationMessage(
                        `${pattern.name}: ${pattern.description}`
                    );
                }
            )
        );
        
        // Show class analysis command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.showClassAnalysis',
                (uri: vscode.Uri, range: vscode.Range, metrics: any) => {
                    vscode.window.showInformationMessage(
                        `Class Analysis - Methods: ${metrics.methodCount}, Properties: ${metrics.propertyCount}, Total Complexity: ${metrics.totalComplexity}`
                    );
                }
            )
        );
        
        // Show performance hints command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.showPerformanceHints',
                (uri: vscode.Uri, range: vscode.Range, issues: string[]) => {
                    vscode.window.showWarningMessage(
                        `Performance Issues: ${issues.join(', ')}`
                    );
                }
            )
        );
        
        // Enable/disable CodeLens command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.toggleCodeLens', () => {
                const config = vscode.workspace.getConfiguration('coachntt.codeAnalysis');
                const enabled = config.get('enableCodeLens', true);
                config.update('enableCodeLens', !enabled, vscode.ConfigurationTarget.Global);
                vscode.window.showInformationMessage(
                    `CodeLens ${!enabled ? 'enabled' : 'disabled'}`
                );
            })
        );
        
        // Analysis status bar item
        const analysisStatus = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            96
        );
        analysisStatus.text = '$(code) Analyze';
        analysisStatus.tooltip = 'Open Code Insights';
        analysisStatus.command = 'coachntt.openCodeInsights';
        analysisStatus.show();
        this.statusBarItems.set('analysis', analysisStatus);
        context.subscriptions.push(analysisStatus);
        
        // Listen for file save to trigger analysis
        context.subscriptions.push(
            vscode.workspace.onDidSaveTextDocument(async (document) => {
                if (this.isSupportedDocument(document)) {
                    const config = vscode.workspace.getConfiguration('coachntt.codeAnalysis');
                    if (config.get('analyzeOnSave', true)) {
                        try {
                            await this.codeAnalysisService!.analyzeFile(document.uri);
                        } catch (error) {
                            this.logger.error('Auto-analysis failed', error);
                        }
                    }
                }
            })
        );
    }
    
    private isSupportedDocument(document: vscode.TextDocument): boolean {
        const supportedLanguages = ['typescript', 'javascript', 'typescriptreact', 'javascriptreact'];
        return supportedLanguages.includes(document.languageId);
    }
    
    /**
     * Register Living Document commands
     */
    private registerLivingDocumentCommands(context: vscode.ExtensionContext): void {
        if (!this.livingDocumentService) return;
        
        // Auto-handle .CoachNTT files
        context.subscriptions.push(
            vscode.workspace.onDidOpenTextDocument(async (document) => {
                if (document.fileName.endsWith('.CoachNTT')) {
                    await this.livingDocumentService!.processCoachNTTFile(document.uri);
                }
            })
        );
        
        // Save handler for .CoachNTT files
        context.subscriptions.push(
            vscode.workspace.onDidSaveTextDocument(async (document) => {
                if (document.fileName.endsWith('.CoachNTT')) {
                    await this.livingDocumentService!.processCoachNTTFile(document.uri);
                    vscode.window.showInformationMessage('Living Document updated and abstracted');
                }
            })
        );
        
        // Convert to Living Document command
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.convertToLivingDocument', async () => {
                const editor = vscode.window.activeTextEditor;
                if (!editor) {
                    vscode.window.showWarningMessage('No active editor');
                    return;
                }
                
                try {
                    const newUri = await this.livingDocumentService!.convertToCoachNTT(editor.document.uri);
                    await vscode.window.showTextDocument(newUri);
                    vscode.window.showInformationMessage('Converted to Living Document');
                } catch (error) {
                    vscode.window.showErrorMessage('Failed to convert to Living Document');
                }
            })
        );
        
        // Register document tree view
        const documentTreeView = vscode.window.createTreeView('coachntt.documents', {
            treeDataProvider: this.documentTreeProvider!,
            showCollapseAll: true
        });
        context.subscriptions.push(documentTreeView);
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
        this.audioCaptureService?.dispose();
        this.monitoringService?.dispose();
        this.codeAnalysisService?.dispose();
        this.codeLensProvider?.dispose();
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