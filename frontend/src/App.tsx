import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Layout } from './components/Layout/Layout';
import { ProductGrid } from './components/ProductGrid/ProductGrid';
import CommissionModal from './components/common/CommissionModal';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import DonationSuccessPage from './components/common/DonationSuccessPage';
import EnhancedFundraisingPage from './components/Fundraising/EnhancedFundraisingPage';

function App() {
  const [isCommissionModalOpen, setIsCommissionModalOpen] = useState(false);
  const [isCommissionInProgress, setIsCommissionInProgress] = useState(false);

  // Set document title to override Vite's default
  useEffect(() => {
    document.title = 'Clouvel';
  }, []);

  const handleCommissionClick = () => {
    setIsCommissionModalOpen(true);
  };

  const handleCommissionClose = () => {
    setIsCommissionModalOpen(false);
  };

  const handleCommissionSuccess = () => {
    setIsCommissionModalOpen(false);
    // Don't show success overlay - let user see their in-progress task card immediately
    // The gallery will automatically show the new in-progress task
  };

  return (
    <Router>
      <Routes>
        {/* Routes with Layout */}
        <Route path="/" element={
          <Layout onCommissionClick={handleCommissionClick} isCommissionInProgress={isCommissionInProgress}>
            <ProductGrid onCommissionProgressChange={setIsCommissionInProgress} onCommissionClick={handleCommissionClick} />
            <CommissionModal 
              isOpen={isCommissionModalOpen} 
              onClose={handleCommissionClose}
              onSuccess={handleCommissionSuccess}
            />
          </Layout>
        } />
        <Route path="/tasks" element={
          <Layout onCommissionClick={handleCommissionClick} isCommissionInProgress={isCommissionInProgress}>
            <ProductGrid onCommissionProgressChange={setIsCommissionInProgress} onCommissionClick={handleCommissionClick} />
            <CommissionModal 
              isOpen={isCommissionModalOpen} 
              onClose={handleCommissionClose}
              onSuccess={handleCommissionSuccess}
            />
          </Layout>
        } />
        <Route path="/donation/success" element={
          <Layout onCommissionClick={handleCommissionClick} isCommissionInProgress={isCommissionInProgress}>
            <DonationSuccessPage />
          </Layout>
        } />
        
        {/* Routes without Layout */}
        <Route path="/fundraising" element={<EnhancedFundraisingPage />} />
      </Routes>
      <ToastContainer position="top-center" autoClose={2000} hideProgressBar newestOnTop closeOnClick pauseOnFocusLoss={false} draggable pauseOnHover theme="colored" />
    </Router>
  );
}

export default App;
