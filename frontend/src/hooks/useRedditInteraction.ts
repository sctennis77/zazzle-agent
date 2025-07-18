import { useState, useCallback } from 'react';
import { redditInteractionService } from '../services/redditInteractionService';
import type { 
  RedditInteraction, 
  RedditInteractionMode, 
  RedditInteractionConfig,
  ProductRedditComment,
  ProductSubredditPost
} from '../types/productTypes';

interface UseRedditInteractionOptions {
  mode?: RedditInteractionMode;
  autoSubmit?: boolean;
}

export const useRedditInteraction = (options: UseRedditInteractionOptions = {}) => {
  const { mode = 'comment', autoSubmit = true } = options;
  
  const [interaction, setInteraction] = useState<RedditInteraction | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getInteraction = useCallback(async (productId: string, interactionMode?: RedditInteractionMode) => {
    try {
      setLoading(true);
      setError(null);
      
      const currentMode = interactionMode || mode;
      const result = await redditInteractionService.getProductInteraction(productId, currentMode);
      setInteraction(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : `Failed to fetch ${mode}`;
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [mode]);

  const submitInteraction = useCallback(async (productId: string, config?: Partial<RedditInteractionConfig>) => {
    try {
      setSubmitting(true);
      setError(null);
      
      const finalConfig: RedditInteractionConfig = {
        mode: config?.mode || mode,
        dryRun: config?.dryRun
      };
      
      const result = await redditInteractionService.submitProductInteraction(productId, finalConfig);
      setInteraction(result);
      
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : `Failed to submit ${mode}`;
      setError(errorMessage);
      throw err;
    } finally {
      setSubmitting(false);
    }
  }, [mode]);

  const autoSubmitIfNeeded = useCallback(async (productId: string, config?: Partial<RedditInteractionConfig>) => {
    if (!autoSubmit) return null;
    
    try {
      const currentMode = config?.mode || mode;
      const existingInteraction = await getInteraction(productId, currentMode);
      
      if (!existingInteraction) {
        console.log(`No ${currentMode} found for product ${productId}, auto-submitting...`);
        return await submitInteraction(productId, config);
      } else {
        // Handle dry-run to live mode transition
        const isLiveMode = import.meta.env.VITE_REDDIT_MODE === 'live';
        if (existingInteraction.dry_run && isLiveMode) {
          console.log(`Product ${productId} has dry run ${currentMode}, submitting live version...`);
          return await submitInteraction(productId, { ...config, dryRun: false });
        }
      }
      
      return existingInteraction;
    } catch (err) {
      console.error(`Error in auto-submit logic for product ${productId}:`, err);
      throw err;
    }
  }, [autoSubmit, mode, getInteraction, submitInteraction]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const reset = useCallback(() => {
    setInteraction(null);
    setError(null);
    setSubmitting(false);
    setLoading(false);
  }, []);

  // Type guards for interaction type checking
  const isComment = useCallback((interaction: RedditInteraction | null): interaction is ProductRedditComment => {
    return interaction !== null && 'comment_id' in interaction;
  }, []);

  const isPost = useCallback((interaction: RedditInteraction | null): interaction is ProductSubredditPost => {
    return interaction !== null && 'reddit_post_id' in interaction;
  }, []);

  return {
    // State
    interaction,
    submitting,
    loading,
    error,
    mode,
    
    // Actions
    getInteraction,
    submitInteraction,
    autoSubmitIfNeeded,
    clearError,
    reset,
    
    // Type guards
    isComment,
    isPost,
    
    // Computed properties
    hasInteraction: interaction !== null,
    isDryRun: interaction?.dry_run || false,
    interactionUrl: isComment(interaction) ? interaction.comment_url : isPost(interaction) ? interaction.reddit_post_url : undefined,
    subredditName: interaction?.subreddit_name,
    interactionDate: isComment(interaction) ? interaction.commented_at : isPost(interaction) ? interaction.submitted_at : undefined
  };
};