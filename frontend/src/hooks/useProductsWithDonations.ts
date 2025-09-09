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
}

interface BulkDonationResponse {
  [pipelineRunId: string]: {
    commission?: CommissionInfo;
    support?: SupportDonation[];
  };
}

export const useProductsWithDonations = (products: GeneratedProduct[]) => {
  const [productsWithDonations, setProductsWithDonations] = useState<ProductWithFullDonationData[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (products.length === 0) {
      setProductsWithDonations([]);
      return;
    }

    const fetchBulkDonations = async () => {
      setLoading(true);

      try {
        const productIds = products.map(p => p.pipeline_run.id);

        // Split into chunks of 50 to stay within reasonable limits
        const chunkSize = 50;
        let allDonationData: BulkDonationResponse = {};

        for (let i = 0; i < productIds.length; i += chunkSize) {
          const chunk = productIds.slice(i, i + chunkSize);
          
          const response = await fetch(`${API_BASE}/api/products/donations/bulk`, {
            method: 'POST',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json',
              'Cache-Control': 'max-age=300', // Use HTTP cache
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
            };
          } else {
            // Fallback for products without donation data
            return {
              ...product,
              totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
              commissionInfo: undefined,
              supportDonations: [],
            };
          }
        });

        setProductsWithDonations(productsWithDonationData);

      } catch (error) {
        console.error('Error fetching bulk donation data:', error);
        // Fallback to products without donation data
        const fallbackProducts = products.map(product => ({
          ...product,
          totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
          commissionInfo: undefined,
          supportDonations: [],
        }));
        setProductsWithDonations(fallbackProducts);
      } finally {
        setLoading(false);
      }
    };

    fetchBulkDonations();
  }, [products]);

  return { productsWithDonations, loading };
};