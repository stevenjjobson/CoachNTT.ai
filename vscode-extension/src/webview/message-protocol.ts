/**
 * Message Protocol for WebView Communication
 * 
 * Provides type-safe bidirectional messaging between extension and WebView
 * with request/response patterns, event handling, and message validation.
 */

import { EventEmitter } from 'events';

/**
 * Base message structure
 */
export interface WebViewMessage {
    id: string;
    type: string;
    timestamp: number;
}

/**
 * Request message from extension to WebView or vice versa
 */
export interface WebViewRequest extends WebViewMessage {
    type: 'request';
    method: string;
    params?: any;
}

/**
 * Response message
 */
export interface WebViewResponse extends WebViewMessage {
    type: 'response';
    requestId: string;
    success: boolean;
    result?: any;
    error?: {
        code: number;
        message: string;
        details?: any;
    };
}

/**
 * Event message for notifications
 */
export interface WebViewEvent extends WebViewMessage {
    type: 'event';
    event: string;
    data?: any;
}

/**
 * Command message for actions
 */
export interface WebViewCommand extends WebViewMessage {
    type: 'command';
    command: string;
    args?: any;
}

/**
 * All message types union
 */
export type WebViewMessageType = WebViewRequest | WebViewResponse | WebViewEvent | WebViewCommand;

/**
 * Message handler function type
 */
export type MessageHandler<T = any> = (message: T) => void | Promise<void>;

/**
 * Request handler function type
 */
export type RequestHandler<TParams = any, TResult = any> = (params: TParams) => TResult | Promise<TResult>;

/**
 * Message validation result
 */
export interface ValidationResult {
    valid: boolean;
    errors?: string[];
}

/**
 * Message Protocol class for handling WebView communication
 */
export class MessageProtocol extends EventEmitter {
    private messageCounter: number = 0;
    private pendingRequests: Map<string, {
        resolve: (result: any) => void;
        reject: (error: any) => void;
        timeout: NodeJS.Timeout;
    }> = new Map();
    
    private requestHandlers: Map<string, RequestHandler> = new Map();
    private commandHandlers: Map<string, MessageHandler<WebViewCommand>> = new Map();
    private requestTimeout: number = 30000; // 30 seconds default
    
    constructor(
        private postMessage: (message: any) => Thenable<boolean>,
        private abstractContent: (content: string) => string
    ) {
        super();
    }
    
    /**
     * Generate unique message ID
     */
    private generateId(): string {
        return `msg_${Date.now()}_${++this.messageCounter}`;
    }
    
    /**
     * Validate message structure
     */
    private validateMessage(message: any): ValidationResult {
        const errors: string[] = [];
        
        if (!message || typeof message !== 'object') {
            errors.push('Message must be an object');
            return { valid: false, errors };
        }
        
        if (!message.id || typeof message.id !== 'string') {
            errors.push('Message must have a string id');
        }
        
        if (!message.type || typeof message.type !== 'string') {
            errors.push('Message must have a string type');
        }
        
        if (!message.timestamp || typeof message.timestamp !== 'number') {
            errors.push('Message must have a number timestamp');
        }
        
        // Type-specific validation
        switch (message.type) {
            case 'request':
                if (!message.method || typeof message.method !== 'string') {
                    errors.push('Request must have a string method');
                }
                break;
                
            case 'response':
                if (!message.requestId || typeof message.requestId !== 'string') {
                    errors.push('Response must have a string requestId');
                }
                if (typeof message.success !== 'boolean') {
                    errors.push('Response must have a boolean success');
                }
                break;
                
            case 'event':
                if (!message.event || typeof message.event !== 'string') {
                    errors.push('Event must have a string event name');
                }
                break;
                
            case 'command':
                if (!message.command || typeof message.command !== 'string') {
                    errors.push('Command must have a string command name');
                }
                break;
                
            default:
                errors.push(`Unknown message type: ${message.type}`);
        }
        
        return {
            valid: errors.length === 0,
            errors: errors.length > 0 ? errors : undefined
        };
    }
    
    /**
     * Send a request and wait for response
     */
    public async sendRequest<TParams = any, TResult = any>(
        method: string,
        params?: TParams
    ): Promise<TResult> {
        const request: WebViewRequest = {
            id: this.generateId(),
            type: 'request',
            method,
            params: params ? this.sanitizeData(params) : undefined,
            timestamp: Date.now()
        };
        
        return new Promise((resolve, reject) => {
            // Set up timeout
            const timeout = setTimeout(() => {
                this.pendingRequests.delete(request.id);
                reject(new Error(`Request timeout: ${method}`));
            }, this.requestTimeout);
            
            // Store pending request
            this.pendingRequests.set(request.id, { resolve, reject, timeout });
            
            // Send the request
            this.postMessage(request).then(sent => {
                if (!sent) {
                    clearTimeout(timeout);
                    this.pendingRequests.delete(request.id);
                    reject(new Error(`Failed to send request: ${method}`));
                }
            });
        });
    }
    
    /**
     * Send an event notification
     */
    public sendEvent(event: string, data?: any): void {
        const message: WebViewEvent = {
            id: this.generateId(),
            type: 'event',
            event,
            data: data ? this.sanitizeData(data) : undefined,
            timestamp: Date.now()
        };
        
        this.postMessage(message);
    }
    
    /**
     * Send a command
     */
    public sendCommand(command: string, args?: any): void {
        const message: WebViewCommand = {
            id: this.generateId(),
            type: 'command',
            command,
            args: args ? this.sanitizeData(args) : undefined,
            timestamp: Date.now()
        };
        
        this.postMessage(message);
    }
    
    /**
     * Register a request handler
     */
    public onRequest<TParams = any, TResult = any>(
        method: string,
        handler: RequestHandler<TParams, TResult>
    ): void {
        this.requestHandlers.set(method, handler);
    }
    
    /**
     * Register a command handler
     */
    public onCommand(command: string, handler: MessageHandler<WebViewCommand>): void {
        this.commandHandlers.set(command, handler);
    }
    
    /**
     * Handle incoming message
     */
    public async handleMessage(message: any): Promise<void> {
        // Validate message
        const validation = this.validateMessage(message);
        if (!validation.valid) {
            console.error('Invalid message received:', validation.errors);
            return;
        }
        
        const typedMessage = message as WebViewMessageType;
        
        switch (typedMessage.type) {
            case 'request':
                await this.handleRequest(typedMessage as WebViewRequest);
                break;
                
            case 'response':
                this.handleResponse(typedMessage as WebViewResponse);
                break;
                
            case 'event':
                this.handleEvent(typedMessage as WebViewEvent);
                break;
                
            case 'command':
                await this.handleCommand(typedMessage as WebViewCommand);
                break;
        }
    }
    
    /**
     * Handle incoming request
     */
    private async handleRequest(request: WebViewRequest): Promise<void> {
        const handler = this.requestHandlers.get(request.method);
        
        if (!handler) {
            const response: WebViewResponse = {
                id: this.generateId(),
                type: 'response',
                requestId: request.id,
                success: false,
                error: {
                    code: -32601,
                    message: `Method not found: ${request.method}`
                },
                timestamp: Date.now()
            };
            
            await this.postMessage(response);
            return;
        }
        
        try {
            const result = await handler(request.params);
            
            const response: WebViewResponse = {
                id: this.generateId(),
                type: 'response',
                requestId: request.id,
                success: true,
                result: result ? this.sanitizeData(result) : undefined,
                timestamp: Date.now()
            };
            
            await this.postMessage(response);
            
        } catch (error) {
            const response: WebViewResponse = {
                id: this.generateId(),
                type: 'response',
                requestId: request.id,
                success: false,
                error: {
                    code: -32603,
                    message: this.abstractContent(error instanceof Error ? error.message : String(error))
                },
                timestamp: Date.now()
            };
            
            await this.postMessage(response);
        }
    }
    
    /**
     * Handle incoming response
     */
    private handleResponse(response: WebViewResponse): void {
        const pending = this.pendingRequests.get(response.requestId);
        
        if (pending) {
            clearTimeout(pending.timeout);
            this.pendingRequests.delete(response.requestId);
            
            if (response.success) {
                pending.resolve(response.result);
            } else {
                pending.reject(response.error || new Error('Unknown error'));
            }
        }
    }
    
    /**
     * Handle incoming event
     */
    private handleEvent(event: WebViewEvent): void {
        this.emit(event.event, event.data);
    }
    
    /**
     * Handle incoming command
     */
    private async handleCommand(command: WebViewCommand): Promise<void> {
        const handler = this.commandHandlers.get(command.command);
        
        if (handler) {
            try {
                await handler(command);
            } catch (error) {
                console.error(`Error handling command ${command.command}:`, error);
            }
        }
    }
    
    /**
     * Sanitize data for safety
     */
    private sanitizeData(data: any): any {
        if (typeof data === 'string') {
            return this.abstractContent(data);
        }
        
        if (Array.isArray(data)) {
            return data.map(item => this.sanitizeData(item));
        }
        
        if (data && typeof data === 'object') {
            const sanitized: any = {};
            for (const [key, value] of Object.entries(data)) {
                sanitized[key] = this.sanitizeData(value);
            }
            return sanitized;
        }
        
        return data;
    }
    
    /**
     * Set request timeout
     */
    public setRequestTimeout(timeout: number): void {
        this.requestTimeout = timeout;
    }
    
    /**
     * Clear all pending requests
     */
    public clearPendingRequests(): void {
        this.pendingRequests.forEach(pending => {
            clearTimeout(pending.timeout);
            pending.reject(new Error('Protocol disposed'));
        });
        this.pendingRequests.clear();
    }
    
    /**
     * Dispose the protocol
     */
    public dispose(): void {
        this.clearPendingRequests();
        this.requestHandlers.clear();
        this.commandHandlers.clear();
        this.removeAllListeners();
    }
}