/**
 * Base Template Generator for WebView HTML
 * 
 * Provides secure HTML template generation with:
 * - Content Security Policy (CSP) with nonces
 * - Theme support (light/dark)
 * - Resource URI handling
 * - VSCode API integration
 */

import * as vscode from 'vscode';

/**
 * Template options for HTML generation
 */
export interface TemplateOptions {
    title: string;
    nonce: string;
    styleUris: vscode.Uri[];
    scriptUris: vscode.Uri[];
    inlineStyles?: string;
    bodyContent: string;
    initialState?: any;
}

/**
 * Theme configuration
 */
export interface ThemeConfig {
    kind: vscode.ColorThemeKind;
    cssClass: string;
}

/**
 * Base template generator
 */
export class BaseTemplate {
    /**
     * Get current theme configuration
     */
    public static getThemeConfig(): ThemeConfig {
        const activeTheme = vscode.window.activeColorTheme;
        
        let cssClass = 'vscode-light';
        if (activeTheme.kind === vscode.ColorThemeKind.Dark) {
            cssClass = 'vscode-dark';
        } else if (activeTheme.kind === vscode.ColorThemeKind.HighContrast) {
            cssClass = 'vscode-high-contrast';
        } else if (activeTheme.kind === vscode.ColorThemeKind.HighContrastLight) {
            cssClass = 'vscode-high-contrast-light';
        }
        
        return {
            kind: activeTheme.kind,
            cssClass
        };
    }
    
    /**
     * Generate Content Security Policy
     */
    public static generateCSP(nonce: string): string {
        return [
            `default-src 'none'`,
            `style-src ${vscode.Uri.file('').scheme}:`,
            `style-src-elem 'nonce-${nonce}' ${vscode.Uri.file('').scheme}:`,
            `script-src 'nonce-${nonce}'`,
            `img-src ${vscode.Uri.file('').scheme}: data:`,
            `font-src ${vscode.Uri.file('').scheme}:`,
            `connect-src 'self'`
        ].join('; ');
    }
    
    /**
     * Generate VSCode CSS variables
     */
    public static generateCSSVariables(): string {
        return `
            :root {
                /* Base colors */
                --vscode-foreground: var(--vscode-editor-foreground);
                --vscode-background: var(--vscode-editor-background);
                
                /* Editor colors */
                --vscode-editor-background: var(--vscode-editor-background);
                --vscode-editor-foreground: var(--vscode-editor-foreground);
                
                /* Button colors */
                --vscode-button-background: var(--vscode-button-background);
                --vscode-button-foreground: var(--vscode-button-foreground);
                --vscode-button-hoverBackground: var(--vscode-button-hoverBackground);
                
                /* Input colors */
                --vscode-input-background: var(--vscode-input-background);
                --vscode-input-foreground: var(--vscode-input-foreground);
                --vscode-input-border: var(--vscode-input-border);
                --vscode-inputOption-activeBorder: var(--vscode-inputOption-activeBorder);
                
                /* Badge colors */
                --vscode-badge-background: var(--vscode-badge-background);
                --vscode-badge-foreground: var(--vscode-badge-foreground);
                
                /* List colors */
                --vscode-list-hoverBackground: var(--vscode-list-hoverBackground);
                --vscode-list-activeSelectionBackground: var(--vscode-list-activeSelectionBackground);
                --vscode-list-activeSelectionForeground: var(--vscode-list-activeSelectionForeground);
                
                /* Text colors */
                --vscode-textLink-foreground: var(--vscode-textLink-foreground);
                --vscode-textLink-activeForeground: var(--vscode-textLink-activeForeground);
                
                /* Border colors */
                --vscode-focusBorder: var(--vscode-focusBorder);
                --vscode-contrastBorder: var(--vscode-contrastBorder);
                
                /* Font settings */
                --vscode-font-family: var(--vscode-font-family);
                --vscode-font-size: var(--vscode-font-size);
                --vscode-font-weight: var(--vscode-font-weight);
            }
        `;
    }
    
    /**
     * Generate base styles
     */
    public static generateBaseStyles(): string {
        return `
            * {
                box-sizing: border-box;
            }
            
            html, body {
                height: 100%;
                margin: 0;
                padding: 0;
            }
            
            body {
                font-family: var(--vscode-font-family);
                font-size: var(--vscode-font-size);
                font-weight: var(--vscode-font-weight);
                color: var(--vscode-foreground);
                background-color: var(--vscode-background);
                line-height: 1.6;
            }
            
            a {
                color: var(--vscode-textLink-foreground);
                text-decoration: none;
            }
            
            a:hover {
                color: var(--vscode-textLink-activeForeground);
                text-decoration: underline;
            }
            
            button {
                background-color: var(--vscode-button-background);
                color: var(--vscode-button-foreground);
                border: none;
                padding: 8px 16px;
                cursor: pointer;
                font-family: var(--vscode-font-family);
                font-size: var(--vscode-font-size);
                border-radius: 2px;
            }
            
            button:hover {
                background-color: var(--vscode-button-hoverBackground);
            }
            
            button:focus {
                outline: 1px solid var(--vscode-focusBorder);
                outline-offset: 2px;
            }
            
            input, textarea {
                background-color: var(--vscode-input-background);
                color: var(--vscode-input-foreground);
                border: 1px solid var(--vscode-input-border);
                padding: 8px;
                font-family: var(--vscode-font-family);
                font-size: var(--vscode-font-size);
            }
            
            input:focus, textarea:focus {
                outline: 1px solid var(--vscode-focusBorder);
                border-color: var(--vscode-inputOption-activeBorder);
            }
            
            .container {
                padding: 20px;
                max-width: 1000px;
                margin: 0 auto;
            }
            
            .error {
                color: var(--vscode-errorForeground, #f48771);
                background-color: var(--vscode-errorBackground, rgba(244, 135, 113, 0.1));
                padding: 10px;
                border-radius: 3px;
                margin: 10px 0;
            }
            
            .warning {
                color: var(--vscode-warningForeground, #ffcc00);
                background-color: var(--vscode-warningBackground, rgba(255, 204, 0, 0.1));
                padding: 10px;
                border-radius: 3px;
                margin: 10px 0;
            }
            
            .info {
                color: var(--vscode-infoForeground, #3794ff);
                background-color: var(--vscode-infoBackground, rgba(55, 148, 255, 0.1));
                padding: 10px;
                border-radius: 3px;
                margin: 10px 0;
            }
            
            .badge {
                background-color: var(--vscode-badge-background);
                color: var(--vscode-badge-foreground);
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 0.85em;
                display: inline-block;
            }
            
            /* Loading spinner */
            .spinner {
                border: 2px solid var(--vscode-foreground);
                border-top: 2px solid transparent;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                animation: spin 1s linear infinite;
                display: inline-block;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
    }
    
    /**
     * Generate WebView API script
     */
    public static generateWebViewAPI(nonce: string): string {
        return `
            <script nonce="${nonce}">
                (function() {
                    const vscode = acquireVsCodeApi();
                    
                    // Global state management
                    const state = vscode.getState() || {};
                    
                    // Message handling
                    window.addEventListener('message', event => {
                        const message = event.data;
                        if (window.handleMessage) {
                            window.handleMessage(message);
                        }
                    });
                    
                    // Expose API to window
                    window.vscode = vscode;
                    window.vsState = state;
                    window.updateState = function(newState) {
                        Object.assign(state, newState);
                        vscode.setState(state);
                    };
                    
                    // Helper functions
                    window.postMessage = function(message) {
                        vscode.postMessage(message);
                    };
                    
                    // Safety helper for content
                    window.abstractContent = function(content) {
                        if (typeof content !== 'string') return content;
                        
                        // Abstract file paths
                        content = content.replace(/([A-Za-z]:)?[\\/\\\\][\\w\\s-]+[\\/\\\\][\\w\\s-]+\\.(ts|js|json|py|md)/g, '<project>/<module>/<file>');
                        content = content.replace(/([A-Za-z]:)?[\\/\\\\][\\w\\s-]+[\\/\\\\]/g, '<directory>/');
                        
                        // Abstract URLs
                        content = content.replace(/https?:\\/\\/[^\\s]+/g, '<url>');
                        
                        // Abstract IPs
                        content = content.replace(/\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b/g, '<ip_address>');
                        
                        // Abstract tokens
                        content = content.replace(/[A-Za-z0-9]{32,}/g, '<token>');
                        
                        return content;
                    };
                })();
            </script>
        `;
    }
    
    /**
     * Generate full HTML template
     */
    public static generateHTML(options: TemplateOptions): string {
        const theme = this.getThemeConfig();
        const csp = this.generateCSP(options.nonce);
        
        // Generate style tags
        const styleTags = options.styleUris
            .map(uri => `<link rel="stylesheet" href="${uri}">`)
            .join('\n');
        
        // Generate script tags
        const scriptTags = options.scriptUris
            .map(uri => `<script nonce="${options.nonce}" src="${uri}"></script>`)
            .join('\n');
        
        return `<!DOCTYPE html>
<html lang="en" class="${theme.cssClass}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="${csp}">
    <title>${options.title}</title>
    
    ${styleTags}
    
    <style nonce="${options.nonce}">
        ${this.generateCSSVariables()}
        ${this.generateBaseStyles()}
        ${options.inlineStyles || ''}
    </style>
</head>
<body>
    ${options.bodyContent}
    
    ${this.generateWebViewAPI(options.nonce)}
    
    ${options.initialState ? `
    <script nonce="${options.nonce}">
        window.initialState = ${JSON.stringify(options.initialState)};
    </script>
    ` : ''}
    
    ${scriptTags}
</body>
</html>`;
    }
    
    /**
     * Generate a simple error page
     */
    public static generateErrorPage(nonce: string, error: string): string {
        return this.generateHTML({
            title: 'Error',
            nonce,
            styleUris: [],
            scriptUris: [],
            bodyContent: `
                <div class="container">
                    <h1>Error</h1>
                    <div class="error">
                        <p>${this.escapeHtml(error)}</p>
                    </div>
                </div>
            `
        });
    }
    
    /**
     * Generate a loading page
     */
    public static generateLoadingPage(nonce: string, message: string = 'Loading...'): string {
        return this.generateHTML({
            title: 'Loading',
            nonce,
            styleUris: [],
            scriptUris: [],
            inlineStyles: `
                .loading-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    gap: 20px;
                }
            `,
            bodyContent: `
                <div class="loading-container">
                    <div class="spinner"></div>
                    <p>${this.escapeHtml(message)}</p>
                </div>
            `
        });
    }
    
    /**
     * Escape HTML for safe display
     */
    public static escapeHtml(text: string): string {
        const map: Record<string, string> = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        
        return text.replace(/[&<>"']/g, char => map[char]);
    }
}