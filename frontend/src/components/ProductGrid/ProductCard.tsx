import React, { useState } from 'react';
import type { GeneratedProduct } from '../../types/productTypes';

interface ProductCardProps {
  product: GeneratedProduct;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div 
      className="product-card group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="aspect-w-1 aspect-h-1 w-full overflow-hidden rounded-t-lg">
        <img
          src={product.product_info.image_url}
          alt={product.product_info.theme}
          className="product-image"
          loading="lazy"
        />
      </div>
      
      <div className="p-4">
        <h3 className="product-title">
          {product.product_info.theme}
        </h3>
        <p className="product-type">
          {product.product_info.product_type}
        </p>
        
        <div className="mt-4 flex justify-between items-center">
          <a
            href={product.product_info.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="product-link"
          >
            View on Zazzle
          </a>
          <button
            onClick={() => setIsModalOpen(true)}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Details
          </button>
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full">
            <h2 className="text-2xl font-bold mb-4">{product.product_info.theme}</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <img
                  src={product.product_info.image_url}
                  alt={product.product_info.theme}
                  className="w-full rounded-lg"
                />
              </div>
              <div>
                <h3 className="font-semibold mb-2">Product Details</h3>
                <p className="text-gray-600 mb-2">Type: {product.product_info.product_type}</p>
                <p className="text-gray-600 mb-2">Model: {product.product_info.model}</p>
                <p className="text-gray-600 mb-4">Version: {product.product_info.prompt_version}</p>
                
                <h3 className="font-semibold mb-2">Reddit Context</h3>
                <p className="text-gray-600 mb-2">Subreddit: {product.reddit_post.subreddit}</p>
                <p className="text-gray-600 mb-2">Title: {product.reddit_post.title}</p>
                <a
                  href={product.reddit_post.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 hover:text-indigo-500"
                >
                  View Reddit Post
                </a>
              </div>
            </div>
            <button
              onClick={() => setIsModalOpen(false)}
              className="mt-6 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}; 