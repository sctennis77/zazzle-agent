import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useProducts } from '../../hooks/useProducts';
import { ProductCard } from './ProductCard';
import { ProductModal } from './ProductModal';
import type { GeneratedProduct } from '../../types/productTypes';

export const ProductGrid: React.FC = () => {
  const { products, loading, error } = useProducts();
  const [searchParams] = useSearchParams();
  const [selectedProduct, setSelectedProduct] = useState<GeneratedProduct | null>(null);
  const [showModal, setShowModal] = useState(false);

  // Handle query parameter for opening specific product
  useEffect(() => {
    const productPostId = searchParams.get('product');
    if (productPostId && products.length > 0) {
      const product = products.find(p => p.reddit_post.post_id === productPostId);
      if (product) {
        setSelectedProduct(product);
        setShowModal(true);
        // Remove the query parameter from URL after opening the modal
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('product');
        window.history.replaceState({}, '', newUrl.toString());
      }
    }
  }, [searchParams, products]);

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedProduct(null);
  };

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
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 p-8 bg-gray-50">
        {products.map((product) => (
          <ProductCard key={product.product_info.id} product={product} />
        ))}
      </div>

      {/* Global modal for query parameter products */}
      {selectedProduct && (
        <ProductModal
          product={selectedProduct}
          isOpen={showModal}
          onClose={handleCloseModal}
        />
      )}
    </>
  );
}; 