/**
 * Tests for the Reddit configuration system.
 * 
 * Tests the environment-based configuration and mode switching functionality.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('redditConfig', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
  });

  describe('getRedditConfig', () => {
    it('should return default configuration', async () => {
      // Mock import.meta.env to return default values
      vi.stubGlobal('import', {
        meta: {
          env: {}
        }
      });

      const { getRedditConfig } = await import('../../utils/redditConfig');
      const config = getRedditConfig();

      expect(config.interactionMode).toBe('comment');
      expect(config.isDryRun).toBe(true);
      expect(config.isLiveMode).toBe(false);
    });

    it('should use comment mode from environment', async () => {
      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_INTERACTION_MODE: 'comment',
            VITE_REDDIT_MODE: 'dryrun'
          }
        }
      });

      const { getRedditConfig } = await import('../../utils/redditConfig');
      const config = getRedditConfig();

      expect(config.interactionMode).toBe('comment');
      expect(config.isDryRun).toBe(true);
      expect(config.isLiveMode).toBe(false);
    });

    it('should use post mode from environment', async () => {
      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_INTERACTION_MODE: 'post',
            VITE_REDDIT_MODE: 'live'
          }
        }
      });

      const { getRedditConfig } = await import('../../utils/redditConfig');
      const config = getRedditConfig();

      expect(config.interactionMode).toBe('post');
      expect(config.isDryRun).toBe(false);
      expect(config.isLiveMode).toBe(true);
    });

    it('should handle live mode correctly', async () => {
      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_MODE: 'live'
          }
        }
      });

      const { getRedditConfig } = await import('../../utils/redditConfig');
      const config = getRedditConfig();

      expect(config.isDryRun).toBe(false);
      expect(config.isLiveMode).toBe(true);
    });

    it('should treat any non-live mode as dry run', async () => {
      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_MODE: 'dryrun'
          }
        }
      });

      const { getRedditConfig } = await import('../../utils/redditConfig');
      const config = getRedditConfig();

      expect(config.isDryRun).toBe(true);
      expect(config.isLiveMode).toBe(false);
    });

    it('should default to dry run when VITE_REDDIT_MODE is not set', async () => {
      vi.stubGlobal('import', {
        meta: {
          env: {}
        }
      });

      const { getRedditConfig } = await import('../../utils/redditConfig');
      const config = getRedditConfig();

      expect(config.isDryRun).toBe(true);
      expect(config.isLiveMode).toBe(false);
    });
  });

  describe('validateRedditConfig', () => {
    it('should log valid configuration', async () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_INTERACTION_MODE: 'comment',
            VITE_REDDIT_MODE: 'live'
          }
        }
      });

      const { validateRedditConfig } = await import('../../utils/redditConfig');
      validateRedditConfig();

      expect(consoleSpy).toHaveBeenCalledWith(
        'Reddit configuration: mode=comment, live=true'
      );

      consoleSpy.mockRestore();
    });

    it('should warn about invalid interaction mode', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const consoleLogSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_INTERACTION_MODE: 'invalid_mode'
          }
        }
      });

      const { validateRedditConfig } = await import('../../utils/redditConfig');
      validateRedditConfig();

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Invalid VITE_REDDIT_INTERACTION_MODE: invalid_mode. Defaulting to \'comment\'.'
      );

      consoleWarnSpy.mockRestore();
      consoleLogSpy.mockRestore();
    });

    it('should not warn about valid interaction modes', async () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const consoleLogSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

      // Test comment mode
      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_INTERACTION_MODE: 'comment'
          }
        }
      });

      let { validateRedditConfig } = await import('../../utils/redditConfig');
      validateRedditConfig();

      expect(consoleWarnSpy).not.toHaveBeenCalledWith(
        expect.stringContaining('Invalid VITE_REDDIT_INTERACTION_MODE')
      );

      // Reset and test post mode
      vi.resetModules();
      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_INTERACTION_MODE: 'post'
          }
        }
      });

      ({ validateRedditConfig } = await import('../../utils/redditConfig'));
      validateRedditConfig();

      expect(consoleWarnSpy).not.toHaveBeenCalledWith(
        expect.stringContaining('Invalid VITE_REDDIT_INTERACTION_MODE')
      );

      consoleWarnSpy.mockRestore();
      consoleLogSpy.mockRestore();
    });
  });

  describe('redditConfig export', () => {
    it('should export the configuration object', async () => {
      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_INTERACTION_MODE: 'comment',
            VITE_REDDIT_MODE: 'dryrun'
          }
        }
      });

      const { redditConfig } = await import('../../utils/redditConfig');

      expect(redditConfig).toEqual({
        interactionMode: 'comment',
        isDryRun: true,
        isLiveMode: false
      });
    });
  });

  describe('Edge cases', () => {
    it('should handle undefined environment variables gracefully', async () => {
      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_INTERACTION_MODE: undefined,
            VITE_REDDIT_MODE: undefined
          }
        }
      });

      const { getRedditConfig } = await import('../../utils/redditConfig');
      const config = getRedditConfig();

      expect(config.interactionMode).toBe('comment'); // Default
      expect(config.isDryRun).toBe(true); // Default when not 'live'
      expect(config.isLiveMode).toBe(false);
    });

    it('should handle empty string environment variables', async () => {
      vi.stubGlobal('import', {
        meta: {
          env: {
            VITE_REDDIT_INTERACTION_MODE: '',
            VITE_REDDIT_MODE: ''
          }
        }
      });

      const { getRedditConfig } = await import('../../utils/redditConfig');
      const config = getRedditConfig();

      expect(config.interactionMode).toBe('comment'); // Default
      expect(config.isDryRun).toBe(true); // Default when not 'live'
      expect(config.isLiveMode).toBe(false);
    });
  });
});