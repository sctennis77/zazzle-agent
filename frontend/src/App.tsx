import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Layout } from './components/Layout/Layout';
import { ProductGrid } from './components/ProductGrid/ProductGrid';
import CommissionModal from './components/common/CommissionModal';
import React from 'react';

// Success overlay component
const CommissionSuccess = ({ onClose }: { onClose: () => void }) => {
  React.useEffect(() => {
    const timeout = setTimeout(() => {
      onClose();
    }, 2000);
    return () => clearTimeout(timeout);
  }, [onClose]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-8 max-w-md mx-4 text-center shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-gray-400 hover:text-gray-700 text-2xl font-bold focus:outline-none"
          aria-label="Close"
        >
          ×
        </button>
        <div className="text-green-600 mb-4">
          <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Commission Submitted Successfully!</h2>
        <p className="text-gray-600 mb-2">Your commission has been submitted and will be processed soon.</p>
      </div>
    </div>
  );
};

function CommissionSuccessPage({ onSuccess }: { onSuccess: () => void }) {
  useEffect(() => {
    // Show overlay, then redirect to gallery after 1.5s
    const timeout = setTimeout(() => {
      onSuccess();
      window.history.replaceState({}, '', '/'); // SPA redirect to gallery
    }, 1500);
    return () => clearTimeout(timeout);
  }, [onSuccess]);

  return <CommissionSuccess onClose={onSuccess} />;
}

function App() {
  const [isCommissionModalOpen, setIsCommissionModalOpen] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleCommissionClick = () => {
    setIsCommissionModalOpen(true);
  };

  const handleCommissionClose = () => {
    setIsCommissionModalOpen(false);
  };

  const handleCommissionSuccess = () => {
    setIsCommissionModalOpen(false);
    setShowSuccess(true);
  };

  const handleSuccessClose = () => {
    setShowSuccess(false);
    window.history.replaceState({}, '', '/'); // SPA redirect to gallery
  };

  return (
    <Router>
      <Layout onCommissionClick={handleCommissionClick}>
        <Routes>
          <Route path="/" element={<ProductGrid />} />
          <Route path="/tasks" element={<ProductGrid />} />
          <Route path="/commission/success" element={<CommissionSuccessPage onSuccess={handleSuccessClose} />} />
        </Routes>
        <CommissionModal 
          isOpen={isCommissionModalOpen} 
          onClose={handleCommissionClose}
          onSuccess={handleCommissionSuccess}
        />
        {showSuccess && <CommissionSuccess onClose={handleSuccessClose} />}
      </Layout>
    </Router>
  );
}

export default App;
