/**
 * Audio Player Client-Side Logic
 * 
 * Handles WebView interactions for audio playback including:
 * - Audio element control
 * - UI state management
 * - Message protocol communication
 * - Queue visualization
 */

(function() {
    'use strict';
    
    // Get VSCode API
    const vscode = window.vscode;
    
    // State management
    let state = {
        queue: [],
        currentItem: null,
        playbackState: 'stopped',
        volume: 100,
        speed: 1.0,
        currentTime: 0,
        duration: 0
    };
    
    // Audio element
    const audioElement = document.getElementById('audio-element');
    let audioContext = null;
    let gainNode = null;
    
    // UI Elements
    const elements = {
        currentTitle: document.getElementById('current-title'),
        currentMeta: document.getElementById('current-meta'),
        playPauseBtn: document.getElementById('play-pause-btn'),
        progressFill: document.getElementById('progress-fill'),
        currentTimeSpan: document.getElementById('current-time'),
        totalTimeSpan: document.getElementById('total-time'),
        volumeSlider: document.getElementById('volume-slider'),
        volumeValue: document.getElementById('volume-value'),
        speedSlider: document.getElementById('speed-slider'),
        speedValue: document.getElementById('speed-value'),
        queueList: document.getElementById('queue-list'),
        queueCount: document.getElementById('queue-count')
    };
    
    // Initialize audio context for advanced control
    function initAudioContext() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            gainNode = audioContext.createGain();
            
            const source = audioContext.createMediaElementSource(audioElement);
            source.connect(gainNode);
            gainNode.connect(audioContext.destination);
        }
    }
    
    // Handle incoming messages
    window.handleMessage = function(message) {
        switch (message.type) {
            case 'event':
                handleEvent(message.event, message.data);
                break;
            case 'command':
                handleCommand(message.command, message.args);
                break;
            case 'response':
                // Handle responses if needed
                break;
        }
    };
    
    // Handle events from extension
    function handleEvent(event, data) {
        switch (event) {
            case 'initialState':
                updateState(data);
                renderQueue();
                updatePlayerUI();
                break;
                
            case 'stateChanged':
                state.playbackState = data.state;
                updatePlayPauseButton();
                break;
                
            case 'itemChanged':
                state.currentItem = data.item;
                updateCurrentTrack();
                renderQueue();
                break;
                
            case 'queueChanged':
                state.queue = data.items;
                renderQueue();
                break;
                
            case 'progressChanged':
                updateProgress(data.progress, data.duration);
                break;
                
            case 'volumeChanged':
                state.volume = data.volume;
                updateVolumeUI();
                break;
                
            case 'speedChanged':
                state.speed = data.speed;
                updateSpeedUI();
                break;
        }
    }
    
    // Handle commands from extension
    function handleCommand(command, args) {
        switch (command) {
            case 'play':
                playAudio(args);
                break;
            case 'pause':
                pauseAudio();
                break;
            case 'stop':
                stopAudio();
                break;
            case 'seek':
                seekAudio(args.position);
                break;
            case 'setVolume':
                setVolume(args.volume);
                break;
            case 'setSpeed':
                setSpeed(args.speed);
                break;
        }
    }
    
    // Play audio
    function playAudio(args) {
        if (args && args.url) {
            // Load new audio
            audioElement.src = args.url;
            audioElement.volume = args.volume / 100;
            audioElement.playbackRate = args.speed;
            
            // Initialize audio context on first play
            initAudioContext();
        }
        
        // Resume audio context if suspended
        if (audioContext && audioContext.state === 'suspended') {
            audioContext.resume();
        }
        
        audioElement.play().catch(error => {
            console.error('Audio playback failed:', error);
            sendRequest('audioError', {
                itemId: state.currentItem?.id,
                error: error.message
            });
        });
    }
    
    // Pause audio
    function pauseAudio() {
        audioElement.pause();
    }
    
    // Stop audio
    function stopAudio() {
        audioElement.pause();
        audioElement.currentTime = 0;
        state.currentTime = 0;
        updateProgressUI();
    }
    
    // Seek audio
    function seekAudio(position) {
        if (audioElement.duration) {
            audioElement.currentTime = position * audioElement.duration;
        }
    }
    
    // Set volume
    function setVolume(volume) {
        state.volume = volume;
        audioElement.volume = volume / 100;
        updateVolumeUI();
    }
    
    // Set playback speed
    function setSpeed(speed) {
        state.speed = speed;
        audioElement.playbackRate = speed;
        updateSpeedUI();
    }
    
    // Update state
    function updateState(newState) {
        Object.assign(state, newState);
    }
    
    // Update current track display
    function updateCurrentTrack() {
        if (state.currentItem) {
            elements.currentTitle.textContent = state.currentItem.metadata.title;
            elements.currentMeta.textContent = formatMetadata(state.currentItem.metadata);
        } else {
            elements.currentTitle.textContent = 'No track selected';
            elements.currentMeta.textContent = '';
        }
    }
    
    // Update play/pause button
    function updatePlayPauseButton() {
        const icon = elements.playPauseBtn.querySelector('.codicon');
        if (state.playbackState === 'playing') {
            icon.className = 'codicon codicon-debug-pause';
            elements.playPauseBtn.title = 'Pause';
        } else {
            icon.className = 'codicon codicon-play';
            elements.playPauseBtn.title = 'Play';
        }
    }
    
    // Update progress
    function updateProgress(progress, duration) {
        state.currentTime = progress * duration;
        state.duration = duration;
        updateProgressUI();
    }
    
    // Update progress UI
    function updateProgressUI() {
        const progress = state.duration > 0 ? (state.currentTime / state.duration) * 100 : 0;
        elements.progressFill.style.width = `${progress}%`;
        elements.currentTimeSpan.textContent = formatTime(state.currentTime);
        elements.totalTimeSpan.textContent = formatTime(state.duration);
    }
    
    // Update volume UI
    function updateVolumeUI() {
        elements.volumeSlider.value = state.volume;
        elements.volumeValue.textContent = `${state.volume}%`;
    }
    
    // Update speed UI
    function updateSpeedUI() {
        elements.speedSlider.value = state.speed * 100;
        elements.speedValue.textContent = `${state.speed.toFixed(1)}x`;
    }
    
    // Update player UI
    function updatePlayerUI() {
        updateCurrentTrack();
        updatePlayPauseButton();
        updateProgressUI();
        updateVolumeUI();
        updateSpeedUI();
    }
    
    // Render queue
    function renderQueue() {
        elements.queueCount.textContent = state.queue.length;
        
        if (state.queue.length === 0) {
            elements.queueList.innerHTML = `
                <li class="empty-queue">
                    <span class="codicon codicon-music"></span>
                    <p>No items in queue</p>
                    <p>Add audio from memories or AI responses</p>
                </li>
            `;
            return;
        }
        
        elements.queueList.innerHTML = state.queue.map(item => {
            const isCurrent = state.currentItem && item.id === state.currentItem.id;
            const statusIcon = getStatusIcon(item.status);
            const statusClass = `status-${item.status}`;
            
            return `
                <li class="queue-item ${isCurrent ? 'current' : ''} ${item.status === 'playing' ? 'playing' : ''}" 
                    data-id="${item.id}">
                    <div class="queue-item-status ${statusClass}">
                        <span class="codicon codicon-${statusIcon}"></span>
                    </div>
                    <div class="queue-item-content">
                        <div class="queue-item-title">${escapeHtml(item.metadata.title)}</div>
                        <div class="queue-item-meta">
                            <span class="queue-item-type">${formatSourceType(item.metadata.sourceType)}</span>
                            ${item.metadata.duration ? `<span class="queue-item-duration">${formatTime(item.metadata.duration)}</span>` : ''}
                            ${getPriorityBadge(item.priority)}
                        </div>
                    </div>
                    <div class="queue-item-actions">
                        ${!isCurrent ? `<button onclick="playItem('${item.id}')" title="Play">
                            <span class="codicon codicon-play"></span>
                        </button>` : ''}
                        <button onclick="removeItem('${item.id}')" title="Remove">
                            <span class="codicon codicon-trash"></span>
                        </button>
                    </div>
                </li>
            `;
        }).join('');
    }
    
    // Get status icon
    function getStatusIcon(status) {
        const icons = {
            pending: 'circle-outline',
            downloading: 'sync~spin',
            ready: 'check',
            playing: 'play-circle',
            paused: 'debug-pause',
            completed: 'pass-filled',
            error: 'error'
        };
        return icons[status] || 'circle-outline';
    }
    
    // Get priority badge
    function getPriorityBadge(priority) {
        if (priority === 0) return ''; // Normal priority
        
        const labels = ['', '', 'High', 'Urgent'];
        const classes = ['', '', 'priority-high', 'priority-urgent'];
        
        return `<span class="priority-badge ${classes[priority]}">${labels[priority]}</span>`;
    }
    
    // Format source type
    function formatSourceType(type) {
        const types = {
            synthesis: 'AI',
            memory: 'Memory',
            notification: 'Notification',
            response: 'Response'
        };
        return types[type] || type;
    }
    
    // Format metadata
    function formatMetadata(metadata) {
        const parts = [];
        if (metadata.sourceType) {
            parts.push(formatSourceType(metadata.sourceType));
        }
        if (metadata.language && metadata.language !== 'en') {
            parts.push(metadata.language.toUpperCase());
        }
        if (metadata.voice && metadata.voice !== 'default') {
            parts.push(metadata.voice);
        }
        return parts.join(' • ');
    }
    
    // Format time
    function formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return '0:00';
        
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
    
    // Escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Send request to extension
    async function sendRequest(method, params) {
        return window.sendRequest(method, params);
    }
    
    // Action handlers
    window.handleAction = async function(action) {
        switch (action) {
            case 'togglePlayback':
                if (state.playbackState === 'playing') {
                    await sendRequest('pause');
                } else {
                    await sendRequest('play');
                }
                break;
                
            case 'previous':
                await sendRequest('previous');
                break;
                
            case 'next':
                await sendRequest('next');
                break;
                
            case 'stop':
                await sendRequest('stop');
                break;
                
            case 'clearCompleted':
                const result = await sendRequest('clearCompleted');
                if (result && result.count > 0) {
                    vscode.postMessage({
                        type: 'info',
                        message: `Cleared ${result.count} completed items`
                    });
                }
                break;
                
            case 'clearQueue':
                const confirm = await vscode.postMessage({
                    type: 'confirm',
                    message: 'Clear all items from queue?'
                });
                if (confirm) {
                    await sendRequest('clearQueue');
                }
                break;
        }
    };
    
    // Play specific item
    window.playItem = async function(itemId) {
        await sendRequest('play', { itemId });
    };
    
    // Remove item from queue
    window.removeItem = async function(itemId) {
        await sendRequest('removeFromQueue', { itemId });
    };
    
    // Handle volume change
    window.handleVolumeChange = function(value) {
        sendRequest('setVolume', { volume: parseInt(value) });
    };
    
    // Handle speed change
    window.handleSpeedChange = function(value) {
        const speed = parseInt(value) / 100;
        sendRequest('setSpeed', { speed });
    };
    
    // Handle seek
    window.handleSeek = function(event) {
        const rect = event.currentTarget.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const position = x / rect.width;
        sendRequest('seek', { position: Math.max(0, Math.min(1, position)) });
    };
    
    // Audio element event listeners
    audioElement.addEventListener('timeupdate', () => {
        if (state.currentItem && audioElement.duration) {
            sendRequest('audioProgress', {
                itemId: state.currentItem.id,
                currentTime: audioElement.currentTime,
                duration: audioElement.duration
            });
        }
    });
    
    audioElement.addEventListener('ended', () => {
        if (state.currentItem) {
            sendRequest('audioEnded', { itemId: state.currentItem.id });
        }
    });
    
    audioElement.addEventListener('error', (e) => {
        if (state.currentItem) {
            const error = e.target.error;
            const errorMessage = error ? `Audio error: ${error.message}` : 'Unknown audio error';
            sendRequest('audioError', {
                itemId: state.currentItem.id,
                error: errorMessage
            });
        }
    });
    
    audioElement.addEventListener('loadedmetadata', () => {
        updateProgressUI();
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Only handle if not in input field
        if (e.target.tagName === 'INPUT') return;
        
        switch (e.key) {
            case ' ':
                e.preventDefault();
                handleAction('togglePlayback');
                break;
            case 'ArrowLeft':
                e.preventDefault();
                handleAction('previous');
                break;
            case 'ArrowRight':
                e.preventDefault();
                handleAction('next');
                break;
            case 'ArrowUp':
                e.preventDefault();
                const newVolume = Math.min(100, state.volume + 5);
                elements.volumeSlider.value = newVolume;
                handleVolumeChange(newVolume);
                break;
            case 'ArrowDown':
                e.preventDefault();
                const newVolume2 = Math.max(0, state.volume - 5);
                elements.volumeSlider.value = newVolume2;
                handleVolumeChange(newVolume2);
                break;
        }
    });
    
    // Initialize
    function initialize() {
        // Request initial state
        sendRequest('getState').then(data => {
            if (data) {
                updateState(data);
                renderQueue();
                updatePlayerUI();
            }
        });
    }
    
    // Initialize when ready
    initialize();
})();