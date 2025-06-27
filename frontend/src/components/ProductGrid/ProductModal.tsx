import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import type { GeneratedProduct, CommissionInfo } from '../../types/productTypes';
import { FaReddit, FaExternalLinkAlt, FaUser, FaThumbsUp, FaComment, FaHeart, FaCrown, FaStar, FaGem, FaPaintBrush } from 'react-icons/fa';
import DonationModal from '../common/DonationModal';

interface ProductModalProps {
  product: GeneratedProduct | null;
  isOpen: boolean;
  onClose: () => void;
}

// Helper function to get tier icon and color
const getTierDisplay = (tierName: string) => {
  const tier = tierName.toLowerCase();
  if (tier.includes('gold') || tier.includes('platinum') || tier.includes('diamond')) {
    return { icon: FaCrown, color: 'text-yellow-600', bgColor: 'bg-yellow-50', borderColor: 'border-yellow-200' };
  } else if (tier.includes('silver')) {
    return { icon: FaStar, color: 'text-gray-600', bgColor: 'bg-gray-50', borderColor: 'border-gray-200' };
  } else if (tier.includes('bronze')) {
    return { icon: FaGem, color: 'text-orange-600', bgColor: 'bg-orange-50', borderColor: 'border-orange-200' };
  } else {
    return { icon: FaHeart, color: 'text-pink-600', bgColor: 'bg-pink-50', borderColor: 'border-pink-200' };
  }
};

export const ProductModal: React.FC<ProductModalProps> = ({ product, isOpen, onClose }) => {
  if (!product) return null;

  // Expand/collapse state for post content
  const [showFullPost, setShowFullPost] = useState(false);
  const [showDonation, setShowDonation] = useState(false);
  const [commissionInfo, setCommissionInfo] = useState<CommissionInfo | null>(null);
  const [loadingDonation, setLoadingDonation] = useState(false);
  const postContent = product.reddit_post.content || '';
  const previewLength = 200;
  const isLong = postContent.length > previewLength;
  const previewContent = isLong ? postContent.slice(0, previewLength) + '…' : postContent;

  // Fetch donation information when modal opens
  useEffect(() => {
    if (isOpen) {
      const fetchDonationInfo = async () => {
        setLoadingDonation(true);
        try {
          const response = await fetch(`/api/products/${product.pipeline_run.id}/donations`);
          if (response.ok) {
            const data = await response.json();
            if (data.commission_info) {
              setCommissionInfo(data.commission_info);
            }
          }
        } catch (error) {
          console.error('Error fetching donation info:', error);
        } finally {
          setLoadingDonation(false);
        }
      };

      fetchDonationInfo();
    }
  }, [isOpen, product.pipeline_run.id]);

  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} title={product.product_info.image_title || product.product_info.theme}>
        <div className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Image Section */}
            <div className="space-y-4">
              <div className="space-y-3">
                <div className="aspect-square overflow-hidden rounded-2xl bg-gray-100 relative">
                  <img
                    src={product.product_info.image_url}
                    alt={product.product_info.image_title || product.product_info.theme}
                    className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                  />
                </div>
                {/* Theme Caption */}
                <div className="text-center">
                  <p className="text-sm text-gray-600 italic leading-relaxed">
                    {product.product_info.theme}
                  </p>
                </div>
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
                <button
                  onClick={() => setShowDonation(true)}
                  className="flex items-center justify-center gap-2 bg-pink-100 text-pink-600 hover:bg-pink-200 hover:text-pink-700 px-6 py-3 rounded-xl transition-all duration-200 font-semibold shadow-sm hover:shadow-md mt-2"
                  title="Support this project"
                  aria-label="Support"
                >
                  <FaHeart size={16} />
                  Support
                </button>
              </div>
            </div>
            {/* Details Section */}
            <div className="space-y-6">
              {/* Commission Information */}
              {commissionInfo && (
                <div className="space-y-2">
                  <h4 className="font-semibold text-gray-900">Commissioned by</h4>
                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl p-4 border border-purple-200">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-full bg-purple-100 border border-purple-200">
                        <FaPaintBrush size={20} className="text-purple-600" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900">
                            {commissionInfo.reddit_username}
                          </span>
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                            {commissionInfo.commission_type || 'Commission'}
                          </span>
                        </div>
                        {commissionInfo.commission_message && (
                          <p className="text-sm text-gray-600 mt-1 italic">
                            "{commissionInfo.commission_message}"
                          </p>
                        )}
                        {commissionInfo.donation_amount && (
                          <p className="text-sm text-gray-600 mt-1">
                            Donated ${commissionInfo.donation_amount.toFixed(2)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {/* Fallback to Sponsor Information */}
              {!commissionInfo && product.product_info.sponsor_info && (
                <div className="space-y-2">
                  <h4 className="font-semibold text-gray-900">Sponsored by</h4>
                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl p-4 border border-purple-200">
                    <div className="flex items-center gap-3">
                      {(() => {
                        const tierDisplay = getTierDisplay(product.product_info.sponsor_info.tier_name);
                        const IconComponent = tierDisplay.icon;
                        return (
                          <div className={`p-2 rounded-full ${tierDisplay.bgColor} border ${tierDisplay.borderColor}`}>
                            <IconComponent size={20} className={tierDisplay.color} />
                          </div>
                        );
                      })()}
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900">
                            {product.product_info.sponsor_info.reddit_username}
                          </span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${(() => {
                            const tier = product.product_info.sponsor_info.tier_name.toLowerCase();
                            if (tier.includes('gold') || tier.includes('platinum') || tier.includes('diamond')) {
                              return 'bg-yellow-100 text-yellow-800';
                            } else if (tier.includes('silver')) {
                              return 'bg-gray-100 text-gray-800';
                            } else if (tier.includes('bronze')) {
                              return 'bg-orange-100 text-orange-800';
                            } else {
                              return 'bg-pink-100 text-pink-800';
                            }
                          })()}`}>
                            {product.product_info.sponsor_info.tier_name}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">
                          Donated ${product.product_info.sponsor_info.donation_amount.toFixed(2)}
                        </p>
                      </div>
                    </div>
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
                      <p className="text-sm leading-relaxed italic text-gray-700" style={{ minHeight: '3.5em' }}>
                        {showFullPost ? postContent : previewContent}
                      </p>
                      {isLong && (
                        <button
                          className="mt-2 text-xs text-blue-600 hover:underline focus:outline-none"
                          onClick={() => setShowFullPost(v => !v)}
                          aria-expanded={showFullPost}
                        >
                          {showFullPost ? 'Show less' : 'Show more'}
                        </button>
                      )}
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
      <DonationModal
        isOpen={showDonation}
        onClose={() => setShowDonation(false)}
        subreddit={product.reddit_post.subreddit}
        postId={product.reddit_post.post_id}
      />
    </>
  );
}; 