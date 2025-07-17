import React, { useState, useEffect, useMemo } from 'react';
import { ExternalLink, MessageSquare, Calendar, TrendingUp, ChevronUp, ChevronDown } from 'lucide-react';

interface ScannedPost {
  id: number;
  post_id: string;
  subreddit: string;
  comment_id: string | null;
  promoted: boolean;
  scanned_at: string;
  post_title: string | null;
  post_score: number | null;
  promotion_message: string | null;
  rejection_reason: string | null;
  is_commissioned: boolean;
  donation_info: {
    donation_id: number;
    amount_usd: number;
    tier: string;
    donor_username: string | null;
  } | null;
  agent_ratings: {
    mood?: string;
    topic?: string;
    illustration_potential?: number;
  } | null;
}

type SortField = 'score' | 'date' | 'subreddit' | 'potential';
type SortDirection = 'asc' | 'desc';

interface CloudvelAgentViewProps {
  onCommissionClick?: (postId?: string) => void;
}

export const CloudvelAgentView: React.FC<CloudvelAgentViewProps> = ({ onCommissionClick }) => {
  const [scannedPosts, setScannedPosts] = useState<ScannedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  useEffect(() => {
    fetchScannedPosts();
  }, []);

  const fetchScannedPosts = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/agent-scanned-posts?promoted=true&limit=50&include_commission_status=true');
      if (!response.ok) {
        throw new Error('Failed to fetch scanned posts');
      }
      const data = await response.json();
      setScannedPosts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getRedditPostUrl = (postId: string) => {
    return `https://reddit.com/r/popular/comments/${postId}`;
  };

  const getRedditCommentUrl = (postId: string, commentId: string) => {
    return `https://reddit.com/r/popular/comments/${postId}/_/${commentId}`;
  };

  const handleCommissionClick = (postId: string) => {
    if (onCommissionClick) {
      onCommissionClick(postId);
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedPosts = useMemo(() => {
    return [...scannedPosts].sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortField) {
        case 'score':
          aValue = a.post_score || 0;
          bValue = b.post_score || 0;
          break;
        case 'date':
          aValue = new Date(a.scanned_at).getTime();
          bValue = new Date(b.scanned_at).getTime();
          break;
        case 'subreddit':
          aValue = a.subreddit.toLowerCase();
          bValue = b.subreddit.toLowerCase();
          break;
        case 'potential':
          aValue = a.agent_ratings?.illustration_potential || 0;
          bValue = b.agent_ratings?.illustration_potential || 0;
          break;
        default:
          return 0;
      }

      if (sortDirection === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      }
    });
  }, [scannedPosts, sortField, sortDirection]);

  const SortableHeader: React.FC<{ field: SortField; children: React.ReactNode }> = ({ field, children }) => {
    const isActive = sortField === field;
    const isDesc = isActive && sortDirection === 'desc';
    
    return (
      <th className="text-left py-4 px-6 font-semibold text-gray-700 text-sm">
        <button
          onClick={() => handleSort(field)}
          className="flex items-center gap-2 hover:text-gray-900 transition-colors"
        >
          {children}
          <div className="flex flex-col">
            <ChevronUp className={`w-3 h-3 ${isActive && !isDesc ? 'text-indigo-600' : 'text-gray-400'}`} />
            <ChevronDown className={`w-3 h-3 -mt-1 ${isActive && isDesc ? 'text-indigo-600' : 'text-gray-400'}`} />
          </div>
        </button>
      </th>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center text-red-600 p-8">
        <p>Error loading scanned posts: {error}</p>
        <button 
          onClick={fetchScannedPosts}
          className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-full flex items-center justify-center">
            <span className="text-white font-bold text-lg">👑</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Clouvel Agent Activity</h1>
            <p className="text-gray-600">Posts scanned and promoted by Queen Clouvel</p>
          </div>
        </div>
        
        <div className="flex items-center gap-6 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            <span>{scannedPosts.length} promoted posts</span>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            <span>Last updated: {formatDate(new Date().toISOString())}</span>
          </div>
        </div>
      </div>

      {/* Posts Table */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
        <div className="max-h-[600px] overflow-y-auto">
          <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
              <tr>
                <th className="text-left py-4 px-6 font-semibold text-gray-700 text-sm">Title</th>
                <SortableHeader field="subreddit">Subreddit</SortableHeader>
                <SortableHeader field="score">Score</SortableHeader>
                <SortableHeader field="potential">Potential</SortableHeader>
                <SortableHeader field="date">Date</SortableHeader>
                <th className="text-left py-4 px-6 font-semibold text-gray-700 text-sm w-28">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sortedPosts.map((post, index) => (
                <tr key={post.id} className={`group hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 transition-all duration-300 ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}`}>
                  <td className="py-5 px-6">
                    <div className="flex items-center gap-3">
                      <div className="flex-1">
                        <div className="text-gray-800 text-sm font-medium line-clamp-2 leading-relaxed">
                          {post.post_title || post.post_id}
                        </div>
                        <div className="flex items-center gap-2 mt-1.5">
                          {post.comment_id ? (
                            <a
                              href={getRedditCommentUrl(post.post_id, post.comment_id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-700 hover:from-blue-200 hover:to-indigo-200 transition-all duration-200 shadow-sm"
                            >
                              <MessageSquare className="w-3 h-3" />
                              Commented
                            </a>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
                              No comment
                            </span>
                          )}
                          {post.is_commissioned && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r from-green-100 to-emerald-100 text-green-700 shadow-sm">
                              🎨 Commissioned
                            </span>
                          )}
                        </div>
                        {post.agent_ratings && (post.agent_ratings.mood || post.agent_ratings.topic) && (
                          <div className="flex items-center gap-3 mt-1 text-xs text-gray-600">
                            {post.agent_ratings.mood && (
                              <span className="flex items-center gap-1">
                                <span className="font-medium">Mood:</span>
                                <span className="capitalize">{post.agent_ratings.mood}</span>
                              </span>
                            )}
                            {post.agent_ratings.topic && (
                              <span className="flex items-center gap-1">
                                <span className="font-medium">Topic:</span>
                                <span className="capitalize">{post.agent_ratings.topic}</span>
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => window.open(getRedditPostUrl(post.post_id), '_blank')}
                        className="flex-shrink-0 p-1.5 hover:bg-gray-200 rounded-full transition-all duration-200 group-hover:bg-white/50"
                        title="Open Reddit post"
                      >
                        <ExternalLink className="w-4 h-4 text-gray-400 hover:text-indigo-600 transition-colors" />
                      </button>
                    </div>
                  </td>
                  <td className="py-5 px-6">
                    <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-gradient-to-r from-blue-100 to-cyan-100 text-blue-700 shadow-sm">
                      r/{post.subreddit}
                    </span>
                  </td>
                  <td className="py-5 px-6">
                    <span className="text-gray-700 font-medium text-sm">
                      {post.post_score?.toLocaleString() || 'N/A'}
                    </span>
                  </td>
                  <td className="py-5 px-6">
                    <span className="text-gray-700 font-medium text-sm">
                      {post.agent_ratings?.illustration_potential !== undefined 
                        ? post.agent_ratings.illustration_potential.toFixed(1)
                        : 'N/A'}
                    </span>
                  </td>
                  <td className="py-5 px-6">
                    <span className="text-gray-600 text-sm font-medium">
                      {formatDate(post.scanned_at)}
                    </span>
                  </td>
                  <td className="py-5 px-6">
                    {post.is_commissioned ? (
                      <a
                        href={`/?filter=reddit_post_id:${post.post_id}`}
                        className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-blue-600 to-blue-500 text-white text-sm font-semibold rounded-lg hover:from-blue-700 hover:to-blue-600 transition-all duration-200 shadow-sm hover:shadow-md"
                      >
                        <span>🎨</span>
                        View Product
                      </a>
                    ) : (
                      <button
                        onClick={() => handleCommissionClick(post.post_id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-gradient-to-r from-purple-600 to-purple-500 text-white text-xs font-medium rounded-md hover:from-purple-700 hover:to-purple-600 transition-all duration-200 shadow-sm hover:shadow-md"
                        title="Commission Art"
                      >
                        🎨
                        Commission
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
        
        {scannedPosts.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">👑</div>
            <p className="text-gray-500">No promoted posts found</p>
            <p className="text-gray-400 text-sm mt-1">Queen Clouvel is working hard to find great content!</p>
          </div>
        )}
      </div>
    </div>
  );
};