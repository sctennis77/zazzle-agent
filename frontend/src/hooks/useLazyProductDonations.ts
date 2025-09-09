import { useState, useCallback } from 'react';
import type { GeneratedProduct } from '../types/productTypes';
import { API_BASE } from '../utils/apiBase';

interface CommissionInfo {
  donation_amount: number;
  reddit_username: string;
  is_anonymous: boolean;
  [key: string]: unknown;
}

interface SupportDonation {
  donation_amount: number;
  [key: string]: unknown;
}

export interface ProductWithFullDonationData extends GeneratedProduct {
  totalDonationAmount: number;
  commissionInfo?: CommissionInfo;
  supportDonations?: SupportDonation[];
  donationDataLoaded?: boolean;
}

interface DonationData {
  commission?: CommissionInfo;
  support?: SupportDonation[];
}

export const useLazyProductDonations = () => {
  const [loadingProducts, setLoadingProducts] = useState<Set<number>>(new Set());

  const loadDonationData = useCallback(async (product: GeneratedProduct): Promise<ProductWithFullDonationData> => {
    const pipelineRunId = product.pipeline_run.id;
    
    // Skip if already loading
    if (loadingProducts.has(pipelineRunId)) {
      return {
        ...product,
        totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
        donationDataLoaded: false,
      };
    }

    setLoadingProducts(prev => new Set(prev).add(pipelineRunId));

    try {
      // Retry logic with exponential backoff
      const maxRetries = 3;
      let retryCount = 0;
      
      while (retryCount < maxRetries) {
        try {
          const response = await fetch(`${API_BASE}/api/products/${pipelineRunId}/donations`, {
            headers: {
              'Accept': 'application/json',
              'Cache-Control': 'max-age=300', // Use cache if available
            },
          });
          
          if (response.ok) {
            const data: DonationData = await response.json();
            const commissionAmount = data.commission?.donation_amount || 0;
            const supportAmount = data.support?.reduce((sum, d) => sum + (d.donation_amount || 0), 0) || 0;
            
            return {
              ...product,
              totalDonationAmount: commissionAmount + supportAmount,
              commissionInfo: data.commission || undefined,
              supportDonations: data.support || [],
              donationDataLoaded: true,
            };
          } else if (response.status === 429) {
            // Rate limited - wait before retry
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
            retryCount++;
            continue;
          } else if (response.status >= 500) {
            // Server error - retry
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
            retryCount++;
            continue;
          } else {
            // Client error (4xx) - don't retry
            console.warn(`HTTP ${response.status} for product ${product.product_info.id}: ${response.statusText}`);
            break;
          }
        } catch (error) {
          if (retryCount === maxRetries - 1) {
            console.error(`Error fetching donations for product ${product.product_info.id} after ${maxRetries} attempts:`, error);
            break;
          }
          // Wait before retry
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
          retryCount++;
        }
      }
    } catch (error) {
      console.error(`Error loading donation data for product ${product.product_info.id}:`, error);
    } finally {
      setLoadingProducts(prev => {
        const newSet = new Set(prev);
        newSet.delete(pipelineRunId);
        return newSet;
      });
    }

    // Fallback to commission amount from product data
    return {
      ...product,
      totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
      commissionInfo: undefined,
      supportDonations: [],
      donationDataLoaded: false,
    };
  }, [loadingProducts]);

  return {
    loadDonationData,
    isLoading: (productId: number) => loadingProducts.has(productId),
  };
};