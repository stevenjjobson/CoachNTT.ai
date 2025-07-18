# 🎯 Next Session: 2.2.2 Voice Activity Detection

## 📋 Session Overview
- **Session**: 2.2.2
- **Title**: Voice Activity Detection & Audio Capture
- **Duration**: 1.5-2 hours
- **Complexity**: Medium-High
- **Prerequisites**: Session 2.2.1 complete ✅, Audio service ready ✅

## 🎯 Primary Goals
1. Implement voice activity detection (VAD) for automatic recording
2. Create audio capture service with streaming support
3. Add push-to-talk functionality
4. Integrate with MCP for speech-to-text processing

## 📁 Files to Create/Modify
1. **vscode-extension/src/services/voice-activity-detector.ts** (~200 lines)
   - VAD algorithm implementation
   - Energy-based detection with adaptive thresholds
   - Noise floor calibration
   
2. **vscode-extension/src/services/audio-capture-service.ts** (~300 lines)
   - WebRTC audio capture
   - Stream management
   - Recording buffer with circular storage
   
3. **vscode-extension/src/webview/voice-input/voice-input-panel.ts** (~250 lines)
   - Voice input UI with waveform visualization
   - Recording status indicators
   - Push-to-talk controls
   
4. **vscode-extension/media/voice-input.css** (~150 lines)
   - Voice input panel styles
   - Waveform animations
   - Recording indicators
   
5. **vscode-extension/media/voice-input.js** (~200 lines)
   - Client-side audio capture
   - Waveform rendering
   - VAD visualization

## 🔍 Technical Requirements
### Voice Activity Detection
- Energy-based detection with 40ms frames
- Adaptive threshold based on noise floor
- Pre-speech buffer (300ms) to capture beginning
- Post-speech timeout (800ms) to avoid cutting off
- Frequency analysis for speech/noise discrimination

### Audio Capture
- WebRTC getUserMedia API
- 16kHz sample rate for speech
- Mono channel recording
- Streaming to backend in chunks
- Automatic gain control (AGC)

### Push-to-Talk
- Configurable hotkey (default: Ctrl+Shift+V)
- Visual feedback during recording
- Auto-stop on key release
- Maximum recording duration (30s)

## 📝 Implementation Plan
### Part 1: Voice Activity Detector
```typescript
export class VoiceActivityDetector {
    private energyThreshold: number;
    private noiseFloor: number;
    private speechFrames: number = 0;
    
    public detectSpeech(audioData: Float32Array): boolean {
        const energy = this.calculateEnergy(audioData);
        const isSpeech = energy > this.energyThreshold;
        // Implement hysteresis and smoothing
        return this.smoothDetection(isSpeech);
    }
}
```

### Part 2: Audio Capture Service
```typescript
export class AudioCaptureService {
    private mediaStream: MediaStream | null = null;
    private audioContext: AudioContext;
    private processor: ScriptProcessorNode;
    
    public async startCapture(): Promise<void> {
        this.mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true
            }
        });
    }
}
```

### Part 3: Voice Input Panel
- Real-time waveform visualization
- Recording status (idle, listening, recording, processing)
- Settings for VAD sensitivity
- Push-to-talk button and hotkey indicator

## ⚡ Performance Targets
- VAD latency: <10ms per frame
- Audio capture latency: <50ms
- Waveform render: 60 FPS
- Memory usage: <20MB for 30s recording

## 🧪 Testing Requirements
1. Test VAD with various noise levels
2. Verify audio quality at 16kHz
3. Test push-to-talk responsiveness
4. Validate maximum recording duration
5. Test cross-platform audio capture

## 📚 Key Concepts
- **Voice Activity Detection**: Distinguishing speech from silence/noise
- **Energy Calculation**: RMS of audio samples
- **Adaptive Thresholding**: Dynamic adjustment based on ambient noise
- **Circular Buffer**: Efficient pre-speech capture
- **WebRTC**: Modern browser audio API

## 🔗 Integration Points
- AudioPlaybackService for playback of captured audio
- MCPClient for speech-to-text requests
- WebViewManager for voice input panel
- Extension settings for VAD configuration

## 📦 Deliverables
1. ✅ Voice activity detection with adaptive thresholds
2. ✅ Audio capture service with streaming
3. ✅ Voice input WebView panel with waveform
4. ✅ Push-to-talk functionality
5. ✅ Integration with existing audio infrastructure

## 🚨 Safety Considerations
- Audio data must be abstracted before storage
- No raw audio persisted without user consent
- Clear visual indicators when recording
- Automatic stop on maximum duration
- Secure handling of microphone permissions

## 💡 Innovation Opportunities
- Advanced VAD using frequency analysis
- Real-time transcription preview
- Voice commands detection
- Multi-language support ready
- Noise profile learning

## 🔄 State Management
```typescript
interface VoiceInputState {
    isRecording: boolean;
    vadActive: boolean;
    audioLevel: number;
    noiseLevel: number;
    recordingDuration: number;
    transcriptionPending: boolean;
}
```

## 📈 Success Metrics
- VAD accuracy: >95% for clear speech
- False positive rate: <5% for typical noise
- User satisfaction with push-to-talk response
- Successful integration with speech-to-text
- Clean audio capture without artifacts

## 🎓 Learning Resources
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [MediaStream Recording](https://developer.mozilla.org/en-US/docs/Web/API/MediaStream_Recording_API)
- [Voice Activity Detection](https://en.wikipedia.org/wiki/Voice_activity_detection)
- [WebRTC getUserMedia](https://webrtc.org/getting-started/media-capture-and-constraints)

## ✅ Pre-Session Checklist
- [ ] Audio playback service working (Session 2.2.1)
- [ ] WebView infrastructure ready
- [ ] Microphone permissions understood
- [ ] VAD algorithm researched
- [ ] Performance profiling tools ready

## 🚀 Quick Start
```bash
# Continue from Session 2.2.1
cd vscode-extension

# Create voice services
mkdir -p src/services
touch src/services/voice-activity-detector.ts
touch src/services/audio-capture-service.ts

# Create voice input WebView
mkdir -p src/webview/voice-input
touch src/webview/voice-input/voice-input-panel.ts

# Create media files
touch media/voice-input.css
touch media/voice-input.js

# Start development
npm run watch
```

## 📝 Context for Next Session
After completing voice activity detection, the next session (2.2.3) will focus on real-time monitoring features including resource usage tracking, performance metrics, and safety score visualization.

**Note**: Session 2.2.1 successfully implemented audio playback with queue management, caching, and MCP integration. The audio infrastructure is ready for voice input features.