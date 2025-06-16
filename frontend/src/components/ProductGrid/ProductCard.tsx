import React, { useState } from 'react';
import type { GeneratedProduct } from '../../types/productTypes';
import { FaReddit, FaInfoCircle } from 'react-icons/fa';

interface ProductCardProps {
  product: GeneratedProduct;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div
      className="bg-white rounded-2xl shadow-md hover:shadow-lg transition-shadow duration-300 max-w-md w-full mx-auto flex flex-col items-center border border-gray-200 group"
    >
      <div className="w-full aspect-square overflow-hidden rounded-t-2xl flex items-center justify-center bg-gray-100 relative">
        <div className="relative">
          <img
            src={product.product_info.image_url}
            alt={product.product_info.theme}
            className="object-cover w-full h-full transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />
          <a
            href={product.reddit_post.url}
            target="_blank"
            rel="noopener noreferrer"
            className="absolute bottom-2 left-2 bg-[#FF4500] text-white text-xs px-2 py-1 rounded-full hover:bg-[#FF4500]/90 transition-colors"
          >
            r/{product.reddit_post.subreddit}
          </a>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="absolute bottom-2 right-2 text-gray-600 hover:text-gray-800 transition-colors"
            title="Show details"
          >
            <FaInfoCircle size={20} />
          </button>
        </div>
      </div>
      <div className="w-full p-5 flex flex-col items-center">
        <h3 className="text-xl font-bold text-gray-900 mb-2 text-center">
          {product.reddit_post.title}
        </h3>
        <div className="p-4">
          <div className="flex flex-col gap-2">
            <a
              href={product.product_info.affiliate_link}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-center"
            >
              Buy
            </a>
            <span className="text-sm text-gray-500">
              {new Date(product.pipeline_run.end_time).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
              })}
            </span>
          </div>
        </div>
        {showDetails && (
          <div className="w-full mt-4 bg-gray-50 rounded-xl p-4 text-gray-700 text-sm border border-gray-200 transition-all duration-300">
            <div className="space-y-2">
              <div>
                <span className="font-semibold">Summary:</span> {product.product_info.theme}
              </div>
              <div>
                <span className="font-semibold">Type:</span> {product.product_info.product_type}
              </div>
              {product.reddit_post.content && (
                <div>
                  <span className="font-semibold">Post Content:</span>
                  <p className="mt-1 text-sm text-gray-600">{product.reddit_post.content}</p>
                </div>
              )}
              {product.reddit_post.comment_summary && (
                <div>
                  <span className="font-semibold">Comments:</span>
                  <p className="mt-1 text-sm text-gray-600">{product.reddit_post.comment_summary}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}; 