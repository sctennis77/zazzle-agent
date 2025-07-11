import React, { useState, useEffect } from 'react';
import type { GeneratedProduct, CommissionInfo } from '../../types/productTypes';
import type { Task } from '../../types/taskTypes';
import { FaExpand, FaCrown, FaStar, FaGem, FaHeart, FaSpinner, FaCheckCircle, FaExclamationTriangle, FaClock, FaReddit } from 'react-icons/fa';
import { ProductModal } from './ProductModal';
import { DonationCard } from './DonationCard';
import { useDonationTiers } from '../../hooks/useDonationTiers';
import { usePublishProduct } from '../../hooks/usePublishProduct';
import DonationModal from '../common/DonationModal';

interface ProductCardProps {
  product: GeneratedProduct;
  activeTasks?: Task[];
  justPublished?: boolean;
}

// Map icon string to actual icon component
const iconMap = {
  crown: FaCrown,
  star: FaStar,
  gem: FaGem,
  heart: FaHeart,
};

export const ProductCard: React.FC<ProductCardProps> = ({ product, activeTasks = [], justPublished }) => {
  const [showModal, setShowModal] = useState(false);
  const [commissionInfo, setCommissionInfo] = useState<CommissionInfo | null>(null);
  const [supportDonations, setSupportDonations] = useState<any[]>([]);
  const [isFlipped, setIsFlipped] = useState(false);
  const [showDonationModal, setShowDonationModal] = useState(false);
  const [showPublishAnimation, setShowPublishAnimation] = useState(false);
  const { getTierDisplay, tiers } = useDonationTiers();
  const { publishing, publishedPost, publishProduct, getPublishedPost } = usePublishProduct();

  // Find associated task for this product by checking if it's a commission product
  // and matching with active tasks
  const associatedTask = activeTasks.find(task => {
    return commissionInfo && task.status !== 'completed' && task.status !== 'failed';
  });

  // Add back showTaskStatus logic, but only render the status indicator if associatedTask exists and is in progress or pending
  const showTaskStatus = associatedTask && (associatedTask.status === 'in_progress' || associatedTask.status === 'pending');

  const handleImageClick = () => {
    setShowModal(true);
  };

  const handleDonationClick = () => {
    setIsFlipped(true);
  };

  const handleFlipBack = () => {
    setIsFlipped(false);
  };

  const handleSupport = () => {
    setShowDonationModal(true);
  };

  // Fetch donation information when component mounts
  useEffect(() => {
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
    fetchDonationInfo();
  }, [product.pipeline_run.id]);

  // For commission products, use commissionInfo and donation_info for tier
  let tierName = '';
  if (commissionInfo && product.product_info.donation_info) {
    tierName = product.product_info.donation_info.tier_name;
  } else if (product.product_info.donation_info) {
    tierName = product.product_info.donation_info.tier_name;
  }
  const tierDisplay = getTierDisplay(tierName);
  const IconComponent = iconMap[tierDisplay.icon.replace('Fa', '').toLowerCase() as keyof typeof iconMap] || FaHeart;

  // Calculate total donation amount and count
  const commissionAmount = commissionInfo?.donation_amount || 0;
  const supportAmount = supportDonations.reduce((sum, d) => sum + (d.donation_amount || 0), 0);
  const totalDonationAmount = commissionAmount + supportAmount;
  const totalDonationCount = (commissionInfo ? 1 : 0) + supportDonations.length;
  
  // Get tier based on total amount
  let totalTierName = '';
  if (tiers && tiers.length > 0 && totalDonationAmount > 0) {
    const sortedTiers = [...tiers].sort((a, b) => b.min_amount - a.min_amount);
    const foundTier = sortedTiers.find(t => totalDonationAmount >= t.min_amount);
    if (foundTier) totalTierName = foundTier.name;
  }
  const totalTierDisplay = getTierDisplay(totalTierName);
  const TotalIconComponent = totalTierDisplay && totalTierDisplay.icon ? 
    iconMap[totalTierDisplay.icon.replace('Fa', '').toLowerCase() as keyof typeof iconMap] || FaHeart : FaHeart;

  return (
    <>
      {!isFlipped ? (
        <div className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow duration-300 flex flex-col border border-gray-200 group h-full">
          <div className="w-full aspect-square overflow-hidden rounded-t-lg flex items-center justify-center bg-gray-100 relative">
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
          <h3 className="text-base font-medium text-gray-800 text-center cursor-pointer leading-relaxed min-h-[2.5em] flex items-center justify-center">
            {product.product_info.image_title || product.product_info.theme}
          </h3>
          <div className="flex justify-center">
            <div className="w-8 h-px bg-gray-300"></div>
          </div>
          {/* Theme Caption */}
          <div className="mt-2 pb-2">
            <p className="text-sm text-gray-600 italic text-center leading-relaxed">
              {product.product_info.theme}
            </p>
          </div>
          {/* Remove publish animation and published status from card */}
          <div className="text-sm text-gray-500 text-center mt-auto">
            {new Date(product.pipeline_run.end_time).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric'
            })}
          </div>
          {/* Total donation display - clickable for flip effect */}
          {totalDonationAmount > 0 && (
            <div className="mt-2 text-center">
              <button 
                className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gray-50 hover:bg-gray-100 transition-colors cursor-pointer"
                onClick={handleDonationClick}
              >
                <span className={totalTierDisplay.color}>
                  <TotalIconComponent className={totalTierDisplay.color} size={14} />
                </span>
                <span className="text-sm text-gray-600">({totalDonationCount})</span>
              </button>
            </div>
          )}
          {justPublished && (
            <div className="absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full animate-success-pop">
              <span>Published to Reddit!</span>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col w-full h-full max-h-full">
          <DonationCard
            product={product}
            commissionInfo={commissionInfo}
            supportDonations={supportDonations}
            onFlipBack={handleFlipBack}
            onSupport={handleSupport}
          />
          <DonationModal
            isOpen={showDonationModal}
            onClose={() => setShowDonationModal(false)}
            subreddit={product.reddit_post.subreddit}
            postId={product.reddit_post.post_id}
            supportOnly={true}
          />
        </div>
      )}
      
      {/* Product Modal */}
      <ProductModal
        product={product}
        isOpen={showModal}
        onClose={() => setShowModal(false)}
      />
    </>
  );
}; 