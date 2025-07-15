import { render, renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DonationTierProvider, useDonationTiers } from '../../hooks/useDonationTiers';

const mockTiers = [
  { name: 'bronze', min_amount: 1, display_name: 'Bronze' },
  { name: 'silver', min_amount: 5, display_name: 'Silver' },
  { name: 'gold', min_amount: 10, display_name: 'Gold' },
  { name: 'diamond', min_amount: 25, display_name: 'Diamond' }
];

const mockFetch = vi.fn();
global.fetch = mockFetch;

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <DonationTierProvider>{children}</DonationTierProvider>
);

describe('useDonationTiers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch and provide donation tiers', async () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockTiers)
    });

    const { result } = renderHook(() => useDonationTiers(), {
      wrapper: TestWrapper
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.tiers).toEqual([]);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.tiers).toEqual(mockTiers);
    expect(result.current.error).toBe(null);
    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/donation-tiers');
  });

  it('should handle API errors', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useDonationTiers(), {
      wrapper: TestWrapper
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.tiers).toEqual([]);
    expect(result.current.error).toBe('Failed to load donation tiers');
  });

  it('should handle non-array response', async () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve({ invalid: 'response' })
    });

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useDonationTiers(), {
      wrapper: TestWrapper
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.tiers).toEqual([]);
    expect(consoleSpy).toHaveBeenCalledWith('Expected array for donation tiers, got:', { invalid: 'response' });

    consoleSpy.mockRestore();
  });

  it('should provide correct tier display for diamond', () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockTiers)
    });

    const { result } = renderHook(() => useDonationTiers(), {
      wrapper: TestWrapper
    });

    const display = result.current.getTierDisplay('diamond');
    
    expect(display).toEqual({
      name: 'Diamond',
      icon: 'FaCrown',
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      borderColor: 'border-purple-200',
      display_name: 'Diamond'
    });
  });

  it('should provide correct tier display for gold', () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockTiers)
    });

    const { result } = renderHook(() => useDonationTiers(), {
      wrapper: TestWrapper
    });

    const display = result.current.getTierDisplay('gold');
    
    expect(display).toEqual({
      name: 'Gold',
      icon: 'FaStar',
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
      borderColor: 'border-yellow-200',
      display_name: 'Gold'
    });
  });

  it('should provide correct tier display for silver', () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockTiers)
    });

    const { result } = renderHook(() => useDonationTiers(), {
      wrapper: TestWrapper
    });

    const display = result.current.getTierDisplay('silver');
    
    expect(display).toEqual({
      name: 'Silver',
      icon: 'FaStar',
      color: 'text-gray-600',
      bgColor: 'bg-gray-100',
      borderColor: 'border-gray-200',
      display_name: 'Silver'
    });
  });

  it('should provide correct tier display for bronze', () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockTiers)
    });

    const { result } = renderHook(() => useDonationTiers(), {
      wrapper: TestWrapper
    });

    const display = result.current.getTierDisplay('bronze');
    
    expect(display).toEqual({
      name: 'Bronze',
      icon: 'FaGem',
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
      borderColor: 'border-orange-200',
      display_name: 'Bronze'
    });
  });

  it('should provide default tier display for unknown tier', () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockTiers)
    });

    const { result } = renderHook(() => useDonationTiers(), {
      wrapper: TestWrapper
    });

    const display = result.current.getTierDisplay('unknown');
    
    expect(display).toEqual({
      name: 'Bronze',
      icon: 'FaHeart',
      color: 'text-pink-600',
      bgColor: 'bg-pink-100',
      borderColor: 'border-pink-200',
      display_name: 'Bronze'
    });
  });

  it('should throw error when used outside provider', () => {
    expect(() => {
      renderHook(() => useDonationTiers());
    }).toThrow('useDonationTiers must be used within a DonationTierProvider');
  });

  it('should render provider with children', () => {
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockTiers)
    });

    const TestChild = () => <div>Test Child</div>;

    const { getByText } = render(
      <DonationTierProvider>
        <TestChild />
      </DonationTierProvider>
    );

    expect(getByText('Test Child')).toBeInTheDocument();
  });
});