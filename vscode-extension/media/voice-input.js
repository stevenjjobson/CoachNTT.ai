// Voice Input WebView Client Script

(function() {
    const vscode = acquireVsCodeApi();
    
    // State
    let state = {
        recordingState: 'idle',
        vadEnabled: true,
        isRecording: false,
        transcriptions: [],
        settings: {
            vadEnabled: true,
            pushToTalkKey: 'Ctrl+Shift+V',
            vadSensitivity: 1.5,
            showWaveform: true,
            autoPlayback: false
        }
    };
    
    // DOM Elements
    const elements = {
        statusIndicator: document.getElementById('statusIndicator'),
        statusText: document.querySelector('.status-text'),
        waveformCanvas: document.getElementById('waveformCanvas'),
        waveformContainer: document.getElementById('waveformContainer'),
        audioLevelFill: document.getElementById('audioLevelFill'),
        vadStatus: document.getElementById('vadStatus'),
        energyValue: document.getElementById('energyValue'),
        thresholdValue: document.getElementById('thresholdValue'),
        confidenceValue: document.getElementById('confidenceValue'),
        recordButton: document.getElementById('recordButton'),
        pushToTalkButton: document.getElementById('pushToTalkButton'),
        vadToggle: document.getElementById('vadToggle'),
        transcriptionContent: document.getElementById('transcriptionContent'),
        audioPlayer: document.getElementById('audioPlayer'),
        playbackContainer: document.getElementById('playbackContainer'),
        clearButton: document.getElementById('clearButton'),
        sensitivitySlider: document.getElementById('sensitivitySlider'),
        sensitivityValue: document.getElementById('sensitivityValue'),
        waveformToggle: document.getElementById('waveformToggle'),
        autoPlaybackToggle: document.getElementById('autoPlaybackToggle'),
        pushToTalkKey: document.getElementById('pushToTalkKey')
    };
    
    // Waveform visualization
    const waveform = {
        ctx: null,
        width: 0,
        height: 0,
        data: new Float32Array(256),
        animationId: null
    };
    
    // Initialize
    function init() {
        setupCanvas();
        setupEventListeners();
        requestState();
        startWaveformAnimation();
    }
    
    // Setup canvas for waveform
    function setupCanvas() {
        const canvas = elements.waveformCanvas;
        const container = elements.waveformContainer;
        
        // Set canvas size
        canvas.width = container.clientWidth - 40;
        canvas.height = 120;
        
        waveform.ctx = canvas.getContext('2d');
        waveform.width = canvas.width;
        waveform.height = canvas.height;
        
        // Handle resize
        window.addEventListener('resize', () => {
            canvas.width = container.clientWidth - 40;
            waveform.width = canvas.width;
        });
    }
    
    // Setup event listeners
    function setupEventListeners() {
        // Record button
        elements.recordButton.addEventListener('click', () => {
            if (state.isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        });
        
        // Push-to-talk button
        elements.pushToTalkButton.addEventListener('mousedown', () => {
            vscode.postMessage({
                command: 'togglePushToTalk',
                data: { active: true }
            });
            elements.pushToTalkButton.classList.add('active');
        });
        
        elements.pushToTalkButton.addEventListener('mouseup', () => {
            vscode.postMessage({
                command: 'togglePushToTalk',
                data: { active: false }
            });
            elements.pushToTalkButton.classList.remove('active');
        });
        
        // VAD toggle
        elements.vadToggle.addEventListener('change', (e) => {
            updateSettings({ vadEnabled: e.target.checked });
        });
        
        // Clear button
        elements.clearButton.addEventListener('click', () => {
            clearTranscriptions();
        });
        
        // Sensitivity slider
        elements.sensitivitySlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            elements.sensitivityValue.textContent = value.toFixed(1);
            updateSettings({ vadSensitivity: value });
        });
        
        // Waveform toggle
        elements.waveformToggle.addEventListener('change', (e) => {
            updateSettings({ showWaveform: e.target.checked });
            elements.waveformContainer.style.display = e.target.checked ? 'block' : 'none';
        });
        
        // Auto-playback toggle
        elements.autoPlaybackToggle.addEventListener('change', (e) => {
            updateSettings({ autoPlayback: e.target.checked });
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'V') {
                e.preventDefault();
                elements.pushToTalkButton.dispatchEvent(new MouseEvent('mousedown'));
            }
        });
        
        document.addEventListener('keyup', (e) => {
            if (e.key === 'V') {
                elements.pushToTalkButton.dispatchEvent(new MouseEvent('mouseup'));
            }
        });
    }
    
    // Request current state from extension
    function requestState() {
        vscode.postMessage({ command: 'requestState' });
    }
    
    // Start recording
    function startRecording() {
        vscode.postMessage({ command: 'startRecording' });
    }
    
    // Stop recording
    function stopRecording() {
        vscode.postMessage({ command: 'stopRecording' });
    }
    
    // Update settings
    function updateSettings(settings) {
        state.settings = { ...state.settings, ...settings };
        vscode.postMessage({
            command: 'updateSettings',
            data: settings
        });
    }
    
    // Clear transcriptions
    function clearTranscriptions() {
        state.transcriptions = [];
        updateTranscriptionDisplay();
    }
    
    // Update UI based on recording state
    function updateRecordingState(newState) {
        state.recordingState = newState;
        state.isRecording = newState === 'recording';
        
        // Update status indicator
        elements.statusIndicator.setAttribute('data-state', newState);
        
        // Update status text
        const statusTexts = {
            idle: 'Ready',
            initializing: 'Initializing...',
            listening: 'Listening',
            recording: 'Recording',
            processing: 'Processing...',
            error: 'Error'
        };
        elements.statusText.textContent = statusTexts[newState] || 'Unknown';
        
        // Update record button
        if (state.isRecording) {
            elements.recordButton.classList.add('active');
            elements.recordButton.querySelector('.label').textContent = 'Stop Recording';
        } else {
            elements.recordButton.classList.remove('active');
            elements.recordButton.querySelector('.label').textContent = 'Start Recording';
        }
    }
    
    // Update audio level display
    function updateAudioLevel(level) {
        const percentage = Math.min(100, level * 100);
        elements.audioLevelFill.style.width = `${percentage}%`;
        
        // Change color based on level
        if (percentage > 80) {
            elements.audioLevelFill.style.background = 'var(--vscode-charts-red)';
        } else if (percentage > 50) {
            elements.audioLevelFill.style.background = 'var(--vscode-charts-yellow)';
        } else {
            elements.audioLevelFill.style.background = 'var(--vscode-charts-green)';
        }
    }
    
    // Update VAD display
    function updateVADState(vadState) {
        const { isSpeaking, energy, threshold, confidence } = vadState;
        
        // Update status
        elements.vadStatus.textContent = isSpeaking ? 'Active' : 'Inactive';
        elements.vadStatus.classList.toggle('active', isSpeaking);
        
        // Update metrics
        elements.energyValue.textContent = energy.toFixed(3);
        elements.thresholdValue.textContent = threshold.toFixed(3);
        elements.confidenceValue.textContent = `${Math.round(confidence * 100)}%`;
    }
    
    // Draw waveform
    function drawWaveform() {
        if (!waveform.ctx || !state.settings.showWaveform) return;
        
        const ctx = waveform.ctx;
        const width = waveform.width;
        const height = waveform.height;
        const data = waveform.data;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        // Draw waveform
        ctx.strokeStyle = getComputedStyle(document.documentElement)
            .getPropertyValue('--vscode-charts-green');
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        const sliceWidth = width / data.length;
        let x = 0;
        
        for (let i = 0; i < data.length; i++) {
            const v = data[i] * 0.5 + 0.5;
            const y = v * height;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
            
            x += sliceWidth;
        }
        
        ctx.stroke();
    }
    
    // Start waveform animation
    function startWaveformAnimation() {
        function animate() {
            drawWaveform();
            waveform.animationId = requestAnimationFrame(animate);
        }
        animate();
    }
    
    // Add transcription to display
    function addTranscription(text) {
        const timestamp = new Date().toLocaleTimeString();
        state.transcriptions.push({ text, timestamp });
        updateTranscriptionDisplay();
    }
    
    // Update transcription display
    function updateTranscriptionDisplay() {
        if (state.transcriptions.length === 0) {
            elements.transcriptionContent.innerHTML = 
                '<p class="placeholder">Start recording to see transcription...</p>';
            return;
        }
        
        const html = state.transcriptions
            .map(t => `<p><span class="timestamp">${t.timestamp}</span>${t.text}</p>`)
            .reverse()
            .join('');
        
        elements.transcriptionContent.innerHTML = html;
    }
    
    // Handle audio playback
    function playAudio(audioData) {
        elements.audioPlayer.src = audioData;
        elements.playbackContainer.style.display = 'block';
        
        if (state.settings.autoPlayback) {
            elements.audioPlayer.play();
        }
    }
    
    // Handle messages from extension
    window.addEventListener('message', event => {
        const message = event.data;
        
        switch (message.command) {
            case 'stateUpdate':
                updateRecordingState(message.data.state);
                if (message.data.settings) {
                    state.settings = message.data.settings;
                    // Update UI to reflect settings
                    elements.vadToggle.checked = state.settings.vadEnabled;
                    elements.sensitivitySlider.value = state.settings.vadSensitivity;
                    elements.sensitivityValue.textContent = state.settings.vadSensitivity.toFixed(1);
                    elements.waveformToggle.checked = state.settings.showWaveform;
                    elements.autoPlaybackToggle.checked = state.settings.autoPlayback;
                    elements.waveformContainer.style.display = 
                        state.settings.showWaveform ? 'block' : 'none';
                }
                break;
                
            case 'levelUpdate':
                updateAudioLevel(message.data.level);
                break;
                
            case 'vadStateUpdate':
                updateVADState(message.data);
                break;
                
            case 'audioData':
                // Update waveform data
                if (message.data.waveform) {
                    waveform.data = new Float32Array(message.data.waveform);
                }
                break;
                
            case 'recordingStarted':
                console.log('Recording started');
                break;
                
            case 'recordingEnded':
                console.log('Recording ended');
                if (message.data.audioData) {
                    playAudio(message.data.audioData);
                }
                break;
                
            case 'transcriptionResult':
                addTranscription(message.data.text);
                break;
                
            case 'error':
                console.error('Voice input error:', message.data.message);
                // Could show error in UI
                break;
        }
    });
    
    // Initialize on load
    init();
})();