import React, { useState, useEffect, useRef } from 'react';
import type { Task } from '../../types/taskTypes.ts';

interface TaskDashboardProps {
  className?: string;
}

const TaskDashboard: React.FC<TaskDashboardProps> = ({ className = '' }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    fetchTasks();
    setupWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/tasks');
      if (!response.ok) {
        throw new Error('Failed to fetch tasks');
      }
      const data = await response.json();
      setTasks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks');
    } finally {
      setLoading(false);
    }
  };

  const setupWebSocket = () => {
    // Connect to the API WebSocket endpoint on port 8000
    const wsUrl = window.location.hostname === 'localhost' 
      ? 'ws://localhost:8000/ws/tasks'
      : `ws://${window.location.hostname}:8000/ws/tasks`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected to:', wsUrl);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === 'task_update') {
        // Update specific task
        setTasks(prevTasks => 
          prevTasks.map(task => 
            task.task_id === message.task_id 
              ? { ...task, ...message.data }
              : task
          )
        );
      } else if (message.type === 'task_created') {
        // Add new task
        setTasks(prevTasks => [message.data.task_info, ...prevTasks]);
      } else if (message.type === 'general_update') {
        // Handle general updates
        if (message.data.type === 'task_created') {
          setTasks(prevTasks => [message.data.task_info, ...prevTasks]);
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'succeeded':
        return 'text-green-600 bg-green-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      case 'running':
        return 'text-blue-600 bg-blue-100';
      case 'pending':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'succeeded':
        return '✅';
      case 'failed':
        return '❌';
      case 'running':
        return '🔄';
      case 'pending':
        return '⏳';
      default:
        return '❓';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const cancelTask = async (taskId: string, taskType: string) => {
    try {
      const response = await fetch(`/api/tasks/${taskId}?task_type=${taskType}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error('Failed to cancel task');
      }
      
      // Refresh tasks
      fetchTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel task');
    }
  };

  if (loading) {
    return (
      <div className={`p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`p-6 ${className}`}>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Commission Tasks</h2>
        <button
          onClick={fetchTasks}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {tasks.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No tasks found</p>
        </div>
      ) : (
        <div className="space-y-4">
          {tasks.map((task) => (
            <div
              key={task.task_id}
              className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-lg">{getStatusIcon(task.status)}</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                      {task.status}
                    </span>
                    <span className="text-sm text-gray-500">
                      Commission Task
                    </span>
                  </div>
                  
                  <div className="text-sm text-gray-600 space-y-1">
                    <p><strong>Task ID:</strong> {task.task_id}</p>
                    <p><strong>Donation ID:</strong> {task.donation_id}</p>
                    {task.created_at && (
                      <p><strong>Created:</strong> {formatDate(task.created_at)}</p>
                    )}
                    {task.completed_at && (
                      <p><strong>Completed:</strong> {formatDate(task.completed_at)}</p>
                    )}
                    {task.error && (
                      <p className="text-red-600"><strong>Error:</strong> {task.error}</p>
                    )}
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  {task.status === 'pending' && (
                                      <button
                    onClick={() => cancelTask(task.task_id, 'commission')}
                    className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
                  >
                    Cancel
                  </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TaskDashboard; 