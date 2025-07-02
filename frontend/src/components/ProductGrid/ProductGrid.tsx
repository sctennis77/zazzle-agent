import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useProducts } from '../../hooks/useProducts';
import { ProductCard } from './ProductCard';
import { ProductModal } from './ProductModal';
import { CommissionStatusBanner } from './CommissionStatusBanner';
import type { GeneratedProduct } from '../../types/productTypes';
import type { Task, WebSocketMessage } from '../../types/taskTypes';
import { FaTasks } from 'react-icons/fa';

export const ProductGrid: React.FC = () => {
  const { products, loading, error, refresh: refreshProducts, setProducts } = useProducts();
  const [searchParams] = useSearchParams();
  const [selectedProduct, setSelectedProduct] = useState<GeneratedProduct | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [activeTasks, setActiveTasks] = useState<Task[]>([]);
  const [showCommissionSidebar, setShowCommissionSidebar] = useState(true);
  const [allTasks, setAllTasks] = useState<Task[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // Handle query parameter for opening specific product
  useEffect(() => {
    const productPostId = searchParams.get('product');
    if (productPostId && products.length > 0) {
      const product = products.find(p => p.reddit_post.post_id === productPostId);
      if (product) {
        setSelectedProduct(product);
        setShowModal(true);
        // Remove the query parameter from URL after opening the modal
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('product');
        window.history.replaceState({}, '', newUrl.toString());
      }
    }
  }, [searchParams, products]);

  // Setup WebSocket for real-time task updates
  useEffect(() => {
    setupWebSocket();
    fetchActiveTasks();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const setupWebSocket = () => {
    const wsUrl = window.location.hostname === 'localhost' 
      ? 'ws://localhost:8000/ws/tasks'
      : `ws://${window.location.hostname}:8000/ws/tasks`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected for gallery updates:', wsUrl);
    };

    ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      if (message.type === 'task_update') {
        // Update specific task
        setActiveTasks(prevTasks => {
          const updatedTasks = prevTasks.map(task =>
            task.task_id === message.task_id
              ? { ...task, ...message.data }
              : task
          );
          // If task just completed, add justCompleted flag and timestamp
          if (message.data.status === 'completed') {
            return updatedTasks.map(task =>
              task.task_id === message.task_id
                ? { ...task, justCompleted: true, completedAt: Date.now() }
                : task
            );
          }
          return updatedTasks;
        });
        setAllTasks(prevTasks =>
          prevTasks.map(task =>
            task.task_id === message.task_id
              ? { ...task, ...message.data }
              : task
          )
        );

        // If task completed successfully, fetch the new product
        if (message.data.status === 'completed') {
          console.log('Task completed, fetching new product...');
          setTimeout(() => {
            fetchNewProduct(message.task_id);
          }, 1000); // Small delay to ensure backend has saved the product

          // Remove the completed task from activeTasks after 7 seconds
          setTimeout(() => {
            setActiveTasks(prevTasks => prevTasks.filter(task => task.task_id !== message.task_id));
          }, 7000);
        }
      } else if (message.type === 'task_created') {
        // Add new task
        setActiveTasks(prevTasks => [message.task_info, ...prevTasks]);
        setAllTasks(prevTasks => [message.task_info, ...prevTasks]);
        setShowCommissionSidebar(true); // Show sidebar when new commission is created
      } else if (message.type === 'general_update') {
        // Handle general updates
        if (message.data.type === 'task_created') {
          setActiveTasks(prevTasks => [message.data.task_info, ...prevTasks]);
          setAllTasks(prevTasks => [message.data.task_info, ...prevTasks]);
          setShowCommissionSidebar(true);
        }
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    wsRef.current = ws;
  };

  const fetchNewProduct = async (taskId: string) => {
    try {
      // Find the task to get the donation ID
      const task = allTasks.find(t => t.task_id === taskId);
      if (!task) {
        console.log('Task not found, doing full refresh');
        refreshProducts();
        return;
      }

      // Fetch the specific product for this commission
      const response = await fetch(`/api/products/commission/${task.donation_id}`);
      if (response.ok) {
        const newProduct = await response.json();
        if (newProduct) {
          console.log('Adding new product to gallery:', newProduct.product_info.id);
          // Add the new product to the beginning of the list
          setProducts((prevProducts: GeneratedProduct[]) => [newProduct, ...prevProducts]);
        } else {
          console.log('No product found, doing full refresh');
          refreshProducts();
        }
      } else {
        console.log('Failed to fetch specific product, doing full refresh');
        refreshProducts();
      }
    } catch (err) {
      console.error('Error fetching new product:', err);
      console.log('Falling back to full refresh');
      refreshProducts();
    }
  };

  const fetchActiveTasks = async () => {
    try {
      const response = await fetch('/api/tasks');
      if (response.ok) {
        const tasks: Task[] = await response.json();
        setAllTasks(tasks);
        // Filter for active tasks (pending, in_progress) - completed tasks are filtered out
        const active = tasks.filter(task => 
          task.status === 'pending' || task.status === 'in_progress'
        );
        setActiveTasks(active);
        setShowCommissionSidebar(active.length > 0);
      }
    } catch (err) {
      console.error('Failed to fetch active tasks:', err);
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedProduct(null);
  };

  const toggleSidebar = () => {
    setShowCommissionSidebar(!showCommissionSidebar);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center text-red-600 p-4">
        Error loading products: {error}
      </div>
    );
  }

  if (!products.length) {
    return (
      <div className="text-center text-gray-600 p-4">
        No products found
      </div>
    );
  }

  return (
    <>
      {/* Main Product Grid - Full Width */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 p-8 bg-gray-50">
        {products.map((product) => (
          <ProductCard 
            key={product.product_info.id} 
            product={product}
            activeTasks={activeTasks}
          />
        ))}
      </div>

      {/* Commission Status Sidebar - Overlay */}
      {showCommissionSidebar && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/10 z-40"
            onClick={() => setShowCommissionSidebar(false)}
          />
          {/* Sidebar */}
          <div className="fixed top-20 right-4 z-50 w-80 max-h-[calc(100vh-6rem)] overflow-y-auto">
            <CommissionStatusBanner 
              tasks={activeTasks.length > 0 ? activeTasks : allTasks}
              onClose={() => setShowCommissionSidebar(false)}
              onRefresh={fetchActiveTasks}
              isSidebar={true}
              onViewProduct={(task: Task) => {
                // Find the product for this completed commission
                fetch(`/api/products/commission/${task.donation_id}`)
                  .then(res => res.json())
                  .then(product => {
                    setSelectedProduct(product);
                    setShowModal(true);
                  });
              }}
            />
          </div>
        </>
      )}

      {/* Toggle Button - Fixed Position */}
      {!showCommissionSidebar && (
        <button
          onClick={toggleSidebar}
          className="fixed top-20 right-4 z-50 p-3 bg-purple-600 text-white rounded-full shadow-lg hover:bg-purple-700 transition-colors"
          title="Show commission status"
        >
          <FaTasks className="w-5 h-5" />
        </button>
      )}

      {/* Global modal for query parameter products */}
      {selectedProduct && (
        <ProductModal
          product={selectedProduct}
          isOpen={showModal}
          onClose={handleCloseModal}
        />
      )}
    </>
  );
}; 