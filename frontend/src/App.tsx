import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Layout } from './components/Layout/Layout';
import { ProductGrid } from './components/ProductGrid/ProductGrid';
import CommissionModal from './components/common/CommissionModal';
import DonationModal from './components/common/DonationModal';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import DonationSuccessPage from './components/common/DonationSuccessPage';
import EnhancedFundraisingPage from './components/Fundraising/EnhancedFundraisingPage';
import { CloudvelAgentView } from './components/CloudvelAgent/CloudvelAgentView';
import { CinemaView } from './components/Cinema/CinemaView';

function App() {
  const [isCommissionModalOpen, setIsCommissionModalOpen] = useState(false);
  const [isCommissionInProgress, setIsCommissionInProgress] = useState(false);
  const [initialPostId, setInitialPostId] = useState<string | undefined>();
  const [isDonationModalOpen, setIsDonationModalOpen] = useState(false);
  const [donationContext, setDonationContext] = useState<{postId: string, subreddit: string} | null>(null);

  // Set document title to override Vite's default
  useEffect(() => {
    document.title = 'Clouvel';
  }, []);

  const handleCommissionClick = (postId?: string) => {
    // Ensure postId is actually a string or undefined, not an event object
    const validPostId = typeof postId === 'string' ? postId : undefined;
    setInitialPostId(validPostId);
    setIsCommissionModalOpen(true);
  };

  const handleCommissionClose = () => {
    setIsCommissionModalOpen(false);
    setInitialPostId(undefined);
  };

  const handleCommissionSuccess = () => {
    setIsCommissionModalOpen(false);
    setInitialPostId(undefined);
    // Don't show success overlay - let user see their in-progress task card immediately
    // The gallery will automatically show the new in-progress task
  };

  const handleDonationClick = (postId: string, subreddit: string) => {
    setDonationContext({ postId, subreddit });
    setIsDonationModalOpen(true);
  };

  const handleDonationClose = () => {
    setIsDonationModalOpen(false);
    setDonationContext(null);
  };

  return (
    <Router>
      <Layout onCommissionClick={handleCommissionClick} isCommissionInProgress={isCommissionInProgress}>
        <Routes>
          <Route path="/" element={<ProductGrid onCommissionProgressChange={setIsCommissionInProgress} onCommissionClick={handleCommissionClick} onDonationClick={handleDonationClick} />} />
          <Route path="/tasks" element={<ProductGrid onCommissionProgressChange={setIsCommissionInProgress} onCommissionClick={handleCommissionClick} onDonationClick={handleDonationClick} />} />
          <Route path="/clouvel-agent" element={<CloudvelAgentView onCommissionClick={handleCommissionClick} />} />
          <Route path="/fundraising" element={<EnhancedFundraisingPage />} />
          <Route path="/donation/success" element={<DonationSuccessPage />} />
          <Route path="/cinema/:postId" element={<CinemaView onCommissionClick={handleCommissionClick} onDonationClick={handleDonationClick} />} />
        </Routes>
        <CommissionModal 
          isOpen={isCommissionModalOpen} 
          onClose={handleCommissionClose}
          onSuccess={handleCommissionSuccess}
          initialPostId={initialPostId}
        />
        {donationContext && (
          <DonationModal
            isOpen={isDonationModalOpen}
            onClose={handleDonationClose}
            subreddit={donationContext.subreddit}
            postId={donationContext.postId}
            supportOnly={true}
          />
        )}
      </Layout>
      <ToastContainer position="top-center" autoClose={2000} hideProgressBar newestOnTop closeOnClick pauseOnFocusLoss={false} draggable pauseOnHover theme="colored" />
    </Router>
  );
}

export default App;
