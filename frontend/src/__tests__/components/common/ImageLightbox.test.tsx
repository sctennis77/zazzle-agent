import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ImageLightbox } from '../../../components/common/ImageLightbox';
import { describe, it, expect, vi } from 'vitest';

describe('ImageLightbox', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    imageUrl: 'https://example.com/test-image.jpg',
    imageAlt: 'Test image',
    imageTitle: 'Test Title'
  };

  it('should not render when closed', () => {
    const { container } = render(
      <ImageLightbox {...defaultProps} isOpen={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('should render when open', () => {
    render(<ImageLightbox {...defaultProps} />);
    expect(screen.getByAltText('Test image')).toBeInTheDocument();
    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('should show zoom controls', () => {
    render(<ImageLightbox {...defaultProps} />);
    expect(screen.getByTitle('Zoom in (+)')).toBeInTheDocument();
    expect(screen.getByTitle('Zoom out (-)')).toBeInTheDocument();
    expect(screen.getByTitle('Reset zoom (0)')).toBeInTheDocument();
    expect(screen.getByTitle('Close (ESC)')).toBeInTheDocument();
  });

  it('should call onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<ImageLightbox {...defaultProps} onClose={onClose} />);
    
    fireEvent.click(screen.getByTitle('Close (ESC)'));
    expect(onClose).toHaveBeenCalled();
  });

  it('should call onClose when clicking outside the image', () => {
    const onClose = vi.fn();
    const { container } = render(<ImageLightbox {...defaultProps} onClose={onClose} />);
    
    // Click on the backdrop
    const backdrop = container.querySelector('.fixed.inset-0');
    if (backdrop) {
      fireEvent.click(backdrop);
    }
    expect(onClose).toHaveBeenCalled();
  });

  it('should handle keyboard events', () => {
    const onClose = vi.fn();
    render(<ImageLightbox {...defaultProps} onClose={onClose} />);
    
    // Press Escape
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('should display instructions', () => {
    render(<ImageLightbox {...defaultProps} />);
    expect(screen.getByText('Scroll or use +/- to zoom')).toBeInTheDocument();
    expect(screen.getByText('Click outside or press ESC to close')).toBeInTheDocument();
  });

  it('should handle image loading state', () => {
    render(<ImageLightbox {...defaultProps} />);
    const image = screen.getByAltText('Test image');
    
    // Initially image should be hidden (opacity-0)
    expect(image).toHaveClass('opacity-0');
    
    // Simulate image load
    fireEvent.load(image);
    expect(image).toHaveClass('opacity-100');
  });
});