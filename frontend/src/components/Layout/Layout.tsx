import type { ReactNode } from 'react';
import logo from '../../assets/logo.png';

interface LayoutProps {
  children: ReactNode;
  onCommissionClick?: () => void;
  isCommissionInProgress?: boolean;
}

export const Layout: React.FC<LayoutProps> = ({ children, onCommissionClick, isCommissionInProgress }) => {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="group relative py-8 px-4 bg-gradient-to-r from-blue-900 via-purple-900 to-indigo-900 shadow-lg overflow-hidden">
        {/* Starry sky overlay, hidden by default, fades in on group-hover */}
        <div
          className={
            `pointer-events-none absolute inset-0 z-0 transition-opacity duration-700 bg-gradient-to-b from-indigo-900 via-purple-900 to-transparent` +
            ` star-bg` +
            ` ${isCommissionInProgress ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`
          }
        />
        <div className="max-w-6xl mx-auto flex items-center justify-center relative z-10">
          <div className="flex flex-col items-center space-y-3">
            <div className="relative group cursor-pointer">
              {/* Soft radiating glow behind the logo */}
              <div className={`absolute inset-0 flex items-center justify-center z-0 ${isCommissionInProgress ? 'animate-pulse' : ''}`}>
                <div className="h-32 w-32 rounded-full bg-white/30 blur-2xl opacity-70"></div>
              </div>
              <img 
                src={logo} 
                alt="Logo" 
                className={`h-24 w-24 rounded-full shadow-2xl border-4 border-white/30 ring-4 ring-white/10 relative z-10 transition-all duration-300
                  ${isCommissionInProgress ? 'scale-115 brightness-125 shadow-3xl ring-8 ring-white/30 animate-pulse' : 'group-hover:scale-115 group-hover:brightness-125 group-hover:shadow-3xl group-hover:ring-8 group-hover:ring-white/30'}
                `}
              />
              <div className={`absolute inset-0 rounded-full bg-gradient-to-r from-yellow-400/20 to-orange-400/20 transition-all duration-300 z-10
                ${isCommissionInProgress ? 'animate-pulse from-yellow-300/40 to-orange-300/40 blur-sm' : 'group-hover:from-yellow-300/40 group-hover:to-orange-300/40 group-hover:blur-sm'}`}></div>
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