import React, { useState, useEffect } from 'react';
import './App.css';
import { ProductGrid } from './components/ProductGrid/ProductGrid';
import { Layout } from './components/Layout/Layout';

// Donation Success Page Component
const DonationSuccess: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
        <div className="text-green-600 mb-6">
          <svg className="w-20 h-20 mx-auto" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Thank You!</h1>
        <p className="text-gray-600 mb-6">
          Your donation has been processed successfully. Your support helps keep this project running!
        </p>
        <button
          onClick={() => window.location.href = '/'}
          className="w-full bg-pink-500 hover:bg-pink-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
        >
          Return to Gallery
        </button>
      </div>
    </div>
  );
};

function App() {
  const [currentPath, setCurrentPath] = useState(window.location.pathname);

  // Handle route changes
  useEffect(() => {
    const handleRouteChange = () => {
      setCurrentPath(window.location.pathname);
    };

    window.addEventListener('popstate', handleRouteChange);
    return () => window.removeEventListener('popstate', handleRouteChange);
  }, []);

  // Show donation success page
  if (currentPath === '/donation-success') {
    return <DonationSuccess />;
  }

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-center mb-8 text-gray-900">
          AI-Generated Products
        </h1>
        <ProductGrid />
      </div>
    </Layout>
  );
}

export default App;
