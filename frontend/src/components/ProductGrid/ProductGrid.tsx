import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams, useLocation, useNavigate } from 'react-router-dom';
import { useProducts } from '../../hooks/useProducts';
import { ProductCard } from './ProductCard';
import { ProductModal } from './ProductModal';
import { CommissionStatusBanner } from './CommissionStatusBanner';
import { InProgressProductCard } from './InProgressProductCard';
import type { GeneratedProduct } from '../../types/productTypes';
import type { Task, WebSocketMessage } from '../../types/taskTypes';
import { toast } from 'react-toastify';

interface ProductGridProps {
  onCommissionProgressChange?: (inProgress: boolean) => void;
}

export const ProductGrid: React.FC<ProductGridProps> = ({ onCommissionProgressChange }) => {
  const { products, loading, error, refresh: refreshProducts } = useProducts();
  const [searchParams] = useSearchParams();
  const [selectedProduct, setSelectedProduct] = useState<GeneratedProduct | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [activeTasks, setActiveTasks] = useState<Task[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const [websocketError, setWebsocketError] = useState<string | null>(null);
  const [showSuccessBanner, setShowSuccessBanner] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const [justPublishedId, setJustPublishedId] = useState<number | null>(null);

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

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('success') === '1') {
      setShowSuccessBanner(true);
      // Remove the query param from the URL
      params.delete('success');
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  useEffect(() => {
    if (location.state?.showToast) {
      toast.success('Commission submitted!');
      navigate(location.pathname, { replace: true });
    }
  }, [location, navigate]);

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

  // Helper to subscribe to all active tasks
  const subscribeToActiveTasks = (ws: WebSocket, tasks: Task[]) => {
    tasks.forEach(task => {
      if (task.status === 'pending' || task.status === 'in_progress') {
        console.log('Subscribing to task', task.task_id);
        ws.send(JSON.stringify({ type: 'subscribe', task_id: task.task_id }));
      }
    });
  };

  const setupWebSocket = () => {
    // Use the current host and /ws/tasks for Nginx reverse proxy compatibility
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = wsProtocol + '//' + window.location.host + '/ws/tasks';
    const ws = new WebSocket(wsUrl);
    ws.onopen = (event) => {
      setWebsocketError(null);
      console.log('WebSocket connected for gallery updates:', wsUrl, event);
      ws.send(JSON.stringify({ type: 'ping' }));
      // Subscribe to all active tasks if already loaded
      if (activeTasks.length > 0) {
        subscribeToActiveTasks(ws, activeTasks);
      }
    };
    ws.onmessage = (event) => {
      console.log('WebSocket message received:', event);
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        console.log('Parsed WebSocket message:', message);
        if (message.type === 'task_update') {
          setActiveTasks(prevTasks => {
            const updatedTasks = prevTasks.map(task =>
              task.task_id === message.task_id
                ? { ...task, ...message.data }
                : task
            );
            if (message.data.status === 'completed') {
              return updatedTasks.map(task =>
                task.task_id === message.task_id
                  ? { ...task, justCompleted: true, completedAt: Date.now() }
                  : task
              );
            }
            return updatedTasks;
          });
          if (message.data.status === 'completed') {
            console.log('Task completed, refreshing product list...');
            
            // Refresh the product list to show the new product
            setTimeout(async () => {
              try {
                await fetchNewProduct();
              } catch (error) {
                console.error('ProductGrid: Error refreshing products:', error);
              }
            }, 1000);
            
            setTimeout(() => {
              setActiveTasks(prevTasks => prevTasks.filter(task => task.task_id !== message.task_id));
            }, 7000);
          }
        } else if (message.type === 'task_created') {
          setActiveTasks(prevTasks => dedupeTasks([message.task_info, ...prevTasks]));
          // Subscribe to the new task
          if (ws.readyState === WebSocket.OPEN) {
            subscribeToActiveTasks(ws, [message.task_info]);
          }
        } else if (message.type === 'general_update') {
          if (message.data.type === 'task_created') {
            setActiveTasks(prevTasks => dedupeTasks([message.data.task_info, ...prevTasks]));
            // Subscribe to the new task
            if (ws.readyState === WebSocket.OPEN) {
              subscribeToActiveTasks(ws, [message.data.task_info]);
            }
          }
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', event.data, err);
      }
    };
    ws.onerror = (error) => {
      setWebsocketError('WebSocket connection failed. Live updates are unavailable.');
      console.error('WebSocket error:', error);
    };
    ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event);
    };
    wsRef.current = ws;
  };

  const fetchActiveTasks = async () => {
    try {
      const response = await fetch('/api/tasks');
      if (response.ok) {
        const tasks = await response.json();
        const active = tasks.filter((task: Task) => 
          task.status === 'pending' || task.status === 'in_progress'
        );
        setActiveTasks(prevTasks => dedupeTasks([...active, ...prevTasks]));
        // Subscribe to all active tasks if WebSocket is open
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          subscribeToActiveTasks(wsRef.current, active);
        }
      }
    } catch (error) {
      console.error('Failed to fetch active tasks:', error);
    }
  };

  const fetchNewProduct = async () => {
    try {
      await refreshProducts();
    } catch (error) {
      console.error('Failed to fetch new product:', error);
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      const response = await fetch(`/api/tasks/${taskId}?task_type=commission`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        setActiveTasks(prevTasks => prevTasks.filter(task => task.task_id !== taskId));
      }
    } catch (error) {
      console.error('Failed to cancel task:', error);
    }
  };

  const handleViewProduct = (task: Task) => {
    // Find the product that was just completed
    const completedProduct = products.find(product => 
      product.reddit_post && product.reddit_post.post_id === task.task_id
    );
    
    if (completedProduct) {
      setSelectedProduct(completedProduct);
      setShowModal(true);
    }
  };

  // Separate in-progress tasks from completed products
  const inProgressTasks = activeTasks.filter(task => 
    task.status === 'pending' || task.status === 'in_progress'
  );

  const hasActiveCommissions = inProgressTasks.length > 0;

  // Notify parent of commission progress state
  useEffect(() => {
    if (onCommissionProgressChange) {
      onCommissionProgressChange(hasActiveCommissions);
    }
  }, [hasActiveCommissions, onCommissionProgressChange]);

  // Handler for ephemeral publish animation
  const handleProductPublished = (productId: number) => {
    setJustPublishedId(productId);
    setTimeout(() => setJustPublishedId(null), 2500);
  };

  // Helper to ensure tasks are unique by task_id
  const dedupeTasks = (tasks: Task[]): Task[] => {
    const map = new Map<string, Task>();
    for (const task of tasks) {
      map.set(task.task_id, { ...map.get(task.task_id), ...task });
    }
    return Array.from(map.values());
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-6xl mx-auto p-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
              {[1, 2, 3, 4, 5, 6, 8].map((i) => (
                <div key={i} className="h-80 bg-gray-200 rounded-2xl animate-pulse"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Error Loading Products</h2>
          <p className="text-gray-600">{error}</p>
          <button
            onClick={refreshProducts}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {showSuccessBanner && (
        <div className="bg-green-100 text-green-800 px-4 py-2 text-center font-semibold rounded shadow mb-4">
          🎉 Commission submitted successfully!
        </div>
      )}
      {websocketError && (
        <div className="bg-red-100 text-red-700 px-4 py-2 text-center">{websocketError}</div>
      )}
      {/* Removed sticky header banner for active commissions - will try something different later */}

      <div className="max-w-6xl mx-auto p-6">
        {/* Product Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {/* In-progress commission cards */}
          {inProgressTasks.map((task) => (
            <InProgressProductCard
              key={task.task_id}
              task={task}
              onCancel={handleCancelTask}
            />
          ))}
          {/* Generated product cards */}
          {[...products]
            .sort((a, b) => b.product_info.id - a.product_info.id)
            .map((product) => (
            <ProductCard
              key={product.product_info.id}
              product={product}
              activeTasks={activeTasks}
              justPublished={justPublishedId === product.product_info.id}
            />
          ))}
        </div>

        {/* Empty state - simplified */}
        {products.length === 0 && inProgressTasks.length === 0 && (
          <div className="text-center py-24">
            <div className="text-6xl mb-4">🎨</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">No Products Yet</h2>
            <p className="text-gray-600 mb-6">
              Start by commissioning a piece or wait for the system to generate products.
            </p>
          </div>
        )}
      </div>

      {/* Product Modal */}
      {selectedProduct && (
        <ProductModal
          product={selectedProduct}
          isOpen={showModal}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}; 