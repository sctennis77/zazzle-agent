import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import { Layout } from './components/Layout/Layout';
import { ProductGrid } from './components/ProductGrid/ProductGrid';
import CommissionModal from './components/common/CommissionModal';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import DonationSuccessPage from './components/common/DonationSuccessPage';

function App() {
  const [isCommissionModalOpen, setIsCommissionModalOpen] = useState(false);

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
      <Layout onCommissionClick={handleCommissionClick}>
        <Routes>
          <Route path="/" element={<ProductGrid />} />
          <Route path="/tasks" element={<ProductGrid />} />
          <Route path="/donation/success" element={<DonationSuccessPage />} />
        </Routes>
        <CommissionModal 
          isOpen={isCommissionModalOpen} 
          onClose={handleCommissionClose}
          onSuccess={handleCommissionSuccess}
        />
      </Layout>
      <ToastContainer position="top-center" autoClose={2000} hideProgressBar newestOnTop closeOnClick pauseOnFocusLoss={false} draggable pauseOnHover theme="colored" />
    </Router>
  );
}

export default App;
