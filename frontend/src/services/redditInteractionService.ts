import axios from 'axios';
import type { 
  ProductSubredditPost, 
  ProductRedditComment, 
  RedditInteraction,
  RedditInteractionMode,
  RedditInteractionConfig
} from '../types/productTypes';
import { API_BASE } from '../utils/apiBase';

const REDDIT_API_BASE = `${API_BASE}/api/reddit`;

export const redditInteractionService = {
  /**
   * Comment-specific methods
   */
  async getProductComment(productId: string): Promise<ProductRedditComment | null> {
    try {
      const response = await axios.get<ProductRedditComment>(
        `${REDDIT_API_BASE}/product/${productId}/comment`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null; // No comment exists yet
      }
      throw error;
    }
  },

  async submitProductComment(productId: string, dryRun?: boolean): Promise<ProductRedditComment> {
    const params = dryRun !== undefined ? { dry_run: dryRun } : {};
    const response = await axios.post<ProductRedditComment>(
      `${REDDIT_API_BASE}/product/${productId}/comment`,
      null,
      { params }
    );
    return response.data;
  },

  /**
   * Post-specific methods
   */
  async getProductPost(productId: string): Promise<ProductSubredditPost | null> {
    try {
      const response = await axios.get<ProductSubredditPost>(
        `${REDDIT_API_BASE}/product/${productId}/post`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null; // No post exists yet
      }
      throw error;
    }
  },

  async submitProductPost(productId: string, dryRun?: boolean): Promise<ProductSubredditPost> {
    const params = dryRun !== undefined ? { dry_run: dryRun } : {};
    const response = await axios.post<ProductSubredditPost>(
      `${REDDIT_API_BASE}/product/${productId}/post`,
      null,
      { params }
    );
    return response.data;
  },

  /**
   * Unified methods with mode parameter
   */
  async getProductInteraction(productId: string, mode: RedditInteractionMode): Promise<RedditInteraction | null> {
    switch (mode) {
      case 'comment':
        return this.getProductComment(productId);
      case 'post':
        return this.getProductPost(productId);
      default:
        throw new Error(`Invalid Reddit interaction mode: ${mode}`);
    }
  },

  async submitProductInteraction(productId: string, config: RedditInteractionConfig): Promise<RedditInteraction> {
    const { mode, dryRun } = config;
    switch (mode) {
      case 'comment':
        return this.submitProductComment(productId, dryRun);
      case 'post':
        return this.submitProductPost(productId, dryRun);
      default:
        throw new Error(`Invalid Reddit interaction mode: ${mode}`);
    }
  }
};

// Legacy compatibility - maps old publishService calls to new comment-based API
export const publishService = {
  /**
   * @deprecated Use redditInteractionService.submitProductComment instead
   */
  async publishProduct(productId: string, dryRun?: boolean): Promise<ProductRedditComment> {
    console.warn('publishService.publishProduct is deprecated. Use redditInteractionService.submitProductComment instead.');
    return redditInteractionService.submitProductComment(productId, dryRun);
  },

  /**
   * @deprecated Use redditInteractionService.getProductComment instead
   */
  async getProductSubredditPost(productId: string): Promise<ProductRedditComment | null> {
    console.warn('publishService.getProductSubredditPost is deprecated. Use redditInteractionService.getProductComment instead.');
    return redditInteractionService.getProductComment(productId);
  }
};