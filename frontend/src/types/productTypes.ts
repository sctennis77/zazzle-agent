export interface RedditContext {
  post_id: string;
  post_title: string;
  post_url: string;
  subreddit: string;
  post_content: string;
  permalink: string;
}

export interface ProductInfo {
  id: number;
  pipeline_run_id: number;
  reddit_post_id: number;
  theme: string;
  image_title?: string;
  image_url: string;
  product_url: string;
  template_id: string;
  model: string;
  prompt_version: string;
  product_type: string;
  design_description: string;
  affiliate_link?: string;
}

export interface PipelineRun {
  id: number;
  start_time: string;
  end_time: string;
  status: string;
  retry_count: number;
}

export interface RedditPost {
  id: number;
  pipeline_run_id: number;
  post_id: string;
  title: string;
  content: string;
  subreddit: string;
  url: string;
  permalink: string;
  comment_summary?: string;
  author?: string;
  score?: number;
  num_comments?: number;
}

export interface PipelineRunUsage {
  id: number;
  pipeline_run_id: number;
  idea_model: string;
  image_model: string;
  prompt_tokens: number;
  completion_tokens: number;
  image_tokens: number;
  total_cost_usd: string;
  created_at: string;
}

export interface GeneratedProduct {
  product_info: ProductInfo;
  pipeline_run: PipelineRun;
  reddit_post: RedditPost;
}

export interface GeneratedProductSchema {
  product_info: ProductInfo;
  pipeline_run: PipelineRun;
  reddit_post: RedditPost;
  usage?: PipelineRunUsage;
} 