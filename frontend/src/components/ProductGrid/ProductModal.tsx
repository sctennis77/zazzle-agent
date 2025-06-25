import React from 'react';
import { Modal } from '../common/Modal';
import type { GeneratedProduct } from '../../types/productTypes';
import { FaReddit, FaExternalLinkAlt, FaUser, FaThumbsUp, FaComment } from 'react-icons/fa';

interface ProductModalProps {
  product: GeneratedProduct | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ProductModal: React.FC<ProductModalProps> = ({ product, isOpen, onClose }) => {
  if (!product) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={product.product_info.image_title || product.product_info.theme}>
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Image Section */}
          <div className="space-y-4">
            <div className="aspect-square overflow-hidden rounded-2xl bg-gray-100 relative">
              <img
                src={product.product_info.image_url}
                alt={product.product_info.image_title || product.product_info.theme}
                className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
              />
            </div>
            
            {/* Action Buttons */}
            <div className="flex flex-col gap-3">
              <a
                href={product.product_info.affiliate_link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-3 rounded-xl hover:from-blue-700 hover:to-blue-800 transition-all duration-200 font-semibold shadow-sm hover:shadow-md"
              >
                <FaExternalLinkAlt size={16} />
                Buy {product.product_info.product_type}
              </a>
              
              <a
                href={product.reddit_post.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 bg-[#FF4500] text-white px-6 py-3 rounded-xl hover:bg-[#FF4500]/90 transition-colors font-semibold"
              >
                <FaReddit size={16} />
                View on Reddit
              </a>
            </div>
          </div>

          {/* Details Section */}
          <div className="space-y-6">
            {/* Product Theme */}
            {product.product_info.image_title && (
              <div className="space-y-2">
                <h4 className="font-semibold text-gray-900">Theme</h4>
                <div className="bg-gray-50 rounded-xl p-4">
                  <p className="text-sm leading-relaxed text-gray-700 italic">{product.product_info.theme}</p>
                </div>
              </div>
            )}

            {/* Reddit Post Content */}
            {product.reddit_post.content && (
              <div className="space-y-2">
                <h4 className="font-semibold text-gray-900">Post</h4>
                <div className="bg-gray-50 rounded-xl p-4 text-gray-700 space-y-3">
                  <h3 className="text-lg font-bold text-gray-900">
                    {product.reddit_post.title}
                  </h3>
                  <div className="border-t border-gray-200 pt-3">
                    <p className="text-sm leading-relaxed italic text-gray-700">{product.reddit_post.content}</p>
                  </div>
                  <div className="border-t border-gray-200 pt-3">
                    <div className="flex items-center gap-4 text-sm">
                      {product.reddit_post.author ? (
                        <div className="flex items-center gap-1">
                          <FaUser size={12} className="text-gray-500" />
                          <span className="text-gray-600">Author:</span>
                          <span className="font-medium text-gray-900">u/{product.reddit_post.author}</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1">
                          <FaUser size={12} className="text-gray-500" />
                          <span className="text-gray-600">Author:</span>
                          <span className="italic text-gray-400">[unknown]</span>
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <FaReddit size={12} className="text-gray-500" />
                        <span className="text-gray-600">Subreddit:</span>
                        <span className="font-medium text-gray-900">r/{product.reddit_post.subreddit}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Community Discussion */}
            <div className="space-y-2">
              <h4 className="font-semibold text-gray-900">Community Discussion</h4>
              <div className="bg-gray-50 rounded-xl p-4 space-y-3">
                {/* Comments Summary */}
                {product.reddit_post.comment_summary && (
                  <div>
                    <p className="text-sm leading-relaxed text-gray-700">{product.reddit_post.comment_summary}</p>
                  </div>
                )}
                
                {/* Reddit post metadata */}
                <div className="flex items-center gap-4 text-sm pt-2 border-t border-gray-200">
                  {product.reddit_post.score !== undefined && (
                    <div className="flex items-center gap-1">
                      <FaThumbsUp size={12} className="text-gray-500" />
                      <span className="text-gray-600">Score:</span>
                      <span className="font-medium text-gray-900">{product.reddit_post.score}</span>
                    </div>
                  )}
                  {product.reddit_post.num_comments !== undefined && (
                    <div className="flex items-center gap-1">
                      <FaComment size={12} className="text-gray-500" />
                      <span className="text-gray-600">Comments:</span>
                      <span className="font-medium text-gray-900">{product.reddit_post.num_comments}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Moved to bottom: Illustration credit */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <div className="text-center text-xs text-gray-500">
            <span>Illustrated by <span className="font-semibold text-gray-700">Clouvel</span> with </span>
            <span className="font-semibold text-gray-700">{product.product_info.model}</span>
            <span> at </span>
            <span className="font-mono text-gray-600">
              {product.pipeline_run && product.pipeline_run.end_time ?
                new Date(product.pipeline_run.end_time).toLocaleString('en-US', {
                  year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                }) : 'Unknown'}
            </span>
          </div>
        </div>
      </div>
    </Modal>
  );
}; 