import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import type { GeneratedProduct, CommissionInfo, ProductSubredditPost } from '../../types/productTypes';
import { FaReddit, FaExternalLinkAlt, FaUser, FaThumbsUp, FaComment, FaHeart, FaCrown, FaStar, FaGem } from 'react-icons/fa';
import DonationModal from '../common/DonationModal';
import { useDonationTiers } from '../../hooks/useDonationTiers';
import { usePublishProduct } from '../../hooks/usePublishProduct';

interface ProductModalProps {
  product: GeneratedProduct | null;
  isOpen: boolean;
  onClose: () => void;
}

// Map icon string to actual icon component
const iconMap = {
  FaCrown,
  FaStar,
  FaGem,
  FaHeart,
};

export const ProductModal: React.FC<ProductModalProps> = ({ product, isOpen, onClose }) => {
  if (!product) return null;

  // Expand/collapse state for post content
  const [showFullPost, setShowFullPost] = useState(false);
  const [showDonation, setShowDonation] = useState(false);
  const [commissionInfo, setCommissionInfo] = useState<CommissionInfo | null>(null);
  const [supportDonations, setSupportDonations] = useState<any[]>([]);
  const postContent = product.reddit_post.content || '';
  const previewLength = 200;
  const isLong = postContent.length > previewLength;
  const previewContent = isLong ? postContent.slice(0, previewLength) + '…' : postContent;

  const { getTierDisplay } = useDonationTiers();
  const { publishedPost, getPublishedPost, publishProduct } = usePublishProduct();

  // Fetch donation information when modal opens
  useEffect(() => {
    if (isOpen) {
      const fetchDonationInfo = async () => {
        try {
          const response = await fetch(`/api/products/${product.pipeline_run.id}/donations`);
          if (response.ok) {
            const data = await response.json();
            if (data.commission) {
              setCommissionInfo(data.commission);
            }
            if (data.support) {
              setSupportDonations(data.support);
            }
          }
        } catch (error) {
          console.error('Error fetching donation info:', error);
        }
      };

      const fetchPublishedPost = async () => {
        try {
          await getPublishedPost(product.product_info.id.toString());
        } catch (error) {
          console.error('Error fetching published post:', error);
        }
      };

      const autoPublishIfNeeded = async () => {
        try {
          // First try to get the published post
          const publishedPost = await getPublishedPost(product.product_info.id.toString());
          
          // If no published post found (404), automatically publish the product
          if (!publishedPost) {
            console.log(`Product ${product.product_info.id} not published yet, auto-publishing...`);
            await publishProduct(product.product_info.id.toString());
          }
        } catch (error) {
          console.error('Error in auto-publish logic:', error);
        }
      };

      fetchDonationInfo();
      autoPublishIfNeeded();
    }
  }, [isOpen, product.pipeline_run.id, product.product_info.id, getPublishedPost, publishProduct]);

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
              {/* Commission Information - always show */}
              {commissionInfo && (
                <div className="space-y-2">
                  <h4 className="font-semibold text-gray-900">Commissioned by</h4>
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-200">
                    <div className="flex items-center gap-3">
                      {(() => {
                        // Use donation tier for commission styling
                        const tierName = product.product_info.donation_info && product.product_info.donation_info.tier_name || '';
                        const tierDisplay = getTierDisplay(tierName);
                        const IconComponent = iconMap[tierDisplay.icon as keyof typeof iconMap] || FaHeart;
                        return (
                          <div className={`p-2 rounded-full ${tierDisplay.bgColor} border ${tierDisplay.borderColor}`}>
                            <IconComponent size={20} className={tierDisplay.color} />
                          </div>
                        );
                      })()}
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900">
                            {commissionInfo.reddit_username}
                          </span>
                          {/* Show tier name as badge, styled like donation */}
                          {(() => {
                            const tierName = product.product_info.donation_info && product.product_info.donation_info.tier_name || '';
                            const tierDisplay = getTierDisplay(tierName);
                            return tierName ? (
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${tierDisplay.bgColor} ${tierDisplay.color}`}>
                                {tierName}
                              </span>
                            ) : null;
                          })()}
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
              {/* Support Donations */}
              {supportDonations.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-semibold text-gray-900">Supported by</h4>
                  <div className="space-y-3">
                    {supportDonations.map((donation) => {
                      const tierDisplay = getTierDisplay(donation.tier_name);
                      const IconComponent = iconMap[tierDisplay.icon as keyof typeof iconMap] || FaHeart;
                      return (
                        <div key={donation.donation_id} className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-200">
                          <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-full ${tierDisplay.bgColor} border ${tierDisplay.borderColor}`}>
                              <IconComponent size={20} className={tierDisplay.color} />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-gray-900">
                                  {donation.reddit_username}
                                </span>
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${tierDisplay.bgColor} ${tierDisplay.color}`}>
                                  {donation.tier_name}
                                </span>
                              </div>
                              {donation.message && (
                                <p className="text-sm text-gray-600 mt-1 italic">
                                  "{donation.message}"
                                </p>
                              )}
                              <p className="text-sm text-gray-600 mt-1">
                                Donated ${donation.donation_amount.toFixed(2)}
                              </p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
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
              
              {/* Published to Reddit Section */}
              {publishedPost && (
                <div className="space-y-2">
                  <h4 className="font-semibold text-gray-900">Published to Reddit</h4>
                  <div className="bg-green-50 rounded-xl p-4 border border-green-200">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-full bg-green-100 border border-green-300">
                        <FaReddit size={20} className="text-green-600" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-gray-900">
                            r/{publishedPost.subreddit_name}
                          </span>
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                            {publishedPost.dry_run ? 'Dry Run' : 'Live'}
                          </span>
                        </div>
                        {publishedPost.reddit_post_title && (
                          <p className="text-sm text-gray-600 mt-1">
                            {publishedPost.reddit_post_title}
                          </p>
                        )}
                        <p className="text-sm text-gray-600 mt-1">
                          Posted on {new Date(publishedPost.submitted_at).toLocaleString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </p>
                        {publishedPost.reddit_post_url && (
                          <a
                            href={publishedPost.reddit_post_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-blue-600 hover:underline mt-1 inline-block"
                          >
                            View on Reddit →
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
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
        supportOnly={true}
      />
    </>
  );
}; 