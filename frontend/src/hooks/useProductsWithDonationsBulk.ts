import { useState, useEffect, useRef } from 'react';
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

interface BulkDonationResponse {
  [pipelineRunId: string]: {
    commission?: CommissionInfo;
    support?: SupportDonation[];
  };
}

interface UseProductsWithDonationsOptions {
  lazy?: boolean;
}

export const useProductsWithDonationsBulk = (
  products: GeneratedProduct[], 
  options: UseProductsWithDonationsOptions = {}
) => {
  const { lazy = false } = options;
  const [productsWithDonations, setProductsWithDonations] = useState<ProductWithFullDonationData[]>([]);
  const [loading, setLoading] = useState(false);
  const fetchingRef = useRef(false);
  const loadedRef = useRef(false);

  useEffect(() => {
    console.log('🚀 useProductsWithDonationsBulk effect triggered', { 
      productsLength: products.length, 
      lazy,
      loading,
      alreadyLoaded: loadedRef.current
    });
    
    if (products.length === 0) {
      setProductsWithDonations([]);
      return;
    }

    // If already loaded successfully, don't refetch
    if (loadedRef.current) {
      console.log('✅ Donation data already loaded, skipping fetch');
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

    const fetchBulkDonations = async () => {
      if (fetchingRef.current || loading) {
        console.log('⏸️ Already fetching, skipping');
        return;
      }

      fetchingRef.current = true;
      setLoading(true);

      try {
        const productIds = products.map(p => p.pipeline_run.id);
        console.log(`📡 Fetching bulk donations for ${productIds.length} products`);

        // Split into chunks of 50 (API allows up to 100 but let's be conservative)
        const chunkSize = 50;
        let allDonationData: BulkDonationResponse = {};

        for (let i = 0; i < productIds.length; i += chunkSize) {
          const chunk = productIds.slice(i, i + chunkSize);
          
          const response = await fetch(`${API_BASE}/api/products/donations/bulk`, {
            method: 'POST',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json',
              'Cache-Control': 'max-age=300',
            },
            body: JSON.stringify({ product_ids: chunk }),
          });

          if (response.ok) {
            const chunkData: BulkDonationResponse = await response.json();
            allDonationData = { ...allDonationData, ...chunkData };
          } else {
            console.error(`Failed to fetch bulk donations: ${response.status} ${response.statusText}`);
          }
        }

        // Merge donation data with products
        const productsWithDonationData = products.map(product => {
          const donationData = allDonationData[product.pipeline_run.id.toString()];
          
          if (donationData) {
            const commissionAmount = donationData.commission?.donation_amount || 0;
            const supportAmount = donationData.support?.reduce((sum, d) => sum + (d.donation_amount || 0), 0) || 0;

            return {
              ...product,
              totalDonationAmount: commissionAmount + supportAmount,
              commissionInfo: donationData.commission || undefined,
              supportDonations: donationData.support || [],
              donationDataLoaded: true,
            };
          } else {
            // Fallback for products without donation data
            return {
              ...product,
              totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
              commissionInfo: undefined,
              supportDonations: [],
              donationDataLoaded: false,
            };
          }
        });

        setProductsWithDonations(productsWithDonationData);
        loadedRef.current = true; // Mark as loaded to prevent refetching
        console.log(`✅ Successfully loaded bulk donation data for ${productsWithDonationData.length} products`);

      } catch (error) {
        console.error('❌ Error fetching bulk donation data:', error);
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

    fetchBulkDonations();
  }, [products, lazy]);

  return { productsWithDonations, loading };
};