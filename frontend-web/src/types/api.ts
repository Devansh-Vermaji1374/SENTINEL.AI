export interface SystemStatus {
  status: string;
  app_env: string;
  database?: string;
  database_connected?: boolean;
  apify_connected: boolean;
  apify_status?: string;
  exa_connected: boolean;
  exa_status?: string;
  finbert_ready?: boolean;
  finbert_status?: string;
  model_registry_ready?: boolean;
  model_registry_status?: string;
  yfinance_ready?: boolean;
  assets_configured?: number;
  last_collection?: string | null;
  latest_market_timestamp?: string | null;
  latest_social_timestamp?: string | null;
  latest_news_timestamp?: string | null;
  historical_bars_count?: number;
  discourse_posts_count?: number;
  news_articles_count?: number;
  sentiment_scores_count?: number;
  trained_models_count?: number;
  predictions_settled_count?: number;
  predictions_pending_count?: number;
}

export interface Asset {
  id?: number;
  ticker: string;
  name: string;
  exchange: 'HKEX' | 'KRX';
  sector: string;
  currency: string;
}

export interface AssetSignal {
  ticker: string;
  asset_name: string;
  exchange: 'HKEX' | 'KRX';
  sector: string;
  currency: string;
  latest_price: number;
  overall_sentiment: string;
  sentiment_score: number;
  social_mentions: number;
  news_count: number;
  news_sentiment: number;
  social_sentiment: number;
  predicted_price: number;
  predicted_return_pct: number;
  direction: 'Bullish' | 'Bearish' | 'Neutral' | 'No Data';
  support_levels: number[];
  resistance_levels: number[];
  signal_strength: number;
  data_quality: string;
  has_real_sentiment: boolean;
}

export interface MarketOverview {
  total_assets: number;
  total_social_mentions: number;
  total_news_articles: number;
  overall_positive_pct: number;
  overall_negative_pct: number;
  overall_neutral_pct: number;
  bullish_assets_count: number;
  bearish_assets_count: number;
  neutral_assets_count: number;
  top_bullish: AssetSignal[];
  top_bearish: AssetSignal[];
  most_discussed: AssetSignal[];
  signals: AssetSignal[];
}

export interface MarketDataPoint {
  ticker: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close: number;
}

export interface SentimentAnalysis {
  ticker: string;
  sample_count: number;
  weighted_sentiment_score: number;
  sentiment_label: string;
  positive_ratio: number;
  negative_ratio: number;
  neutral_ratio: number;
  news_sentiment: number;
  social_sentiment: number;
  has_real_sentiment: boolean;
}

export interface SocialPost {
  id: number;
  ticker: string;
  platform: string;
  text: string;
  author: string;
  timestamp: string;
  likes: number;
  reposts: number;
  views: number;
  followers: number;
  url?: string;
  is_demo_data: boolean;
  age_days?: number;
  sentiment_score?: number;
  sentiment_label?: string;
}

export interface NewsArticle {
  id: number;
  ticker: string;
  title: string;
  source_name: string;
  url: string;
  text?: string;
  published_at: string;
  is_demo_data: boolean;
  age_days?: number;
  sentiment_score?: number;
  sentiment_label?: string;
}

export interface PredictionRecord {
  id?: number;
  ticker?: string;
  model_name: string;
  origin_price?: number;
  prediction_date: string;
  target_date?: string;
  predicted_price: number;
  predicted_return: number;
  predicted_return_pct: number;
  actual_price?: number;
  actual_return?: number;
  prediction_error?: number;
  direction_correct?: boolean;
  settled_at?: string;
  confidence_lower: number;
  confidence_upper: number;
  horizon_days?: number;
}
