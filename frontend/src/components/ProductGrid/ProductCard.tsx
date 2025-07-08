import React, { useState, useEffect } from 'react';
import type { GeneratedProduct, CommissionInfo } from '../../types/productTypes';
import type { Task } from '../../types/taskTypes';
import { FaExpand, FaCrown, FaStar, FaGem, FaHeart, FaSpinner, FaCheckCircle, FaExclamationTriangle, FaClock } from 'react-icons/fa';
import { ProductModal } from './ProductModal';
import { useDonationTiers } from '../../hooks/useDonationTiers';

interface ProductCardProps {
  product: GeneratedProduct;
  activeTasks?: Task[];
}

// Map icon string to actual icon component
const iconMap = {
  crown: FaCrown,
  star: FaStar,
  gem: FaGem,
  heart: FaHeart,
};

export const ProductCard: React.FC<ProductCardProps> = ({ product, activeTasks = [] }) => {
  const [showModal, setShowModal] = useState(false);
  const [commissionInfo, setCommissionInfo] = useState<CommissionInfo | null>(null);
  const { getTierDisplay, tiers } = useDonationTiers();
  const [supportDonations, setSupportDonations] = useState<any[]>([]);

  // Find associated task for this product by checking if it's a commission product
  // and matching with active tasks
  const associatedTask = activeTasks.find(task => {
    // For commission products, we can match by checking if the task is for a commission
    // and if this product has commission info
    return commissionInfo && task.status !== 'completed' && task.status !== 'failed';
  });

  const handleImageClick = () => {
    setShowModal(true);
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

  // Calculate support donation total and count
  const supportCount = supportDonations.length;
  const supportTotal = supportDonations.reduce((sum, d) => sum + (d.donation_amount || 0), 0);
  // Find the highest tier where supportTotal >= min_amount
  let supportTierName = '';
  if (tiers && tiers.length > 0 && supportTotal > 0) {
    const sortedTiers = [...tiers].sort((a, b) => b.min_amount - a.min_amount);
    const foundTier = sortedTiers.find(t => supportTotal >= t.min_amount);
    if (foundTier) supportTierName = foundTier.name;
  }
  const supportTierDisplay = getTierDisplay(supportTierName);
  const SupportIconComponent = supportTierDisplay && supportTierDisplay.icon ? iconMap[supportTierDisplay.icon.replace('Fa', '').toLowerCase() as keyof typeof iconMap] || FaHeart : FaHeart;

  const getTaskStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <FaCheckCircle className="text-green-500" size={12} />;
      case 'failed':
        return <FaExclamationTriangle className="text-red-500" size={12} />;
      case 'in_progress':
        return <FaSpinner className="text-blue-500 animate-spin" size={12} />;
      case 'pending':
        return <FaClock className="text-yellow-500" size={12} />;
      default:
        return <FaClock className="text-gray-500" size={12} />;
    }
  };

  const getTaskStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 border-green-300';
      case 'failed':
        return 'bg-red-100 border-red-300';
      case 'in_progress':
        return 'bg-blue-100 border-blue-300';
      case 'pending':
        return 'bg-yellow-100 border-yellow-300';
      default:
        return 'bg-gray-100 border-gray-300';
    }
  };

  // For commission products, use commissionInfo and donation_info for tier
  let tierName = '';
  if (commissionInfo && product.product_info.donation_info) {
    tierName = product.product_info.donation_info.tier_name;
  } else if (product.product_info.donation_info) {
    tierName = product.product_info.donation_info.tier_name;
  }
  const tierDisplay = getTierDisplay(tierName);
  const IconComponent = iconMap[tierDisplay.icon.replace('Fa', '').toLowerCase() as keyof typeof iconMap] || FaHeart;

  return (
    <>
      <div
        className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow duration-300 flex flex-col border border-gray-200 group h-full"
      >
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
            
            {/* Task status indicator for commission products */}
            {commissionInfo && associatedTask && (
              <div className="absolute top-2 left-2">
                <div className={`p-1 rounded-full border ${getTaskStatusColor(associatedTask.status)}`} title={`Task ${associatedTask.status}`}>
                  {getTaskStatusIcon(associatedTask.status)}
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex flex-col flex-1 px-5 pb-5">
          <h3 className="text-base font-medium text-gray-800 text-center cursor-pointer leading-relaxed" style={{ minHeight: '2.5em', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
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
          
          {/* Task status info for commission products */}
          {associatedTask && (
            <div className="mt-2 text-xs text-center">
              <div className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full ${getTaskStatusColor(associatedTask.status)}`}>
                {getTaskStatusIcon(associatedTask.status)}
                <span className="capitalize">{associatedTask.status.replace('_', ' ')}</span>
              </div>
            </div>
          )}
          
          {/* Unified footer for commission/support info and date */}
          <div className="mt-3 pt-3 border-t border-gray-100">
            <div className="flex items-center justify-between text-xs text-gray-600">
              <span className="flex items-center gap-1 min-w-0">
                {commissionInfo && <><IconComponent size={12} className={tierDisplay.color} />{commissionInfo.is_anonymous ? 'Anonymous' : commissionInfo.reddit_username ? `u/${commissionInfo.reddit_username}` : 'Anonymous'}</>}
              </span>
              <span className="truncate text-center flex-1">{new Date(product.pipeline_run.end_time).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</span>
              <span className="flex items-center gap-1 min-w-0 justify-end">
                {supportCount > 0 ? <><SupportIconComponent size={12} className={supportTierDisplay.color} />{supportCount}</> : <span className="opacity-40 flex items-center gap-1"><FaHeart size={12} />0</span>}
              </span>
            </div>
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