import { useState, useEffect } from 'react';
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

interface UseProductsWithDonationsOptions {
  lazy?: boolean; // If true, only load fallback data initially
}

export const useProductsWithDonations = (
  products: GeneratedProduct[], 
  options: UseProductsWithDonationsOptions = {}
) => {
  const { lazy = false } = options;
  const [productsWithDonations, setProductsWithDonations] = useState<ProductWithFullDonationData[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (products.length === 0) {
      setProductsWithDonations([]);
      return;
    }

    if (lazy) {
      // In lazy mode, just return products with fallback donation amounts
      const productsWithFallback = products.map(product => ({
        ...product,
        totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
        commissionInfo: undefined,
        supportDonations: [],
        donationDataLoaded: false,
      }));
      setProductsWithDonations(productsWithFallback);
      return;
    }

    const fetchDonationData = async () => {
      setLoading(true);
      try {
        // Fetch donation data with connection throttling (max 5 concurrent)
        const results: ProductWithFullDonationData[] = [];
        const BATCH_SIZE = 5; // Max concurrent requests
        
        for (let i = 0; i < products.length; i += BATCH_SIZE) {
          const batch = products.slice(i, i + BATCH_SIZE);
          
          const batchPromises = batch.map(async (product) => {
            // Retry logic with exponential backoff
            const maxRetries = 3;
            let retryCount = 0;
            
            while (retryCount < maxRetries) {
              try {
                const response = await fetch(`${API_BASE}/api/products/${product.pipeline_run.id}/donations`, {
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
            
            // Fallback to commission amount from product data
            return {
              ...product,
              totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
              commissionInfo: undefined,
              supportDonations: [],
              donationDataLoaded: false,
            };
          });
          
          const batchResults = await Promise.all(batchPromises);
          results.push(...batchResults);
          
          // Small delay between batches to be gentle on the server
          if (i + BATCH_SIZE < products.length) {
            await new Promise(resolve => setTimeout(resolve, 100));
          }
        }
        setProductsWithDonations(results);
      } catch (error) {
        console.error('Error fetching donation data:', error);
        // Fallback to products without donation data
        const fallbackProducts = products.map(product => ({
          ...product,
          totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
          commissionInfo: undefined,
          supportDonations: [],
          donationDataLoaded: false,
        }));
        setProductsWithDonations(fallbackProducts);
      } finally {
        setLoading(false);
      }
    };

    fetchDonationData();
  }, [products, lazy]);

  // Function to load donation data for a specific product (for lazy loading)
  const loadProductDonation = async (pipelineRunId: number): Promise<void> => {
    const productIndex = productsWithDonations.findIndex(p => p.pipeline_run.id === pipelineRunId);
    if (productIndex === -1 || productsWithDonations[productIndex].donationDataLoaded) {
      return;
    }

    try {
      // Retry logic with exponential backoff
      const maxRetries = 3;
      let retryCount = 0;
      
      while (retryCount < maxRetries) {
        try {
          const response = await fetch(`${API_BASE}/api/products/${pipelineRunId}/donations`, {
            headers: {
              'Accept': 'application/json',
              'Cache-Control': 'max-age=300',
            },
          });
          
          if (response.ok) {
            const data: DonationData = await response.json();
            const commissionAmount = data.commission?.donation_amount || 0;
            const supportAmount = data.support?.reduce((sum, d) => sum + (d.donation_amount || 0), 0) || 0;
            
            // Update the specific product in the array
            setProductsWithDonations(prev => prev.map(product => 
              product.pipeline_run.id === pipelineRunId 
                ? {
                    ...product,
                    totalDonationAmount: commissionAmount + supportAmount,
                    commissionInfo: data.commission || undefined,
                    supportDonations: data.support || [],
                    donationDataLoaded: true,
                  }
                : product
            ));
            return;
          } else if (response.status === 429 || response.status >= 500) {
            // Rate limited or server error - retry
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
            retryCount++;
            continue;
          } else {
            // Client error (4xx) - don't retry
            console.warn(`HTTP ${response.status} for product ${pipelineRunId}: ${response.statusText}`);
            break;
          }
        } catch (error) {
          if (retryCount === maxRetries - 1) {
            console.error(`Error fetching donations for product ${pipelineRunId} after ${maxRetries} attempts:`, error);
            break;
          }
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
          retryCount++;
        }
      }
    } catch (error) {
      console.error(`Error loading donation data for product ${pipelineRunId}:`, error);
    }
  };

  return { productsWithDonations, loading, loadProductDonation };
};