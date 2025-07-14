import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import DonationsLeaderboardTable from './DonationsLeaderboardTable';
import { API_BASE } from '../../utils/apiBase';

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

interface TierData {
  name: string;
  amount: number;
  count: number;
  color: string;
}

interface ChartData {
  subreddit: string;
  totalAmount: number;
  totalDonations: number;
  tiers: TierData[];
}

const TIER_COLORS = {
  bronze: '#CD7F32',
  silver: '#C0C0C0', 
  gold: '#FFD700',
  platinum: '#E5E4E2',
  emerald: '#50C878',
  topaz: '#FFC87C',
  ruby: '#E0115F',
  sapphire: '#0F52BA'
};

const TIER_NAMES = {
  bronze: 'Bronze',
  silver: 'Silver',
  gold: 'Gold', 
  platinum: 'Platinum',
  emerald: 'Emerald',
  topaz: 'Topaz',
  ruby: 'Ruby',
  sapphire: 'Sapphire'
};

const FundraisingPage: React.FC = () => {
  const [data, setData] = useState<FundraisingData>({});
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/donations/by-subreddit`);
      if (!response.ok) {
        throw new Error('Failed to fetch donation data');
      }
      const donationData: FundraisingData = await response.json();
      setData(donationData);
      processDataForChart(donationData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const processDataForChart = (donationData: FundraisingData) => {
    const processed: ChartData[] = Object.entries(donationData).map(([subreddit, donations]) => {
      // Combine commission and support donations
      const allDonations = [
        ...(donations.commission ? [donations.commission] : []),
        ...donations.support
      ];

      // Group by tier
      const tierGroups: { [key: string]: { amount: number; count: number } } = {};
      
      allDonations.forEach(donation => {
        const tier = donation.tier_name.toLowerCase();
        if (!tierGroups[tier]) {
          tierGroups[tier] = { amount: 0, count: 0 };
        }
        tierGroups[tier].amount += donation.donation_amount;
        tierGroups[tier].count += 1;
      });

      // Convert to chart format
      const tiers: TierData[] = Object.entries(tierGroups)
        .map(([tier, data]) => ({
          name: TIER_NAMES[tier as keyof typeof TIER_NAMES] || tier,
          amount: data.amount,
          count: data.count,
          color: TIER_COLORS[tier as keyof typeof TIER_COLORS] || '#8884d8'
        }))
        .sort((a, b) => b.amount - a.amount); // Sort by amount descending

      const totalAmount = allDonations.reduce((sum, d) => sum + d.donation_amount, 0);
      const totalDonations = allDonations.length;

      return {
        subreddit,
        totalAmount,
        totalDonations,
        tiers
      };
    }).sort((a, b) => b.totalAmount - a.totalAmount); // Sort subreddits by total amount

    setChartData(processed);
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-4 rounded-lg shadow-lg border border-gray-200">
          <p className="font-semibold text-gray-800 mb-2">r/{label}</p>
          <p className="text-sm text-gray-600 mb-2">
            Total: ${payload[0].payload.totalAmount.toFixed(2)} ({payload[0].payload.totalDonations} donations)
          </p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex justify-between items-center mb-1">
              <div className="flex items-center">
                <div 
                  className="w-3 h-3 rounded mr-2" 
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-sm font-medium">{entry.name}</span>
              </div>
              <div className="text-right">
                <div className="text-sm font-semibold">${entry.value.toFixed(2)}</div>
                <div className="text-xs text-gray-500">{entry.payload.tiers[index].count} donations</div>
              </div>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  const CustomBar = (props: any) => {
    const { x, y, width, height, tiers } = props;
    if (!tiers || tiers.length === 0) return null;

    const totalAmount = tiers.reduce((sum: number, tier: TierData) => sum + tier.amount, 0);
    let currentY = y;

    return tiers.map((tier: TierData, index: number) => {
      const segmentHeight = (tier.amount / totalAmount) * height;
      const segmentY = currentY;
      currentY += segmentHeight;

      return (
        <g key={index}>
          <rect
            x={x}
            y={segmentY}
            width={width}
            height={segmentHeight}
            fill={tier.color}
            stroke="#fff"
            strokeWidth={1}
          />
          {segmentHeight > 20 && (
            <text
              x={x + width / 2}
              y={segmentY + segmentHeight / 2}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-xs font-medium fill-white"
              style={{ fontSize: '10px', fontWeight: 600 }}
            >
              {tier.count}
            </text>
          )}
        </g>
      );
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading fundraising data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Error Loading Data</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={fetchData}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Compute summary stats
  const activeCommunities = Object.keys(data).length;
  const allDonations = Object.values(data).flatMap(d => [
    ...(d.commission ? [d.commission] : []),
    ...d.support
  ]);
  const totalRaised = allDonations.reduce((sum, d) => sum + d.donation_amount, 0);
  const totalDonations = allDonations.length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Community Fundraising Leaderboard
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            See how much each community has contributed to support our creative projects
          </p>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6 text-center">
            <div className="text-3xl font-bold text-indigo-600 mb-2">
              {activeCommunities}
            </div>
            <div className="text-gray-600">Active Communities</div>
          </div>
          <div className="bg-white rounded-xl shadow-lg p-6 text-center">
            <div className="text-3xl font-bold text-green-600 mb-2">
              ${totalRaised.toFixed(2)}
            </div>
            <div className="text-gray-600">Total Raised</div>
          </div>
          <div className="bg-white rounded-xl shadow-lg p-6 text-center">
            <div className="text-3xl font-bold text-purple-600 mb-2">
              {totalDonations}
            </div>
            <div className="text-gray-600">Total Donations</div>
          </div>
        </div>

        {/* Leaderboard Table */}
        <DonationsLeaderboardTable data={data} />

      </div>
    </div>
  );
};

export default FundraisingPage; 