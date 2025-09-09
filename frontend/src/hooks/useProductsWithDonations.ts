import { useState, useEffect, useRef, useMemo } from 'react';
import type { GeneratedProduct } from '../types/productTypes';
import { API_BASE } from '../utils/apiBase';
import { donationApiRateLimiter } from '../utils/rateLimiter';

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
  const fetchingRef = useRef(false);

  // Memoize products to prevent unnecessary re-renders from array reference changes
  const memoizedProducts = useMemo(() => products, [JSON.stringify(products.map(p => ({ 
    id: p.pipeline_run.id, 
    donationAmount: p.product_info.donation_info?.donation_amount 
  })))]);

  useEffect(() => {
    console.log('useProductsWithDonations effect triggered', { 
      productsLength: memoizedProducts.length, 
      lazy,
      fetchingRef: fetchingRef.current,
      loading 
    });
    
    if (memoizedProducts.length === 0) {
      setProductsWithDonations([]);
      return;
    }

    // Check if we already have donation data loaded for these products to prevent re-fetching
    const currentProductIds = new Set(memoizedProducts.map(p => p.pipeline_run.id));
    const existingProductIds = new Set(productsWithDonations.map(p => p.pipeline_run.id));
    const hasAllProducts = currentProductIds.size === existingProductIds.size && 
      Array.from(currentProductIds).every(id => existingProductIds.has(id));
    
    if (hasAllProducts && productsWithDonations.some(p => p.donationDataLoaded !== false)) {
      console.log('useProductsWithDonations: skipping fetch - data already loaded');
      return;
    }

    if (lazy) {
      // In lazy mode, just return products with fallback donation amounts
      const productsWithFallback = memoizedProducts.map(product => ({
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
      console.log('fetchDonationData called', { fetchingRef: fetchingRef.current, loading });
      // Prevent multiple simultaneous fetches
      if (fetchingRef.current || loading) {
        console.log('fetchDonationData: skipping - already fetching or loading');
        return;
      }
      
      fetchingRef.current = true;
      setLoading(true);
      try {
        // Fetch donation data with conservative connection throttling 
        const results: ProductWithFullDonationData[] = [];
        const BATCH_SIZE = 3; // Max concurrent requests (reduced from 5)
        
        for (let i = 0; i < memoizedProducts.length; i += BATCH_SIZE) {
          const batch = memoizedProducts.slice(i, i + BATCH_SIZE);
          
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
          
          // Longer delay between batches to be gentle on the server
          if (i + BATCH_SIZE < memoizedProducts.length) {
            await new Promise(resolve => setTimeout(resolve, 500)); // Increased from 100ms to 500ms
          }
        }
        setProductsWithDonations(results);
        fetchingRef.current = false;
      } catch (error) {
        console.error('Error fetching donation data:', error);
        // Fallback to products without donation data
        const fallbackProducts = memoizedProducts.map(product => ({
          ...product,
          totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
          commissionInfo: undefined,
          supportDonations: [],
          donationDataLoaded: false,
        }));
        setProductsWithDonations(fallbackProducts);
      } finally {
        setLoading(false);
        fetchingRef.current = false;
      }
    };

    fetchDonationData();
  }, [memoizedProducts, lazy]);

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