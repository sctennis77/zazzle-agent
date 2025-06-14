import React, { useState } from 'react';
import type { GeneratedProduct } from '../../types/productTypes';

interface ProductCardProps {
  product: GeneratedProduct;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div
      className="bg-white rounded-2xl shadow-md hover:shadow-lg transition-shadow duration-300 max-w-md w-full mx-auto flex flex-col items-center border border-gray-200 group"
    >
      <div className="w-full aspect-square overflow-hidden rounded-t-2xl flex items-center justify-center bg-gray-100">
        <img
          src={product.product_info.image_url}
          alt={product.product_info.theme}
          className="object-cover w-full h-full transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
      </div>
      <div className="w-full p-5 flex flex-col items-center">
        <h3 className="text-xl font-bold text-gray-900 mb-2 text-center">
          {product.product_info.theme}
        </h3>
        <a
          href={product.product_info.product_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block px-6 py-2 mb-2 rounded-full bg-gradient-to-r from-blue-500 to-blue-400 text-white font-semibold shadow hover:from-blue-600 hover:to-blue-500 transition-colors duration-200 text-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          View on Zazzle
        </a>
        <button
          onClick={() => setShowDetails((prev) => !prev)}
          className="text-sm text-gray-500 hover:text-pink-500 mt-1 focus:outline-none"
        >
          {showDetails ? 'Hide Details' : 'Show Details'}
        </button>
        {showDetails && (
          <div className="w-full mt-4 bg-gray-50 rounded-xl p-4 text-gray-700 text-sm border border-gray-200 transition-all duration-300">
            <div className="mb-2">
              <span className="font-semibold">Product Type:</span> {product.product_info.product_type}
            </div>
            <div className="mb-2">
              <span className="font-semibold">Model:</span> {product.product_info.model}
            </div>
            <div className="mb-2">
              <span className="font-semibold">Prompt Version:</span> {product.product_info.prompt_version}
            </div>
            <div className="mb-2">
              <span className="font-semibold">Affiliate Link:</span> <a href={product.product_info.affiliate_link} target="_blank" rel="noopener noreferrer" className="text-pink-500 underline break-all">{product.product_info.affiliate_link}</a>
            </div>
            <div className="mb-2">
              <span className="font-semibold">Reddit Subreddit:</span> {product.reddit_post.subreddit}
            </div>
            <div className="mb-2">
              <span className="font-semibold">Reddit Title:</span> {product.reddit_post.title}
            </div>
            <div className="mb-2">
              <span className="font-semibold">Reddit Post:</span> <a href={product.reddit_post.url} target="_blank" rel="noopener noreferrer" className="text-pink-500 underline break-all">View Reddit Post</a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}; 