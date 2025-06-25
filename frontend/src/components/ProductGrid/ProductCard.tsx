import React, { useState } from 'react';
import type { GeneratedProduct } from '../../types/productTypes';
import { FaExpand } from 'react-icons/fa';
import { ProductModal } from './ProductModal';

interface ProductCardProps {
  product: GeneratedProduct;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const [showModal, setShowModal] = useState(false);

  const handleImageClick = () => {
    setShowModal(true);
  };

  return (
    <>
      <div
        className="bg-white rounded-2xl shadow-md hover:shadow-lg transition-shadow duration-300 max-w-md w-full mx-auto flex flex-col border border-gray-200 group h-full"
      >
        <div className="w-full aspect-square overflow-hidden rounded-t-2xl flex items-center justify-center bg-gray-100 relative">
          <div className="relative w-full h-full">
            <img
              src={product.product_info.image_url}
              alt={product.product_info.image_title || product.product_info.theme}
              className="object-cover w-full h-full transition-transform duration-300 group-hover:scale-105 cursor-pointer"
              loading="lazy"
              onClick={handleImageClick}
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
              onClick={() => setShowModal(true)}
              className="absolute bottom-2 right-2 text-gray-600 hover:text-gray-800 transition-colors bg-white/80 hover:bg-white rounded-full p-1"
              title="View details"
            >
              <FaExpand size={16} />
            </button>
          </div>
        </div>
        
        <div className="flex flex-col flex-1 px-5 pb-5">
          <h3 className="text-base font-medium text-gray-800 mb-2 text-center cursor-pointer flex-1 leading-relaxed">
            {product.product_info.image_title || product.product_info.theme}
          </h3>
          
          {/* Subtle separator */}
          <div className="flex justify-center mb-2">
            <div className="w-8 h-px bg-gray-300"></div>
          </div>
          
          {/* Theme Caption */}
          <div className="pb-2">
            <p className="text-sm text-gray-600 italic text-center leading-relaxed">
              {product.product_info.theme}
            </p>
          </div>
          
          <div className="text-sm text-gray-500 text-center mt-auto">
            {new Date(product.pipeline_run.end_time).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </div>
        </div>
      </div>

      <ProductModal
        product={product}
        isOpen={showModal}
        onClose={() => setShowModal(false)}
      />
    </>
  );
}; 