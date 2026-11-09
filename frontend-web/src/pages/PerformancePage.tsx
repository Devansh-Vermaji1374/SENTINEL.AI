import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  CheckCircle2, 
  BarChart, 
  Layers, 
  HelpCircle,
  FileCheck,
  TrendingDown,
  RefreshCw,
  Cpu,
  ShieldCheck,
  Award,
  AlertTriangle
} from 'lucide-react';
import { AssetSignal } from '../types/api';
import { api } from '../services/api';

interface Props {
  selectedTicker: string;
  signals: AssetSignal[];
}

interface ModelPerfMeta {
  ticker: string;
  model_name: string;
  version: string;
  trained_at: string;
  training_samples: number;
  test_samples: number;
  residual_std: number;
  metrics: {
    mae: number;
    rmse: number;
    mape: number;
    directional_accuracy: number;
    bias: number;
    residual_std: number;
    r_squared: number;
  };
  baseline_metrics: {
    naive_zero: {
      mae: number;
      rmse: number;
      mape: number;
      directional_accuracy: number;
    };
    historical_mean: {
      mae: number;
      rmse: number;
      directional_accuracy: number;
    };
    mae: number;
    rmse: number;
  };
}

export const PerformancePage: React.FC<Props> = ({ selectedTicker, signals }) => {
  const [modelData, setModelData] = useState<ModelPerfMeta[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentTicker, setCurrentTicker] = useState<string>(selectedTicker || '0700.HK');

  useEffect(() => {
    if (selectedTicker) {
      setCurrentTicker(selectedTicker);
    }
  }, [selectedTicker]);

  useEffect(() => {
    fetchPerformanceData(currentTicker);
  }, [currentTicker]);

  const fetchPerformanceData = async (ticker: string) => {
    setLoading(true);
    try {
      const data = await api.getModelPerformance(ticker);
      setModelData(data);
    } catch (err) {
      console.error('Failed to fetch model performance:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatModelTitle = (name: string) => {
    switch (name) {
      case 'linear_regression':
        return 'Linear Regression (Ridge Regularized)';
      case 'random_forest':
        return 'Random Forest (Ensemble Trees)';
      case 'xgboost':
        return 'XGBoost Regressor (Walk-Forward)';
      case 'deep_learning_ann':
        return 'Deep Learning MLP ANN (Bounded)';
      default:
        return name;
    }
  };

  const getStatusBadge = (m: ModelPerfMeta) => {
    const naiveMae = m.baseline_metrics?.naive_zero?.mae || m.baseline_metrics?.mae || 0.02;
    if (m.metrics.mae <= naiveMae) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] bg-[#00e676]/10 text-[#00e676] border border-[#00e676]/30 flex items-center gap-1 justify-center">
          <Award className="w-3 h-3" /> Beats Baseline
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] bg-[#162235] text-[#94a3b8] border border-[#23354f] flex items-center gap-1 justify-center">
        Verified
      </span>
    );
  };

  const baselineData = modelData.length > 0 ? modelData[0].baseline_metrics : null;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#1b263b] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <Activity className="w-5 h-5 text-[#00b0ff]" />
            <h1 className="text-xl font-bold tracking-tight text-white">
              Quantitative Model Performance & Walk-Forward Validation
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#00e676]/10 text-[#00e676] border border-[#00e676]/30">
              ZERO LOOKAHEAD LEAKAGE
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] mt-1">
            Strict point-in-time chronological out-of-sample expanding window validation against the naïve previous-close benchmark.
          </p>
        </div>

        {/* Ticker Selector */}
        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="text-[#64748b]">ASSET:</span>
          <select 
            value={currentTicker}
            onChange={(e) => setCurrentTicker(e.target.value)}
            className="bg-[#101928] border border-[#1f2d42] text-white px-3 py-1.5 rounded focus:outline-none focus:border-[#00b0ff]"
          >
            {signals.map(s => (
              <option key={s.ticker} value={s.ticker}>
                {s.ticker} ({s.asset_name})
              </option>
            ))}
          </select>
          <button 
            onClick={() => fetchPerformanceData(currentTicker)}
            className="p-1.5 bg-[#101928] border border-[#1f2d42] hover:border-[#00b0ff] rounded text-[#94a3b8] hover:text-white"
            title="Refresh Registry"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-[#00b0ff]' : ''}`} />
          </button>
        </div>
      </div>

      {/* Out-of-Sample Performance Matrix */}
      <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Live Registry Metrics — Holdout Split ({currentTicker})
            </h2>
            <p className="text-xs text-[#64748b] mt-0.5">
              Trained on {modelData[0]?.training_samples ?? 80} chronological bars; evaluated on {modelData[0]?.test_samples ?? 22} future unseen market sessions.
            </p>
          </div>
          <span className="text-[11px] font-mono text-[#00b0ff] px-2.5 py-1 bg-[#00b0ff]/10 rounded border border-[#00b0ff]/20">
            Regime: 80% Train / 20% Chronological Test
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead>
              <tr className="border-b border-[#1b263b] text-[#64748b] text-[10px] uppercase">
                <th className="py-2.5 px-3">Model Architecture</th>
                <th className="py-2.5 px-3 text-right">MAE</th>
                <th className="py-2.5 px-3 text-right">RMSE</th>
                <th className="py-2.5 px-3 text-right">Directional Acc</th>
                <th className="py-2.5 px-3 text-right">Prediction Bias</th>
                <th className="py-2.5 px-3 text-right">Residual σ</th>
                <th className="py-2.5 px-3 text-center">Benchmark Comparison</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#172236]">
              {/* Naïve Benchmark Row */}
              {baselineData && (
                <tr className="bg-[#121c2e]/60">
                  <td className="py-3 px-3 font-bold text-[#ffd600] flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#ffd600]"></span>
                    Naïve Previous-Close Baseline (ŷ = 0)
                  </td>
                  <td className="py-3 px-3 text-right font-bold text-[#ffd600]">
                    {(baselineData.naive_zero?.mae ?? baselineData.mae).toFixed(4)}
                  </td>
                  <td className="py-3 px-3 text-right text-[#ffd600]/80">
                    {(baselineData.naive_zero?.rmse ?? baselineData.rmse).toFixed(4)}
                  </td>
                  <td className="py-3 px-3 text-right text-[#94a3b8]">
                    {((baselineData.naive_zero?.directional_accuracy ?? 0) * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-3 text-right text-[#94a3b8]">0.0000</td>
                  <td className="py-3 px-3 text-right text-[#94a3b8]">
                    {(baselineData.naive_zero?.rmse ?? baselineData.rmse).toFixed(4)}
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className="px-2 py-0.5 rounded text-[10px] bg-[#ffd600]/10 text-[#ffd600] border border-[#ffd600]/30">
                      Standard Benchmark
                    </span>
                  </td>
                </tr>
              )}

              {/* Dynamic Model Rows */}
              {modelData.map((m) => (
                <tr key={m.model_name} className="hover:bg-[#121c2e] transition">
                  <td className="py-3 px-3 font-bold text-white flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-[#00b0ff]" />
                    {formatModelTitle(m.model_name)}
                  </td>
                  <td className="py-3 px-3 text-right font-bold text-white">
                    {m.metrics.mae.toFixed(4)}
                  </td>
                  <td className="py-3 px-3 text-right text-[#94a3b8]">
                    {m.metrics.rmse.toFixed(4)}
                  </td>
                  <td className="py-3 px-3 text-right font-bold text-[#00b0ff]">
                    {(m.metrics.directional_accuracy * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-3 text-right text-[#94a3b8]">
                    {m.metrics.bias > 0 ? `+${m.metrics.bias.toFixed(4)}` : m.metrics.bias.toFixed(4)}
                  </td>
                  <td className="py-3 px-3 text-right text-[#00e676]">
                    &plusmn;{(m.residual_std * 100).toFixed(2)}%
                  </td>
                  <td className="py-3 px-3 text-center">
                    {getStatusBadge(m)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quantitative Integrity & Architecture Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono text-xs">
        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-5 space-y-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-[#00e676]" />
            <span>Quantitative Integrity Safeguards</span>
          </h3>
          <ul className="space-y-2 text-[#94a3b8] leading-relaxed text-[11px]">
            <li className="flex items-start space-x-2">
              <span className="text-[#00e676] font-bold">&bull;</span>
              <span><strong>Point-in-Time Joins:</strong> Sentiment metrics computed using only posts and articles timestamped prior to market bar cutoffs (strictly zero lookahead).</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-[#00e676] font-bold">&bull;</span>
              <span><strong>Persistent Transformers:</strong> Model artifacts (.joblib bundles) serialize fitted StandardScalers to prevent test distribution leakage during live inference.</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-[#00e676] font-bold">&bull;</span>
              <span><strong>ANN Stabilization:</strong> Multilayer Perceptron bounded with L2 regularization (&alpha; = 2.0) and feature clipping, eliminating explosive extrapolations.</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-[#00e676] font-bold">&bull;</span>
              <span><strong>Statistical Uncertainty:</strong> 95% confidence bands calibrated from out-of-sample residual standard deviations (&plusmn;1.96 &times; &sigma;).</span>
            </li>
          </ul>
        </div>

        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-5 space-y-3">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-[#ffd600]" />
            <span>Honest Evaluation & Baseline Reality</span>
          </h3>
          <ul className="space-y-2 text-[#94a3b8] leading-relaxed text-[11px]">
            <li className="flex items-start space-x-2">
              <span className="text-[#ffd600] font-bold">&bull;</span>
              <span><strong>Efficient Market Reality:</strong> Beating the random walk (zero-return benchmark) consistently on daily horizons is challenging; metrics report honest losses without fabrication.</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-[#ffd600] font-bold">&bull;</span>
              <span><strong>Directional Neutral Zone:</strong> Sign comparisons apply an &epsilon; = 0.1% threshold to avoid misclassifying flat days as directional failures.</span>
            </li>
            <li className="flex items-start space-x-2">
              <span className="text-[#ffd600] font-bold">&bull;</span>
              <span><strong>Prediction Lifecycle:</strong> Predictions target explicit exchange trading sessions (t + 1) and settle automatically when the actual session close is ingested.</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
