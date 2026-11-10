import {
  SystemStatus,
  Asset,
  AssetSignal,
  MarketOverview,
  MarketDataPoint,
  SentimentAnalysis,
  SocialPost,
  NewsArticle,
  PredictionRecord,
} from '../types/api';

// Configurable API base URL with fallback to relative '/api'
const envApiUrl = import.meta.env.VITE_API_BASE_URL;
const BASE_URL = envApiUrl ? `${envApiUrl.replace(/\/+$/, '')}/api` : '/api';

// Operational session token storage (kept in-memory / sessionStorage only, never in env or build bundles)
let sessionAdminKey: string | null = null;

export const api = {
  getBaseUrl(): string {
    return BASE_URL;
  },
  setAdminKey(key: string | null) {
    sessionAdminKey = key;
    if (key) {
      sessionStorage.setItem('sentinel_admin_key', key);
    } else {
      sessionStorage.removeItem('sentinel_admin_key');
    }
  },
  getAdminKey(): string | null {
    if (!sessionAdminKey) {
      sessionAdminKey = sessionStorage.getItem('sentinel_admin_key');
    }
    return sessionAdminKey;
  },
  getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    const key = this.getAdminKey();
    if (key) {
      headers['X-Sentinel-Admin-Key'] = key;
    }
    return headers;
  },
  async getSystemStatus(): Promise<SystemStatus> {
    const res = await fetch(`${BASE_URL}/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getAssets(exchange?: 'HKEX' | 'KRX'): Promise<Asset[]> {
    const url = exchange ? `${BASE_URL}/assets?exchange=${exchange}` : `${BASE_URL}/assets`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getMarketOverview(): Promise<MarketOverview> {
    const res = await fetch(`${BASE_URL}/market-overview`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getSignals(exchange?: 'HKEX' | 'KRX'): Promise<AssetSignal[]> {
    const url = exchange ? `${BASE_URL}/signals?exchange=${exchange}` : `${BASE_URL}/signals`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getSignal(ticker: string): Promise<AssetSignal> {
    const res = await fetch(`${BASE_URL}/signals/${encodeURIComponent(ticker)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getMarketData(ticker: string, limit: number = 60): Promise<MarketDataPoint[]> {
    const res = await fetch(`${BASE_URL}/market-data/${encodeURIComponent(ticker)}?limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getSentiment(ticker: string): Promise<SentimentAnalysis> {
    const res = await fetch(`${BASE_URL}/sentiment/${encodeURIComponent(ticker)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getSocialPosts(ticker: string, limit: number = 50): Promise<SocialPost[]> {
    const res = await fetch(`${BASE_URL}/social/${encodeURIComponent(ticker)}?limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getNewsArticles(ticker: string, limit: number = 50): Promise<NewsArticle[]> {
    const res = await fetch(`${BASE_URL}/news/${encodeURIComponent(ticker)}?limit=${limit}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getPredictions(ticker: string): Promise<PredictionRecord[]> {
    const res = await fetch(`${BASE_URL}/predictions/${encodeURIComponent(ticker)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async getModelPerformance(ticker?: string): Promise<any[]> {
    const url = ticker ? `${BASE_URL}/models/performance?ticker=${encodeURIComponent(ticker)}` : `${BASE_URL}/models/performance`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  async triggerMarketCollection(ticker?: string) {
    const res = await fetch(`${BASE_URL}/collect/market${ticker ? `?ticker=${ticker}` : ''}`, { 
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  async triggerSocialCollection(ticker?: string) {
    const res = await fetch(`${BASE_URL}/collect/social${ticker ? `?ticker=${ticker}` : ''}`, { 
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  async triggerNewsCollection(ticker?: string) {
    const res = await fetch(`${BASE_URL}/collect/news${ticker ? `?ticker=${ticker}` : ''}`, { 
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  async triggerModelTraining() {
    const res = await fetch(`${BASE_URL}/models/train`, { 
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  async triggerFullPipeline() {
    const res = await fetch(`${BASE_URL}/collect/all`, { 
      method: 'POST',
      headers: this.getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }
};
