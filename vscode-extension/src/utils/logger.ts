import * as vscode from 'vscode';

/**
 * Log levels for the extension
 */
export enum LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARN = 2,
    ERROR = 3
}

/**
 * Logger class with safety-first abstraction
 * All paths and sensitive information are automatically abstracted
 */
export class Logger {
    private static instance: Logger;
    private outputChannel: vscode.OutputChannel;
    private logLevel: LogLevel;

    private constructor() {
        this.outputChannel = vscode.window.createOutputChannel('CoachNTT');
        this.logLevel = this.getConfiguredLogLevel();
        
        // Listen for configuration changes
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('coachntt.logLevel')) {
                this.logLevel = this.getConfiguredLogLevel();
            }
        });
    }

    /**
     * Get singleton instance
     */
    public static getInstance(): Logger {
        if (!Logger.instance) {
            Logger.instance = new Logger();
        }
        return Logger.instance;
    }

    /**
     * Get configured log level from settings
     */
    private getConfiguredLogLevel(): LogLevel {
        const config = vscode.workspace.getConfiguration('coachntt');
        const level = config.get<string>('logLevel', 'info');
        
        switch (level) {
            case 'debug': return LogLevel.DEBUG;
            case 'info': return LogLevel.INFO;
            case 'warn': return LogLevel.WARN;
            case 'error': return LogLevel.ERROR;
            default: return LogLevel.INFO;
        }
    }

    /**
     * Abstract sensitive information from messages
     */
    private abstractMessage(message: string): string {
        // Abstract file paths
        message = message.replace(/([A-Za-z]:)?[\/\\][\w\s-]+[\/\\][\w\s-]+\.(ts|js|json|py|md)/g, '<project>/<module>/<file>');
        message = message.replace(/([A-Za-z]:)?[\/\\][\w\s-]+[\/\\]/g, '<directory>/');
        
        // Abstract URLs
        message = message.replace(/https?:\/\/[^\s]+/g, '<url>');
        message = message.replace(/ws:\/\/[^\s]+/g, '<websocket_url>');
        
        // Abstract IPs
        message = message.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '<ip_address>');
        
        // Abstract API keys and tokens
        message = message.replace(/[A-Za-z0-9]{32,}/g, '<token>');
        
        // Abstract UUIDs
        message = message.replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, '<uuid>');
        
        return message;
    }

    /**
     * Format log message with timestamp
     */
    private formatMessage(level: string, message: string): string {
        const timestamp = new Date().toISOString();
        const abstracted = this.abstractMessage(message);
        return `[${timestamp}] [${level}] ${abstracted}`;
    }

    /**
     * Log debug message
     */
    public debug(message: string, ...args: any[]): void {
        if (this.logLevel <= LogLevel.DEBUG) {
            const formatted = this.formatMessage('DEBUG', message);
            this.outputChannel.appendLine(formatted);
            if (args.length > 0) {
                this.outputChannel.appendLine(`  Details: ${JSON.stringify(args, null, 2)}`);
            }
        }
    }

    /**
     * Log info message
     */
    public info(message: string, ...args: any[]): void {
        if (this.logLevel <= LogLevel.INFO) {
            const formatted = this.formatMessage('INFO', message);
            this.outputChannel.appendLine(formatted);
            if (args.length > 0 && this.logLevel <= LogLevel.DEBUG) {
                this.outputChannel.appendLine(`  Details: ${JSON.stringify(args, null, 2)}`);
            }
        }
    }

    /**
     * Log warning message
     */
    public warn(message: string, ...args: any[]): void {
        if (this.logLevel <= LogLevel.WARN) {
            const formatted = this.formatMessage('WARN', message);
            this.outputChannel.appendLine(formatted);
            if (args.length > 0) {
                this.outputChannel.appendLine(`  Details: ${JSON.stringify(args, null, 2)}`);
            }
        }
    }

    /**
     * Log error message
     */
    public error(message: string, error?: Error | unknown): void {
        if (this.logLevel <= LogLevel.ERROR) {
            const formatted = this.formatMessage('ERROR', message);
            this.outputChannel.appendLine(formatted);
            
            if (error) {
                if (error instanceof Error) {
                    const stack = this.abstractMessage(error.stack || error.message);
                    this.outputChannel.appendLine(`  Error: ${error.message}`);
                    this.outputChannel.appendLine(`  Stack: ${stack}`);
                } else {
                    this.outputChannel.appendLine(`  Error: ${JSON.stringify(error, null, 2)}`);
                }
            }
        }
    }

    /**
     * Show the output channel
     */
    public show(): void {
        this.outputChannel.show();
    }

    /**
     * Clear the output channel
     */
    public clear(): void {
        this.outputChannel.clear();
    }

    /**
     * Dispose the logger
     */
    public dispose(): void {
        this.outputChannel.dispose();
    }
}