import React, { useState, useEffect } from 'react';
import type { GeneratedProduct, CommissionInfo } from '../../types/productTypes';
import { FaExpand, FaCrown, FaStar, FaGem, FaHeart, FaPaintBrush } from 'react-icons/fa';
import { ProductModal } from './ProductModal';

interface ProductCardProps {
  product: GeneratedProduct;
}

// Helper function to get tier icon and color
const getTierDisplay = (tierName: string) => {
  const tier = tierName.toLowerCase();
  if (tier.includes('gold') || tier.includes('platinum') || tier.includes('diamond')) {
    return { icon: FaCrown, color: 'text-yellow-600', bgColor: 'bg-yellow-100' };
  } else if (tier.includes('silver')) {
    return { icon: FaStar, color: 'text-gray-600', bgColor: 'bg-gray-100' };
  } else if (tier.includes('bronze')) {
    return { icon: FaGem, color: 'text-orange-600', bgColor: 'bg-orange-100' };
  } else {
    return { icon: FaHeart, color: 'text-pink-600', bgColor: 'bg-pink-100' };
  }
};

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const [showModal, setShowModal] = useState(false);
  const [commissionInfo, setCommissionInfo] = useState<CommissionInfo | null>(null);
  const [loadingDonation, setLoadingDonation] = useState(false);

  const handleImageClick = () => {
    setShowModal(true);
  };

  // Fetch donation information when component mounts
  useEffect(() => {
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
  }, [product.pipeline_run.id]);

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
            {/* Commission indicator */}
            {commissionInfo && (
              <div className="absolute top-2 left-2">
                <div className="p-1.5 rounded-full bg-purple-100 border border-white shadow-sm" title={`Commissioned by ${commissionInfo.reddit_username}${commissionInfo.commission_message ? `: ${commissionInfo.commission_message}` : ''}`}>
                  <FaPaintBrush size={12} className="text-purple-600" />
                </div>
              </div>
            )}
            {/* Fallback to sponsor indicator if no commission info */}
            {!commissionInfo && product.product_info.sponsor_info && (
              <div className="absolute top-2 left-2">
                {(() => {
                  const tierDisplay = getTierDisplay(product.product_info.sponsor_info.tier_name);
                  const IconComponent = tierDisplay.icon;
                  return (
                    <div className={`p-1.5 rounded-full ${tierDisplay.bgColor} border border-white shadow-sm`} title={`Sponsored by ${product.product_info.sponsor_info.reddit_username} (${product.product_info.sponsor_info.tier_name})`}>
                      <IconComponent size={12} className={tierDisplay.color} />
                    </div>
                  );
                })()}
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
          <div className="text-sm text-gray-500 text-center mt-auto">
            {new Date(product.pipeline_run.end_time).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric'
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