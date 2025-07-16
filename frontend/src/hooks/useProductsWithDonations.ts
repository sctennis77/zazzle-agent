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

interface DonationData {
  commission?: CommissionInfo;
  support?: SupportDonation[];
}

export const useProductsWithDonations = (products: GeneratedProduct[]) => {
  const [productsWithDonations, setProductsWithDonations] = useState<ProductWithFullDonationData[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (products.length === 0) {
      setProductsWithDonations([]);
      return;
    }

    const fetchDonationData = async () => {
      setLoading(true);
      try {
        // Fetch donation data for all products in parallel
        const donationPromises = products.map(async (product) => {
          try {
            const response = await fetch(`${API_BASE}/api/products/${product.pipeline_run.id}/donations`);
            if (response.ok) {
              const data: DonationData = await response.json();
              const commissionAmount = data.commission?.donation_amount || 0;
              const supportAmount = data.support?.reduce((sum, d) => sum + (d.donation_amount || 0), 0) || 0;
              
              return {
                ...product,
                totalDonationAmount: commissionAmount + supportAmount,
                commissionInfo: data.commission || undefined,
                supportDonations: data.support || []
              };
            }
          } catch (error) {
            console.error(`Error fetching donations for product ${product.product_info.id}:`, error);
          }
          
          // Fallback to commission amount from product data
          return {
            ...product,
            totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
            commissionInfo: undefined,
            supportDonations: []
          };
        });

        const results = await Promise.all(donationPromises);
        setProductsWithDonations(results);
      } catch (error) {
        console.error('Error fetching donation data:', error);
        // Fallback to products without donation data
        const fallbackProducts = products.map(product => ({
          ...product,
          totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
          commissionInfo: undefined,
          supportDonations: []
        }));
        setProductsWithDonations(fallbackProducts);
      } finally {
        setLoading(false);
      }
    };

    fetchDonationData();
  }, [products]);

  return { productsWithDonations, loading };
};