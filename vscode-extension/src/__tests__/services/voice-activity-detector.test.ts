import { VoiceActivityDetector } from '../../services/voice-activity-detector';
import { createTestAudioData } from '../utils/test-helpers';
import { vadTestScenarios, expectedVADMetrics } from '../fixtures/audio-fixtures';

describe('VoiceActivityDetector', () => {
  let vad: VoiceActivityDetector;

  beforeEach(() => {
    vad = new VoiceActivityDetector();
  });

  afterEach(() => {
    vad.dispose();
  });

  describe('Basic Detection', () => {
    it('should detect silence correctly', async () => {
      const audioData = createTestAudioData({ 
        amplitude: vadTestScenarios.silence.amplitude 
      });
      
      const result = await vad.process(audioData);
      
      expect(result.isSpeech).toBe(vadTestScenarios.silence.expectedSpeech);
      expect(result.confidence).toBeLessThanOrEqual(vadTestScenarios.silence.expectedConfidence);
    });

    it('should ignore quiet background noise', async () => {
      const audioData = createTestAudioData({ 
        amplitude: vadTestScenarios.quietNoise.amplitude 
      });
      
      const result = await vad.process(audioData);
      
      expect(result.isSpeech).toBe(vadTestScenarios.quietNoise.expectedSpeech);
      expect(result.confidence).toBeLessThanOrEqual(vadTestScenarios.quietNoise.expectedConfidence + 0.1);
    });

    it('should detect normal speech', async () => {
      const audioData = createTestAudioData({ 
        amplitude: vadTestScenarios.normalSpeech.amplitude 
      });
      
      const result = await vad.process(audioData);
      
      expect(result.isSpeech).toBe(vadTestScenarios.normalSpeech.expectedSpeech);
      expect(result.confidence).toBeGreaterThanOrEqual(vadTestScenarios.normalSpeech.expectedConfidence);
    });

    it('should detect loud speech', async () => {
      const audioData = createTestAudioData({ 
        amplitude: vadTestScenarios.loudSpeech.amplitude 
      });
      
      const result = await vad.process(audioData);
      
      expect(result.isSpeech).toBe(vadTestScenarios.loudSpeech.expectedSpeech);
      expect(result.confidence).toBeGreaterThanOrEqual(vadTestScenarios.loudSpeech.expectedConfidence);
    });
  });

  describe('Adaptive Threshold', () => {
    it('should adapt threshold based on noise floor', async () => {
      // Simulate background noise
      for (let i = 0; i < 10; i++) {
        const noiseData = createTestAudioData({ amplitude: 0.05 });
        await vad.process(noiseData);
      }
      
      const metrics = vad.getMetrics();
      const initialThreshold = metrics.threshold;
      
      // Threshold should have adapted above noise floor
      expect(initialThreshold).toBeGreaterThan(0.05);
      expect(initialThreshold).toBeLessThan(0.15);
    });

    it('should maintain minimum threshold', async () => {
      // Process complete silence
      for (let i = 0; i < 20; i++) {
        const silenceData = createTestAudioData({ amplitude: 0 });
        await vad.process(silenceData);
      }
      
      const metrics = vad.getMetrics();
      // Threshold should not go below minimum
      expect(metrics.threshold).toBeGreaterThanOrEqual(0.02);
    });

    it('should handle sudden volume changes', async () => {
      // Start with quiet
      const quietData = createTestAudioData({ amplitude: 0.1 });
      await vad.process(quietData);
      
      // Sudden loud sound
      const loudData = createTestAudioData({ amplitude: 0.9 });
      const result = await vad.process(loudData);
      
      // Should still detect as speech despite sudden change
      expect(result.isSpeech).toBe(true);
      expect(result.confidence).toBeGreaterThan(0.8);
    });
  });

  describe('Performance', () => {
    it('should process audio within time limit', async () => {
      const audioData = createTestAudioData({ 
        amplitude: 0.5,
        duration: 0.1 // 100ms of audio
      });
      
      const startTime = performance.now();
      await vad.process(audioData);
      const processingTime = performance.now() - startTime;
      
      expect(processingTime).toBeLessThan(expectedVADMetrics.processingTime.max);
    });

    it('should handle large audio buffers efficiently', async () => {
      const audioData = createTestAudioData({ 
        amplitude: 0.3,
        duration: 1 // 1 second of audio
      });
      
      const startTime = performance.now();
      await vad.process(audioData);
      const processingTime = performance.now() - startTime;
      
      // Should still be fast even with larger buffer
      expect(processingTime).toBeLessThan(expectedVADMetrics.processingTime.max * 2);
    });
  });

  describe('State Management', () => {
    it('should track consecutive speech frames', async () => {
      // Simulate continuous speech
      for (let i = 0; i < 5; i++) {
        const speechData = createTestAudioData({ amplitude: 0.4 });
        await vad.process(speechData);
      }
      
      const metrics = vad.getMetrics();
      expect(metrics.consecutiveSpeech).toBeGreaterThan(0);
    });

    it('should reset on silence after speech', async () => {
      // Speech
      const speechData = createTestAudioData({ amplitude: 0.4 });
      await vad.process(speechData);
      
      // Silence
      const silenceData = createTestAudioData({ amplitude: 0 });
      await vad.process(silenceData);
      
      const metrics = vad.getMetrics();
      expect(metrics.consecutiveSilence).toBeGreaterThan(0);
    });

    it('should handle intermittent speech', async () => {
      const pattern = vadTestScenarios.intermittentSpeech.pattern;
      const results = [];
      
      for (const amplitude of pattern) {
        const audioData = createTestAudioData({ amplitude });
        const result = await vad.process(audioData);
        results.push(result.isSpeech);
      }
      
      expect(results).toEqual(vadTestScenarios.intermittentSpeech.expectedSpeechFrames);
    });
  });

  describe('Metrics and Monitoring', () => {
    it('should provide accurate metrics', async () => {
      const audioData = createTestAudioData({ amplitude: 0.3 });
      await vad.process(audioData);
      
      const metrics = vad.getMetrics();
      
      expect(metrics).toHaveProperty('energy');
      expect(metrics).toHaveProperty('threshold');
      expect(metrics).toHaveProperty('confidence');
      expect(metrics).toHaveProperty('consecutiveSpeech');
      expect(metrics).toHaveProperty('consecutiveSilence');
      expect(metrics).toHaveProperty('adaptiveThreshold');
      
      expect(metrics.energy).toBeGreaterThan(0);
      expect(metrics.threshold).toBeGreaterThan(0);
      expect(metrics.confidence).toBeGreaterThanOrEqual(0);
      expect(metrics.confidence).toBeLessThanOrEqual(1);
    });

    it('should calculate energy correctly', () => {
      // Test with known values
      const testData = new Float32Array([0.5, -0.5, 0.3, -0.3]);
      const energy = (vad as any).calculateEnergy(testData);
      
      // Energy = RMS = sqrt((0.5² + 0.5² + 0.3² + 0.3²) / 4)
      const expectedEnergy = Math.sqrt((0.25 + 0.25 + 0.09 + 0.09) / 4);
      expect(energy).toBeCloseTo(expectedEnergy, 4);
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty audio data', async () => {
      const emptyData = new Float32Array(0);
      const result = await vad.process(emptyData);
      
      expect(result.isSpeech).toBe(false);
      expect(result.confidence).toBe(0);
    });

    it('should handle single sample', async () => {
      const singleSample = new Float32Array([0.5]);
      const result = await vad.process(singleSample);
      
      expect(result).toHaveProperty('isSpeech');
      expect(result).toHaveProperty('confidence');
    });

    it('should handle very long audio without memory issues', async () => {
      const longAudio = createTestAudioData({ 
        amplitude: 0.3,
        duration: 10 // 10 seconds
      });
      
      const initialMemory = process.memoryUsage().heapUsed;
      await vad.process(longAudio);
      const finalMemory = process.memoryUsage().heapUsed;
      
      // Memory increase should be reasonable (less than 10MB)
      const memoryIncrease = finalMemory - initialMemory;
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024);
    });
  });

  describe('Configuration', () => {
    it('should respect custom configuration', () => {
      const customVad = new VoiceActivityDetector({
        energyThreshold: 0.1,
        minSilenceDuration: 500,
        minSpeechDuration: 200,
        adaptiveRate: 0.05,
        frameSize: 2048,
        sampleRate: 48000
      });
      
      const config = (customVad as any).config;
      expect(config.energyThreshold).toBe(0.1);
      expect(config.minSilenceDuration).toBe(500);
      expect(config.minSpeechDuration).toBe(200);
      expect(config.adaptiveRate).toBe(0.05);
      expect(config.frameSize).toBe(2048);
      expect(config.sampleRate).toBe(48000);
      
      customVad.dispose();
    });

    it('should validate configuration values', () => {
      expect(() => {
        new VoiceActivityDetector({
          energyThreshold: -1 // Invalid negative threshold
        });
      }).toThrow();
      
      expect(() => {
        new VoiceActivityDetector({
          adaptiveRate: 2 // Invalid rate > 1
        });
      }).toThrow();
    });
  });

  describe('Disposal', () => {
    it('should clean up resources on disposal', () => {
      const customVad = new VoiceActivityDetector();
      customVad.dispose();
      
      // Should not throw when processing after disposal
      expect(async () => {
        const audioData = createTestAudioData({ amplitude: 0.3 });
        await customVad.process(audioData);
      }).not.toThrow();
    });
  });
});