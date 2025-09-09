import { useEffect, useState } from 'react';
import type { GeneratedProduct } from '../types/productTypes';
import { useDonationContext } from '../contexts/DonationContext';
import type { ProductWithFullDonationData } from '../contexts/DonationContext';

interface UseProductsWithDonationsOptions {
  lazy?: boolean; // If true, only load fallback data initially
}

export const useProductsWithDonationsV2 = (
  products: GeneratedProduct[], 
  options: UseProductsWithDonationsOptions = {}
) => {
  const { lazy = false } = options;
  const { getProductsWithDonations, loadDonationData, loading } = useDonationContext();
  const [productsWithDonations, setProductsWithDonations] = useState<ProductWithFullDonationData[]>([]);

  useEffect(() => {
    if (products.length === 0) {
      setProductsWithDonations([]);
      return;
    }

    // Always get the current state from context (includes cached data)
    const currentProducts = getProductsWithDonations(products);
    setProductsWithDonations(currentProducts);

    // If not in lazy mode and we have uncached products, trigger fetch
    if (!lazy) {
      const hasUncachedProducts = currentProducts.some(p => !p.donationDataLoaded);
      if (hasUncachedProducts) {
        console.log('useProductsWithDonationsV2: triggering donation data load');
        loadDonationData(products);
      }
    }
  }, [products, lazy, getProductsWithDonations, loadDonationData]);

  // Update local state when context cache changes
  useEffect(() => {
    if (products.length > 0) {
      setProductsWithDonations(getProductsWithDonations(products));
    }
  }, [products, getProductsWithDonations]);

  const loadProductDonation = async (pipelineRunId: number): Promise<void> => {
    const product = products.find(p => p.pipeline_run.id === pipelineRunId);
    if (product) {
      await loadDonationData([product]);
    }
  };

  return { productsWithDonations, loading, loadProductDonation };
};