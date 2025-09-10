import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import logo from '../../assets/logo.png';
import React, { useMemo, useState, useEffect } from 'react';
import { createNoise3D } from 'simplex-noise';
import { AnimatedPainting } from '../common/AnimatedPainting';
import { useScheduledRun } from '../../hooks/useScheduledRun';

interface LayoutProps {
  children: ReactNode;
  onCommissionClick?: () => void;
  isCommissionInProgress?: boolean;
}

export const Layout: React.FC<LayoutProps> = ({ children, onCommissionClick, isCommissionInProgress }) => {
  const location = useLocation();
  const [showAnimated, setShowAnimated] = useState(false);
  const [showLogo, setShowLogo] = useState(true);
  const animationDuration = 20; // seconds
  const { data: scheduledRunData } = useScheduledRun();
  const [localTimeRemaining, setLocalTimeRemaining] = useState<number | null>(null);

  // Handle logo click
  const handleLogoClick = () => {
    triggerLogoAnimation();
  };

  // Function to trigger the complete logo animation
  const triggerLogoAnimation = () => {
    setShowLogo(false);
    setShowAnimated(true);
    
    // Set initial countdown value when animation starts
    if (scheduledRunData?.time_remaining_seconds && scheduledRunData.enabled) {
      setLocalTimeRemaining(scheduledRunData.time_remaining_seconds);
    }
    
    // Trigger FAB animation when thank you message appears
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('trigger-fab-animation'));
    }, 500); // Trigger after 500ms when message starts appearing
    
    // After animation, restore logo
    setTimeout(() => {
      setShowAnimated(false);
      setShowLogo(true);
      setLocalTimeRemaining(null); // Clear countdown when animation ends
    }, animationDuration * 1000); // match animation duration
  };

  // Update local countdown every second when showing animation
  useEffect(() => {
    if (!showAnimated || localTimeRemaining === null || localTimeRemaining <= 0) {
      return;
    }

    const interval = setInterval(() => {
      setLocalTimeRemaining(prev => {
        if (prev === null || prev <= 0) return null;
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [showAnimated, localTimeRemaining]);

  // Listen for external animation triggers (e.g., from commission task creation)
  useEffect(() => {
    const handleExternalTrigger = () => {
      triggerLogoAnimation();
    };
    
    window.addEventListener('trigger-logo-animation', handleExternalTrigger);
    
    return () => {
      window.removeEventListener('trigger-logo-animation', handleExternalTrigger);
    };
  }, []);

  // Helper function to format time remaining
  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-100 to-gray-50 text-gray-900">
      {/* Unified Compact Header */}
      <header className="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200/50 sticky top-0 z-50 relative overflow-hidden transition-all duration-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
          {/* Mobile-first responsive layout */}
          <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4 py-3 w-full">
            {/* Mobile: Logo and title first */}
            <div className="flex flex-col items-center gap-1 order-1 sm:order-2 flex-1">
              {/* Static Logo (clickable) */}
              <img
                src={logo}
                alt="Clouvel Logo"
                className={`w-12 h-12 sm:w-16 sm:h-16 rounded-full border-2 border-white shadow-md object-cover cursor-pointer transition-opacity duration-700 ${showLogo ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
                onClick={handleLogoClick}
                style={{ zIndex: 2 }}
              />
              {/* Animated Painting (shows on click) */}
              <div className={`transition-opacity duration-700 ${showAnimated ? 'opacity-100' : 'opacity-0 pointer-events-none'}`} style={{ position: 'absolute', top: 0 }}>
                {showAnimated && <AnimatedPainting logo={logo} animationDuration={animationDuration} />}
              </div>
              {/* Hide title/subtitle during animation */}
              <span className={`text-lg sm:text-xl font-bold text-gray-900 text-center transition-opacity duration-700 ${showAnimated ? 'opacity-0' : 'opacity-100'}`}>Clouvel</span>
              <span className={`text-xs text-gray-500 font-medium text-center transition-opacity duration-700 ${showAnimated ? 'opacity-0' : 'opacity-100'}`}>An AI illustrator Inspired By Reddit</span>
            </div>
            
            {/* Navigation - below logo on mobile, left on desktop */}
            <div className="flex items-center gap-2 order-2 sm:order-1 sm:flex-1">
              <Link
                to="/"
                className={`px-3 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                  location.pathname === '/'
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md'
                    : 'text-gray-700 hover:text-indigo-600 hover:bg-indigo-50/80'
                }`}
              >
                Gallery
              </Link>
              <Link
                to="/fundraising"
                className={`px-3 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                  location.pathname === '/fundraising'
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md'
                    : 'text-gray-700 hover:text-indigo-600 hover:bg-indigo-50/80'
                }`}
              >
                Community
              </Link>
              <Link
                to="/clouvel-agent"
                className={`px-3 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                  location.pathname === '/clouvel-agent'
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-md'
                    : 'text-gray-700 hover:text-indigo-600 hover:bg-indigo-50/80'
                }`}
              >
                Clouvel Studio
              </Link>
            </div>
            
            {/* Thank you message - hidden on mobile, shown on desktop */}
            <div className="hidden sm:flex items-center justify-end order-3 flex-1">
              <div
                className={`transition-all duration-700 text-white bg-gradient-to-r from-emerald-400 via-green-500 to-teal-500 rounded-2xl px-6 py-3 shadow-lg border border-emerald-300/70 ring-2 ring-emerald-200/60
                  ${showAnimated ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-8 pointer-events-none'}`}
                style={{ minWidth: '20rem', textAlign: 'center', letterSpacing: '0.05em', fontFamily: 'system-ui, -apple-system, sans-serif' }}
              >
                <div className="text-xl font-bold mb-1">
                  Thanks for supporting clouvel 🐶❤️
                </div>
                {localTimeRemaining !== null && localTimeRemaining > 0 && (
                  <div className="text-sm font-medium opacity-90">
                    Clouvel will automatically commission a post in: {formatTime(localTimeRemaining)}
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Mobile thank you message - shows full width below header */}
          <div className="sm:hidden w-full">
            <div
              className={`transition-all duration-700 text-white bg-gradient-to-r from-emerald-400 via-green-500 to-teal-500 rounded-xl px-4 py-3 shadow-lg border border-emerald-300/70 ring-2 ring-emerald-200/60 mx-2 mb-2
                ${showAnimated ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4 pointer-events-none'}`}
              style={{ textAlign: 'center', letterSpacing: '0.05em', fontFamily: 'system-ui, -apple-system, sans-serif' }}
            >
              <div className="text-lg font-bold mb-1">
                Thanks for supporting clouvel 🐶❤️
              </div>
              {localTimeRemaining !== null && localTimeRemaining > 0 && (
                <div className="text-sm font-medium opacity-90">
                  Clouvel will automatically commission a post in: {formatTime(localTimeRemaining)}
                </div>
              )}
            </div>
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

const NoiseMaskPainting: React.FC<{ logo: string }> = ({ logo }) => {
  // Grid settings
  const gridCols = 20;
  const gridRows = 20;
  const width = 180;
  const height = 180;
  const cellW = width / gridCols;
  const cellH = height / gridRows;
  const noise3D = useMemo(() => createNoise3D(() => 0.5), []);

  // Generate organic blob path for each cell
  function generateBlobPath(cx: number, cy: number, r: number, seed: number) {
    const points = 12;
    let d = '';
    for (let i = 0; i < points; i++) {
      const angle = (Math.PI * 2 * i) / points;
      // Use simplex noise to perturb the radius
      const noise = noise3D(
        Math.cos(angle) + cx / width,
        Math.sin(angle) + cy / height,
        seed
      );
      const localR = r * (0.85 + 0.25 * noise);
      const x = cx + Math.cos(angle) * localR;
      const y = cy + Math.sin(angle) * localR;
      d += i === 0 ? `M${x},${y}` : `L${x},${y}`;
    }
    d += 'Z';
    return d;
  }

  // Generate all mask pieces
  const maskPieces = useMemo(() => {
    let pieces = [];
    let idx = 0;
    for (let row = 0; row < gridRows; row++) {
      for (let col = 0; col < gridCols; col++) {
        // Center of the cell, with jitter
        const cx = col * cellW + cellW / 2 + (Math.random() - 0.5) * cellW * 0.3;
        const cy = row * cellH + cellH / 2 + (Math.random() - 0.5) * cellH * 0.3;
        // Radius covers the cell, with overlap
        const r = Math.max(cellW, cellH) * (0.7 + Math.random() * 0.5);
        // Each piece gets a unique seed for noise
        const seed = idx * 0.13;
        const path = generateBlobPath(cx, cy, r, seed);
        // Animate in with staggered delay
        const delay = idx * 0.15; // ~6.6s for 400 pieces
        pieces.push(
          <path
            key={idx}
            d={path}
            fill="white"
            style={{
              opacity: 0,
              animation: `fade-in-stroke 0.8s ease forwards`,
              animationDelay: `${delay}s`,
            }}
          />
        );
        idx++;
      }
    }
    return pieces;
  }, [gridCols, gridRows, cellW, cellH, noise3D]);

  return (
    <svg
      className="absolute right-0 top-1/2 -translate-y-1/2 h-[180px] w-[180px]"
      viewBox="0 0 180 180"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ display: 'block' }}
    >
      <defs>
        <mask id="noiseMask">
          {maskPieces}
        </mask>
        <style>{`
          @keyframes fade-in-stroke {
            to { opacity: 1; }
          }
        `}</style>
      </defs>
      <image
        href={logo}
        x="0"
        y="0"
        height="180"
        width="180"
        mask="url(#noiseMask)"
        style={{ opacity: 0.85 }}
      />
    </svg>
  );
}; 