/**
 * Tests for the new Reddit interaction service.
 * 
 * Tests the clean comment vs post separation introduced in the Reddit interaction refactor.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { redditInteractionService, publishService } from '../../services/redditInteractionService';
import type { ProductRedditComment, ProductSubredditPost } from '../../types/productTypes';

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    isAxiosError: vi.fn(),
  }
}));

const mockedAxios = {
  get: vi.mocked(axios.get),
  post: vi.mocked(axios.post),
  isAxiosError: vi.mocked(axios.isAxiosError)
};

// Mock API_BASE
vi.mock('../../utils/apiBase', () => ({
  API_BASE: 'http://localhost:8000'
}));

describe('redditInteractionService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

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
    status: 'success',
    error_message: undefined,
    engagement_data: undefined
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
    status: 'success',
    error_message: undefined,
    engagement_data: undefined
  };

  describe('Comment methods', () => {
    describe('getProductComment', () => {
      it('should return comment when it exists', async () => {
        mockedAxios.get.mockResolvedValue({ data: mockComment });

        const result = await redditInteractionService.getProductComment('123');

        expect(result).toEqual(mockComment);
        expect(mockedAxios.get).toHaveBeenCalledWith(
          'http://localhost:8000/api/reddit/product/123/comment'
        );
      });

      it('should return null when comment does not exist (404)', async () => {
        const error = { isAxiosError: true, response: { status: 404 } };
        mockedAxios.get.mockRejectedValue(error);
        mockedAxios.isAxiosError.mockReturnValue(true);

        const result = await redditInteractionService.getProductComment('123');

        expect(result).toBeNull();
      });

      it('should throw error for non-404 errors', async () => {
        const error = { isAxiosError: true, response: { status: 500 } };
        mockedAxios.get.mockRejectedValue(error);
        mockedAxios.isAxiosError.mockReturnValue(true);

        await expect(redditInteractionService.getProductComment('123'))
          .rejects.toEqual(error);
      });
    });

    describe('submitProductComment', () => {
      it('should submit comment successfully', async () => {
        mockedAxios.post.mockResolvedValue({ data: mockComment });

        const result = await redditInteractionService.submitProductComment('123', true);

        expect(result).toEqual(mockComment);
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'http://localhost:8000/api/reddit/product/123/comment',
          null,
          { params: { dry_run: true } }
        );
      });

      it('should submit comment without dry_run parameter when undefined', async () => {
        mockedAxios.post.mockResolvedValue({ data: mockComment });

        await redditInteractionService.submitProductComment('123');

        expect(mockedAxios.post).toHaveBeenCalledWith(
          'http://localhost:8000/api/reddit/product/123/comment',
          null,
          { params: {} }
        );
      });
    });
  });

  describe('Post methods', () => {
    describe('getProductPost', () => {
      it('should return post when it exists', async () => {
        mockedAxios.get.mockResolvedValue({ data: mockPost });

        const result = await redditInteractionService.getProductPost('123');

        expect(result).toEqual(mockPost);
        expect(mockedAxios.get).toHaveBeenCalledWith(
          'http://localhost:8000/api/reddit/product/123/post'
        );
      });

      it('should return null when post does not exist (404)', async () => {
        const error = { isAxiosError: true, response: { status: 404 } };
        mockedAxios.get.mockRejectedValue(error);
        mockedAxios.isAxiosError.mockReturnValue(true);

        const result = await redditInteractionService.getProductPost('123');

        expect(result).toBeNull();
      });
    });

    describe('submitProductPost', () => {
      it('should submit post successfully', async () => {
        mockedAxios.post.mockResolvedValue({ data: mockPost });

        const result = await redditInteractionService.submitProductPost('123', false);

        expect(result).toEqual(mockPost);
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'http://localhost:8000/api/reddit/product/123/post',
          null,
          { params: { dry_run: false } }
        );
      });
    });
  });

  describe('Unified methods', () => {
    describe('getProductInteraction', () => {
      it('should call getProductComment for comment mode', async () => {
        const spy = vi.spyOn(redditInteractionService, 'getProductComment').mockResolvedValue(mockComment);

        const result = await redditInteractionService.getProductInteraction('123', 'comment');

        expect(result).toEqual(mockComment);
        expect(spy).toHaveBeenCalledWith('123');
      });

      it('should call getProductPost for post mode', async () => {
        const spy = vi.spyOn(redditInteractionService, 'getProductPost').mockResolvedValue(mockPost);

        const result = await redditInteractionService.getProductInteraction('123', 'post');

        expect(result).toEqual(mockPost);
        expect(spy).toHaveBeenCalledWith('123');
      });

      it('should throw error for invalid mode', async () => {
        await expect(redditInteractionService.getProductInteraction('123', 'invalid' as any))
          .rejects.toThrow('Invalid Reddit interaction mode: invalid');
      });
    });

    describe('submitProductInteraction', () => {
      it('should call submitProductComment for comment mode', async () => {
        const spy = vi.spyOn(redditInteractionService, 'submitProductComment').mockResolvedValue(mockComment);

        const result = await redditInteractionService.submitProductInteraction('123', {
          mode: 'comment',
          dryRun: true
        });

        expect(result).toEqual(mockComment);
        expect(spy).toHaveBeenCalledWith('123', true);
      });

      it('should call submitProductPost for post mode', async () => {
        const spy = vi.spyOn(redditInteractionService, 'submitProductPost').mockResolvedValue(mockPost);

        const result = await redditInteractionService.submitProductInteraction('123', {
          mode: 'post',
          dryRun: false
        });

        expect(result).toEqual(mockPost);
        expect(spy).toHaveBeenCalledWith('123', false);
      });
    });
  });
});

describe('publishService (legacy compatibility)', () => {
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
    status: 'success',
    error_message: undefined,
    engagement_data: undefined
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock console.warn to avoid test output noise
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  describe('publishProduct (deprecated)', () => {
    it('should call redditInteractionService.submitProductComment', async () => {
      const spy = vi.spyOn(redditInteractionService, 'submitProductComment').mockResolvedValue(mockComment);

      const result = await publishService.publishProduct('123', true);

      expect(result).toEqual(mockComment);
      expect(spy).toHaveBeenCalledWith('123', true);
      expect(console.warn).toHaveBeenCalledWith(
        'publishService.publishProduct is deprecated. Use redditInteractionService.submitProductComment instead.'
      );
    });
  });

  describe('getProductSubredditPost (deprecated)', () => {
    it('should call redditInteractionService.getProductComment', async () => {
      const spy = vi.spyOn(redditInteractionService, 'getProductComment').mockResolvedValue(mockComment);

      const result = await publishService.getProductSubredditPost('123');

      expect(result).toEqual(mockComment);
      expect(spy).toHaveBeenCalledWith('123');
      expect(console.warn).toHaveBeenCalledWith(
        'publishService.getProductSubredditPost is deprecated. Use redditInteractionService.getProductComment instead.'
      );
    });
  });
});