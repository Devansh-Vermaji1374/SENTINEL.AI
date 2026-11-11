"""SENTINEL AI - ML Investigation & Feature Correlation Diagnostics.
Inspects feature quality, target correlation, sentiment density, and baseline performance.
Recalculates all statistics dynamically from current SQLite and model metadata.
"""
import sqlite3
import pandas as pd
import numpy as np
import json
from pathlib import Path

def run_diagnostics():
    print("===============================================================")
    print("SENTINEL AI - DYNAMIC ML & FEATURE DIAGNOSTIC REPORT")
    print("===============================================================")
    
    conn = sqlite3.connect("file:sentinel.db?mode=ro", uri=True)
    
    tickers = [
        "0700.HK", "9988.HK", "1299.HK", "0005.HK", "3690.HK",
        "005930.KS", "000660.KS", "373220.KS", "005380.KS", "035420.KS"
    ]
    
    print("\n--- 1. DATASET VOLUMETRICS & SENTIMENT DENSITY PER ASSET ---")
    summary_rows = []
    for ticker in tickers:
        df_m = pd.read_sql_query("SELECT * FROM market_data WHERE ticker=? ORDER BY date", conn, params=(ticker,))
        n_bars = len(df_m)
        
        # Count sentiment by source type
        df_soc = pd.read_sql_query("SELECT count(*) as cnt FROM sentiment_scores WHERE ticker=? AND source_type='social'", conn, params=(ticker,))
        n_soc = df_soc.iloc[0]["cnt"]
        
        df_news = pd.read_sql_query("SELECT count(*) as cnt FROM sentiment_scores WHERE ticker=? AND source_type='news'", conn, params=(ticker,))
        n_news = df_news.iloc[0]["cnt"]
        
        meta_path = Path(f"models/saved/{ticker}_random_forest_meta.json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            n_tr = meta.get("holdout_training_samples", 0)
            n_val = meta.get("validation_samples", 0)
            n_te = meta.get("test_samples", 0)
            n_feat = len(meta.get("features", []))
        else:
            n_tr = n_val = n_te = n_feat = 0
            
        summary_rows.append({
            "ticker": ticker,
            "market_bars": n_bars,
            "social_scores": n_soc,
            "news_scores": n_news,
            "train_samples": n_tr,
            "val_samples": n_val,
            "test_samples": n_te,
            "features_used": n_feat
        })
        
    sum_df = pd.DataFrame(summary_rows)
    print(sum_df.to_string(index=False))
    
    # 2. Performance against baselines for all 40 models
    print("\n--- 2. MODEL VS BASELINE COMPARISON (ALL 40 ARTIFACTS DYNAMICALLY PARSED) ---")
    meta_files = sorted(Path("models/saved").glob("*_meta.json"))
    
    perf_rows = []
    beat_zero_count = 0
    beat_mean_count = 0
    
    for mf in meta_files:
        meta = json.loads(mf.read_text())
        ticker = meta["ticker"]
        model = meta["model_name"]
        m_mae = meta.get("metrics", {}).get("mae", np.nan)
        m_rmse = meta.get("metrics", {}).get("rmse", np.nan)
        m_da = meta.get("metrics", {}).get("directional_accuracy", np.nan)
        m_r2 = meta.get("metrics", {}).get("r_squared", np.nan)
        
        z_mae = meta.get("baseline_metrics", {}).get("naive_zero", {}).get("mae", np.nan)
        h_mae = meta.get("baseline_metrics", {}).get("historical_mean", {}).get("mae", np.nan)
        
        bz = bool(m_mae < z_mae)
        bm = bool(m_mae < h_mae)
        if bz: beat_zero_count += 1
        if bm: beat_mean_count += 1
        
        perf_rows.append({
            "ticker": ticker,
            "model": model,
            "test_mae": round(m_mae, 5),
            "zero_mae": round(z_mae, 5),
            "mean_mae": round(h_mae, 5),
            "beat_zero": bz,
            "beat_mean": bm,
            "dir_acc": round(m_da, 3),
            "r2": round(m_r2, 4)
        })
        
    perf_df = pd.DataFrame(perf_rows)
    print(perf_df.to_string(index=False))
    
    print(f"\nAGGREGATE RECALCULATED RESULTS:")
    print(f"Total evaluated models: {len(perf_rows)}")
    print(f"Beating Zero-Return Baseline (MAE): {beat_zero_count} / {len(perf_rows)} ({beat_zero_count/len(perf_rows)*100:.1f}%)")
    print(f"Beating Historical-Mean Baseline (MAE): {beat_mean_count} / {len(perf_rows)} ({beat_mean_count/len(perf_rows)*100:.1f}%)")
    
    # 3. Dynamic Feature Correlation Analysis
    print("\n--- 3. FEATURE CORRELATION WITH TARGET RETURN (0700.HK SAMPLE) ---")
    df_sample = pd.read_sql_query("SELECT * FROM market_data WHERE ticker='0700.HK' ORDER BY date", conn)
    df_sample["daily_return"] = df_sample["close"].pct_change()
    df_sample["target_return"] = df_sample["close"].pct_change().shift(-1)
    df_sample["close_to_sma_20"] = (df_sample["close"] - df_sample["close"].rolling(20, min_periods=1).mean()) / df_sample["close"]
    df_sample["volatility_20"] = df_sample["daily_return"].rolling(20, min_periods=1).std()
    
    corr_cols = ["daily_return", "close_to_sma_20", "volatility_20"]
    clean_sample = df_sample.dropna(subset=corr_cols + ["target_return"])
    corrs = clean_sample[corr_cols].apply(lambda c: c.corr(clean_sample["target_return"]))
    for col, val in corrs.items():
        print(f"  Corr({col}, target_return): {val:+.4f}")
        
    conn.close()

if __name__ == '__main__':
    run_diagnostics()
