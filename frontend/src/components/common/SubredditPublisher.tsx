import React, { useState, useEffect } from 'react';

interface AvailableProduct {
  id: number;
  theme: string;
  product_type: string;
  image_url: string;
  affiliate_link: string;
  original_subreddit: string;
  original_post_title: string;
  original_post_url: string;
  created_at: string;
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
      const response = await fetch('/api/publish/available-products');
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

      const response = await fetch(`/api/publish/product/${productId}?dry_run=${dryRun}`, {
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

      {availableProducts.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-500">No products available for publishing.</p>
          <p className="text-sm text-gray-400 mt-2">
            Run the pipeline first to generate some products.
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          <h3 className="text-lg font-semibold">
            Available Products ({availableProducts.length})
          </h3>
          {availableProducts.map((product) => (
            <div
              key={product.id}
              className="border rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start space-x-4">
                <img
                  src={product.image_url}
                  alt={product.theme}
                  className="w-24 h-24 object-cover rounded"
                />
                <div className="flex-1">
                  <h4 className="font-semibold text-lg">{product.theme}</h4>
                  <p className="text-sm text-gray-600 mb-2">
                    Type: {product.product_type} | 
                    From: r/{product.original_subreddit}
                  </p>
                  <p className="text-sm text-gray-500 mb-2">
                    Original Post: {product.original_post_title}
                  </p>
                  <p className="text-xs text-gray-400">
                    Created: {new Date(product.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex flex-col space-y-2">
                  <button
                    onClick={() => publishProduct(product.id)}
                    disabled={loading}
                    className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
                  >
                    {loading ? 'Publishing...' : 'Publish to r/clouvel'}
                  </button>
                  <a
                    href={product.affiliate_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-center text-sm"
                  >
                    View on Zazzle
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SubredditPublisher; 