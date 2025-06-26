import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout/Layout';
import { ProductGrid } from './components/ProductGrid/ProductGrid';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<ProductGrid />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
