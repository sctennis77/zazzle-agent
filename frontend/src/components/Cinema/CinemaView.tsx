import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProducts } from '../../hooks/useProducts';
import { useProductsWithDonations, type ProductWithFullDonationData } from '../../hooks/useProductsWithDonations';
import { ImageLightbox } from '../common/ImageLightbox';
import { ProductModal } from '../ProductGrid/ProductModal';
import { SupportPromptModal } from '../common/SupportPromptModal';
import { downloadImage, generateImageFilename } from '../../utils/downloadImage';
import { toast } from 'react-toastify';
import type { GeneratedProduct } from '../../types/productTypes';

interface CinemaViewProps {
  onCommissionClick?: (postId?: string) => void;
  onDonationClick?: (postId: string, subreddit: string) => void;
}

export const CinemaView: React.FC<CinemaViewProps> = ({ onCommissionClick, onDonationClick }) => {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();
  const { products, loading, error } = useProducts();
  const { productsWithDonations } = useProductsWithDonations(products);
  const [currentIndex, setCurrentIndex] = useState<number | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<ProductWithFullDonationData | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showSupportPrompt, setShowSupportPrompt] = useState(false);
  const [downloadContext, setDownloadContext] = useState<{postId: string, subreddit: string} | null>(null);

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
      window.history.replaceState(null, '', `/cinema/${newPostId}`);
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
      setSelectedProduct(product);
      setShowModal(true);
    }
  };

  const handleDownload = async (imageUrl: string, imageTitle: string, postId: string, subreddit: string) => {
    try {
      // Start download immediately
      const filename = generateImageFilename(imageTitle, postId);
      await downloadImage(imageUrl, filename);
      
      // Show support prompt
      setDownloadContext({ postId, subreddit });
      setShowSupportPrompt(true);
    } catch (error) {
      console.error('Download failed:', error);
      toast.error('Failed to download image');
    }
  };

  const handleSupportYes = () => {
    setShowSupportPrompt(false);
    if (downloadContext && onDonationClick) {
      // Close cinema mode and return to gallery
      navigate('/');
      
      // Open support donation modal via parent handler
      onDonationClick(downloadContext.postId, downloadContext.subreddit);
    }
    setDownloadContext(null);
  };

  const handleSupportNo = () => {
    // Modal will handle showing the "woof" message and closing
    setDownloadContext(null);
  };

  const handleSupportPromptClose = () => {
    setShowSupportPrompt(false);
    setDownloadContext(null);
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
        isOpen={true}
        onClose={handleClose}
        images={productsWithDonations.map(product => ({
          id: product.product_info.id.toString(),
          imageUrl: product.product_info.image_url,
          imageTitle: product.product_info.image_title || product.product_info.theme,
          imageAlt: product.product_info.image_title || product.product_info.theme,
          redditUsername: product.product_info.donation_info?.reddit_username,
          tierName: product.product_info.donation_info?.tier_name,
          isAnonymous: product.product_info.donation_info?.is_anonymous,
          postId: product.reddit_post.post_id,
          subreddit: product.reddit_post.subreddit
        }))}
        currentIndex={currentIndex}
        onNavigate={handleNavigate}
        onOpenProductModal={handleOpenProductModal}
        onDownload={handleDownload}
      />

      {/* Product Modal */}
      {selectedProduct && (
        <ProductModal
          product={selectedProduct}
          isOpen={showModal}
          onClose={() => setShowModal(false)}
        />
      )}

      {/* Support Prompt Modal */}
      <SupportPromptModal
        isOpen={showSupportPrompt}
        onClose={handleSupportPromptClose}
        onSupport={handleSupportYes}
        onNoSupport={handleSupportNo}
      />
    </>
  );
};