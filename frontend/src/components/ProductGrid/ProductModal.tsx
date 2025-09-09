import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import type { GeneratedProduct, CommissionInfo, RedditInteraction } from '../../types/productTypes';
import type { ProductWithFullDonationData } from '../../hooks/useProductsWithDonations';
import { FaReddit, FaExternalLinkAlt, FaUser, FaThumbsUp, FaComment, FaHeart, FaCrown, FaStar, FaGem } from 'react-icons/fa';
import DonationModal from '../common/DonationModal';
import { useDonationTiers } from '../../hooks/useDonationTiers';
import { useRedditInteraction } from '../../hooks/useRedditInteraction';
import { redditConfig } from '../../utils/redditConfig';

interface ProductModalProps {
  product: ProductWithFullDonationData | null;
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
  const postContent = product.reddit_post.content || '';
  const previewLength = 200;
  const isLong = postContent.length > previewLength;
  const previewContent = isLong ? postContent.slice(0, previewLength) + '…' : postContent;
  
  // Get donation data from props (already fetched via bulk API)
  const commissionInfo = product.commissionInfo;
  const supportDonations = product.supportDonations || [];

  const { getTierDisplay } = useDonationTiers();
  const { 
    interaction: redditInteraction, 
    autoSubmitIfNeeded, 
    isComment,
    isPost,
    hasInteraction,
    interactionUrl,
    subredditName,
    interactionDate,
    submitting: submittingInteraction 
  } = useRedditInteraction({ 
    mode: redditConfig.interactionMode,
    autoSubmit: true 
  });

  // Handle Reddit interaction when modal opens
  useEffect(() => {
    if (isOpen) {
      const autoSubmitRedditInteraction = async () => {
        try {
          const productId = product.product_info.id.toString();
          const isDryRun = redditConfig.isDryRun;
          
          await autoSubmitIfNeeded(productId, { 
            mode: redditConfig.interactionMode,
            dryRun: isDryRun 
          });
        } catch (error) {
          console.error(`Error in auto-submit ${redditConfig.interactionMode} logic:`, error);
        }
      };

      autoSubmitRedditInteraction();
    }
  }, [isOpen, product.product_info.id, autoSubmitIfNeeded]);

  // Create custom title with HD badge
  const modalTitle = (
    <div className="flex items-center gap-3">
      <span>{product.product_info.image_title || product.product_info.theme}</span>
      {product.product_info.image_quality === 'hd' && (
        <span 
          className="inline-flex items-center px-2.5 py-1 rounded-md bg-gradient-to-r from-blue-500 to-blue-600 text-white text-xs font-bold uppercase tracking-wider shadow-sm cursor-help"
          title={`${product.product_info.donation_info?.tier_name || 'Sapphire'} tier posts are illustrated with HD quality`}
        >
          HD
        </span>
      )}
    </div>
  );

  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} title={modalTitle}>
        <div className="p-4 sm:p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
            {/* Left Column: Image, Theme, Actions */}
            <div className="space-y-4">
              {/* Image Section */}
              <div className="space-y-3">
                <div className="aspect-square overflow-hidden rounded-2xl bg-gray-100">
                  <img
                    src={product.product_info.image_url}
                    alt={product.product_info.image_title || product.product_info.theme}
                    className="w-full h-full object-cover"
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
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={() => setShowDonation(true)}
                  className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-green-600 to-green-700 text-white px-4 py-3 rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-200 font-semibold shadow-sm hover:shadow-md min-h-[48px] touch-manipulation"
                  title="Support"
                >
                  <FaHeart size={16} />
                  Support
                </button>
                <a
                  href={product.product_info.affiliate_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-3 rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all duration-200 font-semibold shadow-sm hover:shadow-md min-h-[48px] touch-manipulation"
                  title="Buy Print"
                >
                  <FaExternalLinkAlt size={16} />
                  Buy Print
                </a>
              </div>
            </div>
            {/* Right Column: Reddit Content and Commission */}
            <div className="space-y-4">
              {/* Original Post Card - Compact Version */}
              <div className="bg-orange-50 rounded-xl p-3 border border-orange-200">
                {/* Header: Reddit icon, post title */}
                <div className="flex items-start gap-3 mb-2">
                  <a
                    href={product.reddit_post.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-full bg-orange-100 border border-orange-300 hover:bg-orange-200 transition-colors cursor-pointer flex-shrink-0"
                    title="View on Reddit"
                  >
                    <FaReddit size={20} className="text-orange-500" />
                  </a>
                  {product.reddit_post.title && (
                    <span className="font-bold text-gray-900 text-sm sm:text-base break-words leading-snug">{product.reddit_post.title}</span>
                  )}
                </div>
                {/* Subheader: author • subreddit */}
                <div className="ml-12 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                  <div className="text-sm text-gray-700 flex items-center gap-2 flex-wrap">
                    <span className="flex items-center gap-1 font-medium">
                      <FaUser size={12} className="text-gray-400" />
                      {product.reddit_post.author ? `u/${product.reddit_post.author}` : <span className='italic text-gray-400'>[unknown]</span>}
                    </span>
                    <span className="text-gray-400">•</span>
                    <span className="font-semibold text-orange-700">r/{product.reddit_post.subreddit}</span>
                  </div>
                  {/* Timestamp moved to the right */}
                  {product.pipeline_run && product.pipeline_run.start_time && (
                    <span className="text-xs text-gray-500 ml-0 sm:ml-2">
                      {new Date(product.pipeline_run.start_time).toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  )}
                </div>
                {/* Community Discussion */}
                <div className="bg-white rounded-lg border border-gray-200 p-2 mt-2">
                  <h5 className="font-semibold text-gray-900 mb-1 text-sm">Community Discussion</h5>
                  {/* Comments Summary */}
                  {product.reddit_post.comment_summary && (
                    <p className="text-sm leading-relaxed text-gray-700">{product.reddit_post.comment_summary}</p>
                  )}
                  {/* Reddit post metadata */}
                  <div className="flex items-center gap-4 text-sm pt-1 border-t border-gray-100 flex-wrap mt-1">
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
                {/* Reddit Interaction Section - Hidden in dry run mode */}
                {hasInteraction && redditInteraction && !redditInteraction.dry_run && (
                  <div className="flex items-center gap-2 mt-2">
                    <a
                      href={interactionUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded-full bg-green-100 border border-green-300 hover:bg-green-200 transition-colors cursor-pointer"
                      title={`View ${isComment(redditInteraction) ? 'Comment' : 'Post'} on Reddit`}
                    >
                      <FaReddit size={16} className="text-green-600" />
                    </a>
                    <span className="font-semibold text-gray-900 text-sm">
                      r/{subredditName}
                    </span>
                    <span className="text-xs text-gray-600">
                      &nbsp;• {isComment(redditInteraction) ? 'Comment' : 'Post'}
                    </span>
                    {interactionDate && (
                      <span className="text-xs text-gray-600">
                        &nbsp;• {new Date(interactionDate).toLocaleString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                    )}
                  </div>
                )}
                {submittingInteraction && (
                  <div className="flex items-center gap-2 mt-2">
                    <div className="p-1.5 rounded-full bg-blue-100 border border-blue-300">
                      <FaReddit size={16} className="text-blue-600 animate-pulse" />
                    </div>
                    <span className="text-sm text-blue-600 italic">
                      Submitting {redditConfig.interactionMode}...
                    </span>
                  </div>
                )}
              </div>
              
              {/* Commissioned By - Now below original post, not full width */}
              {commissionInfo && (
                <div className="flex items-center bg-blue-50 border border-blue-100 rounded-xl px-4 py-2 shadow-sm">
                  {/* Icon */}
                  {(() => {
                    const tierName = product.product_info.donation_info && product.product_info.donation_info.tier_name || '';
                    const tierDisplay = getTierDisplay(tierName);
                    const IconComponent = iconMap[tierDisplay.icon as keyof typeof iconMap] || FaHeart;
                    return (
                      <span className={`flex-shrink-0 flex items-center justify-center ${tierDisplay.color} mr-3`}>
                        <IconComponent size={18} className={tierDisplay.color} />
                      </span>
                    );
                  })()}
                  {/* Username and subtext */}
                  <div className="flex flex-col min-w-0">
                    <span className="font-semibold text-gray-900 text-sm truncate">
                      {commissionInfo.is_anonymous
                        ? 'Anonymous'
                        : commissionInfo.reddit_username
                          ? `u/${commissionInfo.reddit_username}`
                          : ''}
                    </span>
                    <span className="text-xs text-gray-400 font-medium">Commission</span>
                  </div>
                  {/* Commission message centered */}
                  {typeof commissionInfo.commission_message === 'string' && commissionInfo.commission_message && (
                    <span className="flex-1 text-center text-xs text-gray-600 italic px-2">
                      "{commissionInfo.commission_message}"
                    </span>
                  )}
                  {/* Amount and date */}
                  <div className="flex flex-col items-end ml-auto">
                    <span className="font-mono text-gray-700 text-base font-semibold">${commissionInfo.donation_amount?.toFixed(2)}</span>
                    <span className="text-xs text-gray-400 leading-tight">
                      {product.pipeline_run && product.pipeline_run.end_time ?
                        new Date(product.pipeline_run.end_time).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: '2-digit' }) : ''}
                    </span>
                  </div>
                </div>
              )}

              {/* Support Donations - Now at the top of where commission used to be */}
              <div className="mt-auto">
                {supportDonations.length > 0 ? (
                  <div className="flex flex-col gap-2">
                    {supportDonations.map((donation, index) => {
                      const tierName = typeof donation.tier_name === 'string' ? donation.tier_name : '';
                      const tierDisplay = getTierDisplay(tierName);
                      const IconComponent = iconMap[tierDisplay.icon as keyof typeof iconMap] || FaHeart;
                      return (
                        <div key={index} className="flex items-center bg-green-50 border border-green-100 rounded-xl px-4 py-2 shadow-sm">
                          {/* Icon */}
                          <span className={`flex-shrink-0 flex items-center justify-center ${tierDisplay.color} mr-3`}>
                            <IconComponent size={18} className={tierDisplay.color} />
                          </span>
                          {/* Username and subtext */}
                          <div className="flex flex-col min-w-0">
                            <span className="font-semibold text-gray-900 text-sm truncate">
                              {typeof donation.reddit_username === 'string' ? donation.reddit_username : 'Anonymous'}
                            </span>
                            <span className="text-xs text-gray-400 font-medium">Supported</span>
                          </div>
                          {/* Message centered if present */}
                          {typeof donation.message === 'string' && donation.message && (
                            <span className="flex-1 text-center text-xs text-gray-600 italic px-2">
                              "{donation.message}"
                            </span>
                          )}
                          {/* Amount and date */}
                          <div className="flex flex-col items-end ml-auto">
                            <span className="font-mono text-gray-700 text-base font-semibold">${donation.donation_amount?.toFixed(2)}</span>
                            <span className="text-xs text-gray-400 leading-tight">
                              {typeof donation.created_at === 'string' && donation.created_at ?
                                new Date(donation.created_at).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: '2-digit' }) : ''}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="flex items-center justify-center bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
                    <span className="text-sm text-gray-500 italic">No support donations yet</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        {/* Moved to bottom: Illustration credit */}
        <div className="mt-2 pt-2 border-t border-gray-200">
          <div className="text-center text-xs text-gray-500 space-x-1">
            <span>Illustrated by</span>
            <span className="font-semibold text-gray-700">Clouvel</span>
            <span>with</span>
            <span className="font-semibold text-gray-700">{product.product_info.model}</span>
            {product.product_info.image_quality === 'hd' && (
              <>
                <span>in</span>
                <span className="font-semibold text-blue-600 uppercase">HD</span>
              </>
            )}
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