import React from 'react';
import type { Task } from '../../types/taskTypes';
import { FaTimes, FaRedo, FaSpinner, FaCheckCircle, FaExclamationTriangle, FaClock, FaExternalLinkAlt } from 'react-icons/fa';

interface CommissionStatusBannerProps {
  tasks: Task[];
  onClose: () => void;
  onRefresh: () => void;
  isSidebar?: boolean;
  isStickyHeader?: boolean;
  onViewProduct?: (task: Task) => void;
}

export const CommissionStatusBanner: React.FC<CommissionStatusBannerProps> = ({ 
  tasks, 
  onClose, 
  onRefresh,
  isSidebar = false,
  isStickyHeader = false,
  onViewProduct
}) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <FaCheckCircle className="text-green-500" />;
      case 'failed':
        return <FaExclamationTriangle className="text-red-500" />;
      case 'in_progress':
        return <FaSpinner className="text-blue-500 animate-spin" />;
      case 'pending':
        return <FaClock className="text-yellow-500" />;
      default:
        return <FaClock className="text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 border-green-200 text-green-800';
      case 'failed':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'in_progress':
        return 'bg-blue-50 border-blue-200 text-blue-800';
      case 'pending':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'in_progress':
        return 'In Progress';
      case 'pending':
        return 'Pending';
      default:
        return status;
    }
  };

  const getStageIcon = (stage?: string) => {
    switch (stage) {
      case 'post_fetching':
        return '🔍';
      case 'post_fetched':
        return '📄';
      case 'product_designed':
        return '🎨';
      case 'image_generation_started':
        return '🎭';
      case 'image_generated':
        return '🖼️';
      case 'image_stamped':
        return '🏷️';
      case 'commission_complete':
        return '🎉';
      default:
        return '⚙️';
    }
  };

  const getProgressBarColor = (progress?: number) => {
    if (!progress) return 'bg-gray-300';
    if (progress < 30) return 'bg-red-500';
    if (progress < 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  // Sticky header banner
  if (isStickyHeader) {
    const activeTasks = tasks.filter(t => t.status === 'pending' || t.status === 'in_progress');
    if (activeTasks.length === 0) return null;

    const primaryTask = activeTasks[0];
    const progress = primaryTask.progress || 0;

    return (
      <div className="sticky top-0 z-50 bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg border-b border-purple-500">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <FaSpinner className="animate-spin text-white" />
                <span className="font-semibold">Active Commission</span>
              </div>
              <div className="flex items-center space-x-2 text-sm opacity-90">
                <span>{getStageIcon(primaryTask.stage)}</span>
                <span>{primaryTask.message || 'Processing...'}</span>
                <span className="font-medium">{progress}%</span>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="w-24 bg-white/20 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full transition-all duration-500 ${getProgressBarColor(progress)}`}
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <button
                onClick={onRefresh}
                className="p-1 hover:bg-white/20 rounded transition-colors"
                title="Refresh status"
              >
                <FaRedo className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const containerClasses = isSidebar 
    ? "bg-white rounded-lg shadow-xl border border-gray-200 backdrop-blur-sm bg-white/95"
    : "bg-gradient-to-r from-purple-50 to-pink-50 border-b border-purple-200 shadow-sm";

  const headerClasses = isSidebar
    ? "p-4 border-b border-gray-200"
    : "max-w-6xl mx-auto p-4";

  const contentClasses = isSidebar
    ? "p-4"
    : "max-w-6xl mx-auto p-4";

  return (
    <div className={containerClasses}>
      <div className={headerClasses}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <h3 className={`font-semibold ${isSidebar ? 'text-gray-900' : 'text-purple-900'}`}>
              🎨 {tasks.some(t => t.status === 'pending' || t.status === 'in_progress') ? 'Active Commissions' : 'All Commissions'} ({tasks.length})
            </h3>
            <button
              onClick={onRefresh}
              className={`p-1 transition-colors ${isSidebar ? 'text-gray-600 hover:text-gray-800' : 'text-purple-600 hover:text-purple-800'}`}
              title="Refresh status"
            >
              <FaRedo className="w-4 h-4" />
            </button>
          </div>
          <button
            onClick={onClose}
            className={`p-1 transition-colors ${isSidebar ? 'text-gray-600 hover:text-gray-800' : 'text-purple-600 hover:text-purple-800'}`}
            title="Close sidebar"
          >
            <FaTimes className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className={contentClasses}>
        <div className="space-y-2">
          {tasks.map((task) => (
            <div
              key={task.task_id}
              className={`flex items-center justify-between p-6 rounded-2xl border ${getStatusColor(task.status)} shadow-sm mb-4 transition-opacity duration-500 ${task.justCompleted ? 'opacity-100' : ''}`}
              style={{ minHeight: '110px', boxShadow: '0 2px 12px rgba(80,80,120,0.08)' }}
            >
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-white border border-gray-200 shadow">
                  {getStatusIcon(task.status)}
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-lg text-gray-900 flex items-center gap-2">
                    <span>{task.reddit_username || 'Anonymous'}</span>
                    <span className="text-xs font-normal text-gray-400">•</span>
                    <span className="text-purple-700 font-bold capitalize">{task.tier}</span>
                    {task.subreddit && <span className="text-xs font-normal text-gray-400">•</span>}
                    {task.subreddit && <span className="text-blue-700 font-semibold">r/{task.subreddit}</span>}
                  </div>
                  <div className="text-base opacity-90 flex items-center gap-2 mt-2">
                    <span className="font-medium">{getStatusText(task.status)}</span>
                    {task.amount_usd && (
                      <span className="ml-2 text-xs text-gray-500">${task.amount_usd.toFixed(2)}</span>
                    )}
                  </div>
                  
                  {/* Progress bar for in_progress tasks */}
                  {task.status === 'in_progress' && task.progress !== undefined && (
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                        <span className="flex items-center gap-1">
                          <span>{getStageIcon(task.stage)}</span>
                          <span>{task.message || 'Processing...'}</span>
                        </span>
                        <span className="font-medium">{task.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full transition-all duration-500 ${getProgressBarColor(task.progress)}`}
                          style={{ width: `${task.progress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}
                  
                  {task.created_at && (
                    <div className="text-xs opacity-60 mt-2">
                      Created: {formatDate(task.created_at)}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex flex-col items-end space-y-3 min-w-[110px]">
                {task.status === 'in_progress' && !task.progress && (
                  <div className="flex items-center space-x-1 text-base max-w-[140px] truncate whitespace-nowrap">
                    <FaSpinner className="animate-spin text-blue-500" />
                    <span className="truncate">Processing...</span>
                  </div>
                )}
                {task.status === 'completed' && task.justCompleted && (
                  <button
                    className="flex items-center gap-1 px-5 py-2 bg-green-600 text-white rounded-full text-sm font-bold shadow hover:bg-green-700 transition-colors"
                    onClick={() => onViewProduct && onViewProduct(task)}
                  >
                    <FaExternalLinkAlt className="w-4 h-4" /> View Product
                  </button>
                )}
                {task.error && (
                  <div className="text-sm text-red-600 max-w-xs truncate" title={task.error}>
                    Error: {task.error}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {tasks.length === 0 && (
          <div className={`text-center py-4 ${isSidebar ? 'text-gray-700' : 'text-purple-700'}`}>
            No active commissions
          </div>
        )}
      </div>
    </div>
  );
}; 