import React, { useState, useEffect, useRef } from 'react';
import { FaTimes, FaSearchPlus, FaSearchMinus, FaExpand, FaIdCard, FaCrown, FaStar, FaGem, FaHeart } from 'react-icons/fa';
import { useDonationTiers } from '../../hooks/useDonationTiers';

interface ImageLightboxProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl?: string;
  imageAlt?: string;
  imageTitle?: string;
  // For multiple images mode
  images?: Array<{
    id: string;
    imageUrl: string;
    imageTitle?: string;
    imageAlt?: string;
    redditUsername?: string;
    tierName?: string;
    isAnonymous?: boolean;
  }>;
  currentIndex?: number;
  onNavigate?: (index: number) => void;
  onOpenProductModal?: (productId: string) => void;
}

export const ImageLightbox: React.FC<ImageLightboxProps> = ({ 
  isOpen, 
  onClose, 
  imageUrl, 
  imageAlt = 'Product image',
  imageTitle,
  images,
  currentIndex = 0,
  onNavigate,
  onOpenProductModal
}) => {
  const [zoom, setZoom] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const { getTierDisplay } = useDonationTiers();

  // Determine current image data
  const isMultipleMode = images && images.length > 0;
  const currentImage = isMultipleMode ? images[currentIndex] : {
    imageUrl: imageUrl || '',
    imageAlt: imageAlt,
    imageTitle: imageTitle,
    redditUsername: undefined,
    tierName: undefined,
    isAnonymous: undefined
  };

  // No need to reset state via useEffect since we use key prop for remounting

  // Handle keyboard events
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      
      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case '+':
        case '=':
          handleZoomIn();
          break;
        case '-':
        case '_':
          handleZoomOut();
          break;
        case '0':
          handleResetZoom();
          break;
        case 'ArrowLeft':
          if (isMultipleMode && onNavigate && currentIndex > 0) {
            onNavigate(currentIndex - 1);
          }
          break;
        case 'ArrowRight':
          if (isMultipleMode && onNavigate && images && currentIndex < images.length - 1) {
            onNavigate(currentIndex + 1);
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, isMultipleMode, onNavigate, currentIndex, images]);

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev * 1.2, 3));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev / 1.2, 0.5));
  };

  const handleResetZoom = () => {
    setZoom(1);
    setPosition({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoom <= 1) return;
    setIsDragging(true);
    setDragStart({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || zoom <= 1) return;
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(prev => Math.min(Math.max(prev * delta, 0.5), 3));
  };

  // Touch event states for swipe detection
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [touchEnd, setTouchEnd] = useState<{ x: number; y: number } | null>(null);

  // Handle touch events for mobile
  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    setTouchStart({ x: touch.clientX, y: touch.clientY });
    
    if (zoom > 1 && e.touches.length === 1) {
      setIsDragging(true);
      setDragStart({
        x: touch.clientX - position.x,
        y: touch.clientY - position.y
      });
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    setTouchEnd({ x: touch.clientX, y: touch.clientY });
    
    if (isDragging && zoom > 1 && e.touches.length === 1) {
      setPosition({
        x: touch.clientX - dragStart.x,
        y: touch.clientY - dragStart.y
      });
    }
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
    
    // Detect swipe for navigation
    if (!touchStart || !touchEnd) return;
    
    const deltaX = touchStart.x - touchEnd.x;
    const deltaY = Math.abs(touchStart.y - touchEnd.y);
    const minSwipeDistance = 50;
    
    // Only navigate if horizontal swipe is dominant and zoom is 1
    if (zoom === 1 && Math.abs(deltaX) > minSwipeDistance && Math.abs(deltaX) > deltaY) {
      if (isMultipleMode && onNavigate) {
        if (deltaX > 0 && images && currentIndex < images.length - 1) {
          // Swipe left - next image
          onNavigate(currentIndex + 1);
        } else if (deltaX < 0 && currentIndex > 0) {
          // Swipe right - previous image
          onNavigate(currentIndex - 1);
        }
      }
    }
    
    setTouchStart(null);
    setTouchEnd(null);
  };

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-[100] bg-black bg-opacity-95 flex items-center justify-center"
      onClick={onClose}
    >
      {/* Controls */}
      <div className="absolute top-4 right-4 flex items-center gap-2 z-10">
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleZoomIn();
          }}
          className="p-3 bg-white/10 backdrop-blur-sm rounded-full text-white hover:bg-white/20 transition-colors"
          title="Zoom in (+)"
        >
          <FaSearchPlus size={20} />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleZoomOut();
          }}
          className="p-3 bg-white/10 backdrop-blur-sm rounded-full text-white hover:bg-white/20 transition-colors"
          title="Zoom out (-)"
        >
          <FaSearchMinus size={20} />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleResetZoom();
          }}
          className="p-3 bg-white/10 backdrop-blur-sm rounded-full text-white hover:bg-white/20 transition-colors"
          title="Reset zoom (0)"
        >
          <FaExpand size={20} />
        </button>
        {isMultipleMode && onOpenProductModal && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              const currentImageId = images?.[currentIndex]?.id;
              if (currentImageId) {
                onOpenProductModal(currentImageId);
              }
            }}
            className="p-3 bg-white/10 backdrop-blur-sm rounded-full text-white hover:bg-white/20 transition-colors"
            title="Open product details"
          >
            <FaIdCard size={20} />
          </button>
        )}
        <div className="w-px h-8 bg-white/20" />
        <button
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
          className="p-3 bg-white/10 backdrop-blur-sm rounded-full text-white hover:bg-white/20 transition-colors"
          title="Close (ESC)"
        >
          <FaTimes size={20} />
        </button>
      </div>

      {/* Image title and counter */}
      {/* TODO: Fix title wrapping on larger screens - titles get truncated when controls overlap */}
      <div className="absolute top-4 left-4 max-w-lg">
        {currentImage.imageTitle && (
          <h3 className="text-white text-lg font-semibold drop-shadow-lg">
            {currentImage.imageTitle}
          </h3>
        )}
        {isMultipleMode && currentImage.redditUsername && !currentImage.isAnonymous && (
          <div className="flex items-center gap-2 mt-2">
            {currentImage.tierName && (() => {
              const tierDisplay = getTierDisplay(currentImage.tierName);
              // Map icon string to actual icon component
              const iconMap = {
                crown: FaCrown,
                star: FaStar,
                gem: FaGem,
                heart: FaHeart,
              };
              const TierIcon = iconMap[tierDisplay.icon.replace('Fa', '').toLowerCase() as keyof typeof iconMap] || FaHeart;
              return (
                <TierIcon className={`${tierDisplay.color} drop-shadow-lg`} size={16} />
              );
            })()}
            <span className="text-white/80 text-sm drop-shadow-lg">
              u/{currentImage.redditUsername}
            </span>
          </div>
        )}
        {isMultipleMode && images && (
          <p className="text-white/70 text-sm mt-1">
            {currentIndex + 1} of {images.length}
          </p>
        )}
      </div>

      {/* Zoom indicator */}
      {zoom !== 1 && (
        <div className="absolute bottom-4 left-4 px-3 py-1.5 bg-white/10 backdrop-blur-sm rounded-full text-white text-sm font-medium">
          {Math.round(zoom * 100)}%
        </div>
      )}

      {/* Image container */}
      <div 
        ref={containerRef}
        className="relative w-full h-full flex items-center justify-center overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onWheel={handleWheel}
      >
        {/* Loading state */}
        {!imageLoaded && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-16 h-16 border-4 border-white/30 border-t-white rounded-full animate-spin"></div>
          </div>
        )}

        {/* Main image */}
        <img
          ref={imageRef}
          src={currentImage.imageUrl}
          alt={currentImage.imageAlt || 'Product image'}
          className={`max-w-full max-h-full transition-all duration-200 ${
            zoom > 1 ? 'cursor-move' : 'cursor-zoom-in'
          } ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
          style={{
            transform: `scale(${zoom}) translate(${position.x / zoom}px, ${position.y / zoom}px)`,
            userSelect: 'none',
            WebkitUserSelect: 'none',
            msUserSelect: 'none',
            MozUserSelect: 'none',
          }}
          draggable={false}
          onLoad={() => setImageLoaded(true)}
        />
      </div>

      {/* Navigation arrows for multiple images */}
      {isMultipleMode && onNavigate && (
        <>
          {currentIndex > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onNavigate(currentIndex - 1);
              }}
              className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-white/10 hover:bg-white/20 rounded-full backdrop-blur-sm transition-colors"
              title="Previous (←)"
            >
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
          {images && currentIndex < images.length - 1 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onNavigate(currentIndex + 1);
              }}
              className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-white/10 hover:bg-white/20 rounded-full backdrop-blur-sm transition-colors"
              title="Next (→)"
            >
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </>
      )}

      {/* Instructions */}
      <div className="absolute bottom-4 right-4 text-white/60 text-xs space-y-1">
        <div>Scroll or use +/- to zoom</div>
        {zoom > 1 && <div>Drag to pan</div>}
        {isMultipleMode && <div>← → to navigate</div>}
        <div>Click outside or press ESC to close</div>
      </div>
    </div>
  );
};