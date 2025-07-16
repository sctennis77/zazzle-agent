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
  total: number;
  totalDonations: number;
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
    const totalDonations = allDonations.length;
    allDonations.forEach(donation => {
      const tier = donation.tier_name.toLowerCase();
      if (!tiers[tier]) tiers[tier] = { count: 0, amount: 0 };
      tiers[tier].count += 1;
      tiers[tier].amount += donation.donation_amount;
      total += donation.donation_amount;
    });
    return { subreddit, tiers, total, totalDonations };
  }).sort((a, b) => b.total - a.total);
}

interface Props {
  data: FundraisingData;
  fundraisingProgress: FundraisingProgress | null;
}

const DonationsLeaderboardTable: React.FC<Props> = ({ data, fundraisingProgress }) => {
  const rows = summarizeLeaderboard(data);
  // Find which tiers are present in the data
  const presentTiers = TIER_ORDER.filter(tier => rows.some(row => row.tiers[tier]));

  // Compute max total for scaling bar widths (always use amount mode)
  const maxTotal = Math.max(
    ...rows.map(row => row.total),
    1 // avoid division by zero
  );
  const MAX_BAR_WIDTH = 384; // px (24rem, expanded to take more space)
  const BAR_HEIGHT = 16; // px

  return (
    <div className="overflow-x-auto bg-white rounded-xl shadow-lg p-6">
      {/* Header with description */}
      <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">Community Fundraising Leaderboard</h3>
        <p className="text-sm text-gray-600">
          Support your favorite subreddits to unlock custom banner art! When a community reaches its $1,000 goal, 
          Claude will create beautiful, personalized banner artwork for that subreddit.
        </p>
      </div>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left px-3 py-3 font-semibold text-gray-700 bg-gray-50">Subreddit</th>
            <th className="text-center px-3 py-3 font-semibold text-gray-700 bg-gray-50">Total Donations</th>
            <th className="text-left px-3 py-3 font-semibold text-gray-700 bg-gray-50" style={{ width: '50%' }}>Fundraising Progress</th>
            <th className="text-right px-3 py-3 font-semibold text-gray-700 bg-gray-50">Total ($)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
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
                    <span className="font-bold text-xl text-gray-900">{row.totalDonations}</span>
                    <span className="text-xs text-gray-500 font-medium">donations</span>
                  </div>
                </td>
                <td className="px-3 py-4">
                  <div className="space-y-2">
                    {/* Fundraising Progress Bar */}
                    {(() => {
                      const goal = fundraisingProgress?.subreddit_goals.find(g => g.subreddit_name === row.subreddit);
                      const goalAmount = Number(fundraisingProgress?.subreddit_goal_amount || 1000);
                      const currentAmount = row.total;
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
                    
                    {/* Tier Distribution Bar */}
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
                        const value = tierData.amount;
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
                            title={`${TIER_NAMES[tier]}: $${tierData.amount.toFixed(2)} (${tierData.count} donation${tierData.count > 1 ? 's' : ''})`}
                          />
                        );
                      })}
                      </div>
                    </div>
                    
                    {/* Reward Text */}
                    {(() => {
                      const goal = fundraisingProgress?.subreddit_goals.find(g => g.subreddit_name === row.subreddit);
                      const goalAmount = Number(fundraisingProgress?.subreddit_goal_amount || 1000);
                      const currentAmount = row.total;
                      
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
                            ${remaining.toFixed(0)} more for custom banner art by Claude
                          </div>
                        );
                      }
                    })()}
                  </div>
                </td>
                <td className="text-right px-3 py-4 font-bold text-gray-900">
                  ${totalDisplay.toFixed(2)}
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