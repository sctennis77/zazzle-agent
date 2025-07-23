import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProducts } from '../../hooks/useProducts';
import { useProductsWithDonations } from '../../hooks/useProductsWithDonations';

export const CinemaView: React.FC = () => {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();
  const { products, loading } = useProducts();
  const { productsWithDonations } = useProductsWithDonations(products);

  useEffect(() => {
    if (loading || productsWithDonations.length === 0) return;

    if (postId) {
      const index = productsWithDonations.findIndex(
        product => product.reddit_post.post_id === postId
      );
      
      if (index !== -1) {
        // Navigate to main page with cinema query params to trigger full screen mode
        navigate(`/?cinema=${postId}&index=${index}`, { replace: true });
      } else {
        // Post not found, redirect to home
        navigate('/', { replace: true });
      }
    } else {
      navigate('/', { replace: true });
    }
  }, [productsWithDonations, postId, navigate, loading]);

  // Show loading state while redirecting
  return (
    <div className="fixed inset-0 bg-black flex items-center justify-center">
      <div className="text-white text-lg">Loading...</div>
    </div>
  );
};