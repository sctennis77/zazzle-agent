import React from 'react';
import type { GeneratedProduct, CommissionInfo } from '../../types/productTypes';
import { FaCrown, FaStar, FaGem, FaHeart, FaArrowLeft, FaHeart as FaSupport } from 'react-icons/fa';
import { useDonationTiers } from '../../hooks/useDonationTiers';

interface DonationCardProps {
  product: GeneratedProduct;
  commissionInfo: CommissionInfo | null;
  supportDonations: any[];
  onFlipBack: () => void;
  onSupport: () => void;
}

// Map icon string to actual icon component
const iconMap = {
  crown: FaCrown,
  star: FaStar,
  gem: FaGem,
  heart: FaHeart,
};

function truncate(str: string, n: number) {
  return str && str.length > n ? str.slice(0, n - 1) + '…' : str;
}

export const DonationCard: React.FC<DonationCardProps> = ({ 
  product, 
  commissionInfo, 
  supportDonations, 
  onFlipBack, 
  onSupport 
}) => {
  const { getTierDisplay } = useDonationTiers();

  // Commission row data
  const commissionTierName = product.product_info.donation_info?.tier_name || '';
  const commissionTierDisplay = getTierDisplay(commissionTierName);
  const CommissionIconComponent = commissionTierDisplay && commissionTierDisplay.icon ? 
    iconMap[commissionTierDisplay.icon.replace('Fa', '').toLowerCase() as keyof typeof iconMap] || FaHeart : FaHeart;

  // Helper for aligned row - adjusted grid to accommodate 20-char usernames
  const renderRow = (
    icon: React.ReactNode,
    username: string,
    amount: number | null | undefined,
    date: string | null | undefined,
    message: string | null | undefined,
    colorClass: string,
    bgClass: string,
    key: string = ''
  ) => (
    <div
      key={key}
      className={`grid grid-cols-[28px_140px_70px_80px_1fr] items-center gap-2 px-3 py-2 rounded-lg mb-2 text-gray-800 ${bgClass}`}
      style={{ minHeight: 0 }}
    >
      <span className={`flex-shrink-0 flex items-center justify-center ${colorClass}`}>{icon}</span>
      <span className="font-semibold text-xs break-all leading-tight" style={{ wordBreak: 'break-all' }}>
        {username || '-'}
      </span>
      <span className="font-mono text-gray-700 text-sm text-right">{amount != null ? `$${amount.toFixed(2)}` : '-'}</span>
      <span className="text-xs text-gray-500 text-right whitespace-nowrap">{date || '-'}</span>
      {message ? (
        <span
          className="text-xs text-gray-500 truncate max-w-[100px] cursor-help text-right"
          title={message}
        >
          {truncate(message, 15)}
        </span>
      ) : (
        <span className="text-xs text-gray-400 text-right">-</span>
      )}
    </div>
  );

  // Card height: match product card (e.g. min-h-[480px] or h-full if parent is fixed)
  // You may want to adjust min-h to match your actual ProductCard
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col w-full h-full min-h-[480px] relative">
      {/* Header */}
      <div className="px-4 pt-4 pb-2">
        <div className="text-xs text-gray-500 mb-1">Commissioned by</div>
        {commissionInfo && renderRow(
          <CommissionIconComponent size={18} className={commissionTierDisplay.color} />, 
          commissionInfo.is_anonymous ? 'Anonymous' : commissionInfo.reddit_username || '-',
          commissionInfo.donation_amount,
          new Date(product.pipeline_run.end_time).toLocaleDateString(),
          commissionInfo.commission_message,
          commissionTierDisplay.color,
          'bg-blue-50 border border-blue-100',
          'commission'
        )}
        <div className="text-xs text-gray-500 mt-3 mb-1">Supported by</div>
      </div>
      {/* Donation list */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {supportDonations.length > 0 ? supportDonations.map((donation) => {
          const donationTierDisplay = getTierDisplay(donation.tier_name);
          const DonationIconComponent = donationTierDisplay && donationTierDisplay.icon ? 
            iconMap[donationTierDisplay.icon.replace('Fa', '').toLowerCase() as keyof typeof iconMap] || FaHeart : FaHeart;
          return renderRow(
            <DonationIconComponent size={18} className={donationTierDisplay.color} />, 
            donation.reddit_username || '-',
            donation.donation_amount,
            donation.created_at ? new Date(donation.created_at).toLocaleDateString() : '-',
            donation.message,
            donationTierDisplay.color,
            'bg-green-50 border border-green-100',
            donation.donation_id
          );
        }) : (
          <div className="text-center text-gray-400 text-sm py-8">No support donations yet</div>
        )}
      </div>
      {/* Footer with Back and Support buttons */}
      <div className="absolute left-0 right-0 bottom-0 flex items-center justify-between px-4 py-3 bg-white rounded-b-lg border-t border-gray-100">
        <button
          onClick={onFlipBack}
          className="flex items-center gap-1 text-gray-600 hover:text-gray-800 transition-colors text-sm px-3 py-2 rounded-md border border-gray-200 bg-gray-50"
        >
          <FaArrowLeft size={16} />
          <span>Back</span>
        </button>
        <button
          onClick={onSupport}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-pink-500 to-red-500 text-white rounded-md font-semibold hover:from-pink-600 hover:to-red-600 transition-all duration-200 shadow-md hover:shadow-lg text-sm"
        >
          <FaSupport size={16} />
          Support this Post
        </button>
      </div>
    </div>
  );
}; 