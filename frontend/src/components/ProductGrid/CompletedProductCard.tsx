import React from 'react';
import type { Task } from '../../types/taskTypes';
import logo from '../../assets/logo.png';

interface CompletedProductCardProps {
  task: Task;
  transitioning: boolean;
}

export const CompletedProductCard: React.FC<CompletedProductCardProps> = ({ 
  task, 
  transitioning 
}) => {
  return (
    <div className={`group relative bg-gradient-to-br from-green-50 to-emerald-100 border-2 border-green-200 rounded-xl p-6 shadow-sm overflow-hidden ${
      transitioning ? 'transition-out' : 'completion-entrance'
    }`}>
      {/* Success background pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0 bg-gradient-to-r from-green-400 via-emerald-400 to-teal-400"></div>
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full min-h-[200px]">
        {/* Success ring with logo */}
        <div className="relative mb-4">
          {/* Success ring */}
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
            {/* Success circle - fully completed */}
            <circle
              cx="50"
              cy="50"
              r="45"
              stroke="#10B981"
              strokeWidth="4"
              fill="none"
              strokeDasharray="283"
              strokeDashoffset="0"
              strokeLinecap="round"
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          
          {/* Success logo in center */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative">
              <img 
                src={logo} 
                alt="Clouvel" 
                className="w-24 h-24 rounded-full object-cover shadow-2xl border-4 border-green-300 ring-4 ring-green-200 transition-all duration-300"
              />
              {/* Success glow effect */}
              <div className="absolute inset-0 bg-green-400 rounded-full opacity-30 blur-md animate-pulse" style={{ animationDuration: '2s' }}></div>
            </div>
          </div>
        </div>

        {/* Success message */}
        <div className="text-center mb-4">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="text-2xl">🎉</span>
            <span className="text-sm font-medium text-green-700">
              Commission Complete!
            </span>
          </div>
          <div className="text-xs text-green-600">
            {task.reddit_username || 'Anonymous'} • ${task.amount_usd?.toFixed(2) || '0.00'}
          </div>
          {task.commission_message && (
            <div className="mt-2 text-xs text-green-600 italic max-w-xs mx-auto">
              "{task.commission_message}"
            </div>
          )}
        </div>

        {/* Success percentage */}
        <div className="text-2xl font-bold text-green-800 mb-2">
          100%
        </div>

        {/* Success bar */}
        <div className="w-full max-w-xs mb-4">
          <div className="w-full bg-green-200 rounded-full h-2">
            <div 
              className="h-2 rounded-full bg-green-500 transition-all duration-1000 ease-out"
              style={{ width: '100%' }}
            ></div>
          </div>
        </div>

        {/* Success indicator */}
        <div className="flex items-center gap-2 text-green-600">
          <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </div>
          <span className="text-sm font-medium">Ready to view!</span>
        </div>
      </div>

      {/* Success corner accent */}
      <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-green-400/20 to-transparent rounded-bl-full"></div>
    </div>
  );
}; 