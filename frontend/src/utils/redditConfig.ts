import type { RedditInteractionMode } from '../types/productTypes';

interface RedditConfig {
  interactionMode: RedditInteractionMode;
  isDryRun: boolean;
  isLiveMode: boolean;
}

export const getRedditConfig = (): RedditConfig => {
  // Determine interaction mode - defaults to 'comment' for current implementation
  const interactionMode: RedditInteractionMode = 
    (import.meta.env.VITE_REDDIT_INTERACTION_MODE as RedditInteractionMode) || 'comment';
  
  // Determine dry run mode
  const redditMode = import.meta.env.VITE_REDDIT_MODE || 'dryrun';
  const isDryRun = redditMode !== 'live';
  const isLiveMode = redditMode === 'live';

  return {
    interactionMode,
    isDryRun,
    isLiveMode
  };
};

export const redditConfig = getRedditConfig();

// Validation function
export const validateRedditConfig = (): void => {
  const { interactionMode } = redditConfig;
  
  if (!['comment', 'post'].includes(interactionMode)) {
    console.warn(`Invalid VITE_REDDIT_INTERACTION_MODE: ${interactionMode}. Defaulting to 'comment'.`);
  }
  
  console.log(`Reddit configuration: mode=${interactionMode}, live=${redditConfig.isLiveMode}`);
};