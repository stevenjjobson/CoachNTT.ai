# WebView Architecture Documentation

## Overview

The CoachNTT VSCode extension uses WebViews to provide rich, interactive UI components beyond what's possible with standard VSCode APIs. Our WebView implementation follows a safety-first design with complete abstraction of concrete references, strict Content Security Policy (CSP), and type-safe messaging.

## Architecture Components

### 1. WebView Manager (`webview-manager.ts`)

Central service for managing all WebView panels in the extension.

**Key Features:**
- Singleton pattern for centralized management
- Panel lifecycle management (create, show, dispose)
- State persistence across VSCode restarts
- Resource URI handling
- Multiple panel support with unique IDs

**Usage Example:**
```typescript
const webViewManager = WebViewManager.getInstance(context);

const panel = webViewManager.createOrShowPanel(
    'memory-detail-123',
    {
        viewType: 'coachntt.memoryDetail',
        title: 'Memory Details',
        showOptions: vscode.ViewColumn.Two
    },
    (panel) => new MemoryDetailPanel(panel, context, logger, mcpClient, memory)
);
```

### 2. Message Protocol (`message-protocol.ts`)

Type-safe bidirectional communication between extension and WebView.

**Message Types:**
- **Request/Response**: For API-style calls with return values
- **Events**: For notifications and real-time updates
- **Commands**: For one-way actions

**Key Features:**
- Automatic message ID generation
- Request timeout handling
- Message validation
- Content sanitization
- Promise-based request handling

**Usage Example:**
```typescript
// In WebView panel
protocol.onRequest('refresh', async () => {
    await this.loadMemory(this.memory.id);
});

// In WebView JavaScript
await sendRequest('refresh');
```

### 3. Base Template (`base-template.ts`)

Secure HTML template generation with CSP and theme support.

**Features:**
- Content Security Policy with nonces
- VSCode theme integration
- CSS variable generation
- Resource URI handling
- Error and loading page templates

**CSP Implementation:**
```typescript
const csp = [
    `default-src 'none'`,
    `style-src ${vscode.Uri.file('').scheme}:`,
    `script-src 'nonce-${nonce}'`,
    `img-src ${vscode.Uri.file('').scheme}: data:`,
    `connect-src 'self'`
].join('; ');
```

### 4. Memory Detail Panel (`memory-detail-panel.ts`)

First WebView implementation showcasing all architectural patterns.

**Features:**
- Real-time memory updates via WebSocket
- Action buttons (edit, delete, reinforce)
- Theme-aware styling
- State persistence
- Safety-first content display

## Security Design

### Content Security Policy (CSP)

Strict CSP prevents execution of unauthorized scripts:

1. **No inline scripts** without nonces
2. **No external resources** - all assets must be local
3. **No eval()** or dynamic code execution
4. **Restricted protocols** - only vscode-resource scheme

### Content Abstraction

All data displayed in WebViews is automatically abstracted:

```typescript
private abstractContent(content: string): string {
    // Abstract file paths
    content = content.replace(/([A-Za-z]:)?[\/\\][\w\s-]+[\/\\][\w\s-]+\.(ts|js|json|py|md)/g, '<project>/<module>/<file>');
    // Abstract URLs
    content = content.replace(/https?:\/\/[^\s]+/g, '<url>');
    // Abstract IPs
    content = content.replace(/\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g, '<ip_address>');
    // Abstract tokens
    content = content.replace(/[A-Za-z0-9]{32,}/g, '<token>');
    return content;
}
```

### Message Validation

All incoming messages are validated before processing:

```typescript
private validateMessage(message: any): ValidationResult {
    // Validate structure
    // Validate types
    // Validate required fields
    // Return errors if any
}
```

## Theme Support

WebViews automatically adapt to VSCode themes:

1. **Theme Detection**: Current theme kind (light/dark/high-contrast)
2. **CSS Variables**: VSCode colors exposed as CSS variables
3. **Dynamic Updates**: Theme changes trigger WebView updates

```css
:root {
    --vscode-foreground: var(--vscode-editor-foreground);
    --vscode-background: var(--vscode-editor-background);
    --vscode-button-background: var(--vscode-button-background);
    /* ... more variables ... */
}
```

## State Management

### Panel State Persistence

WebView state is preserved across VSCode restarts:

```typescript
interface WebViewPanelState {
    viewType: string;
    title: string;
    viewColumn?: vscode.ViewColumn;
    active: boolean;
    visible: boolean;
    state?: any; // Panel-specific state
}
```

### Message Queue

Messages sent while panel is initializing are queued:

```typescript
private messageQueue: WebViewMessage[] = [];
```

## Performance Optimization

### Resource Loading
- Local resources only (no network requests)
- Resource URIs cached
- CSS/JS bundled with webpack

### Lazy Loading
- Panels created on-demand
- State loaded asynchronously
- Heavy operations debounced

### Memory Management
- Panels disposed when closed
- Event listeners cleaned up
- Message handlers unregistered

## Testing Strategy

### Unit Tests
- WebView manager lifecycle
- Message protocol validation
- Template generation
- Security enforcement

### Integration Tests
- Panel creation/disposal
- Message round-trip
- State persistence
- Theme switching

### Security Tests
- CSP validation
- Content abstraction
- Message sanitization
- Resource isolation

## Usage Guidelines

### Creating a New WebView Panel

1. **Extend ManagedWebViewPanel**:
```typescript
export class MyPanel extends ManagedWebViewPanel {
    protected handleMessage(message: any): void {
        this.protocol.handleMessage(message);
    }
    
    protected getPanelState(): any {
        return { /* panel state */ };
    }
    
    public restoreState(state: any): void {
        // Restore panel state
    }
}
```

2. **Register with WebView Manager**:
```typescript
webViewManager.createOrShowPanel(
    'my-panel-id',
    config,
    (panel) => new MyPanel(panel, context, logger)
);
```

3. **Implement Message Handlers**:
```typescript
this.protocol.onRequest('action', async (params) => {
    // Handle request
    return result;
});
```

### Best Practices

1. **Always abstract content** before display
2. **Use nonces** for all inline scripts/styles
3. **Validate all messages** from WebView
4. **Handle disposal** properly
5. **Test with different themes**
6. **Monitor performance** with large datasets
7. **Implement loading states** for async operations
8. **Provide error feedback** to users

## Extension Points

The WebView architecture is designed for extensibility:

1. **Custom Panels**: Extend `ManagedWebViewPanel`
2. **Message Types**: Add new message types to protocol
3. **Templates**: Create specialized templates
4. **Themes**: Add custom CSS variables
5. **Security**: Enhance content abstraction rules

## Future Enhancements

1. **WebView Serialization**: Restore full panel state after restart
2. **Shared Resources**: Common CSS/JS libraries
3. **WebView Pool**: Reuse panels for performance
4. **Message Compression**: For large data transfers
5. **Offline Support**: Cache WebView content

## Troubleshooting

### Common Issues

1. **CSP Violations**: Check browser console for CSP errors
2. **Theme Issues**: Verify CSS variable usage
3. **Message Failures**: Check message validation
4. **State Loss**: Implement proper state persistence
5. **Performance**: Profile with Chrome DevTools

### Debug Mode

Enable WebView debugging:
1. Open Command Palette
2. Run "Developer: Open WebView Developer Tools"
3. Use Chrome DevTools for debugging

## Summary

The WebView architecture provides a secure, performant, and maintainable foundation for rich UI components in the CoachNTT extension. By following safety-first principles and VSCode best practices, we ensure a seamless user experience while maintaining the highest security standards.