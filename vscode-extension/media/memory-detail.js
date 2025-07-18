/**
 * Memory Detail Panel JavaScript
 * 
 * Client-side logic for the memory detail WebView
 */

(function() {
    'use strict';
    
    // Get VSCode API
    const vscode = window.vscode;
    
    // Get initial state
    const state = window.initialState || {};
    
    // Message ID counter
    let messageIdCounter = 0;
    
    /**
     * Generate unique message ID
     */
    function generateMessageId() {
        return `client_${Date.now()}_${++messageIdCounter}`;
    }
    
    /**
     * Send request to extension
     */
    function sendRequest(method, params) {
        return new Promise((resolve, reject) => {
            const id = generateMessageId();
            const message = {
                id,
                type: 'request',
                method,
                params,
                timestamp: Date.now()
            };
            
            // Set up one-time listener for response
            const responseHandler = (event) => {
                const response = event.data;
                if (response.type === 'response' && response.requestId === id) {
                    window.removeEventListener('message', responseHandler);
                    
                    if (response.success) {
                        resolve(response.result);
                    } else {
                        reject(new Error(response.error?.message || 'Request failed'));
                    }
                }
            };
            
            window.addEventListener('message', responseHandler);
            vscode.postMessage(message);
            
            // Timeout after 30 seconds
            setTimeout(() => {
                window.removeEventListener('message', responseHandler);
                reject(new Error('Request timeout'));
            }, 30000);
        });
    }
    
    /**
     * Handle action buttons
     */
    window.handleAction = async function(action) {
        try {
            // Show loading state
            showLoading(action);
            
            // Send request
            await sendRequest(action);
            
            // Hide loading state
            hideLoading();
            
        } catch (error) {
            hideLoading();
            showError(`Failed to ${action}: ${error.message}`);
        }
    };
    
    /**
     * Show loading state
     */
    function showLoading(action) {
        // Find the button that triggered the action
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            if (button.onclick && button.onclick.toString().includes(action)) {
                button.disabled = true;
                const icon = button.querySelector('.codicon');
                if (icon) {
                    icon.classList.add('codicon-loading', 'codicon-modifier-spin');
                }
            }
        });
    }
    
    /**
     * Hide loading state
     */
    function hideLoading() {
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            button.disabled = false;
            const icon = button.querySelector('.codicon');
            if (icon) {
                icon.classList.remove('codicon-loading', 'codicon-modifier-spin');
            }
        });
    }
    
    /**
     * Show error message
     */
    function showError(message) {
        // Create error alert
        const alert = document.createElement('div');
        alert.className = 'alert alert-error slide-in';
        alert.innerHTML = `
            <span class="codicon codicon-error"></span>
            <span>${window.abstractContent(message)}</span>
        `;
        
        // Insert at top of container
        const container = document.querySelector('.container');
        container.insertBefore(alert, container.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            alert.classList.add('fade-out');
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    }
    
    /**
     * Show success message
     */
    function showSuccess(message) {
        // Create success alert
        const alert = document.createElement('div');
        alert.className = 'alert alert-success slide-in';
        alert.innerHTML = `
            <span class="codicon codicon-check"></span>
            <span>${message}</span>
        `;
        
        // Insert at top of container
        const container = document.querySelector('.container');
        container.insertBefore(alert, container.firstChild);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            alert.classList.add('fade-out');
            setTimeout(() => alert.remove(), 300);
        }, 3000);
    }
    
    /**
     * Update memory display
     */
    function updateMemoryDisplay(memory) {
        // Update title
        const title = document.querySelector('h1');
        if (title) {
            title.textContent = formatIntent(memory.intent) + ' Memory';
        }
        
        // Update metadata
        updateMetadataField('timestamp', new Date(memory.timestamp).toLocaleString());
        updateMetadataField('importance', memory.importance);
        updateMetadataField('reinforcement', memory.reinforcement_count);
        
        // Update content
        const contentDiv = document.querySelector('.memory-content');
        if (contentDiv) {
            contentDiv.textContent = memory.content;
        }
        
        // Update tags
        updateTags(memory.tags);
    }
    
    /**
     * Update metadata field
     */
    function updateMetadataField(field, value) {
        const element = document.querySelector(`[data-field="${field}"]`);
        if (element) {
            if (field === 'importance') {
                // Update progress bar
                const percent = Math.round(value * 100);
                const fill = element.querySelector('.importance-fill');
                const text = element.querySelector('span');
                if (fill) fill.style.width = percent + '%';
                if (text) text.textContent = percent + '%';
            } else {
                element.textContent = value || '';
            }
        }
    }
    
    /**
     * Update tags display
     */
    function updateTags(tags) {
        const tagsContainer = document.querySelector('.memory-tags');
        if (tagsContainer && tags) {
            tagsContainer.innerHTML = tags
                .map(tag => `<span class="tag">${escapeHtml(tag)}</span>`)
                .join('');
        }
    }
    
    /**
     * Format intent for display
     */
    function formatIntent(intent) {
        return intent.split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
    }
    
    /**
     * Escape HTML
     */
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, char => map[char]);
    }
    
    /**
     * Handle incoming messages
     */
    window.handleMessage = function(message) {
        switch (message.type) {
            case 'event':
                handleEvent(message);
                break;
            case 'command':
                handleCommand(message);
                break;
        }
    };
    
    /**
     * Handle events
     */
    function handleEvent(message) {
        switch (message.event) {
            case 'loading':
                if (message.data) {
                    showLoadingOverlay();
                } else {
                    hideLoadingOverlay();
                }
                break;
                
            case 'error':
                showError(message.data);
                break;
                
            case 'memoryUpdated':
                updateMemoryDisplay(message.data);
                showSuccess('Memory updated');
                break;
        }
    }
    
    /**
     * Handle commands
     */
    function handleCommand(message) {
        switch (message.command) {
            case 'refresh':
                location.reload();
                break;
        }
    }
    
    /**
     * Show loading overlay
     */
    function showLoadingOverlay() {
        let overlay = document.querySelector('.loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-container">
                    <div class="spinner"></div>
                    <p>Loading...</p>
                </div>
            `;
            document.body.appendChild(overlay);
        }
        overlay.classList.add('visible');
    }
    
    /**
     * Hide loading overlay
     */
    function hideLoadingOverlay() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.classList.remove('visible');
        }
    }
    
    /**
     * Initialize
     */
    function initialize() {
        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'r':
                        e.preventDefault();
                        handleAction('refresh');
                        break;
                    case 'e':
                        e.preventDefault();
                        handleAction('edit');
                        break;
                    case 'c':
                        e.preventDefault();
                        handleAction('copyContent');
                        break;
                }
            }
        });
        
        // Add copy feedback
        const originalHandleAction = window.handleAction;
        window.handleAction = async function(action) {
            await originalHandleAction(action);
            
            if (action === 'copyContent') {
                showSuccess('Content copied to clipboard');
            }
        };
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
    
})();