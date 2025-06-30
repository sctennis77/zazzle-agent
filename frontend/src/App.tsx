import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import { Layout } from './components/Layout/Layout';
import { ProductGrid } from './components/ProductGrid/ProductGrid';
import CommissionModal from './components/common/CommissionModal';

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
