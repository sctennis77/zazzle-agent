import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import logo from '../../assets/logo.png';

interface LayoutProps {
  children: ReactNode;
  onCommissionClick?: () => void;
  isCommissionInProgress?: boolean;
}

export const Layout: React.FC<LayoutProps> = ({ children, onCommissionClick, isCommissionInProgress }) => {
  const location = useLocation();
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-100 to-gray-50 text-gray-900">
      {/* Unified Compact Header */}
      <header className="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-auto py-3 gap-y-2 w-full">
            {/* Left: Navigation */}
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <Link
                to="/"
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                  location.pathname === '/'
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md'
                    : 'text-gray-700 hover:text-indigo-600 hover:bg-indigo-50/80'
                }`}
              >
                Gallery
              </Link>
              <Link
                to="/fundraising"
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                  location.pathname === '/fundraising'
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md'
                    : 'text-gray-700 hover:text-indigo-600 hover:bg-indigo-50/80'
                }`}
              >
                Fundraising
              </Link>
            </div>
            {/* Center: Logo, Title, Subtitle */}
            <div className="flex flex-col items-center gap-1 min-w-0 flex-1">
              <img
                src={logo}
                alt="Clouvel Logo"
                className="w-16 h-16 rounded-full border-2 border-white shadow-md object-cover mb-1"
              />
              <span className="text-xl font-bold text-gray-900 truncate">Clouvel</span>
              <span className="text-xs text-gray-500 font-medium truncate mb-2">An AI illustrator Inspired By Reddit</span>
            </div>
            {/* Right: Empty for now */}
            <div className="flex-1"></div>
          </div>
        </div>
      </header>
      {/* Main Content */}
      <main className="p-4 sm:p-6 max-w-7xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}; 