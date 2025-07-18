import * as vscode from 'vscode';
import { Logger } from '../utils/logger';
import { ConfigurationService } from '../config/settings';
import { ConnectionManager } from '../services/connection-manager';

/**
 * Command handler type
 */
type CommandHandler = (...args: any[]) => any;

/**
 * Command registry for managing all extension commands
 */
export class CommandRegistry {
    private static instance: CommandRegistry;
    private logger: Logger;
    private config: ConfigurationService;
    private connectionManager: ConnectionManager;
    private commands: Map<string, vscode.Disposable>;

    private constructor() {
        this.logger = Logger.getInstance();
        this.config = ConfigurationService.getInstance();
        this.connectionManager = ConnectionManager.getInstance();
        this.commands = new Map();
    }

    /**
     * Get singleton instance
     */
    public static getInstance(): CommandRegistry {
        if (!CommandRegistry.instance) {
            CommandRegistry.instance = new CommandRegistry();
        }
        return CommandRegistry.instance;
    }

    /**
     * Register all extension commands
     */
    public registerCommands(context: vscode.ExtensionContext): void {
        this.logger.info('Registering extension commands');

        // Initialize connection manager with context
        this.connectionManager.initialize(context);

        // Register each command
        this.register('coachntt.connect', () => this.handleConnect());
        this.register('coachntt.disconnect', () => this.handleDisconnect());
        this.register('coachntt.showLogs', () => this.handleShowLogs());
        this.register('coachntt.openSettings', () => this.handleOpenSettings());
        this.register('coachntt.refreshView', () => this.handleRefreshView());
        this.register('coachntt.checkStatus', () => this.handleCheckStatus());

        // Add all disposables to context
        this.commands.forEach(disposable => {
            context.subscriptions.push(disposable);
        });

        this.logger.info(`Registered ${this.commands.size} commands`);
    }

    /**
     * Register a single command
     */
    private register(commandId: string, handler: CommandHandler): void {
        const disposable = vscode.commands.registerCommand(commandId, async (...args) => {
            try {
                this.logger.debug(`Executing command: ${commandId}`);
                await handler(...args);
            } catch (error) {
                this.logger.error(`Command failed: ${commandId}`, error);
                vscode.window.showErrorMessage(`Command failed: ${commandId}`);
            }
        });

        this.commands.set(commandId, disposable);
    }

    /**
     * Handle connect command
     */
    private async handleConnect(): Promise<void> {
        this.logger.info('Connecting to backend');
        
        try {
            // Validate settings first
            const validation = this.config.validateSettings();
            if (!validation.valid) {
                vscode.window.showErrorMessage(
                    `Invalid configuration: ${validation.errors.join(', ')}`
                );
                return;
            }

            // Connect using ConnectionManager
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'Connecting to CoachNTT backend...',
                cancellable: false
            }, async (progress) => {
                progress.report({ increment: 30 });
                
                try {
                    await this.connectionManager.connect();
                    progress.report({ increment: 70, message: 'Connected!' });
                } catch (error) {
                    throw error;
                }
            });
            
        } catch (error) {
            this.logger.error('Failed to connect', error);
            // Error already handled by ConnectionManager
        }
    }

    /**
     * Handle disconnect command
     */
    private async handleDisconnect(): Promise<void> {
        this.logger.info('Disconnecting from backend');
        
        try {
            await this.connectionManager.disconnect();
            this.logger.info('Successfully disconnected from backend');
            
        } catch (error) {
            this.logger.error('Failed to disconnect', error);
            vscode.window.showErrorMessage('Failed to disconnect from backend');
        }
    }

    /**
     * Handle show logs command
     */
    private handleShowLogs(): void {
        this.logger.show();
    }

    /**
     * Handle open settings command
     */
    private async handleOpenSettings(): Promise<void> {
        await vscode.commands.executeCommand(
            'workbench.action.openSettings',
            '@ext:coachntt.coachntt'
        );
    }

    /**
     * Handle refresh view command
     */
    private async handleRefreshView(): Promise<void> {
        this.logger.info('Refreshing CoachNTT view');
        // TODO: Implement view refresh logic when views are created
        vscode.window.showInformationMessage('View refreshed');
    }

    /**
     * Handle check status command
     */
    private async handleCheckStatus(): Promise<void> {
        const config = this.config.getConnectionConfig();
        const state = this.connectionManager.getState();
        const status = state.connected ? 'Connected' : 'Disconnected';
        
        let message = `
Status: ${status}
API URL: ${config.url}
WebSocket URL: ${config.websocketUrl}
Safety Validation: ${this.config.getSafetyValidation() ? 'Enabled' : 'Disabled'}
Min Safety Score: ${this.config.getMinSafetyScore()}
        `.trim();

        if (state.connected) {
            message += `\n\nConnection Details:`;
            message += `\nUser ID: ${state.userId || 'Unknown'}`;
            message += `\nChannels: ${state.channels.size} subscribed`;
            message += `\nReconnect Attempts: ${state.reconnectAttempts}`;
        }

        vscode.window.showInformationMessage(message, { modal: true });
    }

    /**
     * Get connection status
     */
    public getConnectionStatus(): boolean {
        return this.connectionManager.getState().connected;
    }

    /**
     * Dispose all commands
     */
    public dispose(): void {
        this.commands.forEach(disposable => disposable.dispose());
        this.commands.clear();
        this.connectionManager.dispose();
    }
}