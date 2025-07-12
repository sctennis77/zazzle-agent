import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import type { GeneratedProduct } from '../types/productTypes';
import { API_BASE } from '../utils/apiBase';

const API_URL = `${API_BASE}/api/generated_products`;

export const useProducts = () => {
  const [products, setProducts] = useState<GeneratedProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get<GeneratedProduct[]>(API_URL);
      const data = Array.isArray(response.data) ? response.data : [];
      setProducts(data);
      setError(null);
    } catch (err) {
      setProducts([]);
      setError(err instanceof Error ? err.message : 'An error occurred while fetching products');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  return { products, loading, error, refresh: fetchProducts, setProducts };
}; 