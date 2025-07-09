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
    <div className="min-h-screen bg-gray-50 text-gray-900">
      {/* Navigation Bar */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-8">
              <Link 
                to="/" 
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  location.pathname === '/' 
                    ? 'bg-indigo-100 text-indigo-700' 
                    : 'text-gray-700 hover:text-indigo-600 hover:bg-indigo-50'
                }`}
              >
                Gallery
              </Link>
              <Link 
                to="/fundraising" 
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  location.pathname === '/fundraising' 
                    ? 'bg-indigo-100 text-indigo-700' 
                    : 'text-gray-700 hover:text-indigo-600 hover:bg-indigo-50'
                }`}
              >
                Fundraising
              </Link>
            </div>
          </div>
        </div>
      </nav>
      
      <header className="group relative py-8 px-4 bg-gradient-to-r from-blue-900 via-purple-900 to-indigo-900 shadow-lg overflow-hidden">
        {/* Starry sky overlay - only on hover */}
        <div
          className="pointer-events-none absolute inset-0 z-0 transition-opacity duration-700 bg-gradient-to-b from-indigo-900 via-purple-900 to-transparent star-bg opacity-0 group-hover:opacity-100"
        />
        <div className="max-w-6xl mx-auto flex items-center justify-center relative z-10">
          <div className="flex flex-col items-center space-y-3">
            <div className="relative group cursor-pointer">
              {/* Soft radiating glow behind the logo */}
              <div className={
                `absolute inset-0 flex items-center justify-center z-0 ` +
                ((isCommissionInProgress ? 'animate-pulse ' : '') + 'group-hover:animate-pulse')
              }>
                <div className="h-32 w-32 rounded-full bg-white/30 blur-2xl opacity-70"></div>
              </div>
              <div
                className={
                  `mx-auto mb-4 w-40 h-40 rounded-full border-4 border-white shadow-lg ring-4 ring-purple-400/40 overflow-hidden transition-all duration-500 ` +
                  (isCommissionInProgress ? 'animate-pulse-glow' : '')
                }
              >
                <img
                  src={logo}
                  alt="Clouvel Logo"
                  className="object-cover w-full h-full rounded-full"
                />
              </div>
            </div>
            <div className="text-center">
              <h1 className="text-2xl font-bold text-white tracking-wide drop-shadow-lg">
                Clouvel
              </h1>
              <p className="text-blue-200 text-xs mt-1 font-medium">
                An AI illustrator Inspired By Reddit
              </p>
            </div>
            {/* Commission Button */}
            <button
              onClick={onCommissionClick}
              className="mt-4 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold rounded-full shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 border-2 border-white/20 hover:border-white/30"
            >
              🎨 Commission Art
            </button>
          </div>
        </div>
      </header>
      <main className="p-4 max-w-6xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}; 