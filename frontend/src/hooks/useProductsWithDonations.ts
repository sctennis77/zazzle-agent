import { useState, useEffect, useRef, useMemo } from 'react';
import type { GeneratedProduct } from '../types/productTypes';
import { API_BASE } from '../utils/apiBase';
import { donationApiRateLimiter } from '../utils/rateLimiter';

// Global set to track products being fetched across all hook instances
const globalFetchingIds = new Set<number>();

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
  const loadedProductIds = useRef<Set<number>>(new Set());
  const hookId = useRef(Math.random().toString(36).substr(2, 9));

  useEffect(() => {
    const currentProductIds = products.map(p => p.pipeline_run.id);
    const loadedIds = Array.from(loadedProductIds.current);
    
    console.log(`🔄 [${hookId.current}] useProductsWithDonations effect triggered`, { 
      productsLength: products.length,
      currentProductIds: currentProductIds.slice(0, 3),
      loadedIds: loadedIds.slice(0, 3),
      lazy,
      fetchingRef: fetchingRef.current,
      loading,
      loadedCount: loadedProductIds.current.size,
      allAlreadyLoaded: currentProductIds.every(id => loadedProductIds.current.has(id))
    });
    
    if (products.length === 0) {
      console.log('❌ No products, clearing state');
      setProductsWithDonations([]);
      return;
    }

    // Check if all products have already been loaded successfully
    const allAlreadyLoaded = currentProductIds.every(id => loadedProductIds.current.has(id));
    
    if (allAlreadyLoaded) {
      console.log('✅ useProductsWithDonations: all products already loaded, skipping fetch');
      return;
    }
    
    console.log('🚨 useProductsWithDonations: proceeding with fetch logic');

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
        
        // Only fetch products that haven't been loaded yet
        const productsToFetch = products.filter(p => !loadedProductIds.current.has(p.pipeline_run.id));
        
        console.log('🔍 Filtering products:', {
          totalProducts: products.length,
          productsToFetch: productsToFetch.length,
          productsToFetchIds: productsToFetch.map(p => p.pipeline_run.id).slice(0, 5),
          loadedIds: Array.from(loadedProductIds.current).slice(0, 5)
        });
        
        if (productsToFetch.length === 0) {
          console.log('✅ useProductsWithDonations: no new products to fetch, stopping here');
          fetchingRef.current = false;
          setLoading(false);
          return;
        }
        
        console.log(`🚀 useProductsWithDonations: fetching ${productsToFetch.length} new products`);
        
        for (let i = 0; i < productsToFetch.length; i += BATCH_SIZE) {
          const batch = productsToFetch.slice(i, i + BATCH_SIZE);
          
          const batchPromises = batch.map(async (product) => {
            const productId = product.pipeline_run.id;
            
            // Skip if this product is already being fetched by another hook instance
            if (globalFetchingIds.has(productId)) {
              console.log(`Product ${productId} already being fetched by another instance`);
              return {
                ...product,
                totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
                commissionInfo: undefined,
                supportDonations: [],
                donationDataLoaded: false,
              };
            }
            
            // Mark this product as being fetched
            globalFetchingIds.add(productId);
            
            try {
              // Retry logic with exponential backoff
              const maxRetries = 3;
              let retryCount = 0;
            
            while (retryCount < maxRetries) {
              try {
                const response = await donationApiRateLimiter.execute(() =>
                  fetch(`${API_BASE}/api/products/${product.pipeline_run.id}/donations`, {
                    headers: {
                      'Accept': 'application/json',
                      'Cache-Control': 'max-age=300', // Use cache if available
                    },
                  })
                );
                
                if (response.ok) {
                  const data: DonationData = await response.json();
                  const commissionAmount = data.commission?.donation_amount || 0;
                  const supportAmount = data.support?.reduce((sum, d) => sum + (d.donation_amount || 0), 0) || 0;
                  
                  // Mark this product as successfully loaded
                  loadedProductIds.current.add(productId);
                  console.log(`✅ Marked product ${productId} as loaded. Total loaded: ${loadedProductIds.current.size}`);
                  
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
            } finally {
              // Always clean up the global fetching marker
              globalFetchingIds.delete(productId);
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
          if (i + BATCH_SIZE < productsToFetch.length) {
            await new Promise(resolve => setTimeout(resolve, 500)); // Increased from 100ms to 500ms
          }
        }
        setProductsWithDonations(results);
        fetchingRef.current = false;
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
        fetchingRef.current = false;
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

    // Skip if already being fetched globally
    if (globalFetchingIds.has(pipelineRunId)) {
      console.log(`Product ${pipelineRunId} already being fetched globally`);
      return;
    }

    globalFetchingIds.add(pipelineRunId);

    try {
      // Retry logic with exponential backoff
      const maxRetries = 3;
      let retryCount = 0;
      
      while (retryCount < maxRetries) {
        try {
          const response = await donationApiRateLimiter.execute(() =>
            fetch(`${API_BASE}/api/products/${pipelineRunId}/donations`, {
              headers: {
                'Accept': 'application/json',
                'Cache-Control': 'max-age=300',
              },
            })
          );
          
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
    } finally {
      globalFetchingIds.delete(pipelineRunId);
    }
  };

  return { productsWithDonations, loading, loadProductDonation };
};