/**
 * Simple rate limiter to throttle API requests
 */
class RateLimiter {
  private queue: Array<() => void> = [];
  private running = false;
  private minInterval: number;

  constructor(requestsPerSecond: number = 2) {
    this.minInterval = 1000 / requestsPerSecond; // Convert to milliseconds between requests
  }

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const result = await fn();
          resolve(result);
        } catch (error) {
          reject(error);
        }
      });

      this.processQueue();
    });
  }

  private async processQueue() {
    if (this.running || this.queue.length === 0) {
      return;
    }

    this.running = true;

    while (this.queue.length > 0) {
      const nextRequest = this.queue.shift();
      if (nextRequest) {
        await nextRequest();
        
        // Wait before processing next request
        if (this.queue.length > 0) {
          await new Promise(resolve => setTimeout(resolve, this.minInterval));
        }
      }
    }

    this.running = false;
  }
}

// Global rate limiter instance - 2 requests per second max
export const donationApiRateLimiter = new RateLimiter(2);