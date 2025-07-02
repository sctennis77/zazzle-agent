export interface Task {
  task_id: string;
  task_type: 'k8s_job' | 'database_queue';
  status: TaskStatus;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  donation_id: number;
  error?: string;
}

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';

export interface TaskUpdate {
  type: 'task_update';
  task_id: string;
  data: Partial<Task>;
}

export interface TaskCreated {
  type: 'task_created';
  task_info: Task;
  donation_id: number;
}

export interface GeneralUpdate {
  type: 'general_update';
  data: TaskCreated;
}

export type WebSocketMessage = TaskUpdate | TaskCreated | GeneralUpdate; 