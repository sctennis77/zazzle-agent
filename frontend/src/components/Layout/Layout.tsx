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
      {/* Enhanced Navigation Bar */}
      <nav className="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-1">
              <Link 
                to="/" 
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 relative overflow-hidden ${
                  location.pathname === '/' 
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg shadow-indigo-500/25' 
                    : 'text-gray-700 hover:text-indigo-600 hover:bg-indigo-50/80 hover:shadow-md'
                }`}
              >
                <span className="relative z-10">Gallery</span>
                {location.pathname === '/' && (
                  <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 to-purple-600 opacity-0 hover:opacity-100 transition-opacity duration-300"></div>
                )}
              </Link>
              <Link 
                to="/fundraising" 
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-300 relative overflow-hidden ${
                  location.pathname === '/fundraising' 
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg shadow-indigo-500/25' 
                    : 'text-gray-700 hover:text-indigo-600 hover:bg-indigo-50/80 hover:shadow-md'
                }`}
              >
                <span className="relative z-10">Fundraising</span>
                {location.pathname === '/fundraising' && (
                  <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 to-purple-600 opacity-0 hover:opacity-100 transition-opacity duration-300"></div>
                )}
              </Link>
            </div>
          </div>
        </div>
      </nav>
      
      {/* Enhanced Header */}
      <header className="group relative py-12 px-6 bg-gradient-to-r from-blue-900 via-purple-900 to-indigo-900 shadow-2xl overflow-hidden">
        {/* Enhanced starry sky overlay */}
        <div
          className="pointer-events-none absolute inset-0 z-0 transition-opacity duration-1000 bg-gradient-to-b from-indigo-900 via-purple-900 to-transparent bg-star-bg bg-repeat bg-star-pattern animate-twinkle opacity-0 group-hover:opacity-100"
        />
        
        {/* Additional animated elements */}
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-indigo-500/10 animate-pulse"></div>
        
        <div className="max-w-7xl mx-auto flex items-center justify-center relative z-10">
          <div className="flex flex-col items-center space-y-6">
            <div className="relative group cursor-pointer">
              {/* Enhanced radiating glow behind the logo */}
              <div className={
                `absolute inset-0 flex items-center justify-center z-0 transition-all duration-700 ` +
                ((isCommissionInProgress ? 'animate-pulse ' : '') + 'group-hover:animate-pulse')
              }>
                <div className="h-40 w-40 rounded-full bg-white/20 blur-3xl opacity-60 group-hover:opacity-80 transition-opacity duration-500"></div>
                <div className="h-32 w-32 rounded-full bg-purple-400/30 blur-2xl opacity-40 group-hover:opacity-60 transition-opacity duration-500"></div>
              </div>
              
              {/* Enhanced logo container */}
              <div
                className={
                  `mx-auto mb-4 w-44 h-44 rounded-full border-4 border-white/90 shadow-2xl ring-4 ring-purple-400/30 overflow-hidden transition-all duration-700 transform group-hover:scale-105 group-hover:rotate-3 ` +
                  (isCommissionInProgress ? 'animate-pulse-glow' : '')
                }
              >
                <img
                  src={logo}
                  alt="Clouvel Logo"
                  className="object-cover w-full h-full rounded-full transition-transform duration-700 group-hover:scale-110"
                />
              </div>
            </div>
            
            {/* Enhanced typography */}
            <div className="text-center space-y-2">
              <h1 className="text-4xl font-bold text-white tracking-wide drop-shadow-2xl bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent">
                Clouvel
              </h1>
              <p className="text-blue-200 text-sm font-medium tracking-wide">
                An AI illustrator Inspired By Reddit
              </p>
            </div>
            
            {/* Enhanced Commission Button */}
            <button
              onClick={onCommissionClick}
              className="mt-6 px-8 py-4 bg-gradient-to-r from-purple-600 via-pink-600 to-purple-600 hover:from-purple-700 hover:via-pink-700 hover:to-purple-700 text-white font-bold rounded-2xl shadow-2xl hover:shadow-purple-500/25 transform hover:scale-105 transition-all duration-300 border-2 border-white/20 hover:border-white/40 relative overflow-hidden group"
            >
              <span className="relative z-10 flex items-center gap-2">
                <span className="text-lg">🎨</span>
                Commission Art
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-purple-400/20 via-pink-400/20 to-purple-400/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            </button>
          </div>
        </div>
      </header>
      
      {/* Enhanced Main Content */}
      <main className="p-6 max-w-7xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}; 