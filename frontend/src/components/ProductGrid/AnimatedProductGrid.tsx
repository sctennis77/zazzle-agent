import React from 'react';
import { ProductCard } from './ProductCard';
import type { GeneratedProduct } from '../../types/productTypes';
import type { Task } from '../../types/taskTypes';
import type { ProductWithFullDonationData } from '../../hooks/useProductsWithDonations';

interface AnimatedProductGridProps {
  products: ProductWithFullDonationData[];
  activeTasks: Task[];
  justPublishedId: number | null;
  isProductJustCompleted: (product: GeneratedProduct) => boolean;
}

export const AnimatedProductGrid: React.FC<AnimatedProductGridProps> = ({
  products,
  activeTasks,
  justPublishedId,
  isProductJustCompleted
}) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6 lg:gap-8">
      {products.map((product, index) => (
        <div key={product.product_info.id}>
          <ProductCard
            product={product}
            activeTasks={activeTasks}
            justPublished={justPublishedId === product.product_info.id}
            justCompleted={isProductJustCompleted(product)}
          />
        </div>
      ))}
    </div>
  );
};