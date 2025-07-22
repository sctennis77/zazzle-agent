import React, { useState, useEffect, useRef } from 'react';
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

interface Milestone {
  amount: number;
  title: string;
  description: string;
  icon: string;
  achieved: boolean;
  isStretched?: boolean;
}

const AnimatedCounter: React.FC<{ value: number; prefix?: string; suffix?: string; decimals?: number }> = ({ 
  value, prefix = '', suffix = '', decimals = 2 
}) => {
  const [displayValue, setDisplayValue] = useState(0);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }

    const startValue = displayValue;
    const difference = value - startValue;
    const duration = 1500;
    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      const easeOutCubic = 1 - Math.pow(1 - progress, 3);
      const currentValue = startValue + (difference * easeOutCubic);
      
      setDisplayValue(currentValue);
      
      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [value]);

  return <span>{prefix}{displayValue.toFixed(decimals)}{suffix}</span>;
};

const ProgressBar: React.FC<{ 
  current: number; 
  target: number; 
  className?: string;
  showGlow?: boolean;
  negative?: number;
  positive?: number;
}> = ({ current, target, className = '', showGlow = false, negative = 0, positive = 0 }) => {
  // If we have negative and positive values, use the new dual bar
  if (negative !== 0 || positive !== 0) {
    const zeroPoint = 33.33; // 1/3 from left
    const maxNegative = Math.abs(negative);
    const maxRange = Math.max(maxNegative, positive, target);
    
    // Calculate widths as percentages of available space
    const negativeWidth = (maxNegative / maxRange) * zeroPoint;
    const positiveWidth = (positive / maxRange) * (100 - zeroPoint);
    
    return (
      <div className={`relative bg-gray-200 rounded-full overflow-hidden ${className}`}>
        {/* Zero line indicator */}
        <div 
          className="absolute top-0 w-0.5 h-full bg-gray-400 z-10"
          style={{ left: `${zeroPoint}%` }}
        />
        
        {/* Negative bar (red, extends left from zero) */}
        {negative < 0 && (
          <div 
            className="absolute top-0 h-full bg-rose-400 rounded-l-full transition-all duration-1000 ease-out"
            style={{ 
              right: `${100 - zeroPoint}%`,
              width: `${negativeWidth}%`
            }}
          />
        )}
        
        {/* Positive bar (blue, extends right from zero) */}
        {positive > 0 && (
          <div 
            className="absolute top-0 h-full bg-blue-500 rounded-r-full transition-all duration-1000 ease-out"
            style={{ 
              left: `${zeroPoint}%`,
              width: `${positiveWidth}%`
            }}
          />
        )}
      </div>
    );
  }
  
  // Original single progress bar logic
  const percentage = Math.min((current / target) * 100, 100);
  
  return (
    <div className={`relative bg-gray-200 rounded-full overflow-hidden ${className}`}>
      <div 
        className={`h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-full transition-all duration-1000 ease-out ${
          showGlow ? 'shadow-lg shadow-indigo-500/50' : ''
        }`}
        style={{ width: `${percentage}%` }}
      >
        {showGlow && (
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
        )}
      </div>
    </div>
  );
};

const MilestoneCard: React.FC<{ milestone: Milestone; isNext?: boolean }> = ({ milestone, isNext = false }) => {
  return (
    <div className={`relative p-4 rounded-xl transition-all duration-300 ${
      milestone.achieved 
        ? 'bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 shadow-lg' 
        : isNext
          ? 'bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 shadow-md'
          : 'bg-gray-50 border-2 border-gray-200'
    }`}>
      {milestone.achieved && (
        <div className="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
          <span className="text-white text-xs">✓</span>
        </div>
      )}
      
      <div className="flex items-center space-x-3 mb-2">
        <div className={`text-2xl ${milestone.achieved ? 'grayscale-0' : 'grayscale'}`}>
          {milestone.icon}
        </div>
        <div>
          <div className={`font-bold text-lg ${
            milestone.achieved ? 'text-green-800' : isNext ? 'text-blue-800' : 'text-gray-600'
          }`}>
            ${milestone.amount.toLocaleString()}
          </div>
          {milestone.isStretched && (
            <div className="text-xs text-orange-600 font-medium">STRETCH GOAL</div>
          )}
        </div>
      </div>
      
      <h4 className={`font-semibold mb-1 ${
        milestone.achieved ? 'text-green-800' : isNext ? 'text-blue-800' : 'text-gray-700'
      }`}>
        {milestone.title}
      </h4>
      
      <p className={`text-sm ${
        milestone.achieved ? 'text-green-600' : isNext ? 'text-blue-600' : 'text-gray-500'
      }`}>
        {milestone.description}
      </p>
    </div>
  );
};

const ImpactMetrics: React.FC<{ 
  communityRaised: number; 
  clouvelContributed: number; 
  totalValue: number;
}> = ({ communityRaised, clouvelContributed, totalValue }) => {
  return (
    <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border border-purple-200">
      <h3 className="text-xl font-bold text-purple-900 mb-4 flex items-center">
        <span className="mr-2">💝</span>
        Community Impact
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">
            <AnimatedCounter value={communityRaised} prefix="$" />
          </div>
          <div className="text-sm text-gray-600">Community Raised</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600">
            <AnimatedCounter value={clouvelContributed} decimals={0} />
          </div>
          <div className="text-sm text-gray-600">System Generated</div>
        </div>
        
        <div className="text-center">
          <div className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            <AnimatedCounter value={totalValue} prefix="$" />
          </div>
          <div className="text-sm text-gray-600 font-medium">Total Value</div>
        </div>
      </div>
      
      <div className="mt-4 text-center text-sm text-gray-600">
        <span className="bg-purple-100 px-3 py-1 rounded-full">
          🎨 Clouvel matches community support with pro-bono creative work
        </span>
      </div>
    </div>
  );
};

const EnhancedFundraisingPage: React.FC = () => {
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
      
      const [donationResponse, progressResponse] = await Promise.all([
        fetch(`${API_BASE}/api/donations/by-subreddit`),
        fetch(`${API_BASE}/api/fundraising/progress`)
      ]);

      if (!donationResponse.ok || !progressResponse.ok) {
        throw new Error('Failed to fetch data');
      }

      const donationData: FundraisingData = await donationResponse.json();
      const progressData: FundraisingProgress = await progressResponse.json();
      
      setData(donationData);
      setFundraisingProgress(progressData);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <div className="absolute inset-0 rounded-full border-t-2 border-purple-400 animate-spin" style={{ animationDelay: '0.15s' }}></div>
          </div>
          <p className="text-gray-600 font-medium">Loading fundraising data...</p>
          <p className="text-sm text-gray-500 mt-1">Preparing amazing things ✨</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-orange-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-red-500 text-6xl mb-4">🚫</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Oops! Something went wrong</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={fetchData}
            className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-3 rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
          >
            Try Again 🔄
          </button>
        </div>
      </div>
    );
  }

  // Calculate metrics
  const allDonations = Object.values(data).flatMap(d => [
    ...(d.commission ? [d.commission] : []),
    ...d.support
  ]);
  
  const communityDonations = allDonations.filter(d => d.source === null || d.source === 'stripe');
  const selfCommissionedDonations = allDonations.filter(d => d.source === 'manual');
  
  const communityRaised = communityDonations.reduce((sum, d) => sum + d.donation_amount, 0);
  const selfCommissionedAmount = selfCommissionedDonations.reduce((sum, d) => sum + d.donation_amount, 0);
  const totalValue = communityRaised - selfCommissionedAmount;
  
  const activeCommunities = Object.keys(data).length;
  const totalDonations = allDonations.length;

  // Define milestones
  const milestones: Milestone[] = [
    {
      amount: 1000,
      title: 'Community Bootstrap',
      description: 'Keep Clouvel alive for a few months - she\'s running low on treats! 🍪',
      icon: '💝',
      achieved: communityRaised >= 1000
    },
    {
      amount: 5000,
      title: 'Vision Unlocked',
      description: 'Clouvel awakens her visual powers - understanding images and links with mystical clarity',
      icon: '👁️',
      achieved: communityRaised >= 5000
    },
    {
      amount: 10000,
      title: 'Banner Art Mastery',
      description: 'Clouvel creates stunning banner art that captures each subreddit\'s unique story and spirit',
      icon: '🎨',
      achieved: communityRaised >= 10000
    },
    {
      amount: 25000,
      title: 'Summon Mandolf',
      description: 'Awaken Mandolf (twin brother of Mandalf) and Clouvel\'s best friend. This mini Maltese master blends watercolors with traditional Seigaiha waves',
      icon: '🐕',
      achieved: communityRaised >= 25000,
      isStretched: true
    },
    {
      amount: 100000,
      title: 'Clouvel Ascends',
      description: 'The ultimate transformation awaits... What lies beyond mortal creativity? Only the bravest supporters will discover this mystery! ✨',
      icon: '🌟',
      achieved: communityRaised >= 100000,
      isStretched: true
    }
  ];

  const nextMilestone = milestones.find(m => !m.achieved);
  const currentProgress = fundraisingProgress?.overall_progress_percentage || 0;

  return (
    <div className="space-y-8">
        {/* Main Progress Section */}
        <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8 border border-gray-100">
            <div className="mb-8">
              {/* Section Header */}
              <div className="text-center mb-6">
                <h2 className="text-xl md:text-2xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-2">
                  Clouvel's Requisition
                </h2>
                <p className="text-xs md:text-sm text-gray-600 leading-relaxed">
                  Every contribution supports Clouvel's dream to illustrate the wonderful stories and community of Reddit.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="text-left">
                  <div className="text-2xl font-bold text-blue-600">
                    <AnimatedCounter value={communityRaised} prefix="$" />
                  </div>
                  <div className="text-sm text-gray-600">Community Raised</div>
                </div>
                
                <div className="text-center relative group">
                  <div className={`text-3xl font-bold bg-gradient-to-r ${totalValue >= 0 ? 'from-purple-600 to-pink-600' : 'from-rose-400 to-rose-500'} bg-clip-text text-transparent`}>
                    <AnimatedCounter value={totalValue} prefix="$" />
                  </div>
                  <div className="text-sm text-gray-600 font-medium flex items-center justify-center gap-1">
                    Net Total
                    <svg 
                      className="w-3 h-3 text-gray-400 cursor-help" 
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <circle cx="12" cy="12" r="10"/>
                      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                      <path d="M12 17h.01"/>
                    </svg>
                  </div>
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
                    🎨 Net total = Community support minus Clouvel's self-commissioned work
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
                  </div>
                </div>
                
                <div className="text-right">
                  <div className="text-2xl font-bold text-rose-400">
                    <AnimatedCounter value={selfCommissionedAmount} prefix="$" />
                  </div>
                  <div className="text-sm text-gray-600">Self Commissioned</div>
                </div>
              </div>

              <ProgressBar 
                current={Math.max(0, communityRaised)} 
                target={nextMilestone?.amount || 100000}
                className="h-8 mb-2"
                showGlow={communityRaised > (nextMilestone?.amount || 100000) * 0.5}
                negative={-selfCommissionedAmount}
                positive={communityRaised}
              />
              
              <div className="flex justify-end">
                <div className="text-right">
                  <div className="text-sm font-medium text-gray-700">
                    ${(nextMilestone?.amount || 100000).toLocaleString()}
                  </div>
                </div>
              </div>

              {nextMilestone && (
                <div className="text-center">
                  <div className="inline-flex items-center space-x-2 bg-blue-50 px-4 py-2 rounded-full border border-blue-200">
                    <span className="text-blue-600 font-medium">Current Goal:</span>
                    <span className="text-blue-800 font-bold">${nextMilestone.amount.toLocaleString()}</span>
                    <span className="text-blue-600">- {nextMilestone.title}</span>
                  </div>
                </div>
              )}
            </div>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl shadow-lg p-6 text-center border border-gray-100">
            <div className="text-4xl font-bold text-indigo-600 mb-2">
              <AnimatedCounter value={activeCommunities} decimals={0} />
            </div>
            <div className="text-gray-600 font-medium">Active Communities</div>
            <div className="text-sm text-gray-500 mt-1">Growing strong! 🌱</div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6 text-center border border-gray-100">
            <div className="text-4xl font-bold text-rose-400 mb-2">
              <AnimatedCounter value={selfCommissionedDonations.length} decimals={0} />
            </div>
            <div className="text-gray-600 font-medium">Self Commissions</div>
            <div className="text-sm text-gray-500 mt-1">Creator funded 🎨</div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6 text-center border border-gray-100">
            <div className="text-4xl font-bold text-blue-600 mb-2">
              <AnimatedCounter value={communityDonations.length} decimals={0} />
            </div>
            <div className="text-gray-600 font-medium">Community Contributions</div>
            <div className="text-sm text-gray-500 mt-1">Thank you! 🙏</div>
          </div>
        </div>

        {/* Milestones Grid */}
        <div>
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            🎯 Funding Milestones & Rewards
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {milestones.map((milestone, index) => (
              <MilestoneCard 
                key={milestone.amount} 
                milestone={milestone}
                isNext={milestone === nextMilestone}
              />
            ))}
          </div>
        </div>


        {/* Community Leaderboard */}
        <div>
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            🏆 Community Leaderboard
          </h3>
          <DonationsLeaderboardTable data={data} fundraisingProgress={fundraisingProgress} />
        </div>

        {/* Recent Activity Feed */}
        <div>
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            🔥 Recent Activity
          </h3>
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
            <div className="space-y-4">
              {allDonations.slice(0, 5).map((donation, index) => (
                <div key={donation.donation_id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold">
                      {donation.reddit_username?.charAt(0).toUpperCase() || 'A'}
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">
                        {donation.is_anonymous ? 'Anonymous' : donation.reddit_username}
                        {donation.source === 'manual' && (
                          <span className="ml-2 px-2 py-1 bg-rose-100 text-rose-400 text-xs rounded-full">
                            Self Commissioned
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-gray-500">
                        {new Date(donation.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-bold ${
                      donation.source === 'manual' ? 'text-rose-400' : 'text-green-600'
                    }`}>
                      ${donation.donation_amount.toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-500 capitalize">
                      {donation.tier_name} Tier
                    </div>
                  </div>
                </div>
              ))}
              {allDonations.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-2">🌱</div>
                  <p>Be the first to support our mission!</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Call to Action */}
        <div className="text-center bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl p-6 md:p-8 text-white shadow-xl">
          <h3 className="text-2xl md:text-3xl font-bold mb-4">Ready to Join Our Mission?</h3>
          <p className="text-lg md:text-xl mb-6 opacity-90">
            Every contribution brings us closer to revolutionary AI capabilities
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a 
              href="/" 
              className="bg-white text-indigo-600 px-6 md:px-8 py-3 rounded-lg font-bold hover:bg-gray-50 transition-all duration-200 transform hover:scale-105 shadow-lg inline-block"
            >
              Support the Campaign 💝
            </a>
            <a 
              href="/" 
              className="border-2 border-white text-white px-6 md:px-8 py-3 rounded-lg font-bold hover:bg-white hover:text-indigo-600 transition-all duration-200 inline-block"
            >
              View Gallery 🎨
            </a>
          </div>
        </div>
    </div>
  );
};

export default EnhancedFundraisingPage;