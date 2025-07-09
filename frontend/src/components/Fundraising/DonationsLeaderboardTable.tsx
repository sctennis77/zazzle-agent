import React, { useState } from 'react';

interface DonationData {
  reddit_username: string;
  tier_name: string;
  tier_min_amount: number;
  donation_amount: number;
  is_anonymous: boolean;
  message?: string;
  created_at: string;
  donation_id: number;
  commission_message?: string;
  commission_type?: string;
}

interface SubredditDonations {
  commission: DonationData | null;
  support: DonationData[];
}

interface FundraisingData {
  [subreddit: string]: SubredditDonations;
}

interface TierSummary {
  count: number;
  amount: number;
}

interface LeaderboardRow {
  subreddit: string;
  tiers: { [tier: string]: TierSummary };
  total: number;
}

const TIER_ORDER = [
  'gold', 'silver', 'bronze', 'platinum', 'emerald', 'topaz', 'ruby', 'sapphire'
];
const TIER_COLORS: { [tier: string]: string } = {
  gold: '#FFD700',
  silver: '#C0C0C0',
  bronze: '#CD7F32',
  platinum: '#E5E4E2',
  emerald: '#50C878',
  topaz: '#FFC87C',
  ruby: '#E0115F',
  sapphire: '#0F52BA',
};
const TIER_NAMES: { [tier: string]: string } = {
  gold: 'Gold',
  silver: 'Silver',
  bronze: 'Bronze',
  platinum: 'Platinum',
  emerald: 'Emerald',
  topaz: 'Topaz',
  ruby: 'Ruby',
  sapphire: 'Sapphire',
};

function summarizeLeaderboard(data: FundraisingData): LeaderboardRow[] {
  return Object.entries(data).map(([subreddit, donations]) => {
    const allDonations = [
      ...(donations.commission ? [donations.commission] : []),
      ...donations.support
    ];
    const tiers: { [tier: string]: TierSummary } = {};
    let total = 0;
    allDonations.forEach(donation => {
      const tier = donation.tier_name.toLowerCase();
      if (!tiers[tier]) tiers[tier] = { count: 0, amount: 0 };
      tiers[tier].count += 1;
      tiers[tier].amount += donation.donation_amount;
      total += donation.donation_amount;
    });
    return { subreddit, tiers, total };
  }).sort((a, b) => b.total - a.total);
}

interface Props {
  data: FundraisingData;
}

const DonationsLeaderboardTable: React.FC<Props> = ({ data }) => {
  const [mode, setMode] = useState<'count' | 'amount'>('amount');
  const rows = summarizeLeaderboard(data);
  // Find which tiers are present in the data
  const presentTiers = TIER_ORDER.filter(tier => rows.some(row => row.tiers[tier]));

  // Compute max total for scaling bar widths
  const maxTotal = Math.max(
    ...rows.map(row =>
      mode === 'amount'
        ? row.total
        : presentTiers.reduce((sum, tier) => sum + (row.tiers[tier]?.count || 0), 0)
    ),
    1 // avoid division by zero
  );
  const MAX_BAR_WIDTH = 192; // px (12rem, matches w-48)
  const BAR_HEIGHT = 16; // px

  return (
    <div className="overflow-x-auto bg-white rounded-xl shadow-lg p-6">
      {/* Toggle */}
      <div className="flex items-center mb-4">
        <span className="mr-3 font-medium text-gray-700">Show:</span>
        <button
          className={`px-3 py-1 rounded-l border border-gray-300 font-semibold transition-colors ${mode === 'amount' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
          onClick={() => setMode('amount')}
        >
          $
        </button>
        <button
          className={`px-3 py-1 rounded-r border-t border-b border-r border-gray-300 font-semibold transition-colors ${mode === 'count' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
          onClick={() => setMode('count')}
        >
          #
        </button>
      </div>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left px-2 py-2 font-semibold text-gray-700">Subreddit</th>
            <th className="text-left px-2 py-2 font-semibold text-gray-700">Donations</th>
            {presentTiers.map(tier => (
              <th key={tier} className="text-center px-2 py-2 font-semibold" style={{ color: TIER_COLORS[tier] }}>{TIER_NAMES[tier]}</th>
            ))}
            <th className="text-right px-2 py-2 font-semibold text-gray-700">Total {mode === 'amount' ? '($)' : '(#)'}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
            // For the stacked bar: sum all donation counts or amounts per tier
            const totalValue = mode === 'count'
              ? presentTiers.reduce((sum, tier) => sum + (row.tiers[tier]?.count || 0), 0) || 1
              : presentTiers.reduce((sum, tier) => sum + (row.tiers[tier]?.amount || 0), 0) || 1;
            const totalDisplay = mode === 'count'
              ? presentTiers.reduce((sum, tier) => sum + (row.tiers[tier]?.count || 0), 0)
              : row.total;
            // Calculate bar width
            const barWidth = Math.max(8, (totalDisplay / maxTotal) * MAX_BAR_WIDTH);
            return (
              <tr key={row.subreddit} className="border-b hover:bg-gray-50">
                <td className="px-2 py-2 font-medium text-gray-900 whitespace-nowrap">r/{row.subreddit}</td>
                <td className="px-2 py-2">
                  <div
                    className="relative rounded overflow-hidden border border-gray-200"
                    style={{ width: `${MAX_BAR_WIDTH}px`, height: `${BAR_HEIGHT}px` }}
                  >
                    {/* Unfilled bar (track) */}
                    <div
                      className="absolute left-0 top-0 h-full w-full bg-gray-200"
                      style={{ zIndex: 0 }}
                    />
                    {/* Filled stacked bar */}
                    <div
                      className="absolute left-0 top-0 h-full flex"
                      style={{ width: `${barWidth}px`, zIndex: 1, transition: 'width 0.3s' }}
                    >
                      {presentTiers.map(tier => {
                        const tierData = row.tiers[tier];
                        if (!tierData) return null;
                        const value = mode === 'count' ? tierData.count : tierData.amount;
                        const width = (value / totalValue) * 100;
                        return (
                          <div
                            key={tier}
                            style={{
                              width: `${width}%`,
                              background: TIER_COLORS[tier],
                              borderRight: '1px solid #fff',
                              transition: 'width 0.3s',
                            }}
                            title={
                              mode === 'count'
                                ? `${TIER_NAMES[tier]}: ${tierData.count} donation${tierData.count > 1 ? 's' : ''}`
                                : `${TIER_NAMES[tier]}: $${tierData.amount.toFixed(2)}`
                            }
                          />
                        );
                      })}
                    </div>
                  </div>
                </td>
                {presentTiers.map(tier => {
                  const tierData = row.tiers[tier];
                  return (
                    <td key={tier} className="text-center px-2 py-2 font-mono">
                      {tierData
                        ? mode === 'count'
                          ? tierData.count
                          : `$${tierData.amount.toFixed(2)}`
                        : <span className="text-gray-300">–</span>}
                    </td>
                  );
                })}
                <td className="text-right px-2 py-2 font-bold text-gray-900">
                  {mode === 'count' ? totalDisplay : `$${totalDisplay.toFixed(2)}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default DonationsLeaderboardTable; 