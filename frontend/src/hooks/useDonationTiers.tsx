import React, { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
// import type { DonationTier, DonationTierContextType } from '../types/productTypes';
import { API_BASE } from '../utils/apiBase';

interface DonationTier {
  name: string;
  min_amount: number;
  display_name: string;
}

interface DonationTierContextType {
  tiers: DonationTier[];
  loading: boolean;
  error: string | null;
  getTierDisplay: (tierName: string) => {
    name: string;
    icon: string;
    color: string;
    bgColor: string;
    borderColor?: string;
    display_name?: string;
  };
}

const DonationTierContext = createContext<DonationTierContextType | undefined>(undefined);

export const DonationTierProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [tiers, setTiers] = useState<DonationTier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/donation-tiers`)
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
      return { name: 'Sapphire', icon: 'FaCrown', color: 'text-blue-600', bgColor: 'bg-blue-100', borderColor: 'border-blue-200', display_name: 'Sapphire' };
    } else if (tier === 'ruby') {
      return { name: 'Ruby', icon: 'FaCrown', color: 'text-red-600', bgColor: 'bg-red-100', borderColor: 'border-red-200', display_name: 'Ruby' };
    } else if (tier === 'topaz') {
      return { name: 'Topaz', icon: 'FaCrown', color: 'text-yellow-500', bgColor: 'bg-yellow-100', borderColor: 'border-yellow-200', display_name: 'Topaz' };
    } else if (tier === 'emerald') {
      return { name: 'Emerald', icon: 'FaCrown', color: 'text-green-600', bgColor: 'bg-green-100', borderColor: 'border-green-200', display_name: 'Emerald' };
    } else if (tier === 'platinum') {
      return { name: 'Platinum', icon: 'FaCrown', color: 'text-gray-700', bgColor: 'bg-gray-200', borderColor: 'border-gray-300', display_name: 'Platinum' };
    } else if (tier === 'gold') {
      return { name: 'Gold', icon: 'FaStar', color: 'text-yellow-600', bgColor: 'bg-yellow-100', borderColor: 'border-yellow-200', display_name: 'Gold' };
    } else if (tier === 'silver') {
      return { name: 'Silver', icon: 'FaStar', color: 'text-gray-600', bgColor: 'bg-gray-100', borderColor: 'border-gray-200', display_name: 'Silver' };
    } else if (tier === 'bronze') {
      return { name: 'Bronze', icon: 'FaGem', color: 'text-orange-600', bgColor: 'bg-orange-100', borderColor: 'border-orange-200', display_name: 'Bronze' };
    } else {
      return { name: 'Bronze', icon: 'FaHeart', color: 'text-pink-600', bgColor: 'bg-pink-100', borderColor: 'border-pink-200', display_name: 'Bronze' };
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