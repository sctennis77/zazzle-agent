import { useState, useEffect } from 'react';
import axios from 'axios';
import type { GeneratedProduct } from '../types/productTypes';

const API_URL = 'http://localhost:8000/api/generated_products';

export const useProducts = () => {
  const [products, setProducts] = useState<GeneratedProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        const response = await axios.get<GeneratedProduct[]>(API_URL);
        setProducts(response.data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred while fetching products');
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  return { products, loading, error };
}; 