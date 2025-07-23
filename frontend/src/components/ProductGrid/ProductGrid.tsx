import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useProducts } from '../../hooks/useProducts';
import { ProductCard } from './ProductCard';
import { ProductModal } from './ProductModal';
import { CommissionStatusBanner } from './CommissionStatusBanner';
import { InProgressProductCard } from './InProgressProductCard';
import { CompletedProductCard } from './CompletedProductCard';
import { SortingControls } from './SortingControls';
import CommissionModal from '../common/CommissionModal';
import type { GeneratedProduct } from '../../types/productTypes';
import type { Task, WebSocketMessage } from '../../types/taskTypes';
import { toast } from 'react-toastify';
import { API_BASE, WS_BASE } from '../../utils/apiBase';
import { sortProducts, filterProductsBySubreddits, getUniqueSubreddits } from '../../utils/productSorting';
import { useProductsWithDonations, type ProductWithFullDonationData } from '../../hooks/useProductsWithDonations';
import { FaExpand } from 'react-icons/fa';
import { ImageLightbox } from '../common/ImageLightbox';

interface ProductGridProps {
  onCommissionProgressChange?: (inProgress: boolean) => void;
  onCommissionClick?: () => void;
}

export const ProductGrid: React.FC<ProductGridProps> = ({ onCommissionProgressChange, onCommissionClick }) => {
  const { products, loading, error, refresh: refreshProducts } = useProducts();
  const [searchParams] = useSearchParams();
  const [selectedProduct, setSelectedProduct] = useState<GeneratedProduct | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showFullScreen, setShowFullScreen] = useState(false);
  const [fullScreenIndex, setFullScreenIndex] = useState(0);
  const [activeTasks, setActiveTasks] = useState<Task[]>([]);
  const [completingTasks, setCompletingTasks] = useState<Map<string, {
    task: Task;
    stage: 'completing' | 'transitioning' | 'removing';
    startTime: number;
    timeoutId?: number;
  }>>(new Map());
  const wsRef = useRef<WebSocket | null>(null);
  const [websocketError, setWebsocketError] = useState<string | null>(null);
  const [showSuccessBanner, setShowSuccessBanner] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const [justPublishedId, setJustPublishedId] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState('time-desc');
  const [selectedSubreddits, setSelectedSubreddits] = useState<string[]>([]);
  const [sortedAndFilteredProducts, setSortedAndFilteredProducts] = useState<ProductWithFullDonationData[]>([]);
  const { productsWithDonations, loading: donationsLoading } = useProductsWithDonations(products);
  
  // Cleanup completing tasks and clear timeouts on unmount
  useEffect(() => {
    return () => {
      // Clear all pending timeouts
      completingTasks.forEach(({ timeoutId }) => {
        if (timeoutId) clearTimeout(timeoutId);
      });
    };
  }, []);
  
  // Manage transition state machine
  const processCompletedTask = async (taskId: string, completedTask: Task) => {
    // Prevent duplicate processing
    if (completingTasks.has(taskId)) {
      console.log('Task already being processed:', taskId);
      return;
    }

    // Add to completing tasks
    setCompletingTasks(prev => new Map(prev).set(taskId, {
      task: completedTask,
      stage: 'completing',
      startTime: Date.now()
    }));

    try {
      // Fetch new product first
      await refreshProducts();
      
      // Move to transitioning stage
      const transitionTimeoutId = window.setTimeout(() => {
        setCompletingTasks(prev => {
          const newMap = new Map(prev);
          const taskData = newMap.get(taskId);
          if (taskData) {
            newMap.set(taskId, { ...taskData, stage: 'transitioning' });
          }
          return newMap;
        });
        
        // Move to removing stage after animation
        const removeTimeoutId = window.setTimeout(() => {
          setCompletingTasks(prev => {
            const newMap = new Map(prev);
            newMap.delete(taskId);
            return newMap;
          });
        }, 600); // Match animation duration
        
        // Update timeout reference
        setCompletingTasks(prev => {
          const newMap = new Map(prev);
          const taskData = newMap.get(taskId);
          if (taskData) {
            newMap.set(taskId, { ...taskData, timeoutId: removeTimeoutId });
          }
          return newMap;
        });
      }, 1200); // Show completion card for 1.2s
      
      // Store timeout reference
      setCompletingTasks(prev => {
        const newMap = new Map(prev);
        const taskData = newMap.get(taskId);
        if (taskData) {
          newMap.set(taskId, { ...taskData, timeoutId: transitionTimeoutId });
        }
        return newMap;
      });
      
    } catch (error) {
      console.error('Error processing completed task:', error);
      // Clear any pending timeout
      setCompletingTasks(prev => {
        const taskData = prev.get(taskId);
        if (taskData?.timeoutId) {
          clearTimeout(taskData.timeoutId);
        }
        // Remove from completing tasks on error after brief delay
        const errorTimeoutId = window.setTimeout(() => {
          setCompletingTasks(current => {
            const newMap = new Map(current);
            newMap.delete(taskId);
            return newMap;
          });
        }, 2000);
        
        const newMap = new Map(prev);
        newMap.set(taskId, {
          task: completedTask,
          stage: 'removing',
          startTime: Date.now(),
          timeoutId: errorTimeoutId
        });
        return newMap;
      });
    }
  };
  const [fabAnimation, setFabAnimation] = useState(false);
  const [failedTask, setFailedTask] = useState<Task | null>(null);
  const [showFailedModal, setShowFailedModal] = useState(false);
  const [failedDonation, setFailedDonation] = useState<any>(null);

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

  // Handle cinema mode query parameters (from CinemaView redirect)
  useEffect(() => {
    const cinemaPostId = searchParams.get('cinema');
    const cinemaIndex = searchParams.get('index');
    
    if (cinemaPostId && cinemaIndex && sortedAndFilteredProducts.length > 0) {
      const index = parseInt(cinemaIndex, 10);
      if (!isNaN(index) && index >= 0 && index < sortedAndFilteredProducts.length) {
        setFullScreenIndex(index);
        setShowFullScreen(true);
        // Clean up URL
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('cinema');
        newUrl.searchParams.delete('index');
        window.history.replaceState({}, '', newUrl.toString());
      }
    }
  }, [searchParams, sortedAndFilteredProducts]);

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
      // Clear all pending timeouts
      completingTasks.forEach(({ timeoutId }) => {
        if (timeoutId) clearTimeout(timeoutId);
      });
      
      if (wsRef.current) {
        // Only close if open or connecting, and suppress onclose to avoid browser warning
        if (
          wsRef.current.readyState === WebSocket.OPEN ||
          wsRef.current.readyState === WebSocket.CONNECTING
        ) {
          wsRef.current.onclose = null;
          wsRef.current.close();
        }
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
    const ws = new WebSocket(WS_BASE);
    ws.onopen = (event) => {
      setWebsocketError(null);
      console.log('WebSocket connected for gallery updates:', WS_BASE, event);
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
          // Update active tasks
          setActiveTasks(prevTasks => {
            return prevTasks.map(task =>
              task.task_id === message.task_id
                ? { ...task, ...message.data }
                : task
            );
          });
          
          // Handle task completion
          if (message.data.status === 'completed') {
            // Remove from active tasks
            setActiveTasks(prevTasks => prevTasks.filter(task => task.task_id !== message.task_id));
            
            // Create completed task data
            const completedTaskData = {
              task_id: message.task_id,
              status: 'completed' as const,
              ...message.data
            } as Task;
            
            // Process through state machine
            processCompletedTask(message.task_id, completedTaskData);
          }
          // Handle failed commission task
          if (message.data.status === 'failed') {
            setFailedTask({
              task_id: message.task_id,
              status: message.data.status || 'failed',
              donation_id: message.data.donation_id || 0,
              ...message.data
            } as Task);
            setShowFailedModal(true);
            
            // Fetch donation details for refund information
            if (message.data.donation_id) {
              fetchDonationDetails(message.data.donation_id);
            }
          }
        } else if (message.type === 'task_created') {
          setActiveTasks(prevTasks => dedupeTasks([message.task_info, ...prevTasks]));
          // Subscribe to the new task
          if (ws.readyState === WebSocket.OPEN) {
            subscribeToActiveTasks(ws, [message.task_info]);
          }
          // Trigger thank you message animation for new commission tasks
          window.setTimeout(() => {
            window.dispatchEvent(new CustomEvent('trigger-logo-animation'));
          }, 1000); // Delay to let the task card appear first
        } else if (message.type === 'general_update') {
          if (message.data.type === 'task_created') {
            setActiveTasks(prevTasks => dedupeTasks([message.data.task_info, ...prevTasks]));
            // Subscribe to the new task
            if (ws.readyState === WebSocket.OPEN) {
              subscribeToActiveTasks(ws, [message.data.task_info]);
            }
            // Trigger thank you message animation for new commission tasks
            window.setTimeout(() => {
              window.dispatchEvent(new CustomEvent('trigger-logo-animation'));
            }, 1000); // Delay to let the task card appear first
          }
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', event.data, err);
      }
    };
    ws.onerror = (error) => {
      // Only show/log the error if there are active tasks (i.e., user expects live updates)
      if (activeTasks.length > 0) {
        setWebsocketError('WebSocket connection failed. Live updates are unavailable.');
        console.error('WebSocket error:', error);
      }
      // Otherwise, suppress the error
    };
    ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event);
    };
    wsRef.current = ws;
  };

  const fetchActiveTasks = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/tasks`);
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
      throw error; // Re-throw to handle in processCompletedTask
    }
  };

  // Helper function to check if a product should be hidden during completion transition
  const shouldHideProduct = (product: GeneratedProduct) => {
    return Array.from(completingTasks.values()).some(
      ({ task, stage }) => task.task_id === product.reddit_post.post_id && (stage === 'completing' || stage === 'transitioning')
    );
  };

  // Update sorted and filtered products when products, sorting, or filters change
  useEffect(() => {
    // If donation data is still loading, use original products with fallback donation amounts
    const sourceProducts = productsWithDonations.length > 0 ? productsWithDonations : 
      products.map(product => ({
        ...product,
        totalDonationAmount: product.product_info.donation_info?.donation_amount || 0,
        commissionInfo: undefined,
        supportDonations: []
      }));
    
    if (sourceProducts.length === 0) {
      setSortedAndFilteredProducts([]);
      return;
    }
    
    const filteredProducts = sourceProducts.filter(product => !shouldHideProduct(product));
    const sorted = sortProducts(filteredProducts, sortBy);
    const filtered = filterProductsBySubreddits(sorted, selectedSubreddits);
    setSortedAndFilteredProducts(filtered);
  }, [products, productsWithDonations, sortBy, selectedSubreddits, completingTasks]);

  // Helper function to check if a product is newly completed (should show with animation)
  const isProductJustCompleted = (product: GeneratedProduct) => {
    // Check if this product was recently completed (has a completion task that's in removing stage)
    const completionTask = Array.from(completingTasks.values()).find(
      ({ task }) => task.task_id === product.reddit_post.post_id
    );
    
    if (completionTask) {
      const timeSinceCompletion = Date.now() - completionTask.startTime;
      // Show animation for products that appear after completion transition (1.8-3.0 seconds)
      return timeSinceCompletion >= 1800 && timeSinceCompletion < 3000;
    }
    
    return false;
  };

  const fetchDonationDetails = async (donationId: number) => {
    try {
      // Get all donations and find the one with matching ID
      const response = await fetch(`${API_BASE}/api/donations`);
      if (response.ok) {
        const donations = await response.json();
        const donation = donations.find((d: any) => d.id === donationId);
        if (donation) {
          setFailedDonation(donation);
        }
      }
    } catch (error) {
      console.error('Failed to fetch donation details:', error);
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/tasks/${taskId}?task_type=commission`, {
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
    window.setTimeout(() => setJustPublishedId(null), 2500);
  };

  // Helper to ensure tasks are unique by task_id
  const dedupeTasks = (tasks: Task[]): Task[] => {
    const map = new Map<string, Task>();
    for (const task of tasks) {
      map.set(task.task_id, { ...map.get(task.task_id), ...task });
    }
    return Array.from(map.values());
  };

  // Full screen navigation handlers
  const handleFullScreenNavigate = (newIndex: number) => {
    setFullScreenIndex(newIndex);
    // Update URL when navigating in full screen mode
    if (showFullScreen && sortedAndFilteredProducts[newIndex]) {
      const postId = sortedAndFilteredProducts[newIndex].reddit_post.post_id;
      window.history.replaceState(null, '', `/cinema/${postId}`);
    }
  };

  const handleOpenProductModal = (productId: string) => {
    const product = sortedAndFilteredProducts.find(p => p.product_info.id.toString() === productId);
    if (product) {
      setSelectedProduct(product as GeneratedProduct);
      setShowModal(true);
      setShowFullScreen(false);
      // Return to main page URL when closing full screen
      window.history.replaceState(null, '', '/');
    }
  };

  // Function to trigger FAB animation
  const triggerFabAnimation = () => {
    setFabAnimation(true);
    window.setTimeout(() => setFabAnimation(false), 1000); // Reset after 1 second
  };

  // Expose the trigger function to parent component
  useEffect(() => {
    if (onCommissionProgressChange) {
      onCommissionProgressChange(hasActiveCommissions);
    }
  }, [hasActiveCommissions, onCommissionProgressChange]);

  // Listen for animation trigger from parent
  useEffect(() => {
    const handleAnimationTrigger = () => {
      triggerFabAnimation();
    };
    
    // Add event listener for custom event
    window.addEventListener('trigger-fab-animation', handleAnimationTrigger);
    
    return () => {
      window.removeEventListener('trigger-fab-animation', handleAnimationTrigger);
    };
  }, []);

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
      {/* Error Modal for Failed Commission Task */}
      {showFailedModal && failedTask && (
        <div className="fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-40">
          <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
            <h2 className="text-2xl font-bold text-red-600 mb-4">Commission Failed</h2>
            <p className="mb-4">
              Clouvel ran into unexpected issues processing this commission.<br/>
              {failedDonation ? (
                <span className="font-semibold">
                  Your donation {failedDonation.customer_email} ({failedDonation.stripe_payment_intent_id}) has been fully refunded.
                </span>
              ) : (
                <span className="font-semibold">
                  Your donation has been fully refunded.
                </span>
              )}
              <br/>Please try supporting Clouvel again.
            </p>
            <button
              className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              onClick={() => {
                setShowFailedModal(false);
                setFailedDonation(null);
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
      {/* Removed sticky header banner for active commissions - will try something different later */}

      <div className="max-w-6xl mx-auto p-4 sm:p-6">
        {/* Sorting Controls */}
        {(products.length > 0 || inProgressTasks.length > 0) && (
          <div className="flex items-center justify-between mb-6">
            <SortingControls
              sortBy={sortBy}
              onSortChange={setSortBy}
              selectedSubreddits={selectedSubreddits}
              onSubredditChange={setSelectedSubreddits}
              availableSubreddits={getUniqueSubreddits(products)}
            />
            {sortedAndFilteredProducts.length > 0 && (
              <button
                onClick={() => {
                  setFullScreenIndex(0);
                  setShowFullScreen(true);
                  // Update URL when entering full screen mode
                  const firstPostId = sortedAndFilteredProducts[0].reddit_post.post_id;
                  window.history.pushState(null, '', `/cinema/${firstPostId}`);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-gray-700 hover:text-gray-900"
                title="Enter full screen mode"
              >
                <FaExpand size={16} />
                <span className="hidden sm:inline">Full Screen</span>
              </button>
            )}
          </div>
        )}

        {/* Product Grid */}
        <div className="space-y-4 sm:space-y-6 lg:space-y-8">
          {/* In-progress and completing tasks */}
          {(inProgressTasks.length > 0 || completingTasks.size > 0) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6 lg:gap-8">
              {/* In-progress commission cards */}
              {inProgressTasks.map((task) => (
                <InProgressProductCard
                  key={task.task_id}
                  task={task}
                  onCancel={handleCancelTask}
                />
              ))}
              {/* Completed commission cards (transitioning) */}
              {Array.from(completingTasks.values()).map(({ task, stage }) => (
                <CompletedProductCard
                  key={task.task_id}
                  task={task}
                  transitioning={stage === 'transitioning'}
                />
              ))}
            </div>
          )}
          
          {/* Generated product cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6 lg:gap-8">
            {sortedAndFilteredProducts.map((product) => (
              <ProductCard
                key={product.product_info.id}
                product={product as GeneratedProduct}
                activeTasks={activeTasks}
                justPublished={justPublishedId === product.product_info.id}
                justCompleted={isProductJustCompleted(product)}
              />
            ))}
          </div>
        </div>

        {/* Empty state - simplified */}
        {products.length === 0 && inProgressTasks.length === 0 && completingTasks.size === 0 && (
          <div className="text-center py-24">
            <div className="text-6xl mb-4">🎨</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">No Products Yet</h2>
            <p className="text-gray-600 mb-6">
              Start by commissioning a piece or wait for the system to generate products.
            </p>
          </div>
        )}
      </div>

      {/* Floating Action Button for Commission Art */}
      <button
        onClick={(e) => {
          e.preventDefault();
          onCommissionClick && onCommissionClick();
        }}
        disabled={import.meta.env.VITE_COMISSION_ART_ENABLED !== 'true'}
        className={`fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-50 px-4 py-3 rounded-full sm:rounded-lg text-sm font-semibold transition-all duration-200 focus:outline-none flex items-center gap-2 min-h-[56px] touch-manipulation ${
          import.meta.env.VITE_COMISSION_ART_ENABLED === 'true'
            ? 'bg-gradient-to-r from-purple-600 to-purple-400 text-white shadow-lg hover:shadow-xl cursor-pointer'
            : 'bg-gray-400 text-gray-200 shadow-lg cursor-not-allowed'
        } ${
          fabAnimation ? 'animate-bounce shadow-xl shadow-gray-400/50 ring-2 ring-gray-300' : ''
        }`}
        aria-label={import.meta.env.VITE_COMISSION_ART_ENABLED === 'true' ? "Commission Art" : "Commission Art (Temporarily Disabled)"}
        title={import.meta.env.VITE_COMISSION_ART_ENABLED === 'true' ? "Commission a custom piece of art" : "Commission Art is temporarily disabled while we improve the system"}
      >
        <span className="text-lg">🎨</span>
        <span className="hidden sm:inline">Commission Art</span>
      </button>

      {/* Product Modal */}
      {selectedProduct && (
        <ProductModal
          product={selectedProduct}
          isOpen={showModal}
          onClose={() => setShowModal(false)}
        />
      )}

      {/* Full Screen Image Lightbox */}
      {showFullScreen && (
        <ImageLightbox
          isOpen={showFullScreen}
          onClose={() => {
            setShowFullScreen(false);
            // Return to main page URL when closing full screen
            window.history.pushState(null, '', '/');
          }}
          images={sortedAndFilteredProducts.map(product => ({
            id: product.product_info.id.toString(),
            imageUrl: product.product_info.image_url,
            imageTitle: product.product_info.image_title || product.product_info.theme,
            imageAlt: product.product_info.image_title || product.product_info.theme,
            redditUsername: product.product_info.donation_info?.reddit_username,
            tierName: product.product_info.donation_info?.tier_name,
            isAnonymous: product.product_info.donation_info?.is_anonymous
          }))}
          currentIndex={fullScreenIndex}
          onNavigate={handleFullScreenNavigate}
          onOpenProductModal={handleOpenProductModal}
        />
      )}

    </div>
  );
}; 