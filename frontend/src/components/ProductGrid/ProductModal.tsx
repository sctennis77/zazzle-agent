import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import type { GeneratedProduct, CommissionInfo, ProductSubredditPost } from '../../types/productTypes';
import { FaReddit, FaExternalLinkAlt, FaUser, FaThumbsUp, FaComment, FaHeart, FaCrown, FaStar, FaGem } from 'react-icons/fa';
import DonationModal from '../common/DonationModal';
import { useDonationTiers } from '../../hooks/useDonationTiers';
import { usePublishProduct } from '../../hooks/usePublishProduct';
import { API_BASE } from '../../utils/apiBase';

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
          const response = await fetch(`${API_BASE}/api/products/${product.pipeline_run.id}/donations`);
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
        <div className="p-4 sm:p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
            {/* Left Column: Image, Theme, Actions */}
            <div className="space-y-4">
              {/* Image Section */}
              <div className="space-y-3">
                <div className="aspect-square overflow-hidden rounded-2xl bg-gray-100 relative group">
                  <img
                    src={product.product_info.image_url}
                    alt={product.product_info.image_title || product.product_info.theme}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                </div>
                {/* Theme Caption */}
                <div className="text-center">
                  <p className="text-sm text-gray-600 italic leading-relaxed">
                    {product.product_info.theme}
                  </p>
                </div>
              </div>
              {/* Action Buttons - Support and Buy Print only */}
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDonation(true)}
                  className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-green-600 to-green-700 text-white px-4 py-3 rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-200 font-semibold shadow-sm hover:shadow-md"
                  title="Support"
                >
                  <FaHeart size={16} />
                  Support
                </button>
                <a
                  href={product.product_info.affiliate_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-3 rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all duration-200 font-semibold shadow-sm hover:shadow-md"
                  title="Buy Print"
                >
                  <FaExternalLinkAlt size={16} />
                  Buy Print
                </a>
              </div>
            </div>
            {/* Right Column: Reddit Content Only */}
            <div className="space-y-4 flex flex-col h-full justify-between">
              {/* Original Post Card */}
              <div className="flex-1 flex flex-col justify-between">
                <div className="space-y-2 flex flex-col h-full justify-between">
                  <div className="bg-orange-50 rounded-xl p-2 border border-orange-200 flex flex-col justify-between h-full">
                    {/* Header: Orange Reddit button, subreddit, timestamp, author */}
                    <div className="flex items-start gap-3 mb-2">
                      <a
                        href={product.reddit_post.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 rounded-full bg-orange-100 border border-orange-300 hover:bg-orange-200 transition-colors cursor-pointer mt-0.5"
                        title="View on Reddit"
                      >
                        <FaReddit size={20} className="text-orange-500" />
                      </a>
                      <div className="flex flex-col flex-1 min-w-0">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-bold text-gray-900 text-base truncate">
                            r/{product.reddit_post.subreddit}
                          </span>
                          {product.pipeline_run && product.pipeline_run.start_time && (
                            <span className="text-sm text-gray-600">
                              &nbsp;• {new Date(product.pipeline_run.start_time).toLocaleString('en-US', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
                          <FaUser size={12} className="text-gray-400" />
                          <span className="font-medium text-gray-700">{product.reddit_post.author ? `u/${product.reddit_post.author}` : <span className='italic text-gray-400'>[unknown]</span>}</span>
                        </div>
                      </div>
                    </div>
                    {/* Body: Post title, post content, then Community Discussion */}
                    <div className="flex-1 flex flex-col overflow-y-auto max-h-72">
                      {product.reddit_post.title && (
                        <div className="font-bold text-gray-900 text-base">
                          {product.reddit_post.title}
                        </div>
                      )}
                      {product.reddit_post.content && (
                        <div className="text-sm text-gray-700 whitespace-pre-line">
                          {product.reddit_post.content}
                        </div>
                      )}
                      {/* Community Discussion as inner section */}
                      <div className="mt-1">
                        <div className="bg-white rounded-lg border border-gray-200 p-2">
                          <h5 className="font-semibold text-gray-900 mb-1 text-sm">Community Discussion</h5>
                          {/* Comments Summary */}
                          {product.reddit_post.comment_summary && (
                            <div>
                              <p className="text-sm leading-relaxed text-gray-700">{product.reddit_post.comment_summary}</p>
                            </div>
                          )}
                          {/* Reddit post metadata */}
                          <div className="flex items-center gap-4 text-sm pt-1 border-t border-gray-100 flex-wrap">
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
                    {/* Footer: Published to Reddit/Clouvel Section */}
                    {publishedPost && (
                      <div className="flex items-center gap-2 mt-4">
                        <a
                          href={publishedPost.reddit_post_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 rounded-full bg-green-100 border border-green-300 hover:bg-green-200 transition-colors cursor-pointer"
                          title="View on Reddit"
                        >
                          <FaReddit size={20} className="text-green-600" />
                        </a>
                        <span className="font-semibold text-gray-900">
                          r/{publishedPost.subreddit_name}
                        </span>
                        <span className="text-sm text-gray-600">
                          &nbsp;• {new Date(publishedPost.submitted_at).toLocaleString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
          {/* Commissioned By - Styled Like DonationCard Row, Full Width, Message Centered */}
          {commissionInfo && (
            <div className="flex justify-center mt-6">
              <div className="flex items-center w-full bg-blue-50 border border-blue-100 rounded-xl px-6 py-2 shadow-sm">
                {/* Icon */}
                {(() => {
                  const tierName = product.product_info.donation_info && product.product_info.donation_info.tier_name || '';
                  const tierDisplay = getTierDisplay(tierName);
                  const IconComponent = iconMap[tierDisplay.icon as keyof typeof iconMap] || FaHeart;
                  return (
                    <span className={`flex-shrink-0 flex items-center justify-center ${tierDisplay.color} mr-3`}>
                      <IconComponent size={20} className={tierDisplay.color} />
                    </span>
                  );
                })()}
                {/* Username and subtext */}
                <div className="flex flex-col min-w-0">
                  <span className="font-semibold text-gray-900 text-base truncate">
                    {commissionInfo.reddit_username}
                  </span>
                  <span className="text-xs text-gray-400 font-medium">Commission</span>
                </div>
                {/* Commission message centered */}
                {commissionInfo.commission_message && (
                  <span className="flex-1 text-center text-xs text-gray-600 italic px-4">
                    "{commissionInfo.commission_message}"
                  </span>
                )}
                {/* Amount and date */}
                <div className="flex flex-col items-end ml-auto">
                  <span className="font-mono text-gray-700 text-lg font-semibold">${commissionInfo.donation_amount?.toFixed(2)}</span>
                  <span className="text-xs text-gray-400 leading-tight">
                    {product.pipeline_run && product.pipeline_run.end_time ?
                      new Date(product.pipeline_run.end_time).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: '2-digit' }) : ''}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Support Donations - Styled Like Commission Row */}
          {supportDonations.length > 0 && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <div className="flex flex-col gap-3">
                {supportDonations.map((donation, index) => {
                  const tierDisplay = getTierDisplay(donation.tier_name);
                  const IconComponent = iconMap[tierDisplay.icon as keyof typeof iconMap] || FaHeart;
                  return (
                    <div key={index} className="flex items-center w-full bg-green-50 border border-green-100 rounded-xl px-6 py-2 shadow-sm">
                      {/* Icon */}
                      <span className={`flex-shrink-0 flex items-center justify-center ${tierDisplay.color} mr-3`}>
                        <IconComponent size={20} className={tierDisplay.color} />
                      </span>
                      {/* Username and subtext */}
                      <div className="flex flex-col min-w-0">
                        <span className="font-semibold text-gray-900 text-base truncate">
                          {donation.reddit_username}
                        </span>
                        <span className="text-xs text-gray-400 font-medium">Supported</span>
                      </div>
                      {/* Message centered if present */}
                      {donation.message && (
                        <span className="flex-1 text-center text-xs text-gray-600 italic px-4">
                          "{donation.message}"
                        </span>
                      )}
                      {/* Amount and date */}
                      <div className="flex flex-col items-end ml-auto">
                        <span className="font-mono text-gray-700 text-lg font-semibold">${donation.donation_amount?.toFixed(2)}</span>
                        <span className="text-xs text-gray-400 leading-tight">
                          {donation.created_at ?
                            new Date(donation.created_at).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: '2-digit' }) : ''}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
        {/* Moved to bottom: Illustration credit */}
        <div className="mt-2 pt-2 border-t border-gray-200">
          <div className="text-center text-xs text-gray-500 space-x-1">
            <span>Illustrated by</span>
            <span className="font-semibold text-gray-700">Clouvel</span>
            <span>with</span>
            <span className="font-semibold text-gray-700">{product.product_info.model}</span>
            <span>at</span>
            <span className="font-mono text-gray-600">
              {product.pipeline_run && product.pipeline_run.end_time ?
                new Date(product.pipeline_run.end_time).toLocaleString('en-US', {
                  year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                }) : 'Unknown'}
            </span>
          </div>
        </div>
      </Modal>

      {/* Remove any floating or duplicated footer outside the modal */}

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