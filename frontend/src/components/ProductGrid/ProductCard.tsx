import React, { useState, useEffect } from 'react';
import type { GeneratedProduct, CommissionInfo } from '../../types/productTypes';
import type { Task } from '../../types/taskTypes';
import { FaExpand, FaCrown, FaStar, FaGem, FaHeart, FaSpinner, FaCheckCircle, FaExclamationTriangle, FaClock, FaReddit } from 'react-icons/fa';
import { ProductModal } from './ProductModal';
import { DonationCard } from './DonationCard';
import { useDonationTiers } from '../../hooks/useDonationTiers';
import { usePublishProduct } from '../../hooks/usePublishProduct';
import DonationModal from '../common/DonationModal';
import { API_BASE } from '../../utils/apiBase';

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
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
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

  // Format date with time in a human-readable way
  const formatDateWithTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    } catch (error) {
      // Fallback to simple date if parsing fails
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    }
  };

  // Fetch donation information when component mounts
  useEffect(() => {
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
        <div className="group relative bg-white rounded-2xl shadow-sm hover:shadow-xl transition-all duration-500 flex flex-col border border-gray-100 h-full overflow-hidden transform hover:-translate-y-1 focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-opacity-50">
          {/* Image Container with Enhanced Styling */}
          <div className="relative w-full aspect-square overflow-hidden bg-gradient-to-br from-gray-50 to-gray-100">
            {/* Loading State */}
            {!imageLoaded && !imageError && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-100 animate-pulse">
                <div className="w-16 h-16 border-4 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
              </div>
            )}
            
            {/* Error State */}
            {imageError && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                <div className="text-center text-gray-500">
                  <div className="text-4xl mb-2">🖼️</div>
                  <div className="text-sm">Image unavailable</div>
                </div>
              </div>
            )}
            
            <div className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10"></div>
            <img
              src={product.product_info.image_url}
              alt={product.product_info.image_title || product.product_info.theme}
              className={`object-cover w-full h-full transition-all duration-700 group-hover:scale-110 cursor-pointer ${
                imageLoaded ? 'opacity-100' : 'opacity-0'
              }`}
              loading="lazy"
              onClick={handleImageClick}
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageError(true)}
            />
            
            {/* Enhanced Reddit Badge */}
            <a
              href={product.reddit_post.url}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute bottom-3 left-3 bg-gradient-to-r from-[#FF4500] to-[#FF6B35] text-white text-xs px-3 py-1.5 rounded-full hover:from-[#FF6B35] hover:to-[#FF4500] transition-all duration-300 shadow-lg hover:shadow-xl transform hover:scale-105 font-medium focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50"
            >
              r/{product.reddit_post.subreddit}
            </a>
            
            {/* Enhanced Expand Button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowModal(true);
              }}
              className="absolute bottom-3 right-3 text-gray-700 hover:text-gray-900 transition-all duration-300 bg-white/90 hover:bg-white backdrop-blur-sm rounded-full p-2 shadow-lg hover:shadow-xl transform hover:scale-110 z-20 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
              title="View details"
            >
              <FaExpand size={14} />
            </button>

            {/* Published Badge with Enhanced Animation */}
            {justPublished && (
              <div className="absolute top-3 right-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white text-xs px-3 py-1.5 rounded-full animate-success-pop shadow-lg font-medium">
                <span>Published to Reddit!</span>
              </div>
            )}
          </div>

          {/* Content Section with Better Typography */}
          <div className="flex-1 flex flex-col p-4 space-y-3">
            {/* Title with Enhanced Typography */}
            <h3 className="text-lg font-semibold text-gray-900 text-center leading-tight min-h-[2.5em] flex items-center justify-center line-clamp-2">
              {product.product_info.image_title || product.product_info.theme}
            </h3>
            
            {/* Enhanced Divider */}
            <div className="flex justify-center">
              <div className="w-12 h-0.5 bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
            </div>
            
            {/* Theme Caption with Better Styling */}
            <div className="flex-1">
              <p className="text-sm text-gray-600 text-center leading-relaxed font-medium line-clamp-3 px-2">
                {product.product_info.theme}
              </p>
            </div>
            
            {/* Date with Enhanced Styling */}
            <div className="text-xs text-gray-500 text-center font-medium">
              {formatDateWithTime(product.pipeline_run.end_time)}
            </div>
            
            {/* Enhanced Donation Display */}
            {totalDonationAmount > 0 && (
              <div className="text-center pt-2">
                <button 
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-gray-50 to-gray-100 hover:from-gray-100 hover:to-gray-200 transition-all duration-300 cursor-pointer shadow-sm hover:shadow-md transform hover:scale-105 border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
                  onClick={handleDonationClick}
                >
                  <span className={totalTierDisplay.color}>
                    <TotalIconComponent className={totalTierDisplay.color} size={16} />
                  </span>
                  <span className="text-sm font-medium text-gray-700">({totalDonationCount})</span>
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 flex flex-col w-full h-full max-h-full overflow-hidden">
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