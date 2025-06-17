import type { ReactNode } from 'react';
import logo from '../../assets/logo.png';

interface LayoutProps {
  children: ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="group relative py-8 px-4 bg-gradient-to-r from-blue-900 via-purple-900 to-indigo-900 shadow-lg overflow-hidden">
        {/* Starry sky overlay, hidden by default, fades in on group-hover */}
        <div className="pointer-events-none absolute inset-0 z-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 bg-gradient-to-b from-indigo-900 via-blue-900 to-slate-800">
          {/* Star field with more stars and twinkling effect */}
          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Static and twinkling stars */}
            <circle cx="10" cy="20" r="0.7" fill="white" fillOpacity="0.8" className="twinkle"/>
            <circle cx="30" cy="40" r="1.2" fill="white" fillOpacity="0.7" className="twinkle delay-1"/>
            <circle cx="70" cy="60" r="0.9" fill="white" fillOpacity="0.6" className="twinkle delay-2"/>
            <circle cx="50" cy="80" r="0.5" fill="white" fillOpacity="0.5"/>
            <circle cx="80" cy="30" r="1.1" fill="white" fillOpacity="0.8" className="twinkle delay-3"/>
            <circle cx="60" cy="15" r="0.6" fill="white" fillOpacity="0.7"/>
            <circle cx="90" cy="90" r="0.8" fill="white" fillOpacity="0.6" className="twinkle delay-4"/>
            <circle cx="20" cy="70" r="0.5" fill="white" fillOpacity="0.5"/>
            <circle cx="15" cy="10" r="0.4" fill="white" fillOpacity="0.6"/>
            <circle cx="25" cy="60" r="0.6" fill="white" fillOpacity="0.7" className="twinkle delay-5"/>
            <circle cx="40" cy="25" r="0.5" fill="white" fillOpacity="0.8"/>
            <circle cx="55" cy="35" r="0.7" fill="white" fillOpacity="0.6"/>
            <circle cx="65" cy="75" r="0.5" fill="white" fillOpacity="0.7"/>
            <circle cx="75" cy="50" r="0.6" fill="white" fillOpacity="0.7" className="twinkle delay-6"/>
            <circle cx="85" cy="20" r="0.4" fill="white" fillOpacity="0.5"/>
            <circle cx="95" cy="55" r="0.5" fill="white" fillOpacity="0.6"/>
            <circle cx="35" cy="90" r="0.6" fill="white" fillOpacity="0.7"/>
            <circle cx="60" cy="55" r="0.4" fill="white" fillOpacity="0.5"/>
            <circle cx="12" cy="55" r="0.5" fill="white" fillOpacity="0.6"/>
            <circle cx="22" cy="80" r="0.4" fill="white" fillOpacity="0.5" className="twinkle delay-7"/>
            <circle cx="45" cy="60" r="0.6" fill="white" fillOpacity="0.7"/>
            <circle cx="58" cy="10" r="0.5" fill="white" fillOpacity="0.6"/>
            <circle cx="77" cy="18" r="0.7" fill="white" fillOpacity="0.7"/>
            <circle cx="88" cy="40" r="0.5" fill="white" fillOpacity="0.6"/>
            <circle cx="70" cy="85" r="0.6" fill="white" fillOpacity="0.7" className="twinkle delay-8"/>
            <circle cx="80" cy="60" r="0.4" fill="white" fillOpacity="0.5"/>
            <circle cx="55" cy="90" r="0.5" fill="white" fillOpacity="0.6"/>
            <circle cx="25" cy="15" r="0.5" fill="white" fillOpacity="0.7"/>
            <circle cx="38" cy="50" r="0.4" fill="white" fillOpacity="0.5"/>
            <circle cx="90" cy="10" r="0.5" fill="white" fillOpacity="0.6" className="twinkle delay-9"/>
          </svg>
        </div>
        <div className="max-w-6xl mx-auto flex items-center justify-center relative z-10">
          <div className="flex flex-col items-center space-y-3">
            <div className="relative group cursor-pointer">
              {/* Soft radiating glow behind the logo */}
              <div className="absolute inset-0 flex items-center justify-center z-0">
                <div className="h-32 w-32 rounded-full bg-white/30 blur-2xl opacity-70 animate-pulse"></div>
              </div>
              <img 
                src={logo} 
                alt="Logo" 
                className="h-24 w-24 rounded-full shadow-2xl border-4 border-white/30 group-hover:scale-115 group-hover:brightness-125 group-hover:shadow-3xl group-hover:ring-8 group-hover:ring-white/30 transition-all duration-300 ring-4 ring-white/10 relative z-10"
              />
              <div className="absolute inset-0 rounded-full bg-gradient-to-r from-yellow-400/20 to-orange-400/20 animate-pulse group-hover:from-yellow-300/40 group-hover:to-orange-300/40 group-hover:blur-sm transition-all duration-300 z-10"></div>
            </div>
            <div className="text-center">
              <h1 className="text-2xl font-bold text-white tracking-wide drop-shadow-lg">
                Clouvel
              </h1>
              <p className="text-blue-200 text-xs mt-1 font-medium">
                An AI illustrator Inspired By Reddit
              </p>
            </div>
          </div>
        </div>
      </header>
      <main className="p-4 max-w-6xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}; 