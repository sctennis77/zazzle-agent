import React from 'react';
import { Modal } from '../common/Modal';
import type { GeneratedProduct } from '../../types/productTypes';
import { FaReddit, FaExternalLinkAlt, FaCalendarAlt, FaTag, FaUser, FaThumbsUp, FaComment } from 'react-icons/fa';

interface ProductModalProps {
  product: GeneratedProduct | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ProductModal: React.FC<ProductModalProps> = ({ product, isOpen, onClose }) => {
  if (!product) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={product.reddit_post.title}>
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Image Section */}
          <div className="space-y-4">
            <div className="aspect-square overflow-hidden rounded-2xl bg-gray-100 relative">
              <img
                src={product.product_info.image_url}
                alt={product.product_info.theme}
                className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
              />
              {/* Subreddit badge moved to bottom left of image */}
              <a
                href={product.reddit_post.url}
                target="_blank"
                rel="noopener noreferrer"
                className="absolute bottom-2 left-2 bg-[#FF4500] text-white text-xs px-2 py-1 rounded-full hover:bg-[#FF4500]/90 transition-colors"
              >
                r/{product.reddit_post.subreddit}
              </a>
            </div>
            
            {/* Action Buttons */}
            <div className="flex flex-col gap-3">
              <a
                href={product.product_info.affiliate_link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 transition-colors font-semibold"
              >
                <FaExternalLinkAlt size={16} />
                Buy Product
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
            {/* Product Info */}
            <div className="space-y-4">
              <div>
                <h3 className="text-2xl font-bold text-gray-900 mb-2">
                  {product.product_info.theme}
                </h3>
                
                {/* Post Author - First piece of information */}
                {product.reddit_post.author && (
                  <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
                    <FaUser size={14} />
                    <span className="font-mono text-blue-600">u/{product.reddit_post.author}</span>
                  </div>
                )}
                
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <FaTag size={14} />
                  <span className="capitalize">Generated {product.product_info.product_type} with {product.product_info.model}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 text-sm text-gray-600">
                <FaCalendarAlt size={14} />
                <span>
                  Generated on {new Date(product.pipeline_run.end_time).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              </div>
            </div>

            {/* Reddit Post Content */}
            {product.reddit_post.content && (
              <div className="space-y-2">
                <h4 className="font-semibold text-gray-900">Reddit Post Content</h4>
                <div className="bg-gray-50 rounded-xl p-4 text-gray-700">
                  <p className="text-sm leading-relaxed">{product.reddit_post.content}</p>
                </div>
              </div>
            )}

            {/* Community Discussion */}
            <div className="space-y-2">
              <h4 className="font-semibold text-gray-900">Community Discussion</h4>
              <div className="bg-gray-50 rounded-xl p-4 space-y-3">
                {/* Reddit post metadata */}
                <div className="flex items-center gap-4 text-sm">
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
                
                {/* Comments Summary */}
                {product.reddit_post.comment_summary && (
                  <div className="pt-2 border-t border-gray-200">
                    <p className="text-sm leading-relaxed text-gray-700">{product.reddit_post.comment_summary}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Technical Details */}
            <div className="space-y-2">
              <h4 className="font-semibold text-gray-900">Technical Details</h4>
              <div className="bg-gray-50 rounded-xl p-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Template ID:</span>
                  <span className="font-mono text-gray-900">{product.product_info.template_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Prompt Version:</span>
                  <span className="font-mono text-gray-900">{product.product_info.prompt_version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Pipeline Run ID:</span>
                  <span className="font-mono text-gray-900">#{product.pipeline_run.id}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}; 