export interface Task {
  task_id: string;
  status: string;
  created_at?: string;
  completed_at?: string;
  donation_id: number;
  error?: string;
  reddit_username?: string;
  tier?: string;
  subreddit?: string;
  amount_usd?: number;
  is_anonymous?: boolean;
  justCompleted?: boolean;
  completedAt?: number;
  stage?: string;
  message?: string;
  progress?: number;
  timestamp?: number;
  commission_message?: string;
}

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';

export type TaskStage = 
  | 'post_fetching'
  | 'post_fetched'
  | 'product_designed'
  | 'image_generation_started'
  | 'image_generated'
  | 'image_stamped'
  | 'commission_complete';

export interface TaskUpdate {
  type: 'task_update';
  task_id: string;
  data: Partial<Task>;
}

export interface TaskCreated {
  type: 'task_created';
  task_info: Task;
}

export interface GeneralUpdate {
  type: 'general_update';
  data: TaskCreated;
}

export type WebSocketMessage = TaskUpdate | TaskCreated | GeneralUpdate; 