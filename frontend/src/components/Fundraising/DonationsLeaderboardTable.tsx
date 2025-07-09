import React from 'react';

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
  const rows = summarizeLeaderboard(data);
  // Find which tiers are present in the data
  const presentTiers = TIER_ORDER.filter(tier => rows.some(row => row.tiers[tier]));

  return (
    <div className="overflow-x-auto bg-white rounded-xl shadow-lg p-6">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left px-2 py-2 font-semibold text-gray-700">Subreddit</th>
            <th className="text-left px-2 py-2 font-semibold text-gray-700">Donations</th>
            {presentTiers.map(tier => (
              <th key={tier} className="text-center px-2 py-2 font-semibold" style={{ color: TIER_COLORS[tier] }}>{TIER_NAMES[tier]}</th>
            ))}
            <th className="text-right px-2 py-2 font-semibold text-gray-700">Total ($)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => {
            // For the stacked bar
            const total = row.total || 1; // avoid div by zero
            let acc = 0;
            return (
              <tr key={row.subreddit} className="border-b hover:bg-gray-50">
                <td className="px-2 py-2 font-medium text-gray-900 whitespace-nowrap">r/{row.subreddit}</td>
                <td className="px-2 py-2">
                  <div className="flex h-6 w-48 rounded overflow-hidden bg-gray-100 border border-gray-200">
                    {presentTiers.map(tier => {
                      const tierData = row.tiers[tier];
                      if (!tierData) return null;
                      const width = (tierData.amount / total) * 100;
                      acc += width;
                      return (
                        <div
                          key={tier}
                          style={{
                            width: `${width}%`,
                            background: TIER_COLORS[tier],
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#fff',
                            fontWeight: 600,
                            fontSize: '0.85em',
                            borderRight: '1px solid #fff',
                          }}
                          title={`${TIER_NAMES[tier]}: $${tierData.amount.toFixed(2)} (${tierData.count})`}
                        >
                          {tierData.count}
                        </div>
                      );
                    })}
                  </div>
                </td>
                {presentTiers.map(tier => {
                  const tierData = row.tiers[tier];
                  return (
                    <td key={tier} className="text-center px-2 py-2 font-mono">
                      {tierData ? `${tierData.count} ($${tierData.amount.toFixed(2)})` : <span className="text-gray-300">–</span>}
                    </td>
                  );
                })}
                <td className="text-right px-2 py-2 font-bold text-gray-900">${row.total.toFixed(2)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default DonationsLeaderboardTable; 