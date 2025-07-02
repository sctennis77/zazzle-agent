import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
import { Layout } from './components/Layout/Layout';
import { ProductGrid } from './components/ProductGrid/ProductGrid';
import TaskDashboard from './components/TaskDashboard/TaskDashboard';
import CommissionModal from './components/common/CommissionModal';

// Simple success component that redirects to gallery
const CommissionSuccess = () => {
  // Redirect to gallery after a brief moment
  setTimeout(() => {
    window.location.href = '/';
  }, 1000);
  
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="text-green-600 mb-4">
          <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Commission Submitted Successfully!</h2>
        <p className="text-gray-600">Redirecting to gallery...</p>
      </div>
    </div>
  );
};

function App() {
  const [isCommissionModalOpen, setIsCommissionModalOpen] = useState(false);

  const handleCommissionClick = () => {
    setIsCommissionModalOpen(true);
  };

  const handleCommissionClose = () => {
    setIsCommissionModalOpen(false);
  };

  return (
    <Router>
      <Layout onCommissionClick={handleCommissionClick}>
        <Routes>
          <Route path="/" element={<ProductGrid />} />
          <Route path="/tasks" element={<TaskDashboard />} />
          <Route path="/commission/success" element={<CommissionSuccess />} />
        </Routes>
      </Layout>
      <CommissionModal 
        isOpen={isCommissionModalOpen} 
        onClose={handleCommissionClose} 
      />
    </Router>
  );
}

export default App;
