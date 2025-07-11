import React, { useState } from 'react';
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

// Use the same date formatting as ProductCard
function formatDateWithTime(date: string | Date | null | undefined) {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
}

function formatShortDate(date: string | Date | null | undefined) {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return `${d.getMonth() + 1}/${d.getDate()}/${String(d.getFullYear()).slice(-2)}`;
}

function truncateWithEllipsis(str: string, n: number) {
  if (!str) return '-';
  return str.length > n ? str.slice(0, n - 1) + '…' : str;
}

const MAX_MSG_LEN = 32;

export const DonationCard: React.FC<DonationCardProps> = ({ 
  product, 
  commissionInfo, 
  supportDonations, 
  onFlipBack, 
  onSupport 
}) => {
  const { getTierDisplay } = useDonationTiers();
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);

  // Commission row data
  const commissionTierName = product.product_info.donation_info?.tier_name || '';
  const commissionTierDisplay = getTierDisplay(commissionTierName);
  const CommissionIconComponent = commissionTierDisplay && commissionTierDisplay.icon ? 
    iconMap[commissionTierDisplay.icon.replace('Fa', '').toLowerCase() as keyof typeof iconMap] || FaHeart : FaHeart;

  // Helper for aligned row with hover message
  const renderRow = (
    icon: React.ReactElement,
    username: string,
    amount: number | null | undefined,
    date: string | Date | null | undefined,
    message: string | null | undefined,
    colorClass: string,
    bgClass: string,
    key: string = ''
  ) => {
    const hasMsg = !!message && message.trim() !== '';
    const tooltip = hasMsg ? message : '-';
    return (
      <div
        key={key}
        className={`mb-3 ${bgClass} rounded-xl px-4 py-2 min-h-0 flex items-center shadow-sm transition-all duration-200 group hover:shadow-md focus-within:ring-2 focus-within:ring-blue-400`}
        onMouseEnter={() => setHoveredRow(key)}
        onMouseLeave={() => setHoveredRow(null)}
        tabIndex={hasMsg ? 0 : -1}
      >
        {/* Icon */}
        <span className={`flex-shrink-0 flex items-center justify-center ${colorClass} mr-1`}>
          {icon}
        </span>
        {/* Username and message */}
        <span className={`font-semibold max-w-[180px] whitespace-nowrap overflow-hidden ${username.length > 20 ? 'truncate text-[11px]' : 'text-[12px]'}`} title={username}>
          {username || '-'}
        </span>
        {/* Amount and date */}
        <span className="flex flex-col items-end ml-auto">
          <span className="font-mono text-gray-700 text-sm">{amount != null ? `$${amount.toFixed(2)}` : '-'}</span>
          <span className="text-[11px] text-gray-400 leading-tight">{formatShortDate(date)}</span>
        </span>
        {/* Tooltip for message */}
        {hasMsg && hoveredRow === key && (
          <div className="absolute left-1/2 top-full mt-2 -translate-x-1/2 bg-white border border-gray-200 rounded-lg shadow-lg px-4 py-2 text-xs text-gray-700 z-30 w-64 max-w-xs">
            {tooltip}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-gray-100 flex flex-col w-full max-w-lg mx-auto h-full min-h-[480px] relative overflow-hidden">
      {/* Header */}
      <div className="px-6 pt-6 pb-2">
        <div className="text-xs text-gray-500 mb-2 font-semibold tracking-wide">Commissioned by</div>
        {commissionInfo && renderRow(
          <CommissionIconComponent size={15} className={commissionTierDisplay.color} />, 
          commissionInfo.is_anonymous ? 'Anonymous' : commissionInfo.reddit_username || '-',
          commissionInfo.donation_amount,
          product.pipeline_run.end_time,
          commissionInfo.commission_message,
          commissionTierDisplay.color,
          'bg-blue-50 border border-blue-100',
          'commission'
        )}
        <div className="text-xs text-gray-500 mt-4 mb-2 font-semibold tracking-wide">Supported by</div>
      </div>
      {/* Donation list */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {supportDonations.length > 0 ? supportDonations.map((donation) => {
          const donationTierDisplay = getTierDisplay(donation.tier_name);
          const DonationIconComponent = donationTierDisplay && donationTierDisplay.icon ? 
            iconMap[donationTierDisplay.icon.replace('Fa', '').toLowerCase() as keyof typeof iconMap] || FaHeart : FaHeart;
          return renderRow(
            <DonationIconComponent size={15} className={donationTierDisplay.color} />, 
            donation.reddit_username || '-',
            donation.donation_amount,
            donation.created_at,
            donation.message,
            donationTierDisplay.color,
            'bg-green-50 border border-green-100',
            donation.donation_id
          );
        }) : (
          <div className="text-center text-gray-400 text-base py-12 font-medium">No support donations yet</div>
        )}
      </div>
      {/* Footer with Back and Support buttons */}
      <div className="absolute left-0 right-0 bottom-0 flex items-center justify-between px-6 py-4 bg-white rounded-b-2xl border-t border-gray-100 shadow-md">
        <button
          onClick={onFlipBack}
          className="flex items-center justify-center w-10 h-10 rounded-full border border-gray-200 bg-gray-50 text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-all focus:outline-none focus:ring-2 focus:ring-blue-400"
          title="Flip back"
        >
          <FaArrowLeft size={18} />
        </button>
        <button
          onClick={onSupport}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-pink-500 to-red-500 text-white rounded-xl font-bold hover:from-pink-600 hover:to-red-600 transition-all duration-200 shadow-lg hover:shadow-xl text-base focus:outline-none focus:ring-2 focus:ring-pink-400"
        >
          <FaSupport size={18} />
          Support
        </button>
      </div>
    </div>
  );
}; 