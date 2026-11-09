import React, { useEffect, useState } from 'react';
import { 
  FileText, 
  MessageSquare, 
  Newspaper, 
  ExternalLink, 
  Calendar, 
  ThumbsUp, 
  Share2, 
  Eye, 
  Filter
} from 'lucide-react';
import { api } from '../services/api';
import { AssetSignal, NewsArticle, SocialPost } from '../types/api';

interface Props {
  selectedTicker: string;
  signal: AssetSignal | null;
}

export const IntelligencePage: React.FC<Props> = ({ selectedTicker, signal }) => {
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [social, setSocial] = useState<SocialPost[]>([]);
  const [activeTab, setActiveTab] = useState<'news' | 'social'>('news');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    Promise.all([
      api.getNewsArticles(selectedTicker, 50),
      api.getSocialPosts(selectedTicker, 50)
    ]).then(([newsData, socialData]) => {
      if (mounted) {
        setNews(newsData);
        setSocial(socialData);
        setLoading(false);
      }
    }).catch(() => {
      if (mounted) setLoading(false);
    });

    return () => { mounted = false; };
  }, [selectedTicker]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#1b263b] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <FileText className="w-5 h-5 text-[#00b0ff]" />
            <h1 className="text-xl font-bold tracking-tight text-white">
              News & Social Discourse Stream &middot; <span className="text-[#00b0ff] font-mono">{selectedTicker}</span>
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#00b0ff]/10 text-[#00b0ff] border border-[#00b0ff]/30">
              SOURCE PROVENANCE & TIMESTAMPS
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] mt-1">
            Separate financial news and social discourse streams with explicit published dates, source provenance, and age tracking.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center space-x-1 p-1 bg-[#0e1626] border border-[#1c2a40] rounded font-mono text-xs">
          <button
            onClick={() => setActiveTab('news')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activeTab === 'news' 
                ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold border border-[#00b0ff]/40' 
                : 'text-[#94a3b8] hover:text-white'
            }`}
          >
            <Newspaper className="w-3.5 h-3.5" />
            <span>Curated News ({news.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('social')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activeTab === 'social' 
                ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold border border-[#00b0ff]/40' 
                : 'text-[#94a3b8] hover:text-white'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Social Discourse ({social.length})</span>
          </button>
        </div>
      </div>

      {/* Stream Feed */}
      {loading ? (
        <div className="flex items-center justify-center h-64 text-[#64748b] font-mono text-xs">
          Loading intelligence records...
        </div>
      ) : activeTab === 'news' ? (
        <div className="space-y-3">
          {news.length === 0 ? (
            <div className="p-8 text-center bg-[#0e1626] border border-[#1c2a40] rounded text-xs text-[#64748b] font-mono">
              Real data unavailable &mdash; ingestion required for this symbol.
            </div>
          ) : (
            news.map(art => (
              <div 
                key={art.id}
                className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 hover:border-[#253954] transition"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center space-x-2 text-[10px] font-mono text-[#64748b] mb-1">
                      <span className="text-[#00b0ff] font-bold uppercase">{art.source_name}</span>
                      <span>&middot;</span>
                      <span>{art.published_at ? art.published_at.split('T')[0] : 'Recent'}</span>
                      {art.age_days !== undefined && art.age_days !== null && (
                        <>
                          <span>&middot;</span>
                          <span className={art.age_days > 30 ? "text-[#ffd600]" : "text-[#00e676]"}>
                            {art.age_days === 0 ? "Today" : `${art.age_days}d ago`}
                          </span>
                        </>
                      )}
                      {art.sentiment_label && art.sentiment_score !== undefined && (
                        <>
                          <span>&middot;</span>
                          <span className={art.sentiment_label === 'positive' ? 'text-[#00e676]' : (art.sentiment_label === 'negative' ? 'text-[#ff5252]' : 'text-[#94a3b8]')}>
                            FinBERT: {art.sentiment_label.toUpperCase()} ({art.sentiment_score > 0 ? `+${art.sentiment_score.toFixed(2)}` : art.sentiment_score.toFixed(2)})
                          </span>
                        </>
                      )}
                    </div>
                    <h3 className="text-sm font-semibold text-white leading-snug">
                      {art.title}
                    </h3>
                    {art.text && (
                      <p className="text-xs text-[#94a3b8] mt-1.5 line-clamp-2 leading-relaxed">
                        {art.text}
                      </p>
                    )}
                  </div>

                  {art.url && (
                    <a
                      href={art.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded bg-[#121c2d] hover:bg-[#1a283f] text-[#00b0ff] transition shrink-0"
                      title="Open Verified Source"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {social.length === 0 ? (
            <div className="col-span-2 p-8 text-center bg-[#0e1626] border border-[#1c2a40] rounded text-xs text-[#64748b] font-mono">
              Real data unavailable &mdash; ingestion required for this symbol.
            </div>
          ) : (
            social.map(post => (
              <div 
                key={post.id}
                className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 hover:border-[#253954] transition flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between text-[10px] font-mono text-[#64748b] mb-2">
                    <span className="px-1.5 py-0.5 rounded bg-[#152033] text-[#00b0ff] uppercase font-bold">
                      {post.platform}
                    </span>
                    <div className="flex items-center space-x-2">
                      <span>{post.timestamp ? post.timestamp.split('T')[0] : 'Recent'}</span>
                      {post.age_days !== undefined && post.age_days !== null && (
                        <span className={post.age_days > 14 ? "text-[#ffd600]" : "text-[#00e676]"}>
                          ({post.age_days === 0 ? "Today" : `${post.age_days}d ago`})
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-[#f1f5f9] leading-relaxed">
                    {post.text}
                  </p>
                </div>

                <div className="mt-3 pt-2.5 border-t border-[#172236] flex items-center justify-between text-[11px] font-mono text-[#64748b]">
                  <span className="text-[#94a3b8]">@{post.author || 'analyst'}</span>
                  <div className="flex items-center space-x-3">
                    <span className="flex items-center space-x-1">
                      <ThumbsUp className="w-3 h-3 text-[#00b0ff]" />
                      <span>{post.likes}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Share2 className="w-3 h-3 text-[#64748b]" />
                      <span>{post.reposts}</span>
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
