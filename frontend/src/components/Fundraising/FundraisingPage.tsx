import React, { useState, useEffect } from 'react';
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


interface SubredditGoal {
  id: number;
  subreddit_id: number;
  subreddit_name: string;
  goal_amount: number;
  current_amount: number;
  status: string;
  created_at: string;
  completed_at?: string;
  deadline?: string;
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
  const [fundraisingProgress, setFundraisingProgress] = useState<FundraisingProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch donation data
      const donationResponse = await fetch(`${API_BASE}/api/donations/by-subreddit`);
      if (!donationResponse.ok) {
        throw new Error('Failed to fetch donation data');
      }
      const donationData: FundraisingData = await donationResponse.json();
      setData(donationData);
      
      // Fetch fundraising progress
      const progressResponse = await fetch(`${API_BASE}/api/fundraising/progress`);
      if (!progressResponse.ok) {
        throw new Error('Failed to fetch fundraising progress');
      }
      const progressData: FundraisingProgress = await progressResponse.json();
      setFundraisingProgress(progressData);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
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

        {/* Fundraising Goals */}
        {fundraisingProgress && (
          <div className="mb-8">
            {/* Overall Goal */}
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4 text-center">
                Overall Fundraising Goal
              </h2>
              <div className="mb-4">
                <div className="flex justify-between text-sm font-medium text-gray-700 mb-2">
                  <span>${Number(fundraisingProgress.overall_raised).toFixed(2)} raised</span>
                  <span>${Number(fundraisingProgress.overall_goal).toFixed(2)} goal</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4">
                  <div 
                    className="bg-gradient-to-r from-indigo-500 to-purple-600 h-4 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(fundraisingProgress.overall_progress_percentage, 100)}%` }}
                  ></div>
                </div>
                <div className="text-center mt-2 text-sm text-gray-600">
                  {fundraisingProgress.overall_progress_percentage.toFixed(1)}% complete
                </div>
              </div>
              <div className="text-center text-gray-600">
                <span className="font-medium">Reward:</span> {fundraisingProgress.overall_reward}
              </div>
            </div>

          </div>
        )}

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
              ${Number(totalRaised).toFixed(2)}
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
        <DonationsLeaderboardTable data={data} fundraisingProgress={fundraisingProgress} />

      </div>
    </div>
  );
};

export default FundraisingPage; 