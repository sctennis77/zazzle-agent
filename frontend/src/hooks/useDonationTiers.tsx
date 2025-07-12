import React, { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
// import type { DonationTier, DonationTierContextType } from '../types/productTypes';
import { API_BASE } from '../utils/apiBase';

interface DonationTier {
  name: string;
  min_amount: number;
}

interface DonationTierContextType {
  tiers: DonationTier[];
  loading: boolean;
  error: string | null;
  getTierDisplay: (tierName: string) => { name: string; icon: string };
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
      return { name: 'Sapphire', icon: 'FaCrown' };
    } else if (tier === 'ruby') {
      return { name: 'Ruby', icon: 'FaCrown' };
    } else if (tier === 'topaz') {
      return { name: 'Topaz', icon: 'FaCrown' };
    } else if (tier === 'emerald') {
      return { name: 'Emerald', icon: 'FaCrown' };
    } else if (tier === 'platinum') {
      return { name: 'Platinum', icon: 'FaCrown' };
    } else if (tier === 'gold') {
      return { name: 'Gold', icon: 'FaStar' };
    } else if (tier === 'silver') {
      return { name: 'Silver', icon: 'FaStar' };
    } else if (tier === 'bronze') {
      return { name: 'Bronze', icon: 'FaGem' };
    } else {
      return { name: 'Bronze', icon: 'FaHeart' };
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