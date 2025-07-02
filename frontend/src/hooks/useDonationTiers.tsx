import React, { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

export interface DonationTier {
  name: string;
  min_amount: number;
  display_name: string;
}

interface DonationTierContextType {
  tiers: DonationTier[];
  loading: boolean;
  error: string | null;
  getTierDisplay: (tierName: string) => {
    icon: string;
    color: string;
    bgColor: string;
    borderColor?: string;
  };
}

const DonationTierContext = createContext<DonationTierContextType | undefined>(undefined);

export const DonationTierProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [tiers, setTiers] = useState<DonationTier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/donation-tiers')
      .then(res => res.json())
      .then(data => {
        // Ensure data is an array
        if (Array.isArray(data)) {
          setTiers(data);
        } else {
          console.error('Expected array for donation tiers, got:', data);
          setTiers([]);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load donation tiers:', err);
        setError('Failed to load donation tiers');
        setTiers([]);
        setLoading(false);
      });
  }, []);

  // Map tier name to icon/color (string names for icons, actual icons used in components)
  const getTierDisplay = (tierName: string) => {
    const tier = tierName.toLowerCase();
    if (tier === 'sapphire') {
      return { icon: 'FaCrown', color: 'text-blue-600', bgColor: 'bg-blue-100', borderColor: 'border-blue-200' };
    } else if (tier === 'ruby') {
      return { icon: 'FaCrown', color: 'text-red-600', bgColor: 'bg-red-100', borderColor: 'border-red-200' };
    } else if (tier === 'topaz') {
      return { icon: 'FaCrown', color: 'text-yellow-500', bgColor: 'bg-yellow-100', borderColor: 'border-yellow-200' };
    } else if (tier === 'emerald') {
      return { icon: 'FaCrown', color: 'text-green-600', bgColor: 'bg-green-100', borderColor: 'border-green-200' };
    } else if (tier === 'platinum') {
      return { icon: 'FaCrown', color: 'text-gray-700', bgColor: 'bg-gray-200', borderColor: 'border-gray-300' };
    } else if (tier === 'gold') {
      return { icon: 'FaStar', color: 'text-yellow-600', bgColor: 'bg-yellow-100', borderColor: 'border-yellow-200' };
    } else if (tier === 'silver') {
      return { icon: 'FaStar', color: 'text-gray-600', bgColor: 'bg-gray-100', borderColor: 'border-gray-200' };
    } else if (tier === 'bronze') {
      return { icon: 'FaGem', color: 'text-orange-600', bgColor: 'bg-orange-100', borderColor: 'border-orange-200' };
    } else {
      return { icon: 'FaHeart', color: 'text-pink-600', bgColor: 'bg-pink-100', borderColor: 'border-pink-200' };
    }
  };

  return (
    <DonationTierContext.Provider value={{ tiers, loading, error, getTierDisplay }}>
      {children}
    </DonationTierContext.Provider>
  );
};

export const useDonationTiers = () => {
  const context = useContext(DonationTierContext);
  if (!context) {
    throw new Error('useDonationTiers must be used within a DonationTierProvider');
  }
  return context;
}; 