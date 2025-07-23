import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProducts } from '../../hooks/useProducts';
import { useProductsWithDonations, type ProductWithFullDonationData } from '../../hooks/useProductsWithDonations';
import { ImageLightbox } from '../common/ImageLightbox';
import { ProductModal } from '../ProductGrid/ProductModal';
import type { GeneratedProduct } from '../../types/productTypes';

export const CinemaView: React.FC = () => {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();
  const { products, loading, error } = useProducts();
  const { productsWithDonations } = useProductsWithDonations(products);
  const [currentIndex, setCurrentIndex] = useState<number | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<GeneratedProduct | null>(null);
  const [showModal, setShowModal] = useState(false);

  // Find the product index based on postId
  useEffect(() => {
    if (productsWithDonations.length > 0 && postId) {
      const index = productsWithDonations.findIndex(
        product => product.reddit_post.post_id === postId
      );
      if (index !== -1) {
        setCurrentIndex(index);
      } else {
        // If post not found, redirect to home
        navigate('/');
      }
    }
  }, [productsWithDonations, postId, navigate]);

  // Update URL when navigating between images
  const handleNavigate = (newIndex: number) => {
    setCurrentIndex(newIndex);
    const newPostId = productsWithDonations[newIndex]?.reddit_post.post_id;
    if (newPostId) {
      navigate(`/cinema/${newPostId}`, { replace: true });
    }
  };

  // Close cinema mode and return to gallery
  const handleClose = () => {
    navigate('/');
  };

  // Open product modal
  const handleOpenProductModal = (productId: string) => {
    const product = productsWithDonations.find(p => p.product_info.id.toString() === productId);
    if (product) {
      setSelectedProduct(product as GeneratedProduct);
      setShowModal(true);
    }
  };

  if (loading || currentIndex === null) {
    return (
      <div className="fixed inset-0 bg-black flex items-center justify-center">
        <div className="text-white text-lg">Loading...</div>
      </div>
    );
  }

  if (error || productsWithDonations.length === 0) {
    return (
      <div className="fixed inset-0 bg-black flex items-center justify-center">
        <div className="text-white text-lg">Unable to load cinema view</div>
      </div>
    );
  }

  return (
    <>
      <ImageLightbox
        key={`lightbox-${currentIndex}`}
        isOpen={true}
        onClose={handleClose}
        images={productsWithDonations.map(product => ({
          id: product.product_info.id.toString(),
          imageUrl: product.product_info.image_url,
          imageTitle: product.product_info.image_title || product.product_info.theme,
          imageAlt: product.product_info.image_title || product.product_info.theme,
          redditUsername: product.product_info.donation_info?.reddit_username,
          tierName: product.product_info.donation_info?.tier_name,
          isAnonymous: product.product_info.donation_info?.is_anonymous
        }))}
        currentIndex={currentIndex}
        onNavigate={handleNavigate}
        onOpenProductModal={handleOpenProductModal}
      />

      {/* Product Modal */}
      {selectedProduct && (
        <ProductModal
          product={selectedProduct}
          isOpen={showModal}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
};