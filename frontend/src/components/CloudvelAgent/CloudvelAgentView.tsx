import React, { useState, useEffect } from 'react';
import { ExternalLink, MessageSquare, DollarSign, Calendar, TrendingUp } from 'lucide-react';

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
}

interface CloudvelAgentViewProps {
  onCommissionClick?: (postId?: string) => void;
}

export const CloudvelAgentView: React.FC<CloudvelAgentViewProps> = ({ onCommissionClick }) => {
  const [scannedPosts, setScannedPosts] = useState<ScannedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Title</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Subreddit</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Score</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Comment</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Date</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {scannedPosts.map((post) => (
                <tr key={post.id} className="hover:bg-gray-50 transition-colors">
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <a
                        href={getRedditPostUrl(post.post_id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-900 hover:text-indigo-600 font-medium line-clamp-2 flex-1"
                      >
                        {post.post_title || post.post_id}
                      </a>
                      {post.is_commissioned && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          🎨 Commissioned
                        </span>
                      )}
                      <ExternalLink className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      r/{post.subreddit}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-600">
                    {post.post_score?.toLocaleString() || 'N/A'}
                  </td>
                  <td className="py-3 px-4">
                    {post.comment_id ? (
                      <a
                        href={getRedditCommentUrl(post.post_id, post.comment_id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                      >
                        <MessageSquare className="w-4 h-4" />
                        View Comment
                      </a>
                    ) : (
                      <span className="text-gray-400 text-sm">No comment</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-gray-600 text-sm">
                    {formatDate(post.scanned_at)}
                  </td>
                  <td className="py-3 px-4">
                    {post.is_commissioned ? (
                      <a
                        href={`/?filter=reddit_post_id:${post.post_id}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
                      >
                        <span>🎨</span>
                        View Product
                      </a>
                    ) : (
                      <button
                        onClick={() => handleCommissionClick(post.post_id)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 transition-colors"
                      >
                        <DollarSign className="w-4 h-4" />
                        Commission
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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