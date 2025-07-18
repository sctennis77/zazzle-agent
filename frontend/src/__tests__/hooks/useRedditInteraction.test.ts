/**
 * Tests for the useRedditInteraction hook.
 * 
 * Tests the clean comment vs post separation and auto-submission logic.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useRedditInteraction } from '../../hooks/useRedditInteraction';
import { redditInteractionService } from '../../services/redditInteractionService';
import type { ProductRedditComment, ProductSubredditPost } from '../../types/productTypes';

// Mock the service
vi.mock('../../services/redditInteractionService');
const mockedService = vi.mocked(redditInteractionService);

// Mock environment variables
vi.mock('../../utils/redditConfig', () => ({
  redditConfig: {
    interactionMode: 'comment',
    isDryRun: true,
    isLiveMode: false
  }
}));

const mockComment: ProductRedditComment = {
  id: 1,
  product_info_id: 123,
  original_post_id: 'test123',
  comment_id: 'comment456',
  comment_url: 'https://reddit.com/r/test/comments/test123/comment456',
  subreddit_name: 'test',
  commented_at: '2024-01-01T12:00:00Z',
  comment_content: 'Test comment',
  dry_run: true,
  status: 'success'
};

const mockPost: ProductSubredditPost = {
  id: 1,
  product_info_id: 123,
  subreddit_name: 'clouvel',
  reddit_post_id: 'post789',
  reddit_post_url: 'https://reddit.com/r/clouvel/comments/post789',
  reddit_post_title: 'Test Post',
  submitted_at: '2024-01-01T12:00:00Z',
  dry_run: false,
  status: 'success'
};

describe('useRedditInteraction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic functionality', () => {
    it('should initialize with default values', () => {
      const { result } = renderHook(() => useRedditInteraction());

      expect(result.current.interaction).toBeNull();
      expect(result.current.submitting).toBe(false);
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.mode).toBe('comment');
      expect(result.current.hasInteraction).toBe(false);
    });

    it('should initialize with custom mode', () => {
      const { result } = renderHook(() => useRedditInteraction({ mode: 'post' }));

      expect(result.current.mode).toBe('post');
    });

    it('should initialize with autoSubmit disabled', () => {
      const { result } = renderHook(() => useRedditInteraction({ autoSubmit: false }));

      // We can't directly test autoSubmit, but we can test that it's passed to the hook
      expect(result.current.mode).toBe('comment'); // Default mode
    });
  });

  describe('getInteraction', () => {
    it('should fetch comment successfully', async () => {
      mockedService.getProductInteraction.mockResolvedValue(mockComment);

      const { result } = renderHook(() => useRedditInteraction());

      await waitFor(async () => {
        const interaction = await result.current.getInteraction('123');
        expect(interaction).toEqual(mockComment);
      });

      expect(result.current.interaction).toEqual(mockComment);
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(mockedService.getProductInteraction).toHaveBeenCalledWith('123', 'comment');
    });

    it('should handle fetch error', async () => {
      const error = new Error('Network error');
      mockedService.getProductInteraction.mockRejectedValue(error);

      const { result } = renderHook(() => useRedditInteraction());

      await waitFor(async () => {
        try {
          await result.current.getInteraction('123');
        } catch (e) {
          // Expected to throw
        }
      });

      expect(result.current.error).toBe('Network error');
      expect(result.current.loading).toBe(false);
    });

    it('should use custom mode when provided', async () => {
      mockedService.getProductInteraction.mockResolvedValue(mockPost);

      const { result } = renderHook(() => useRedditInteraction({ mode: 'comment' }));

      await waitFor(async () => {
        await result.current.getInteraction('123', 'post');
      });

      expect(mockedService.getProductInteraction).toHaveBeenCalledWith('123', 'post');
    });
  });

  describe('submitInteraction', () => {
    it('should submit comment successfully', async () => {
      mockedService.submitProductInteraction.mockResolvedValue(mockComment);

      const { result } = renderHook(() => useRedditInteraction());

      await waitFor(async () => {
        const interaction = await result.current.submitInteraction('123');
        expect(interaction).toEqual(mockComment);
      });

      expect(result.current.interaction).toEqual(mockComment);
      expect(result.current.submitting).toBe(false);
      expect(result.current.error).toBeNull();
      expect(mockedService.submitProductInteraction).toHaveBeenCalledWith('123', {
        mode: 'comment',
        dryRun: undefined
      });
    });

    it('should submit with custom config', async () => {
      mockedService.submitProductInteraction.mockResolvedValue(mockPost);

      const { result } = renderHook(() => useRedditInteraction({ mode: 'comment' }));

      await waitFor(async () => {
        await result.current.submitInteraction('123', { mode: 'post', dryRun: false });
      });

      expect(mockedService.submitProductInteraction).toHaveBeenCalledWith('123', {
        mode: 'post',
        dryRun: false
      });
    });

    it('should handle submit error', async () => {
      const error = new Error('Submit failed');
      mockedService.submitProductInteraction.mockRejectedValue(error);

      const { result } = renderHook(() => useRedditInteraction());

      await waitFor(async () => {
        try {
          await result.current.submitInteraction('123');
        } catch (e) {
          // Expected to throw
        }
      });

      expect(result.current.error).toBe('Submit failed');
      expect(result.current.submitting).toBe(false);
    });
  });

  describe('autoSubmitIfNeeded', () => {
    it('should not auto-submit when autoSubmit is disabled', async () => {
      const { result } = renderHook(() => useRedditInteraction({ autoSubmit: false }));

      const interaction = await result.current.autoSubmitIfNeeded('123');

      expect(interaction).toBeNull();
      expect(mockedService.getProductInteraction).not.toHaveBeenCalled();
      expect(mockedService.submitProductInteraction).not.toHaveBeenCalled();
    });

    it('should submit when no existing interaction', async () => {
      mockedService.getProductInteraction.mockResolvedValue(null);
      mockedService.submitProductInteraction.mockResolvedValue(mockComment);

      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

      const { result } = renderHook(() => useRedditInteraction({ autoSubmit: true }));

      await waitFor(async () => {
        const interaction = await result.current.autoSubmitIfNeeded('123');
        expect(interaction).toEqual(mockComment);
      });

      expect(consoleSpy).toHaveBeenCalledWith('No comment found for product 123, auto-submitting...');
      expect(mockedService.getProductInteraction).toHaveBeenCalledWith('123', 'comment');
      expect(mockedService.submitProductInteraction).toHaveBeenCalledWith('123', {
        mode: 'comment',
        dryRun: undefined
      });

      consoleSpy.mockRestore();
    });

    it('should not submit when interaction already exists', async () => {
      mockedService.getProductInteraction.mockResolvedValue(mockComment);

      const { result } = renderHook(() => useRedditInteraction({ autoSubmit: true }));

      await waitFor(async () => {
        const interaction = await result.current.autoSubmitIfNeeded('123');
        expect(interaction).toEqual(mockComment);
      });

      expect(mockedService.getProductInteraction).toHaveBeenCalledWith('123', 'comment');
      expect(mockedService.submitProductInteraction).not.toHaveBeenCalled();
    });
  });

  describe('Type guards', () => {
    it('should identify comment correctly', () => {
      const { result } = renderHook(() => useRedditInteraction());

      expect(result.current.isComment(mockComment)).toBe(true);
      expect(result.current.isComment(mockPost)).toBe(false);
      expect(result.current.isComment(null)).toBe(false);
    });

    it('should identify post correctly', () => {
      const { result } = renderHook(() => useRedditInteraction());

      expect(result.current.isPost(mockPost)).toBe(true);
      expect(result.current.isPost(mockComment)).toBe(false);
      expect(result.current.isPost(null)).toBe(false);
    });
  });

  describe('Computed properties', () => {
    it('should compute properties for comment', () => {
      const { result } = renderHook(() => useRedditInteraction());

      // Manually set the interaction to test computed properties
      result.current.interaction = mockComment;

      expect(result.current.hasInteraction).toBe(true);
      expect(result.current.isDryRun).toBe(true);
      expect(result.current.interactionUrl).toBe(mockComment.comment_url);
      expect(result.current.subredditName).toBe(mockComment.subreddit_name);
      expect(result.current.interactionDate).toBe(mockComment.commented_at);
    });

    it('should compute properties for post', () => {
      const { result } = renderHook(() => useRedditInteraction());

      // Manually set the interaction to test computed properties
      result.current.interaction = mockPost;

      expect(result.current.hasInteraction).toBe(true);
      expect(result.current.isDryRun).toBe(false);
      expect(result.current.interactionUrl).toBe(mockPost.reddit_post_url);
      expect(result.current.subredditName).toBe(mockPost.subreddit_name);
      expect(result.current.interactionDate).toBe(mockPost.submitted_at);
    });

    it('should handle null interaction', () => {
      const { result } = renderHook(() => useRedditInteraction());

      expect(result.current.hasInteraction).toBe(false);
      expect(result.current.isDryRun).toBe(false);
      expect(result.current.interactionUrl).toBeUndefined();
      expect(result.current.subredditName).toBeUndefined();
      expect(result.current.interactionDate).toBeUndefined();
    });
  });

  describe('Utility methods', () => {
    it('should clear error', () => {
      const { result } = renderHook(() => useRedditInteraction());

      // Manually set error
      result.current.error = 'Test error';
      
      result.current.clearError();

      expect(result.current.error).toBeNull();
    });

    it('should reset state', () => {
      const { result } = renderHook(() => useRedditInteraction());

      // Manually set some state
      result.current.interaction = mockComment;
      result.current.error = 'Test error';

      result.current.reset();

      expect(result.current.interaction).toBeNull();
      expect(result.current.error).toBeNull();
      expect(result.current.submitting).toBe(false);
      expect(result.current.loading).toBe(false);
    });
  });
});