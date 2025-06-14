import React from 'react';
import { useProducts } from '../../hooks/useProducts';
import { ProductCard } from './ProductCard';

export const ProductGrid: React.FC = () => {
  const { products, loading, error } = useProducts();

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center text-red-600 p-4">
        Error loading products: {error}
      </div>
    );
  }

  if (!products.length) {
    return (
      <div className="text-center text-gray-600 p-4">
        No products found
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center w-full min-h-screen py-8 gap-8 bg-gray-50">
      {products.map((product) => (
        <ProductCard key={product.product_info.id} product={product} />
      ))}
    </div>
  );
}; 