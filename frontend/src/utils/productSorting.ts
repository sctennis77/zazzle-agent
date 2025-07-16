import type { GeneratedProduct } from '../types/productTypes';
import type { ProductWithFullDonationData } from '../hooks/useProductsWithDonations';

export interface ProductWithDonationTotal extends GeneratedProduct {
  _totalDonationAmount?: number;
}

export const sortProducts = (
  products: ProductWithFullDonationData[],
  sortBy: string
): ProductWithFullDonationData[] => {
  switch (sortBy) {
    case 'time-desc':
      return [...products].sort((a, b) => {
        const dateA = new Date(a.pipeline_run.end_time || a.pipeline_run.start_time);
        const dateB = new Date(b.pipeline_run.end_time || b.pipeline_run.start_time);
        return dateB.getTime() - dateA.getTime();
      });
    
    case 'donation-desc':
      return [...products].sort((a, b) => {
        // Primary sort by donation amount
        const donationDiff = b.totalDonationAmount - a.totalDonationAmount;
        if (donationDiff !== 0) return donationDiff;
        
        // Secondary sort by time (newest first) for products with same donation amount
        const dateA = new Date(a.pipeline_run.end_time || a.pipeline_run.start_time);
        const dateB = new Date(b.pipeline_run.end_time || b.pipeline_run.start_time);
        return dateB.getTime() - dateA.getTime();
      });
    
    default:
      // Default to time descending (newest first)
      return [...products].sort((a, b) => {
        const dateA = new Date(a.pipeline_run.end_time || a.pipeline_run.start_time);
        const dateB = new Date(b.pipeline_run.end_time || b.pipeline_run.start_time);
        return dateB.getTime() - dateA.getTime();
      });
  }
};

export const filterProductsBySubreddits = (
  products: ProductWithFullDonationData[],
  selectedSubreddits: string[]
): ProductWithFullDonationData[] => {
  if (selectedSubreddits.length === 0) {
    return products;
  }
  
  return products.filter(product => 
    selectedSubreddits.includes(product.reddit_post.subreddit)
  );
};

export const getUniqueSubreddits = (products: GeneratedProduct[]): string[] => {
  const subreddits = products.map(product => product.reddit_post.subreddit);
  return Array.from(new Set(subreddits)).sort();
};