import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

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
  source?: string;
}

interface SubredditDonations {
  commission: DonationData | null;
  support: DonationData[];
}

interface FundraisingData {
  [subreddit: string]: SubredditDonations;
}

interface SubredditGoal {
  id: number;
  subreddit_id: number;
  subreddit_name: string;
  goal_amount: number;
  current_amount: number;
  status: string;
  created_at: string;
  completed_at?: string;
}

interface FundraisingProgress {
  overall_raised: number;
  overall_goal: number;
  overall_progress_percentage: number;
  overall_reward: string;
  subreddit_goals: SubredditGoal[];
  subreddit_goal_amount: number;
  subreddit_goal_reward: string;
}

interface TierSummary {
  count: number;
  amount: number;
}

interface LeaderboardRow {
  subreddit: string;
  tiers: { [tier: string]: TierSummary };
  communityTiers: { [tier: string]: TierSummary };
  total: number;
  totalDonations: number;
  communityTotal: number;
  communityDonations: number;
  selfCommissions: number;
  selfCommissionTotal: number;
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
    
    // Separate community and self-commissioned donations
    const communityDonations = allDonations.filter(d => d.source === null || d.source === 'stripe');
    const selfCommissionedDonations = allDonations.filter(d => d.source === 'manual');
    
    const tiers: { [tier: string]: TierSummary } = {};
    const communityTiers: { [tier: string]: TierSummary } = {};
    let total = 0;
    let communityTotal = 0;
    let selfCommissionTotal = 0;
    
    // Process all donations for overall tier display
    allDonations.forEach(donation => {
      const tier = donation.tier_name.toLowerCase();
      if (!tiers[tier]) tiers[tier] = { count: 0, amount: 0 };
      tiers[tier].count += 1;
      tiers[tier].amount += donation.donation_amount;
      total += donation.donation_amount;
    });
    
    // Process only community donations for community tier display
    communityDonations.forEach(donation => {
      const tier = donation.tier_name.toLowerCase();
      if (!communityTiers[tier]) communityTiers[tier] = { count: 0, amount: 0 };
      communityTiers[tier].count += 1;
      communityTiers[tier].amount += donation.donation_amount;
    });
    
    // Calculate community and self-commission totals
    communityTotal = communityDonations.reduce((sum, d) => sum + d.donation_amount, 0);
    selfCommissionTotal = selfCommissionedDonations.reduce((sum, d) => sum + d.donation_amount, 0);
    
    return { 
      subreddit, 
      tiers, 
      communityTiers,
      total, 
      totalDonations: allDonations.length,
      communityTotal,
      communityDonations: communityDonations.length,
      selfCommissions: selfCommissionedDonations.length,
      selfCommissionTotal
    };
  }).sort((a, b) => b.total - a.total);
}

interface Props {
  data: FundraisingData;
  fundraisingProgress: FundraisingProgress | null;
}

const DonationsLeaderboardTable: React.FC<Props> = ({ data, fundraisingProgress }) => {
  const [showAll, setShowAll] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const rows = summarizeLeaderboard(data);
  // Find which tiers are present in the data
  const presentTiers = TIER_ORDER.filter(tier => rows.some(row => row.tiers[tier]));

  // Determine which rows to display
  const displayedRows = showAll ? rows : rows.slice(0, 5);
  const hasMoreRows = rows.length > 5;

  // Compute max total for scaling bar widths (always use amount mode)
  const maxTotal = Math.max(
    ...rows.map(row => row.total),
    1 // avoid division by zero
  );
  const MAX_BAR_WIDTH = 384; // px (24rem, expanded to take more space)
  const BAR_HEIGHT = 16; // px

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Header with description - always visible */}
      <div className="p-6">
        <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">⭐ Community Fundraising Leaderboard</h3>
              <p className="text-sm text-gray-600">
                Support your favorite subreddits and help maintain Clouvel. 🤍
              </p>
            </div>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="ml-4 p-2 hover:bg-blue-100 rounded-lg transition-colors duration-200 flex items-center justify-center"
              aria-label={isExpanded ? 'Collapse leaderboard' : 'Expand leaderboard'}
            >
              {isExpanded ? (
                <ChevronUp className="w-5 h-5 text-gray-600" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-600" />
              )}
            </button>
          </div>
        </div>
      </div>
      
      {/* Collapsible content */}
      <div 
        className={`transition-all duration-300 ease-in-out ${
          isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0 overflow-hidden'
        }`}
      >
        <div className="p-6 pt-4 overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left px-3 py-3 font-semibold text-gray-700 bg-gray-50">Subreddit</th>
            <th className="text-center px-3 py-3 font-semibold text-gray-700 bg-gray-50">Community Donations</th>
            <th className="text-center px-3 py-3 font-semibold text-gray-700 bg-gray-50">Self Commissions</th>
            <th className="text-left px-3 py-3 font-semibold text-gray-700 bg-gray-50" style={{ width: '40%' }}>Fundraising Progress</th>
            <th className="text-right px-3 py-3 font-semibold text-gray-700 bg-gray-50">Total ($)</th>
          </tr>
        </thead>
        <tbody>
          {displayedRows.map(row => {
            // For the stacked bar: sum all donation amounts per tier
            const totalValue = presentTiers.reduce((sum, tier) => sum + (row.tiers[tier]?.amount || 0), 0) || 1;
            const totalDisplay = row.total;
            // Calculate bar width
            const barWidth = Math.max(8, (totalDisplay / maxTotal) * MAX_BAR_WIDTH);
            return (
              <tr key={row.subreddit} className="border-b hover:bg-gray-50 transition-colors">
                <td className="px-3 py-4 font-medium text-gray-900 whitespace-nowrap">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <span className="font-semibold">r/{row.subreddit}</span>
                  </div>
                </td>
                <td className="px-3 py-4 text-center">
                  <div className="flex flex-col items-center">
                    <span className="font-bold text-xl text-blue-600">{row.communityDonations}</span>
                    <span className="text-xs text-gray-500 font-medium">donations</span>
                  </div>
                </td>
                <td className="px-3 py-4 text-center">
                  <div className="flex flex-col items-center">
                    <span className="font-bold text-xl text-rose-400">{row.selfCommissions}</span>
                    <span className="text-xs text-gray-500 font-medium">commissions</span>
                  </div>
                </td>
                <td className="px-3 py-4">
                  <div className="space-y-2">
                    {/* Community Fundraising Progress Bar */}
                    {(() => {
                      const goal = fundraisingProgress?.subreddit_goals.find(g => g.subreddit_name === row.subreddit);
                      const goalAmount = Number(fundraisingProgress?.subreddit_goal_amount || 1000);
                      const currentAmount = row.communityTotal; // Only community donations count toward goal
                      const progressPercentage = Math.min((currentAmount / goalAmount) * 100, 100);
                      
                      return (
                        <div className="space-y-1">
                          <div className="flex justify-between items-center text-xs">
                            <span className="text-gray-600">Fundraising Goal</span>
                            <span className={`font-medium ${
                              goal?.status === 'completed' 
                                ? 'text-green-600' 
                                : progressPercentage >= 50 
                                  ? 'text-blue-600'
                                  : 'text-gray-700'
                            }`}>
                              {progressPercentage.toFixed(1)}%
                              {goal?.status === 'completed' && ' ✓'}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full transition-all duration-500 ${
                                goal?.status === 'completed'
                                  ? 'bg-green-500'
                                  : progressPercentage >= 50
                                    ? 'bg-blue-500'
                                    : 'bg-gray-400'
                              }`}
                              style={{ width: `${progressPercentage}%` }}
                            />
                          </div>
                        </div>
                      );
                    })()}

                    {/* Self Commission Progress Bar */}
                    {row.selfCommissionTotal > 0 && (() => {
                      const selfCommissionPercentage = Math.min((row.selfCommissionTotal / 1000) * 100, 100);
                      
                      return (
                        <div className="space-y-1">
                          <div className="flex justify-between items-center text-xs">
                            <span className="text-rose-400">Self Commissions</span>
                            <span className="font-medium text-rose-400">
                              ${row.selfCommissionTotal.toFixed(0)}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="h-2 rounded-full transition-all duration-500 bg-rose-400"
                              style={{ width: `${selfCommissionPercentage}%` }}
                            />
                          </div>
                        </div>
                      );
                    })()}
                    
                    {/* Community Donations Tier Distribution Bar */}
                    <div className="space-y-1">
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-blue-600">Community Donations</span>
                        <span className="font-medium text-blue-600">
                          ${row.communityTotal.toFixed(0)}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="h-2 rounded-full transition-all duration-500 flex overflow-hidden"
                          style={{ width: `${Math.min((row.communityTotal / Math.max(...rows.map(r => r.communityTotal), 1)) * 100, 100)}%` }}
                        >
                          {presentTiers.map(tier => {
                            const tierData = row.communityTiers[tier];
                            if (!tierData) return null;
                            const value = tierData.amount;
                            const width = row.communityTotal > 0 ? (value / row.communityTotal) * 100 : 0;
                            return (
                              <div
                                key={tier}
                                style={{
                                  width: `${width}%`,
                                  background: TIER_COLORS[tier],
                                  borderRight: width > 0 ? '1px solid #fff' : 'none',
                                  transition: 'width 0.3s',
                                }}
                                title={`${TIER_NAMES[tier]}: $${tierData.amount.toFixed(2)} (${tierData.count} community donation${tierData.count > 1 ? 's' : ''})`}
                              />
                            );
                          })}
                        </div>
                      </div>
                    </div>
                    
                    {/* Reward Text */}
                    {(() => {
                      const goal = fundraisingProgress?.subreddit_goals.find(g => g.subreddit_name === row.subreddit);
                      const goalAmount = Number(fundraisingProgress?.subreddit_goal_amount || 1000);
                      const currentAmount = row.communityTotal; // Only community donations count toward goal
                      
                      if (goal?.status === 'completed') {
                        return (
                          <div className="text-xs text-green-600 font-medium">
                            🎨 Goal reached! Banner art commissioned
                          </div>
                        );
                      } else {
                        const remaining = Math.max(0, goalAmount - currentAmount);
                        return (
                          <div className="text-xs text-gray-600">
                            ${remaining.toFixed(0)} more for custom banner art by Clouvel
                          </div>
                        );
                      }
                    })()}
                  </div>
                </td>
                <td className="text-right px-3 py-4 font-bold text-gray-900">
                  ${row.communityTotal.toFixed(2)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      
      {/* Show More/Less Button */}
      {hasMoreRows && (
        <div className="mt-4 text-center">
          <button
            onClick={() => setShowAll(!showAll)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 hover:text-indigo-700 transition-colors duration-200"
          >
            {showAll ? (
              <>
                <span>Show Less</span>
                <svg 
                  className="w-4 h-4" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M5 15l7-7 7 7" 
                  />
                </svg>
              </>
            ) : (
              <>
                <span>Show More ({rows.length - 5} more)</span>
                <svg 
                  className="w-4 h-4" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M19 9l-7 7-7-7" 
                  />
                </svg>
              </>
            )}
          </button>
        </div>
      )}
        </div>
      </div>
    </div>
  );
};

export default DonationsLeaderboardTable; 