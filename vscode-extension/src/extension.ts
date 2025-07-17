import * as vscode from 'vscode';
import { Logger } from './utils/logger';
import { ConfigurationService } from './config/settings';
import { CommandRegistry } from './commands';
import { WelcomeViewProvider } from './providers/welcomeView';

/**
 * Extension state management
 */
class ExtensionState {
    private static instance: ExtensionState;
    private logger: Logger;
    private config: ConfigurationService;
    private commands: CommandRegistry;
    private welcomeViewProvider: WelcomeViewProvider | undefined;
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
            // Register commands
            this.commands.registerCommands(context);
            
            // Create status bar items
            this.createStatusBarItems(context);
            
            // Register views
            this.registerViews(context);
            
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
        const treeView = vscode.window.createTreeView('coachntt.welcome', {
            treeDataProvider: this.welcomeViewProvider,
            showCollapseAll: true
        });
        
        context.subscriptions.push(treeView);
        
        // Register refresh command for the view
        context.subscriptions.push(
            vscode.commands.registerCommand('coachntt.refreshView', () => {
                this.welcomeViewProvider?.refresh();
            })
        );
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
     * Cleanup extension state
     */
    public dispose(): void {
        this.logger.info('CoachNTT extension deactivating...');
        
        // Dispose all disposables
        this.disposables.forEach(d => d.dispose());
        
        // Dispose status bar items
        this.statusBarItems.forEach(item => item.dispose());
        
        // Dispose services
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