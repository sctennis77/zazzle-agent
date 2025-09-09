import React, { createContext, useContext, useState, useRef } from 'react';
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

interface DonationContextType {
  getProductsWithDonations: (products: GeneratedProduct[]) => ProductWithFullDonationData[];
  loadDonationData: (products: GeneratedProduct[]) => Promise<void>;
  loading: boolean;
}

const DonationContext = createContext<DonationContextType | null>(null);

export const DonationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [donationCache, setDonationCache] = useState<Map<number, ProductWithFullDonationData>>(new Map());
  const [loading, setLoading] = useState(false);
  const fetchingRef = useRef(false);
  const fetchingIds = useRef<Set<number>>(new Set());

  const getProductsWithDonations = (products: GeneratedProduct[]): ProductWithFullDonationData[] => {
    return products.map(product => {
      const cached = donationCache.get(product.pipeline_run.id);
      if (cached) {
        return cached;
      }
      
      // Return fallback data if not cached
      return {
        ...product,
        totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
        commissionInfo: undefined,
        supportDonations: [],
        donationDataLoaded: false,
      };
    });
  };

  const loadDonationData = async (products: GeneratedProduct[]): Promise<void> => {
    if (fetchingRef.current || loading) {
      console.log('DonationContext: skipping load - already fetching');
      return;
    }

    // Filter out products that are already cached or being fetched
    const productsToFetch = products.filter(p => 
      !donationCache.has(p.pipeline_run.id) && 
      !fetchingIds.current.has(p.pipeline_run.id)
    );

    if (productsToFetch.length === 0) {
      console.log('DonationContext: all products already cached');
      return;
    }

    console.log(`DonationContext: fetching ${productsToFetch.length} products`);
    fetchingRef.current = true;
    setLoading(true);

    // Mark products as being fetched
    productsToFetch.forEach(p => fetchingIds.current.add(p.pipeline_run.id));

    try {
      const BATCH_SIZE = 3;
      const newCacheData = new Map(donationCache);

      for (let i = 0; i < productsToFetch.length; i += BATCH_SIZE) {
        const batch = productsToFetch.slice(i, i + BATCH_SIZE);
        
        const batchPromises = batch.map(async (product) => {
          const maxRetries = 3;
          let retryCount = 0;
          
          while (retryCount < maxRetries) {
            try {
              const response = await fetch(`${API_BASE}/api/products/${product.pipeline_run.id}/donations`, {
                headers: {
                  'Accept': 'application/json',
                  'Cache-Control': 'max-age=300',
                },
              });
              
              if (response.ok) {
                const data: DonationData = await response.json();
                const commissionAmount = data.commission?.donation_amount || 0;
                const supportAmount = data.support?.reduce((sum, d) => sum + (d.donation_amount || 0), 0) || 0;
                
                const productWithDonations: ProductWithFullDonationData = {
                  ...product,
                  totalDonationAmount: commissionAmount + supportAmount,
                  commissionInfo: data.commission || undefined,
                  supportDonations: data.support || [],
                  donationDataLoaded: true,
                };
                
                newCacheData.set(product.pipeline_run.id, productWithDonations);
                return;
              } else if (response.status === 429 || response.status >= 500) {
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
                retryCount++;
                continue;
              } else {
                console.warn(`HTTP ${response.status} for product ${product.product_info.id}: ${response.statusText}`);
                break;
              }
            } catch (error) {
              if (retryCount === maxRetries - 1) {
                console.error(`Error fetching donations for product ${product.product_info.id} after ${maxRetries} attempts:`, error);
                break;
              }
              await new Promise(resolve => setTimeout(resolve, Math.pow(2, retryCount) * 1000));
              retryCount++;
            }
          }
          
          // Add fallback to cache even if fetch failed
          const fallbackProduct: ProductWithFullDonationData = {
            ...product,
            totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
            commissionInfo: undefined,
            supportDonations: [],
            donationDataLoaded: false,
          };
          
          newCacheData.set(product.pipeline_run.id, fallbackProduct);
        });
        
        await Promise.all(batchPromises);
        
        // Update cache after each batch
        setDonationCache(new Map(newCacheData));
        
        // Delay between batches
        if (i + BATCH_SIZE < productsToFetch.length) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
      
    } finally {
      // Clear fetching markers
      productsToFetch.forEach(p => fetchingIds.current.delete(p.pipeline_run.id));
      
      fetchingRef.current = false;
      setLoading(false);
    }
  };

  return (
    <DonationContext.Provider value={{ getProductsWithDonations, loadDonationData, loading }}>
      {children}
    </DonationContext.Provider>
  );
};

export const useDonationContext = () => {
  const context = useContext(DonationContext);
  if (!context) {
    throw new Error('useDonationContext must be used within a DonationProvider');
  }
  return context;
};