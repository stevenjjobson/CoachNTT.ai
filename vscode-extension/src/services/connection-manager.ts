import * as vscode from 'vscode';
import pRetry from 'p-retry';
import { MCPClient } from './mcp-client';
import { MCPConnectionState, MCPChannel, MCPUserNotification } from '../types/mcp.types';
import { Logger } from '../utils/logger';
import { ConfigurationService } from '../config/settings';
import { ExtensionState } from '../extension';

/**
 * Connection Manager
 * 
 * Manages the lifecycle of MCP connections including authentication,
 * retry logic, and integration with VSCode extension state.
 */
export class ConnectionManager {
    private static instance: ConnectionManager;
    
    private mcpClient: MCPClient;
    private logger: Logger;
    private config: ConfigurationService;
    private context: vscode.ExtensionContext | null = null;
    private connectionStatusItem: vscode.StatusBarItem | null = null;
    private unsubscribers: (() => void)[] = [];

    private constructor() {
        this.mcpClient = MCPClient.getInstance();
        this.logger = Logger.getInstance();
        this.config = ConfigurationService.getInstance();
        
        this.setupEventListeners();
    }

    /**
     * Get singleton instance
     */
    public static getInstance(): ConnectionManager {
        if (!ConnectionManager.instance) {
            ConnectionManager.instance = new ConnectionManager();
        }
        return ConnectionManager.instance;
    }

    /**
     * Initialize with extension context
     */
    public initialize(context: vscode.ExtensionContext): void {
        this.context = context;
        
        // Restore previous connection state
        const wasConnected = context.workspaceState.get<boolean>('mcp.connected', false);
        
        if (wasConnected && this.config.getAutoConnect()) {
            this.logger.info('Restoring previous connection');
            this.connect().catch(error => {
                this.logger.error('Failed to restore connection', error);
            });
        }
    }

    /**
     * Connect to MCP server with retry logic
     */
    public async connect(token?: string): Promise<void> {
        try {
            // Get or request token
            const authToken = token || await this.getOrRequestToken();
            if (!authToken) {
                throw new Error('No authentication token provided');
            }

            // Token is already saved in secure storage by getOrRequestToken

            // Connect with retry
            await pRetry(
                async () => {
                    await this.mcpClient.connect(authToken);
                    this.logger.info('Successfully connected to MCP server');
                },
                {
                    retries: 3,
                    minTimeout: 1000,
                    maxTimeout: 5000,
                    onFailedAttempt: error => {
                        this.logger.warn(`Connection attempt ${error.attemptNumber} failed. ${error.retriesLeft} retries left.`);
                        vscode.window.setStatusBarMessage(
                            `Connecting to CoachNTT... (attempt ${error.attemptNumber})`,
                            2000
                        );
                    }
                }
            );

            // Update state
            if (this.context) {
                await this.context.workspaceState.update('mcp.connected', true);
            }
            await vscode.commands.executeCommand('setContext', 'coachntt.connected', true);

            // Subscribe to default channels
            await this.subscribeToDefaultChannels();

            // Update UI
            this.updateConnectionStatus(true);
            vscode.window.showInformationMessage('Connected to CoachNTT backend');

        } catch (error) {
            this.logger.error('Failed to connect to MCP server', error);
            
            // Update state
            if (this.context) {
                await this.context.workspaceState.update('mcp.connected', false);
            }
            await vscode.commands.executeCommand('setContext', 'coachntt.connected', false);
            
            // Update UI
            this.updateConnectionStatus(false);
            
            // Show error with retry option
            const retry = await vscode.window.showErrorMessage(
                'Failed to connect to CoachNTT backend',
                'Retry',
                'Settings'
            );
            
            if (retry === 'Retry') {
                await this.connect();
            } else if (retry === 'Settings') {
                await vscode.commands.executeCommand('coachntt.openSettings');
            }
        }
    }

    /**
     * Disconnect from MCP server
     */
    public async disconnect(): Promise<void> {
        this.mcpClient.disconnect();
        
        // Update state
        if (this.context) {
            await this.context.workspaceState.update('mcp.connected', false);
        }
        await vscode.commands.executeCommand('setContext', 'coachntt.connected', false);
        
        // Update UI
        this.updateConnectionStatus(false);
        vscode.window.showInformationMessage('Disconnected from CoachNTT backend');
    }

    /**
     * Get connection state
     */
    public getState(): Readonly<MCPConnectionState> {
        return this.mcpClient.getState();
    }

    /**
     * Subscribe to channels
     */
    public async subscribe(channels: MCPChannel[]): Promise<void> {
        await this.mcpClient.subscribe(channels);
    }

    /**
     * Unsubscribe from channels
     */
    public async unsubscribe(channels: MCPChannel[]): Promise<void> {
        await this.mcpClient.unsubscribe(channels);
    }

    /**
     * Get or request authentication token
     */
    private async getOrRequestToken(): Promise<string | undefined> {
        // Check if token is saved in secure storage
        if (this.context && this.context.secrets) {
            const savedToken = await this.context.secrets.get('coachntt.authToken');
            if (savedToken) {
                return savedToken;
            }
        }

        // Check configuration for development token
        const configToken = this.config.getAll().apiUrl;
        if (configToken && this.config.getAll().apiUrl.includes('localhost')) {
            // Use development token for local testing
            return 'dev-token';
        }

        // Prompt user for token
        const token = await vscode.window.showInputBox({
            prompt: 'Enter your CoachNTT authentication token',
            password: true,
            placeHolder: 'Your JWT token',
            ignoreFocusOut: true,
            validateInput: (value) => {
                if (!value || value.trim().length === 0) {
                    return 'Token cannot be empty';
                }
                return null;
            }
        });

        // Save token to secure storage if provided
        if (token && this.context && this.context.secrets) {
            await this.context.secrets.store('coachntt.authToken', token);
        }

        return token;
    }

    /**
     * Subscribe to default channels
     */
    private async subscribeToDefaultChannels(): Promise<void> {
        const state = this.mcpClient.getState();
        if (!state.userId) return;

        const defaultChannels: MCPChannel[] = [
            'memory_updates',
            'graph_updates',
            'system_notifications',
            `user_${state.userId}_personal` as MCPChannel
        ];

        try {
            await this.mcpClient.subscribe(defaultChannels);
            this.logger.info(`Subscribed to default channels: ${defaultChannels.join(', ')}`);
        } catch (error) {
            this.logger.error('Failed to subscribe to default channels', error);
        }
    }

    /**
     * Set up event listeners
     */
    private setupEventListeners(): void {
        const events = this.mcpClient.getEventEmitter();

        // Connection events
        this.unsubscribers.push(
            events.on('connected', (info) => {
                this.logger.info(`Connected as user: ${info.user_id}`);
                this.updateConnectionStatus(true);
            })
        );

        this.unsubscribers.push(
            events.on('disconnected', (reason) => {
                this.logger.info(`Disconnected: ${reason}`);
                this.updateConnectionStatus(false);
            })
        );

        this.unsubscribers.push(
            events.on('error', (error) => {
                this.logger.error('MCP connection error', error);
                vscode.window.showErrorMessage(`Connection error: ${error.message}`);
            })
        );

        // Notification events
        this.unsubscribers.push(
            events.onNotification('all', (notification) => {
                this.handleNotification(notification as MCPUserNotification);
            })
        );

        // Memory update events
        this.unsubscribers.push(
            events.onMemoryUpdate('all', (update) => {
                const action = update.data.action;
                const type = update.data.memory_type;
                vscode.window.setStatusBarMessage(
                    `Memory ${action}: ${type}`,
                    3000
                );
            })
        );

        // Integration update events
        this.unsubscribers.push(
            events.onIntegrationUpdate('all', (update) => {
                const type = update.data.integration_type;
                const status = update.data.status;
                
                if (status === 'completed') {
                    vscode.window.showInformationMessage(
                        `${type.replace('_', ' ')} completed successfully`
                    );
                } else if (status === 'failed') {
                    vscode.window.showErrorMessage(
                        `${type.replace('_', ' ')} failed`
                    );
                }
            })
        );
    }

    /**
     * Handle notifications
     */
    private handleNotification(notification: MCPUserNotification): void {
        const { title, message, level } = notification.data;
        
        switch (level) {
            case 'info':
                vscode.window.showInformationMessage(`${title}: ${message}`);
                break;
            case 'warning':
                vscode.window.showWarningMessage(`${title}: ${message}`);
                break;
            case 'error':
                vscode.window.showErrorMessage(`${title}: ${message}`);
                break;
            case 'success':
                vscode.window.showInformationMessage(`✓ ${title}: ${message}`);
                break;
        }
    }

    /**
     * Update connection status in UI
     */
    private updateConnectionStatus(connected: boolean): void {
        // Update extension state
        const extensionState = ExtensionState.getInstance();
        const state = this.mcpClient.getState();
        
        // Calculate safety score from state or use default
        const safetyScore = connected ? 0.95 : 0.0; // TODO: Get actual score from backend
        
        extensionState.updateStatusBarItems(connected, safetyScore);
        
        // Log connection details (abstracted)
        if (connected && state.connectionId) {
            this.logger.info(`Connection established: ${state.connectionId.substring(0, 8)}...`);
        }
    }

    /**
     * Dispose the connection manager
     */
    public dispose(): void {
        // Clean up event listeners
        this.unsubscribers.forEach(unsubscribe => unsubscribe());
        this.unsubscribers = [];
        
        // Disconnect if connected
        this.disconnect().catch(error => {
            this.logger.error('Error during disposal disconnect', error);
        });
        
        // Dispose MCP client
        this.mcpClient.dispose();
    }
}