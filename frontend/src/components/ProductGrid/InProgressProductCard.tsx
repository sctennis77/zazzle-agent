import React from 'react';
import type { Task } from '../../types/taskTypes';
import logo from '../../assets/logo.png';

interface InProgressProductCardProps {
  task: Task;
  onCancel?: (taskId: string) => void;
}

export const InProgressProductCard: React.FC<InProgressProductCardProps> = ({ 
  task, 
  onCancel 
}) => {
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

  const getProgressColor = (progress?: number) => {
    if (!progress) return '#6B7280';
    if (progress < 30) return '#EF4444'; // red
    if (progress < 70) return '#F59E0B'; // yellow
    return '#10B981'; // green
  };

  const progress = task.progress || 0;
  const progressColor = getProgressColor(progress);
  const circumference = 2 * Math.PI * 45; // radius = 45
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="group relative bg-gradient-to-br from-gray-50 to-gray-100 border-2 border-gray-200 rounded-xl p-6 shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden">
      {/* Animated background pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute inset-0 bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 animate-pulse"></div>
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full min-h-[200px]">
        {/* Progress ring with logo */}
        <div className="relative mb-4">
          {/* Progress ring */}
          <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 100 100">
            {/* Background circle */}
            <circle
              cx="50"
              cy="50"
              r="45"
              stroke="#E5E7EB"
              strokeWidth="4"
              fill="none"
            />
            {/* Progress circle */}
            <circle
              cx="50"
              cy="50"
              r="45"
              stroke={progressColor}
              strokeWidth="4"
              fill="none"
              strokeDasharray={strokeDasharray}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              className="transition-all duration-500 ease-out"
            />
          </svg>
          
          {/* Animated logo in center */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative">
              <img 
                src={logo} 
                alt="Clouvel" 
                className="w-24 h-24 rounded-full object-cover shadow-2xl border-4 border-white/30 ring-4 ring-white/10 animate-pulse transition-all duration-300"
                style={{ animationDuration: '2s' }}
              />
              {/* Subtle glow effect */}
              <div className="absolute inset-0 bg-purple-400 rounded-full opacity-20 blur-md animate-ping"></div>
            </div>
          </div>
        </div>

        {/* Status message */}
        <div className="text-center mb-4">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="text-2xl">{getStageIcon(task.stage)}</span>
            <span className="text-sm font-medium text-gray-700">
              {task.message || 'Processing...'}
            </span>
          </div>
          <div className="text-xs text-gray-500">
            {task.reddit_username || 'Anonymous'} • ${task.amount_usd?.toFixed(2) || '0.00'}
          </div>
          {task.commission_message && (
            <div className="mt-2 text-xs text-gray-600 italic max-w-xs mx-auto">
              "{task.commission_message}"
            </div>
          )}
        </div>

        {/* Progress percentage */}
        <div className="text-2xl font-bold text-gray-800 mb-2">
          {progress}%
        </div>

        {/* Progress bar */}
        <div className="w-full max-w-xs mb-4">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="h-2 rounded-full transition-all duration-500 ease-out"
              style={{ 
                width: `${progress}%`,
                backgroundColor: progressColor
              }}
            ></div>
          </div>
        </div>

        {/* Cancel button */}
        {onCancel && (
          <button
            onClick={() => onCancel(task.task_id)}
            className="px-4 py-2 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-colors duration-200 opacity-0 group-hover:opacity-100"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Subtle corner accent */}
      <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-purple-400/20 to-transparent rounded-bl-full"></div>
    </div>
  );
}; 