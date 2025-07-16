import React, { useState, useRef, useEffect } from 'react';
import { FaChevronDown, FaFilter, FaClock, FaDollarSign, FaReddit, FaTimes, FaCheck } from 'react-icons/fa';

export interface SortOption {
  value: string;
  label: string;
  icon: React.ReactNode;
}

export interface SortingControlsProps {
  sortBy: string;
  onSortChange: (sortBy: string) => void;
  selectedSubreddits: string[];
  onSubredditChange: (subreddits: string[]) => void;
  availableSubreddits: string[];
}

const sortOptions: SortOption[] = [
  { value: 'time-desc', label: 'Newest First', icon: <FaClock className="w-4 h-4" /> },
  { value: 'donation-desc', label: 'Most Donated', icon: <FaDollarSign className="w-4 h-4" /> },
];

export const SortingControls: React.FC<SortingControlsProps> = ({
  sortBy,
  onSortChange,
  selectedSubreddits,
  onSubredditChange,
  availableSubreddits
}) => {
  const [showSubredditFilter, setShowSubredditFilter] = useState(false);
  const filterRef = useRef<HTMLDivElement>(null);
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
        setShowSubredditFilter(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubredditToggle = (subreddit: string) => {
    if (selectedSubreddits.includes(subreddit)) {
      onSubredditChange(selectedSubreddits.filter(s => s !== subreddit));
    } else {
      onSubredditChange([...selectedSubreddits, subreddit]);
    }
  };

  const clearSubredditFilter = () => {
    onSubredditChange([]);
  };

  const currentSortOption = sortOptions.find(option => option.value === sortBy) || sortOptions[0];

  return (
    <div className="mb-6">
      <div className="flex items-center justify-end gap-2">
        {/* Sort Controls - Icon only buttons */}
        {sortOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => onSortChange(option.value)}
            className={`flex items-center justify-center w-10 h-10 rounded-lg text-sm font-medium transition-all duration-200 ${
              sortBy === option.value
                ? 'bg-blue-600 text-white shadow-md'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 hover:border-gray-400'
            }`}
            title={option.label}
            aria-label={option.label}
          >
            {option.icon}
          </button>
        ))}

        {/* Subreddit Filter */}
        <div className="flex items-center gap-2" ref={filterRef}>

          {/* Filter button */}
          <div className="relative">
            <button
              onClick={() => setShowSubredditFilter(!showSubredditFilter)}
              className={`relative flex items-center justify-center w-10 h-10 rounded-lg text-sm font-medium transition-all duration-200 ${
                showSubredditFilter || selectedSubreddits.length > 0
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 hover:border-gray-400'
              }`}
              title="Filter by subreddit"
              aria-label="Filter by subreddit"
            >
              <FaFilter className="w-4 h-4" />
              {selectedSubreddits.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
                  {selectedSubreddits.length}
                </span>
              )}
            </button>

            {/* Subreddit dropdown */}
            {showSubredditFilter && (
              <div className="absolute right-0 top-full mt-2 w-72 bg-white rounded-xl shadow-lg border border-gray-200 z-20 max-h-80 overflow-hidden">
                <div className="p-4 border-b border-gray-100 bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                      <FaReddit className="w-4 h-4 text-orange-500" />
                      Filter by Subreddit
                    </div>
                    {selectedSubreddits.length > 0 && (
                      <button
                        onClick={clearSubredditFilter}
                        className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                      >
                        Clear all
                      </button>
                    )}
                  </div>
                </div>
                <div className="max-h-60 overflow-y-auto">
                  {availableSubreddits.map((subreddit) => {
                    const isSelected = selectedSubreddits.includes(subreddit);
                    return (
                      <button
                        key={subreddit}
                        onClick={() => handleSubredditToggle(subreddit)}
                        className="w-full flex items-center gap-3 p-3 hover:bg-gray-50 transition-colors text-left"
                      >
                        <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                          isSelected 
                            ? 'bg-blue-600 border-blue-600' 
                            : 'border-gray-300'
                        }`}>
                          {isSelected && <FaCheck className="w-2 h-2 text-white" />}
                        </div>
                        <span className="text-sm text-gray-700 font-medium">r/{subreddit}</span>
                      </button>
                    );
                  })}
                  {availableSubreddits.length === 0 && (
                    <div className="text-sm text-gray-500 text-center py-8">
                      No subreddits available
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};