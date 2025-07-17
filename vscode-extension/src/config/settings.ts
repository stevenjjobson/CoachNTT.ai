import * as vscode from 'vscode';
import { Logger } from '../utils/logger';

/**
 * Extension configuration interface
 */
export interface ExtensionConfig {
    apiUrl: string;
    vpsUrl: string;
    websocketUrl: string;
    safetyValidation: boolean;
    minSafetyScore: number;
    autoConnect: boolean;
    logLevel: string;
}

/**
 * Configuration service for managing extension settings
 */
export class ConfigurationService {
    private static instance: ConfigurationService;
    private logger: Logger;
    private config: vscode.WorkspaceConfiguration;
    private onConfigChangeEmitter: vscode.EventEmitter<ExtensionConfig>;
    
    public readonly onConfigChange: vscode.Event<ExtensionConfig>;

    private constructor() {
        this.logger = Logger.getInstance();
        this.config = vscode.workspace.getConfiguration('coachntt');
        this.onConfigChangeEmitter = new vscode.EventEmitter<ExtensionConfig>();
        this.onConfigChange = this.onConfigChangeEmitter.event;
        
        // Listen for configuration changes
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('coachntt')) {
                this.logger.info('Configuration changed, reloading settings');
                this.config = vscode.workspace.getConfiguration('coachntt');
                this.onConfigChangeEmitter.fire(this.getAll());
            }
        });
    }

    /**
     * Get singleton instance
     */
    public static getInstance(): ConfigurationService {
        if (!ConfigurationService.instance) {
            ConfigurationService.instance = new ConfigurationService();
        }
        return ConfigurationService.instance;
    }

    /**
     * Get all configuration values
     */
    public getAll(): ExtensionConfig {
        return {
            apiUrl: this.getApiUrl(),
            vpsUrl: this.getVpsUrl(),
            websocketUrl: this.getWebsocketUrl(),
            safetyValidation: this.getSafetyValidation(),
            minSafetyScore: this.getMinSafetyScore(),
            autoConnect: this.getAutoConnect(),
            logLevel: this.getLogLevel()
        };
    }

    /**
     * Get API URL with fallback and validation
     */
    public getApiUrl(): string {
        const apiUrl = this.config.get<string>('apiUrl', 'http://localhost:8000');
        
        // Use VPS URL if configured and not in development
        if (this.isProduction()) {
            const vpsUrl = this.getVpsUrl();
            if (vpsUrl) {
                this.logger.debug('Using VPS URL for API connection');
                return vpsUrl;
            }
        }
        
        return this.validateUrl(apiUrl, 'http://localhost:8000');
    }

    /**
     * Get VPS URL
     */
    public getVpsUrl(): string {
        return this.config.get<string>('vpsUrl', '');
    }

    /**
     * Get WebSocket URL
     */
    public getWebsocketUrl(): string {
        const wsUrl = this.config.get<string>('websocketUrl', 'ws://localhost:8000/ws');
        
        // Convert API URL to WebSocket URL if using VPS
        if (this.isProduction()) {
            const vpsUrl = this.getVpsUrl();
            if (vpsUrl) {
                const wsProtocol = vpsUrl.startsWith('https') ? 'wss' : 'ws';
                const baseUrl = vpsUrl.replace(/^https?:\/\//, '');
                return `${wsProtocol}://${baseUrl}/ws`;
            }
        }
        
        return this.validateUrl(wsUrl, 'ws://localhost:8000/ws');
    }

    /**
     * Get safety validation setting
     */
    public getSafetyValidation(): boolean {
        return this.config.get<boolean>('safetyValidation', true);
    }

    /**
     * Get minimum safety score
     */
    public getMinSafetyScore(): number {
        const score = this.config.get<number>('minSafetyScore', 0.8);
        // Ensure score is between 0 and 1
        return Math.max(0, Math.min(1, score));
    }

    /**
     * Get auto-connect setting
     */
    public getAutoConnect(): boolean {
        return this.config.get<boolean>('autoConnect', false);
    }

    /**
     * Get log level
     */
    public getLogLevel(): string {
        return this.config.get<string>('logLevel', 'info');
    }

    /**
     * Update a configuration value
     */
    public async update<T>(key: string, value: T, global = true): Promise<void> {
        try {
            await this.config.update(key, value, global);
            this.logger.info(`Configuration updated: ${key}`);
        } catch (error) {
            this.logger.error(`Failed to update configuration: ${key}`, error);
            throw error;
        }
    }

    /**
     * Validate URL format
     */
    private validateUrl(url: string, defaultUrl: string): string {
        try {
            new URL(url);
            return url;
        } catch {
            this.logger.warn(`Invalid URL format: ${url}, using default`);
            return defaultUrl;
        }
    }

    /**
     * Check if running in production mode
     */
    private isProduction(): boolean {
        // Check if we're in production based on various indicators
        return process.env.NODE_ENV === 'production' || 
               vscode.env.machineId !== 'someValue' ||
               !vscode.env.isNewAppInstall;
    }

    /**
     * Get secure connection configuration
     */
    public getConnectionConfig(): { 
        url: string; 
        websocketUrl: string; 
        secure: boolean;
        headers: Record<string, string>;
    } {
        const url = this.getApiUrl();
        const websocketUrl = this.getWebsocketUrl();
        const secure = url.startsWith('https') || websocketUrl.startsWith('wss');
        
        return {
            url,
            websocketUrl,
            secure,
            headers: {
                'X-Client-Type': 'vscode-extension',
                'X-Client-Version': this.getExtensionVersion(),
                'X-Safety-Validation': this.getSafetyValidation() ? 'enabled' : 'disabled'
            }
        };
    }

    /**
     * Get extension version from package.json
     */
    private getExtensionVersion(): string {
        const extension = vscode.extensions.getExtension('coachntt.coachntt');
        return extension?.packageJSON.version || '0.1.0';
    }

    /**
     * Validate all settings
     */
    public validateSettings(): { valid: boolean; errors: string[] } {
        const errors: string[] = [];
        
        // Validate URLs
        try {
            new URL(this.getApiUrl());
        } catch {
            errors.push('Invalid API URL format');
        }
        
        try {
            new URL(this.getWebsocketUrl());
        } catch {
            errors.push('Invalid WebSocket URL format');
        }
        
        // Validate safety score
        const score = this.getMinSafetyScore();
        if (score < 0 || score > 1) {
            errors.push('Safety score must be between 0 and 1');
        }
        
        return {
            valid: errors.length === 0,
            errors
        };
    }

    /**
     * Dispose the service
     */
    public dispose(): void {
        this.onConfigChangeEmitter.dispose();
    }
}