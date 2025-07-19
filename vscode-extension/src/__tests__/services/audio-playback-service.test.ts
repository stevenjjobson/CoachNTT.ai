import { AudioPlaybackService } from '../../services/audio-playback-service';
import { AudioQueue, AudioQueueItem, AudioPriority } from '../../models/audio-queue';
import { MCPClient } from '../../services/mcp-client';
import { AudioCache } from '../../utils/audio-cache';
import { playbackTestScenarios } from '../fixtures/audio-fixtures';
import { waitFor, createDeferred } from '../utils/test-helpers';
import * as vscode from 'vscode';

// Mock dependencies
jest.mock('../../services/mcp-client');
jest.mock('../../utils/audio-cache');

describe('AudioPlaybackService', () => {
  let playbackService: AudioPlaybackService;
  let mockMCPClient: jest.Mocked<MCPClient>;
  let mockCache: jest.Mocked<AudioCache>;
  let mockStatusBarItem: any;

  beforeEach(() => {
    // Reset singleton
    (AudioPlaybackService as any).instance = null;
    
    // Setup mocks
    mockMCPClient = {
      isConnected: jest.fn().mockReturnValue(true),
      synthesizeAudio: jest.fn().mockResolvedValue({
        audio_data: 'base64AudioData',
        format: 'wav',
        duration_ms: 1000
      })
    } as any;
    
    mockCache = {
      get: jest.fn(),
      set: jest.fn(),
      has: jest.fn().mockReturnValue(false),
      delete: jest.fn(),
      clear: jest.fn(),
      getSize: jest.fn().mockReturnValue(0)
    } as any;
    
    mockStatusBarItem = {
      text: '',
      tooltip: '',
      show: jest.fn(),
      hide: jest.fn()
    };
    
    // Mock VSCode APIs
    (vscode.window.createStatusBarItem as jest.Mock).mockReturnValue(mockStatusBarItem);
    (MCPClient.getInstance as jest.Mock).mockReturnValue(mockMCPClient);
    (AudioCache as jest.Mock).mockImplementation(() => mockCache);
    
    // Get service instance
    playbackService = AudioPlaybackService.getInstance();
  });

  afterEach(() => {
    playbackService.dispose();
    jest.clearAllMocks();
  });

  describe('Singleton Pattern', () => {
    it('should return the same instance', () => {
      const instance1 = AudioPlaybackService.getInstance();
      const instance2 = AudioPlaybackService.getInstance();
      
      expect(instance1).toBe(instance2);
    });
  });

  describe('Queue Management', () => {
    it('should add items to queue', async () => {
      const item = playbackTestScenarios.singleItem.items[0];
      
      await playbackService.addToQueue(item.content, item.priority);
      
      const queue = playbackService.getQueue();
      expect(queue).toHaveLength(1);
      expect(queue[0].content).toBe(item.content);
      expect(queue[0].priority).toBe(item.priority);
    });

    it('should respect priority ordering', async () => {
      const items = playbackTestScenarios.queueWithPriorities.items;
      
      // Add items in original order
      for (const item of items) {
        await playbackService.addToQueue(item.content, item.priority);
      }
      
      const queue = playbackService.getQueue();
      const queueIds = queue.map(item => item.id);
      
      // Check if high priority items are first
      const highPriorityIndex = queueIds.indexOf('high-1');
      const mediumPriorityIndex = queueIds.indexOf('medium-1');
      const lowPriorityIndex = queueIds.indexOf('low-1');
      
      expect(highPriorityIndex).toBeLessThan(mediumPriorityIndex);
      expect(mediumPriorityIndex).toBeLessThan(lowPriorityIndex);
    });

    it('should limit queue size', async () => {
      const maxSize = 100;
      
      // Add more than max items
      for (let i = 0; i < maxSize + 10; i++) {
        await playbackService.addToQueue(`Item ${i}`, 'medium');
      }
      
      const queue = playbackService.getQueue();
      expect(queue.length).toBeLessThanOrEqual(maxSize);
    });

    it('should remove old items when queue is full', async () => {
      // Fill queue
      for (let i = 0; i < 100; i++) {
        await playbackService.addToQueue(`Item ${i}`, 'low');
      }
      
      // Add high priority item
      await playbackService.addToQueue('High priority item', 'high');
      
      const queue = playbackService.getQueue();
      expect(queue[0].content).toBe('High priority item');
      expect(queue.length).toBe(100);
    });

    it('should clear queue', () => {
      playbackService.addToQueue('Item 1', 'medium');
      playbackService.addToQueue('Item 2', 'medium');
      
      playbackService.clearQueue();
      
      const queue = playbackService.getQueue();
      expect(queue).toHaveLength(0);
    });

    it('should remove specific item from queue', async () => {
      await playbackService.addToQueue('Item 1', 'medium');
      await playbackService.addToQueue('Item 2', 'medium');
      
      const queue = playbackService.getQueue();
      const itemToRemove = queue[0];
      
      playbackService.removeFromQueue(itemToRemove.id);
      
      const updatedQueue = playbackService.getQueue();
      expect(updatedQueue).toHaveLength(1);
      expect(updatedQueue[0].id).not.toBe(itemToRemove.id);
    });
  });

  describe('Playback Control', () => {
    it('should start playback', async () => {
      await playbackService.addToQueue('Test content', 'medium');
      
      await playbackService.play();
      
      expect(playbackService.isPlaying()).toBe(true);
      expect(mockMCPClient.synthesizeAudio).toHaveBeenCalledWith('Test content');
    });

    it('should pause playback', async () => {
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      
      await playbackService.pause();
      
      expect(playbackService.isPlaying()).toBe(false);
    });

    it('should stop playback', async () => {
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      
      await playbackService.stop();
      
      expect(playbackService.isPlaying()).toBe(false);
      expect(playbackService.getCurrentItem()).toBeNull();
    });

    it('should skip to next item', async () => {
      await playbackService.addToQueue('Item 1', 'medium');
      await playbackService.addToQueue('Item 2', 'medium');
      
      await playbackService.play();
      const firstItem = playbackService.getCurrentItem();
      
      await playbackService.next();
      const secondItem = playbackService.getCurrentItem();
      
      expect(secondItem).not.toBe(firstItem);
      expect(secondItem?.content).toBe('Item 2');
    });

    it('should go to previous item', async () => {
      await playbackService.addToQueue('Item 1', 'medium');
      await playbackService.addToQueue('Item 2', 'medium');
      
      await playbackService.play();
      await playbackService.next();
      
      await playbackService.previous();
      const currentItem = playbackService.getCurrentItem();
      
      expect(currentItem?.content).toBe('Item 1');
    });

    it('should handle empty queue gracefully', async () => {
      await expect(playbackService.play()).resolves.not.toThrow();
      expect(playbackService.isPlaying()).toBe(false);
    });
  });

  describe('Audio Synthesis', () => {
    it('should synthesize audio via MCP', async () => {
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      
      expect(mockMCPClient.synthesizeAudio).toHaveBeenCalledWith('Test content');
    });

    it('should use cached audio when available', async () => {
      const cachedAudio = 'cachedBase64Audio';
      mockCache.has.mockReturnValue(true);
      mockCache.get.mockResolvedValue(cachedAudio);
      
      await playbackService.addToQueue('Cached content', 'medium');
      await playbackService.play();
      
      expect(mockCache.get).toHaveBeenCalled();
      expect(mockMCPClient.synthesizeAudio).not.toHaveBeenCalled();
    });

    it('should cache synthesized audio', async () => {
      const audioData = 'base64AudioData';
      mockMCPClient.synthesizeAudio.mockResolvedValue({
        audio_data: audioData,
        format: 'wav',
        duration_ms: 1000
      });
      
      await playbackService.addToQueue('New content', 'medium');
      await playbackService.play();
      
      expect(mockCache.set).toHaveBeenCalledWith(expect.any(String), audioData);
    });

    it('should handle synthesis errors', async () => {
      mockMCPClient.synthesizeAudio.mockRejectedValue(new Error('Synthesis failed'));
      
      await playbackService.addToQueue('Error content', 'medium');
      await playbackService.play();
      
      // Should handle error gracefully and move to next item
      expect(playbackService.isPlaying()).toBe(false);
    });

    it('should handle MCP disconnection', async () => {
      mockMCPClient.isConnected.mockReturnValue(false);
      
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      
      expect(playbackService.isPlaying()).toBe(false);
      expect(mockMCPClient.synthesizeAudio).not.toHaveBeenCalled();
    });
  });

  describe('Volume Control', () => {
    it('should set volume', () => {
      playbackService.setVolume(0.5);
      expect(playbackService.getVolume()).toBe(0.5);
    });

    it('should clamp volume between 0 and 1', () => {
      playbackService.setVolume(-0.5);
      expect(playbackService.getVolume()).toBe(0);
      
      playbackService.setVolume(1.5);
      expect(playbackService.getVolume()).toBe(1);
    });

    it('should increase volume', () => {
      playbackService.setVolume(0.5);
      playbackService.volumeUp();
      expect(playbackService.getVolume()).toBe(0.6);
    });

    it('should decrease volume', () => {
      playbackService.setVolume(0.5);
      playbackService.volumeDown();
      expect(playbackService.getVolume()).toBe(0.4);
    });

    it('should not exceed volume limits', () => {
      playbackService.setVolume(0.95);
      playbackService.volumeUp();
      expect(playbackService.getVolume()).toBe(1);
      
      playbackService.setVolume(0.05);
      playbackService.volumeDown();
      expect(playbackService.getVolume()).toBe(0);
    });
  });

  describe('Status Bar Integration', () => {
    it('should show status when playing', async () => {
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      
      expect(mockStatusBarItem.show).toHaveBeenCalled();
      expect(mockStatusBarItem.text).toContain('$(play)');
    });

    it('should show pause icon when paused', async () => {
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      await playbackService.pause();
      
      expect(mockStatusBarItem.text).toContain('$(debug-pause)');
    });

    it('should hide status when stopped', async () => {
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      await playbackService.stop();
      
      expect(mockStatusBarItem.hide).toHaveBeenCalled();
    });

    it('should show queue count', async () => {
      await playbackService.addToQueue('Item 1', 'medium');
      await playbackService.addToQueue('Item 2', 'medium');
      await playbackService.play();
      
      expect(mockStatusBarItem.text).toContain('[1/2]');
    });
  });

  describe('Event Handling', () => {
    it('should emit playback started event', async () => {
      const deferred = createDeferred<void>();
      
      playbackService.onPlaybackStarted(() => {
        deferred.resolve();
      });
      
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      
      await expect(deferred.promise).resolves.toBeUndefined();
    });

    it('should emit playback stopped event', async () => {
      const deferred = createDeferred<void>();
      
      playbackService.onPlaybackStopped(() => {
        deferred.resolve();
      });
      
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      await playbackService.stop();
      
      await expect(deferred.promise).resolves.toBeUndefined();
    });

    it('should emit queue changed event', async () => {
      let queueChangeCount = 0;
      
      playbackService.onQueueChanged(() => {
        queueChangeCount++;
      });
      
      await playbackService.addToQueue('Item 1', 'medium');
      await playbackService.addToQueue('Item 2', 'medium');
      playbackService.clearQueue();
      
      expect(queueChangeCount).toBe(3);
    });

    it('should emit item completed event', async () => {
      const deferred = createDeferred<AudioQueueItem>();
      
      playbackService.onItemCompleted((item) => {
        deferred.resolve(item);
      });
      
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      
      // Simulate completion
      (playbackService as any).handleItemComplete();
      
      const completedItem = await deferred.promise;
      expect(completedItem.content).toBe('Test content');
    });
  });

  describe('Auto-play Behavior', () => {
    it('should auto-play next item in queue', async () => {
      await playbackService.addToQueue('Item 1', 'medium');
      await playbackService.addToQueue('Item 2', 'medium');
      
      await playbackService.play();
      
      // Simulate first item completion
      (playbackService as any).handleItemComplete();
      
      await waitFor(() => playbackService.getCurrentItem()?.content === 'Item 2');
      
      expect(playbackService.isPlaying()).toBe(true);
      expect(playbackService.getCurrentItem()?.content).toBe('Item 2');
    });

    it('should stop when queue is empty', async () => {
      await playbackService.addToQueue('Last item', 'medium');
      await playbackService.play();
      
      // Simulate item completion
      (playbackService as any).handleItemComplete();
      
      await waitFor(() => !playbackService.isPlaying());
      
      expect(playbackService.isPlaying()).toBe(false);
      expect(playbackService.getCurrentItem()).toBeNull();
    });
  });

  describe('Error Recovery', () => {
    it('should skip failed items', async () => {
      mockMCPClient.synthesizeAudio
        .mockRejectedValueOnce(new Error('Synthesis failed'))
        .mockResolvedValueOnce({
          audio_data: 'base64AudioData',
          format: 'wav',
          duration_ms: 1000
        });
      
      await playbackService.addToQueue('Failing item', 'medium');
      await playbackService.addToQueue('Working item', 'medium');
      
      await playbackService.play();
      
      // Should skip to working item
      await waitFor(() => playbackService.getCurrentItem()?.content === 'Working item');
      
      expect(playbackService.getCurrentItem()?.content).toBe('Working item');
    });

    it('should handle cache errors gracefully', async () => {
      mockCache.get.mockRejectedValue(new Error('Cache read failed'));
      
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      
      // Should fall back to synthesis
      expect(mockMCPClient.synthesizeAudio).toHaveBeenCalled();
    });
  });

  describe('Performance', () => {
    it('should handle large queues efficiently', async () => {
      const startTime = performance.now();
      
      // Add many items
      for (let i = 0; i < 100; i++) {
        await playbackService.addToQueue(`Item ${i}`, 'medium');
      }
      
      const addTime = performance.now() - startTime;
      expect(addTime).toBeLessThan(100); // Should be fast
      
      // Getting queue should also be fast
      const getStartTime = performance.now();
      const queue = playbackService.getQueue();
      const getTime = performance.now() - getStartTime;
      
      expect(getTime).toBeLessThan(10);
      expect(queue).toHaveLength(100);
    });

    it('should not block UI during synthesis', async () => {
      // Make synthesis take some time
      mockMCPClient.synthesizeAudio.mockImplementation(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
        return {
          audio_data: 'base64AudioData',
          format: 'wav',
          duration_ms: 1000
        };
      });
      
      await playbackService.addToQueue('Test content', 'medium');
      
      const playPromise = playbackService.play();
      
      // Should be able to interact while synthesis happens
      expect(playbackService.getQueue()).toHaveLength(1);
      expect(playbackService.getVolume()).toBe(1);
      
      await playPromise;
    });
  });

  describe('Disposal', () => {
    it('should clean up resources', async () => {
      await playbackService.addToQueue('Test content', 'medium');
      await playbackService.play();
      
      playbackService.dispose();
      
      expect(playbackService.isPlaying()).toBe(false);
      expect(playbackService.getQueue()).toHaveLength(0);
      expect(mockStatusBarItem.hide).toHaveBeenCalled();
    });

    it('should cancel ongoing synthesis', async () => {
      const synthesisDeferred = createDeferred<any>();
      
      mockMCPClient.synthesizeAudio.mockReturnValue(synthesisDeferred.promise);
      
      await playbackService.addToQueue('Test content', 'medium');
      const playPromise = playbackService.play();
      
      playbackService.dispose();
      
      synthesisDeferred.resolve({
        audio_data: 'base64AudioData',
        format: 'wav',
        duration_ms: 1000
      });
      
      await playPromise;
      
      expect(playbackService.isPlaying()).toBe(false);
    });
  });
});