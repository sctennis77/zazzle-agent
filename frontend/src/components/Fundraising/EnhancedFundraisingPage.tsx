import React, { useState, useEffect, useRef } from 'react';
import { ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
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
  post_id?: string;
  post_title?: string;
  subreddit?: string;
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
  // If we have negative and positive values, use sequential bar logic
  if (negative !== 0 || positive !== 0) {
    const communityAmount = positive;
    const selfCommissionAmount = Math.abs(negative);
    const netAmount = positive + negative; // Community raised + negative self commissions
    
    // Calculate percentages relative to target
    const communityPercentage = Math.min((communityAmount / target) * 100, 100);
    const netPercentage = Math.min((Math.max(0, netAmount) / target) * 100, 100);
    
    return (
      <div className="relative">
        <div className={`relative bg-gray-200 rounded-full overflow-hidden ${className}`}>
          {/* Community donations bar (full amount) */}
          <div 
            className={`h-full bg-blue-500 rounded-full transition-all duration-1000 ease-out ${
              showGlow ? 'shadow-lg shadow-blue-500/50' : ''
            }`}
            style={{ width: `${communityPercentage}%` }}
          >
            {showGlow && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
            )}
          </div>
          
          {/* Self-commission "subtraction" overlay */}
          {selfCommissionAmount > 0 && netPercentage < communityPercentage && (
            <div 
              className="absolute top-0 h-full bg-rose-400 transition-all duration-1000 ease-out"
              style={{ 
                left: `${netPercentage}%`,
                width: `${communityPercentage - netPercentage}%`,
                backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 3px, rgba(255,255,255,0.4) 3px, rgba(255,255,255,0.4) 6px)'
              }}
            />
          )}
          
          {/* If net is negative, show the negative portion extending from 0 */}
          {netAmount < 0 && (
            <div 
              className="absolute top-0 h-full bg-rose-500 rounded-l-full transition-all duration-1000 ease-out"
              style={{ 
                width: `${Math.min((Math.abs(netAmount) / target) * 100, 100)}%`
              }}
            />
          )}
        </div>
        
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
  const isLocked = !milestone.achieved && !isNext;
  
  return (
    <div className={`relative p-3 sm:p-4 rounded-xl transition-all duration-300 ${
      milestone.achieved 
        ? 'bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 shadow-lg' 
        : isNext
          ? 'bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 shadow-md'
          : 'bg-gray-50 border-2 border-gray-200'
    }`}>
      {milestone.achieved && (
        <div className="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center z-10">
          <span className="text-white text-xs">✓</span>
        </div>
      )}
      
      <div className="flex items-center space-x-3 mb-2">
        <div className={`text-2xl ${milestone.achieved ? 'grayscale-0' : 'grayscale'}`}>
          {milestone.icon}
        </div>
        <div>
          <div className={`font-bold text-base sm:text-lg ${
            milestone.achieved ? 'text-green-800' : isNext ? 'text-blue-800' : 'text-gray-600'
          }`}>
            ${milestone.amount.toLocaleString()}
          </div>
          {milestone.isStretched && (
            <div className="text-xs text-orange-600 font-medium">STRETCH GOAL</div>
          )}
        </div>
      </div>
      
      <h4 className={`font-semibold ${
        milestone.achieved ? 'text-green-800' : isNext ? 'text-blue-800' : 'text-gray-700'
      }`}>
        {milestone.title}
      </h4>
      
      {/* Only show description for Community Bootstrap milestone */}
      {milestone.amount === 1000 && (
        <p className={`text-sm mt-1 ${
          milestone.achieved ? 'text-green-600' : isNext ? 'text-blue-600' : 'text-gray-500'
        }`}>
          Keep Clouvel running for a few more months.
        </p>
      )}
      
      {/* Locked overlay for future milestones */}
      {isLocked && (
        <div className="absolute inset-0 bg-gray-400 rounded-xl"></div>
      )}
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
  const [isActivityExpanded, setIsActivityExpanded] = useState(false);

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
  const allDonations = Object.entries(data).flatMap(([subredditName, d]) => [
    ...(d.commission ? [{ ...d.commission, subreddit: subredditName }] : []),
    ...d.support.map(donation => ({ ...donation, subreddit: subredditName }))
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
      icon: '🐕',
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
        {/* Call to Action Header with Integrated Progress Bar */}
        <div className="text-center bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl p-4 sm:p-6 md:p-8 text-white shadow-xl">
          <h3 className="text-xl sm:text-2xl md:text-3xl font-bold mb-3 sm:mb-4">Ready to Join Our Mission?</h3>
          <p className="text-base sm:text-lg md:text-xl mb-6 opacity-90">
            Every contribution helps sustain and improve Clouvel
          </p>
          
          {/* Progress section integrated */}
          <div className="mb-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-6">
                <div className="text-center sm:text-left relative group">
                  <div className="text-2xl font-bold text-rose-300">
                    <AnimatedCounter value={selfCommissionedAmount} prefix="-$" />
                  </div>
                  <div className="text-sm text-white/80 flex items-center gap-1">
                    Self Commissioned
                    <svg 
                      className="w-3 h-3 text-white/60 cursor-help" 
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
                  <div className="absolute bottom-full left-0 mb-2 px-3 py-2 bg-gray-700 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
                    Clouvel incurs the cost of self commissioned works.
                    <div className="absolute top-full left-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-700"></div>
                  </div>
                </div>
                
                <div className="text-center relative group">
                  <div className={`text-3xl font-bold ${totalValue >= 0 ? 'text-red-300' : 'text-red-400'}`}>
                    <AnimatedCounter value={totalValue} prefix="$" />
                  </div>
                  <div className="text-sm text-white/80 font-medium flex items-center justify-center gap-1">
                    Net Total
                    <svg 
                      className="w-3 h-3 text-white/60 cursor-help" 
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
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-700 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
                    🎨 Net total = Community support minus Clouvel's self-commissioned work
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-700"></div>
                  </div>
                </div>
                
                <div className="text-center sm:text-right relative group">
                  <div className="text-2xl font-bold text-blue-200">
                    <AnimatedCounter value={communityRaised} prefix="$" />
                  </div>
                  <div className="text-sm text-white/80 flex items-center justify-end gap-1">
                    Community Raised
                    <svg 
                      className="w-3 h-3 text-white/60 cursor-help" 
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
                  <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-gray-700 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
                    Community sponsored art that contributes towards fundraising progress
                    <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-700"></div>
                  </div>
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
                <div className="text-right relative group">
                  <div className="text-2xl font-bold text-white/80">
                    ${(nextMilestone?.amount || 100000).toLocaleString()}
                  </div>
                  <div className="text-sm text-white/80 flex items-center justify-end gap-1">
                    Current Goal
                    {nextMilestone && (
                      <svg 
                        className="w-3 h-3 text-white/60 cursor-help" 
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24"
                      >
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                        <path d="M12 17h.01"/>
                      </svg>
                    )}
                  </div>
                  {/* Tooltip */}
                  {nextMilestone && (
                    <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-gray-700 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
                      Current Goal: {nextMilestone.title}
                      <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-700"></div>
                    </div>
                  )}
                </div>
              </div>
              
          </div>
          
          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a 
              href="/" 
              className="bg-white text-indigo-600 px-6 md:px-8 py-3 rounded-lg font-bold hover:bg-gray-50 transition-all duration-200 transform hover:scale-105 shadow-lg inline-block"
            >
              Support Clouvel 💝
            </a>
            <a 
              href="/" 
              className="border-2 border-white text-white px-6 md:px-8 py-3 rounded-lg font-bold hover:bg-white hover:text-indigo-600 transition-all duration-200 inline-block"
            >
              View Gallery 🎨
            </a>
          </div>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
          <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6 text-center border border-gray-100">
            <div className="text-3xl sm:text-4xl font-bold text-indigo-600 mb-2">
              <AnimatedCounter value={activeCommunities} decimals={0} />
            </div>
            <div className="text-gray-600 font-medium">Active Communities</div>
            <div className="text-sm text-gray-500 mt-1">Growing strong! 🌱</div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6 text-center border border-gray-100">
            <div className="text-3xl sm:text-4xl font-bold text-rose-400 mb-2">
              <AnimatedCounter value={selfCommissionedDonations.length} decimals={0} />
            </div>
            <div className="text-gray-600 font-medium">Self Commissions</div>
            <div className="text-sm text-gray-500 mt-1">Creator funded 🎨</div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6 text-center border border-gray-100">
            <div className="text-3xl sm:text-4xl font-bold text-blue-600 mb-2">
              <AnimatedCounter value={communityDonations.length} decimals={0} />
            </div>
            <div className="text-gray-600 font-medium">Community Contributions</div>
            <div className="text-sm text-gray-500 mt-1">Thank you! 🙏</div>
          </div>
        </div>

        {/* Community Leaderboard */}
        <div>
          <DonationsLeaderboardTable data={data} fundraisingProgress={fundraisingProgress} />
        </div>

        {/* Recent Activity Feed */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
          {/* Header with description - always visible */}
          <div className="p-4 sm:p-6">
            <div className="p-4 bg-gradient-to-r from-red-50 to-pink-50 rounded-lg border border-red-200">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-800 mb-2">🔥 Recent Activity</h3>
                  <p className="text-sm text-gray-600">
                    Latest contributions from our amazing community supporters
                  </p>
                </div>
                <button
                  onClick={() => setIsActivityExpanded(!isActivityExpanded)}
                  className="ml-4 p-2 hover:bg-red-100 rounded-lg transition-colors duration-200 flex items-center justify-center"
                  aria-label={isActivityExpanded ? 'Collapse activity' : 'Expand activity'}
                >
                  {isActivityExpanded ? (
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
              isActivityExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0 overflow-hidden'
            }`}
          >
            <div className="p-4 sm:p-6 pt-0">
              <div className="space-y-3 sm:space-y-4">
              {allDonations.slice(0, 5).map((donation, index) => (
                <div key={donation.donation_id} className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 sm:gap-2">
                    {/* Left: User info */}
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0">
                        {donation.reddit_username?.charAt(0).toUpperCase() || 'A'}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-medium text-gray-900 text-sm">
                          {donation.is_anonymous ? 'Anonymous' : donation.reddit_username}
                          {donation.source === 'manual' && (
                            <span className="ml-1 sm:ml-2 px-1.5 sm:px-2 py-0.5 sm:py-1 bg-rose-100 text-rose-400 text-xs rounded-full">
                              Self Commissioned
                            </span>
                          )}
                        </div>
                        <div className="text-xs sm:text-sm text-gray-500">
                          {new Date(donation.created_at).toLocaleString('en-US', {
                            year: 'numeric',
                            month: 'numeric', 
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </div>
                        {/* Message below user info on mobile */}
                        {(donation.message || donation.commission_message) && (
                          <div className="mt-1 text-xs text-gray-600 truncate sm:hidden">
                            <span className="font-medium">Message:</span> {donation.message || donation.commission_message}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Center: Post title and subreddit - only on desktop */}
                    <div className="hidden sm:flex sm:flex-1 sm:px-3 sm:text-center sm:min-w-0 flex-col">
                      {donation.post_title && (
                        <div className="text-xs text-gray-700 font-medium break-words line-clamp-2 leading-tight mb-1">
                          "{donation.post_title}"
                        </div>
                      )}
                      {donation.subreddit && (
                        <div className="text-xs text-gray-500 font-bold bg-gray-100 px-2 py-1 rounded-full inline-block">
                          r/{donation.subreddit}
                        </div>
                      )}
                      {/* Message on desktop */}
                      {(donation.message || donation.commission_message) && (
                        <div className="mt-2 text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded italic">
                          <span className="font-medium">Message:</span> {donation.message || donation.commission_message}
                        </div>
                      )}
                    </div>

                    {/* Mobile: Post title and subreddit row */}
                    <div className="sm:hidden">
                      {donation.post_title && (
                        <div className="text-sm text-gray-700 font-medium break-words leading-tight mb-2">
                          "{donation.post_title}"
                        </div>
                      )}
                      {donation.subreddit && (
                        <div className="text-xs text-gray-500 font-bold bg-gray-100 px-2 py-1 rounded-full inline-block mb-2">
                          r/{donation.subreddit}
                        </div>
                      )}
                    </div>

                    {/* Right: Amount and gallery link */}
                    <div className="flex items-center justify-between sm:justify-end gap-3 flex-shrink-0">
                      {donation.post_id && (
                        <button
                          onClick={() => window.location.href = `/?product=${donation.post_id}`}
                          className="p-1.5 hover:bg-gray-200 rounded-full transition-all duration-200"
                          title="View in gallery"
                        >
                          <ExternalLink className="w-4 h-4 text-gray-400 hover:text-indigo-600 transition-colors" />
                        </button>
                      )}
                      <div className="text-right">
                        <div className={`font-bold text-sm sm:text-base ${
                          donation.source === 'manual' ? 'text-rose-400' : 'text-green-600'
                        }`}>
                          ${donation.donation_amount.toFixed(2)}
                        </div>
                        <div className="text-xs text-gray-500 capitalize">
                          {donation.tier_name} Tier
                        </div>
                      </div>
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
        </div>

        {/* Milestones Grid */}
        <div>
          <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4 sm:mb-6 text-center">
            🎯 Funding Milestones & Rewards
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {milestones.map((milestone, index) => (
              <MilestoneCard 
                key={milestone.amount} 
                milestone={milestone}
                isNext={milestone === nextMilestone}
              />
            ))}
          </div>
        </div>

    </div>
  );
};

export default EnhancedFundraisingPage;