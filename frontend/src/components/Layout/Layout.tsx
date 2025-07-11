import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import logo from '../../assets/logo.png';
import React, { useMemo, useState, useEffect } from 'react';
import { createNoise3D } from 'simplex-noise';
import { AnimatedPainting } from '../common/AnimatedPainting';

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

  // Handle logo click
  const handleLogoClick = () => {
    triggerLogoAnimation();
  };

  // Function to trigger the complete logo animation
  const triggerLogoAnimation = () => {
    setShowLogo(false);
    setShowAnimated(true);
    
    // Trigger FAB animation when thank you message appears
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('trigger-fab-animation'));
    }, 500); // Trigger after 500ms when message starts appearing
    
    // After animation, restore logo
    setTimeout(() => {
      setShowAnimated(false);
      setShowLogo(true);
    }, animationDuration * 1000); // match animation duration
  };

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-100 to-gray-50 text-gray-900">
      {/* Unified Compact Header */}
      <header className="bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200/50 sticky top-0 z-50 relative overflow-hidden transition-all duration-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
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
            {/* Center: Interactive Logo/AnimatedPainting, Title, Subtitle */}
            <div className="flex flex-col items-center gap-1 min-w-0 flex-1">
              {/* Static Logo (clickable) */}
              <img
                src={logo}
                alt="Clouvel Logo"
                className={`w-16 h-16 rounded-full border-2 border-white shadow-md object-cover mb-1 cursor-pointer transition-opacity duration-700 ${showLogo ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
                onClick={handleLogoClick}
                style={{ zIndex: 2 }}
              />
              {/* Animated Painting (shows on click) */}
              <div className={`transition-opacity duration-700 ${showAnimated ? 'opacity-100' : 'opacity-0 pointer-events-none'}`} style={{ position: 'absolute', top: 0 }}>
                {showAnimated && <AnimatedPainting logo={logo} animationDuration={animationDuration} />}
              </div>
              {/* Hide title/subtitle during animation */}
              <span className={`text-xl font-bold text-gray-900 truncate transition-opacity duration-700 ${showAnimated ? 'opacity-0' : 'opacity-100'}`}>Clouvel</span>
              <span className={`text-xs text-gray-500 font-medium truncate mb-2 transition-opacity duration-700 ${showAnimated ? 'opacity-0' : 'opacity-100'}`}>An AI illustrator Inspired By Reddit</span>
            </div>
            {/* Right: Show message during animation */}
            <div className="flex-1 flex items-center justify-end">
              <span
                className={`transition-all duration-700 text-2xl font-bold text-white bg-gradient-to-r from-emerald-400 via-green-500 to-teal-500 rounded-2xl px-8 py-4 shadow-lg border border-emerald-300/70 ring-2 ring-emerald-200/60
                  ${showAnimated ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-8 pointer-events-none'}`}
                style={{ minWidth: '22rem', textAlign: 'center', letterSpacing: '0.05em', fontFamily: 'system-ui, -apple-system, sans-serif', fontWeight: '600' }}
              >
                Thanks for supporting clouvel 🐶❤️
              </span>
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