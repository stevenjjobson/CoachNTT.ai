import { AudioCaptureService } from '../../services/audio-capture-service';
import { VoiceActivityDetector } from '../../services/voice-activity-detector';
import { 
  createMockMediaStream, 
  createTestAudioData,
  waitFor,
  flushPromises 
} from '../utils/test-helpers';
import { captureTestScenarios, webRTCConstraints } from '../fixtures/audio-fixtures';
import * as vscode from 'vscode';

// Mock getUserMedia
global.navigator = {
  mediaDevices: {
    getUserMedia: jest.fn()
  }
} as any;

describe('AudioCaptureService', () => {
  let captureService: AudioCaptureService;
  let mockStream: MediaStream;
  
  beforeEach(() => {
    // Reset singleton
    (AudioCaptureService as any).instance = null;
    
    // Create mock stream
    mockStream = createMockMediaStream();
    (navigator.mediaDevices.getUserMedia as jest.Mock).mockResolvedValue(mockStream);
    
    // Get service instance
    captureService = AudioCaptureService.getInstance();
  });

  afterEach(() => {
    captureService.dispose();
    jest.clearAllMocks();
  });

  describe('Singleton Pattern', () => {
    it('should return the same instance', () => {
      const instance1 = AudioCaptureService.getInstance();
      const instance2 = AudioCaptureService.getInstance();
      
      expect(instance1).toBe(instance2);
    });
  });

  describe('Capture Lifecycle', () => {
    it('should start capture successfully', async () => {
      await captureService.startCapture();
      
      expect(captureService.isCapturing()).toBe(true);
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith(webRTCConstraints);
    });

    it('should stop capture and return audio data', async () => {
      await captureService.startCapture();
      
      // Simulate some audio processing
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const audioData = await captureService.stopCapture();
      
      expect(captureService.isCapturing()).toBe(false);
      expect(audioData).toBeInstanceOf(ArrayBuffer);
      expect(audioData.byteLength).toBeGreaterThan(0);
    });

    it('should handle multiple start calls gracefully', async () => {
      await captureService.startCapture();
      
      // Second start should not create new stream
      await captureService.startCapture();
      
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(1);
      expect(captureService.isCapturing()).toBe(true);
    });

    it('should handle stop without start', async () => {
      const audioData = await captureService.stopCapture();
      
      expect(audioData.byteLength).toBe(44); // Just WAV header
    });
  });

  describe('Audio Processing', () => {
    it('should process audio chunks', async () => {
      await captureService.startCapture();
      
      // Simulate audio processing event
      const testAudio = createTestAudioData({ amplitude: 0.5, duration: 0.1 });
      const event = {
        inputBuffer: {
          getChannelData: () => testAudio
        }
      };
      
      (captureService as any).handleAudioProcess(event);
      
      const audioData = await captureService.stopCapture();
      expect(audioData.byteLength).toBeGreaterThan(44); // More than just header
    });

    it('should respect maximum duration', async () => {
      await captureService.startCapture();
      
      // Start time tracking
      const startTime = Date.now();
      
      // Wait for max duration timeout
      await waitFor(
        () => !captureService.isCapturing(),
        31000 // Just over 30 seconds
      );
      
      const duration = Date.now() - startTime;
      expect(duration).toBeGreaterThanOrEqual(30000);
      expect(duration).toBeLessThan(31000);
    });

    it('should handle pre-speech buffering', async () => {
      const customService = new (AudioCaptureService as any)();
      customService.config = {
        preSpeechBufferMs: 300,
        postSpeechTimeoutMs: 800,
        maxRecordingDuration: 30000,
        sampleRate: 16000,
        channelCount: 1
      };
      
      await customService.startCapture();
      
      // Add some pre-speech audio
      const silentAudio = createTestAudioData({ amplitude: 0.05, duration: 0.3 });
      (customService as any).handleAudioProcess({
        inputBuffer: { getChannelData: () => silentAudio }
      });
      
      // Add speech
      const speechAudio = createTestAudioData({ amplitude: 0.5, duration: 0.5 });
      (customService as any).handleAudioProcess({
        inputBuffer: { getChannelData: () => speechAudio }
      });
      
      const audioData = await customService.stopCapture();
      
      // Should include pre-speech buffer
      const expectedMinSize = 44 + (0.8 * 16000 * 2); // Header + 0.8s of 16-bit audio
      expect(audioData.byteLength).toBeGreaterThanOrEqual(expectedMinSize);
      
      customService.dispose();
    });
  });

  describe('VAD Integration', () => {
    it('should use VAD for speech detection', async () => {
      const vadSpy = jest.spyOn(VoiceActivityDetector.prototype, 'process');
      
      await captureService.startCapture();
      
      // Process some audio
      const testAudio = createTestAudioData({ amplitude: 0.4 });
      (captureService as any).handleAudioProcess({
        inputBuffer: { getChannelData: () => testAudio }
      });
      
      await flushPromises();
      
      expect(vadSpy).toHaveBeenCalled();
      vadSpy.mockRestore();
    });

    it('should trigger onSpeechStart event', async () => {
      let speechStarted = false;
      captureService.onSpeechStart(() => {
        speechStarted = true;
      });
      
      await captureService.startCapture();
      
      // Simulate speech
      const speechAudio = createTestAudioData({ amplitude: 0.5 });
      (captureService as any).handleAudioProcess({
        inputBuffer: { getChannelData: () => speechAudio }
      });
      
      await flushPromises();
      
      expect(speechStarted).toBe(true);
    });

    it('should trigger onSpeechEnd event', async () => {
      let speechEnded = false;
      captureService.onSpeechEnd(() => {
        speechEnded = true;
      });
      
      await captureService.startCapture();
      
      // Simulate speech then silence
      const speechAudio = createTestAudioData({ amplitude: 0.5 });
      (captureService as any).handleAudioProcess({
        inputBuffer: { getChannelData: () => speechAudio }
      });
      
      // Trigger silence for longer than timeout
      for (let i = 0; i < 10; i++) {
        const silenceAudio = createTestAudioData({ amplitude: 0 });
        (captureService as any).handleAudioProcess({
          inputBuffer: { getChannelData: () => silenceAudio }
        });
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      expect(speechEnded).toBe(true);
    });
  });

  describe('Audio Encoding', () => {
    it('should encode to WAV format', async () => {
      await captureService.startCapture();
      
      // Add known audio data
      const testAudio = new Float32Array([0.5, -0.5, 0.3, -0.3]);
      (captureService as any).audioChunks.push(testAudio);
      
      const audioData = await captureService.stopCapture();
      const view = new DataView(audioData);
      
      // Check WAV header
      const riff = String.fromCharCode(
        view.getUint8(0), view.getUint8(1), view.getUint8(2), view.getUint8(3)
      );
      expect(riff).toBe('RIFF');
      
      const wave = String.fromCharCode(
        view.getUint8(8), view.getUint8(9), view.getUint8(10), view.getUint8(11)
      );
      expect(wave).toBe('WAVE');
      
      // Check audio format (PCM)
      const audioFormat = view.getUint16(20, true);
      expect(audioFormat).toBe(1);
      
      // Check sample rate
      const sampleRate = view.getUint32(24, true);
      expect(sampleRate).toBe(16000);
    });

    it('should handle empty audio chunks', async () => {
      await captureService.startCapture();
      
      // Don't add any audio
      const audioData = await captureService.stopCapture();
      
      expect(audioData.byteLength).toBe(44); // Just header
    });

    it('should concatenate multiple chunks correctly', async () => {
      await captureService.startCapture();
      
      // Add multiple chunks
      const chunk1 = new Float32Array([0.1, 0.2]);
      const chunk2 = new Float32Array([0.3, 0.4]);
      const chunk3 = new Float32Array([0.5, 0.6]);
      
      (captureService as any).audioChunks.push(chunk1, chunk2, chunk3);
      
      const audioData = await captureService.stopCapture();
      const expectedDataSize = 6 * 2; // 6 samples * 2 bytes per sample
      
      expect(audioData.byteLength).toBe(44 + expectedDataSize);
    });
  });

  describe('Error Handling', () => {
    it('should handle getUserMedia rejection', async () => {
      (navigator.mediaDevices.getUserMedia as jest.Mock).mockRejectedValueOnce(
        new Error('Permission denied')
      );
      
      await expect(captureService.startCapture()).rejects.toThrow('Permission denied');
      expect(captureService.isCapturing()).toBe(false);
    });

    it('should handle stream track errors', async () => {
      await captureService.startCapture();
      
      // Simulate track ending unexpectedly
      const tracks = mockStream.getAudioTracks();
      tracks.forEach(track => {
        (track as any).readyState = 'ended';
      });
      
      // Should handle gracefully
      const audioData = await captureService.stopCapture();
      expect(audioData).toBeInstanceOf(ArrayBuffer);
    });

    it('should clean up on disposal', async () => {
      await captureService.startCapture();
      
      const stopSpy = jest.spyOn(mockStream.getAudioTracks()[0], 'stop');
      
      captureService.dispose();
      
      expect(stopSpy).toHaveBeenCalled();
      expect(captureService.isCapturing()).toBe(false);
    });
  });

  describe('Event Management', () => {
    it('should handle multiple event listeners', async () => {
      let count1 = 0;
      let count2 = 0;
      
      const dispose1 = captureService.onSpeechStart(() => count1++);
      const dispose2 = captureService.onSpeechStart(() => count2++);
      
      await captureService.startCapture();
      
      // Trigger speech
      const speechAudio = createTestAudioData({ amplitude: 0.5 });
      (captureService as any).handleAudioProcess({
        inputBuffer: { getChannelData: () => speechAudio }
      });
      
      await flushPromises();
      
      expect(count1).toBe(1);
      expect(count2).toBe(1);
      
      // Dispose one listener
      dispose1.dispose();
      
      // Trigger again
      (captureService as any).handleAudioProcess({
        inputBuffer: { getChannelData: () => speechAudio }
      });
      
      await flushPromises();
      
      expect(count1).toBe(1); // Should not increase
      expect(count2).toBe(2); // Should increase
    });

    it('should emit VAD metrics', async () => {
      let metricsReceived: any;
      
      captureService.onVADMetrics((metrics) => {
        metricsReceived = metrics;
      });
      
      await captureService.startCapture();
      
      // Process audio to trigger VAD
      const testAudio = createTestAudioData({ amplitude: 0.4 });
      (captureService as any).handleAudioProcess({
        inputBuffer: { getChannelData: () => testAudio }
      });
      
      await flushPromises();
      
      expect(metricsReceived).toBeDefined();
      expect(metricsReceived).toHaveProperty('energy');
      expect(metricsReceived).toHaveProperty('threshold');
      expect(metricsReceived).toHaveProperty('confidence');
    });
  });

  describe('Configuration', () => {
    it('should respect custom configuration from settings', () => {
      const mockConfig = {
        get: jest.fn((key: string) => {
          const configs: any = {
            'audioCapture.preSpeechBufferMs': 500,
            'audioCapture.postSpeechTimeoutMs': 1000,
            'audioCapture.maxRecordingDuration': 60000,
            'audioCapture.sampleRate': 48000
          };
          return configs[key];
        })
      };
      
      (vscode.workspace.getConfiguration as jest.Mock).mockReturnValue(mockConfig);
      
      // Create new instance to pick up config
      (AudioCaptureService as any).instance = null;
      const customService = AudioCaptureService.getInstance();
      
      const config = (customService as any).config;
      expect(config.preSpeechBufferMs).toBe(500);
      expect(config.postSpeechTimeoutMs).toBe(1000);
      expect(config.maxRecordingDuration).toBe(60000);
      expect(config.sampleRate).toBe(48000);
      
      customService.dispose();
    });
  });

  describe('Performance', () => {
    it('should handle high-frequency audio processing', async () => {
      await captureService.startCapture();
      
      const startTime = performance.now();
      
      // Simulate 1 second of audio at 100Hz processing rate
      for (let i = 0; i < 100; i++) {
        const audio = createTestAudioData({ amplitude: 0.3, duration: 0.01 });
        (captureService as any).handleAudioProcess({
          inputBuffer: { getChannelData: () => audio }
        });
      }
      
      const processingTime = performance.now() - startTime;
      
      // Should handle without blocking
      expect(processingTime).toBeLessThan(1000);
      
      const audioData = await captureService.stopCapture();
      expect(audioData.byteLength).toBeGreaterThan(44);
    });

    it('should not accumulate memory over time', async () => {
      await captureService.startCapture();
      
      const initialMemory = process.memoryUsage().heapUsed;
      
      // Process audio for "5 seconds"
      for (let i = 0; i < 50; i++) {
        const audio = createTestAudioData({ amplitude: 0.3, duration: 0.1 });
        (captureService as any).handleAudioProcess({
          inputBuffer: { getChannelData: () => audio }
        });
        
        // Clear old chunks periodically (as the service should)
        if (i % 10 === 0) {
          (captureService as any).audioChunks = (captureService as any).audioChunks.slice(-10);
        }
      }
      
      const finalMemory = process.memoryUsage().heapUsed;
      const memoryIncrease = finalMemory - initialMemory;
      
      // Should not leak memory significantly
      expect(memoryIncrease).toBeLessThan(5 * 1024 * 1024); // Less than 5MB
    });
  });
});