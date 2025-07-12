import React, { useState, useEffect } from 'react';
// Use local type definitions if not exported from productTypes
// import type { AvailableProduct, PublishResult } from '../../types/productTypes';
import { API_BASE } from '../../utils/apiBase';

interface AvailableProduct {
  id: number;
  name: string;
  description: string;
}

interface PublishResult {
  success: boolean;
  product_id: string;
  subreddit: string;
  dry_run: boolean;
  result: any;
}

const SubredditPublisher: React.FC = () => {
  const [availableProducts, setAvailableProducts] = useState<AvailableProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [publishResult, setPublishResult] = useState<PublishResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dryRun, setDryRun] = useState(true);

  useEffect(() => {
    fetchAvailableProducts();
  }, []);

  const fetchAvailableProducts = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/publish/available-products`);
      if (!response.ok) {
        throw new Error('Failed to fetch available products');
      }
      const data = await response.json();
      setAvailableProducts(data.available_products || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const publishProduct = async (productId: number) => {
    try {
      setLoading(true);
      setError(null);
      setPublishResult(null);

      const response = await fetch(`${API_BASE}/api/publish/product/${productId}?dry_run=${dryRun}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to publish product');
      }

      const result: PublishResult = await response.json();
      setPublishResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading && availableProducts.length === 0) {
    return (
      <div className="p-6">
        <h2 className="text-2xl font-bold mb-4">Subreddit Publisher</h2>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2">Loading available products...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Subreddit Publisher</h2>
        <div className="flex items-center space-x-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="mr-2"
            />
            <span className="text-sm">Dry Run Mode</span>
          </label>
          <button
            onClick={fetchAvailableProducts}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {publishResult && (
        <div className={`mb-4 p-4 border rounded ${
          publishResult.success ? 'bg-green-100 border-green-400 text-green-700' : 'bg-red-100 border-red-400 text-red-700'
        }`}>
          <h3 className="font-bold mb-2">
            {publishResult.success ? '✅ Publication Successful' : '❌ Publication Failed'}
          </h3>
          <pre className="text-sm overflow-auto">
            {JSON.stringify(publishResult, null, 2)}
          </pre>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {availableProducts.map((product) => (
          <div key={product.id} className="border rounded p-4 bg-white shadow">
            <div className="mb-2 font-bold">{product.name}</div>
            <div className="mb-2 text-sm text-gray-600">{product.description}</div>
            <button
              onClick={() => publishProduct(product.id)}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Publish
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SubredditPublisher; 