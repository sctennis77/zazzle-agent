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
    icon: React.ReactNode,
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
        className={`mb-2 ${bgClass} rounded-lg px-3 pt-2 pb-1 min-h-0`}
        onMouseEnter={() => setHoveredRow(key)}
        onMouseLeave={() => setHoveredRow(null)}
      >
        {/* Main row: icon, username, amount, date */}
        <div className="grid grid-cols-2 sm:grid-cols-[24px_1fr_70px] md:grid-cols-[24px_1fr_90px] items-center gap-2 pb-0.5">
          <span className={`flex-shrink-0 flex items-center justify-center ${colorClass}`}>{icon}</span>
          <span className={`font-semibold text-xs max-w-[150px] whitespace-nowrap overflow-hidden ${username.length > 16 ? 'text-[11px]' : 'text-[13px]'}`}>
            {username || '-'}
          </span>
          <span className="flex flex-col items-end">
            <span className="font-mono text-gray-700 text-xs">{amount != null ? `$${amount.toFixed(2)}` : '-'}</span>
            <span className="text-[11px] text-gray-400 leading-tight">{formatShortDate(date)}</span>
          </span>
        </div>
        {/* Message row, only on hover */}
        {hoveredRow === key && (
          <div className="ml-7 pl-2 text-xs text-gray-400 leading-snug break-words min-h-[18px]">
            {tooltip}
          </div>
        )}
      </div>
    );
  };

  // Card height: match product card (e.g. min-h-[480px] or h-full if parent is fixed)
  // You may want to adjust min-h to match your actual ProductCard
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col w-full max-w-2xl mx-auto h-full min-h-[480px] relative">
      {/* Header */}
      <div className="px-4 pt-4 pb-2">
        <div className="text-xs text-gray-500 mb-1">Commissioned by</div>
        {commissionInfo && renderRow(
          <CommissionIconComponent size={18} className={commissionTierDisplay.color} />, 
          commissionInfo.is_anonymous ? 'Anonymous' : commissionInfo.reddit_username || '-',
          commissionInfo.donation_amount,
          product.pipeline_run.end_time,
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
            donation.created_at,
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
          className="flex items-center justify-center w-9 h-9 rounded-full border border-gray-200 bg-gray-50 text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
          title="Flip back"
        >
          <FaArrowLeft size={18} />
        </button>
        <button
          onClick={onSupport}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-pink-500 to-red-500 text-white rounded-md font-semibold hover:from-pink-600 hover:to-red-600 transition-all duration-200 shadow-md hover:shadow-lg text-sm"
        >
          <FaSupport size={16} />
          Support
        </button>
      </div>
    </div>
  );
}; 