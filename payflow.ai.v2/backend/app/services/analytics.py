"""
analytics.py - Insight Engine

Transforms DataFrames into business insights using signal extraction,
hypothesis scoring, and LLM-powered insight generation.
"""

import json
import os
from typing import Dict, List, Set, Tuple, Optional
import pandas as pd
import numpy as np
from groq import Groq
from loguru import logger


class InsightGenerationError(Exception):
    pass


class InsightEngine:
    """Transform query results into business insights via hypothesis scoring."""

    def __init__(
        self,
        hypothesis_library_path: str,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key required.")
        self.client = Groq(api_key=self.api_key)
        self.model = model

        with open(hypothesis_library_path, 'r') as f:
            data = json.load(f)
        self.hypotheses = data.get('hypotheses', [])
        logger.info(f"InsightEngine: {len(self.hypotheses)} hypotheses loaded.")

    def extract_signals(self, df: pd.DataFrame, query_context: str) -> Set[str]:
        signals: Set[str] = set()
        if df.empty:
            return signals

        columns = set(df.columns.str.lower())

        # HIGH_FAILURE_RATE
        failure_detected = False
        for col in df.columns:
            cl = col.lower()
            if ('failure' in cl or 'fail' in cl) and ('rate' in cl or 'pct' in cl or 'percent' in cl):
                if df[col].dtype in ['float64', 'int64', 'float32']:
                    if pd.notna(df[col].max()) and df[col].max() > 5.0:
                        signals.add("HIGH_FAILURE_RATE")
                        failure_detected = True

        if not failure_detected and 'transaction_status' in columns:
            total = len(df)
            if total > 0:
                failed = (df['transaction_status'].str.upper() == 'FAILED').sum()
                if (failed / total) * 100 > 5.0:
                    signals.add("HIGH_FAILURE_RATE")

        if not failure_detected:
            for col in df.columns:
                cl = col.lower()
                if ('failed' in cl or 'failures' in cl) and df[col].dtype in ['float64', 'int64']:
                    total_col = next(
                        (tc for tc in df.columns if 'total' in tc.lower() or 'count' in tc.lower()),
                        None,
                    )
                    if total_col and df[total_col].dtype in ['float64', 'int64']:
                        try:
                            rates = df[col] / df[total_col] * 100
                            if rates.max() > 5.0:
                                signals.add("HIGH_FAILURE_RATE")
                        except Exception:
                            pass

        # PEAK_SENSITIVE
        if 'hour_of_day' in columns:
            for val_col in df.columns:
                if df[val_col].dtype in ['float64', 'int64'] and val_col.lower() != 'hour_of_day':
                    try:
                        vals = df[val_col].dropna()
                        if len(vals) > 1:
                            mean_val = vals.mean()
                            if mean_val > 0 and (vals.max() - mean_val) / mean_val > 0.5:
                                signals.add("PEAK_SENSITIVE")
                                break
                    except Exception:
                        pass

        # NETWORK_FRAGILITY
        if 'network_type' in columns:
            signals.add("NETWORK_FRAGILITY")

        # DEVICE_SENSITIVITY
        if 'device_type' in columns:
            for val_col in df.columns:
                if ('fail' in val_col.lower() or 'rate' in val_col.lower()) and df[val_col].dtype in ['float64', 'int64']:
                    try:
                        vals = df[val_col].dropna()
                        if len(vals) > 1 and vals.std() > 0:
                            signals.add("DEVICE_SENSITIVITY")
                            break
                    except Exception:
                        pass

        # MAINTENANCE_WINDOW_PATTERN
        if 'is_weekend' in columns:
            for val_col in df.columns:
                if ('fail' in val_col.lower() or 'rate' in val_col.lower()) and df[val_col].dtype in ['float64', 'int64']:
                    try:
                        wknd = df[df['is_weekend'] == 1]
                        wkdy = df[df['is_weekend'] == 0]
                        if not wknd.empty and not wkdy.empty:
                            if wkdy[val_col].mean() > 0 and wknd[val_col].mean() > wkdy[val_col].mean() * 1.5:
                                signals.add("MAINTENANCE_WINDOW_PATTERN")
                    except Exception:
                        pass

        # EXTERNAL_DEPENDENCY
        if 'transaction_type' in columns:
            types = set(df['transaction_type'].dropna().unique())
            if types & {'Bill Payment', 'Recharge'}:
                signals.add("EXTERNAL_DEPENDENCY")

        query_lower = query_context.lower()
        if any(k in query_lower for k in ('bill', 'recharge', 'biller')):
            signals.add("EXTERNAL_DEPENDENCY")
            signals.add("HEAVY_VALIDATION")

        # HEAVY_VALIDATION
        if 'transaction_type' in columns:
            types = set(df['transaction_type'].dropna().unique())
            if types & {'Bill Payment', 'Recharge'}:
                signals.add("HEAVY_VALIDATION")

        # HIGH_RETRIES
        if "HIGH_FAILURE_RATE" in signals and "EXTERNAL_DEPENDENCY" in signals:
            signals.add("HIGH_RETRIES")

        # HIGH_VALUE_RISK
        if 'amount_inr' in columns and 'fraud_flag' in columns:
            try:
                high_val = df[df['amount_inr'] > df['amount_inr'].median()]
                if not high_val.empty and high_val['fraud_flag'].mean() > 0.05:
                    signals.add("HIGH_VALUE_RISK")
            except Exception:
                pass

        if any(k in query_lower for k in ('fraud', 'flag', 'risk')):
            signals.add("FRAUD_CONCENTRATION")

        # BANK_CONCENTRATION
        bank_col = 'sender_bank' if 'sender_bank' in columns else ('receiver_bank' if 'receiver_bank' in columns else None)
        if bank_col:
            for val_col in df.columns:
                if ('fail' in val_col.lower() or 'rate' in val_col.lower()) and df[val_col].dtype in ['float64', 'int64']:
                    try:
                        vals = df[val_col].dropna()
                        if len(vals) > 1 and vals.std() / vals.mean() > 0.3:
                            signals.add("BANK_CONCENTRATION")
                            break
                    except Exception:
                        pass

        logger.info(f"Signals: {signals}")
        return signals

    def score_hypotheses(self, signals: Set[str]) -> List[Tuple[Dict, float]]:
        scored = []
        for h in self.hypotheses:
            required = set(h.get('required_signals', []))
            supporting = set(h.get('supporting_signals', []))
            if not required:
                continue
            req_score = len(required & signals) / len(required)
            sup_score = len(supporting & signals) / len(supporting) if supporting else 0
            score = 0.7 * req_score + 0.3 * sup_score
            scored.append((h, round(score, 3)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def generate_insight(
        self,
        user_query: str,
        df: pd.DataFrame,
        top_hypotheses: List[Tuple[Dict, float]],
    ) -> str:
        data_summary = self._summarize_dataframe(df)

        if top_hypotheses and top_hypotheses[0][1] >= 0.3:
            best_hyp, best_score = top_hypotheses[0]
            hypothesis_context = (
                f"Top Hypothesis: {best_hyp['name']} (Confidence: {best_score:.2f})\n"
                f"Description: {best_hyp['description']}\n"
                f"Business Implication: {best_hyp['business_implication']}"
            )
            if len(top_hypotheses) > 1 and top_hypotheses[1][1] >= 0.3:
                h2, s2 = top_hypotheses[1]
                hypothesis_context += (
                    f"\n\nAlternative: {h2['name']} (Confidence: {s2:.2f})\n"
                    f"Description: {h2['description']}"
                )
        else:
            hypothesis_context = (
                "No strong hypothesis match. Provide factual summary without speculating."
            )

        prompt = f"""You are a Leadership Analyst for a digital payments company.

USER QUERY: "{user_query}"

DATA EVIDENCE:
{data_summary}

HYPOTHESIS ANALYSIS:
{hypothesis_context}

OUTPUT STRUCTURE (What / Why / So What):
1. THE "WHAT": Exact numbers from data.
2. THE "WHY": Explanation using hypothesis (if confidence >= 0.5).
3. THE "SO WHAT": Actionable context using cautious language.

RULES:
- Use "likely due to", "suggests that", "may indicate" — never claim certainty.
- Never invent data not in evidence.
- fraud_flag=1 = "flagged for review", NOT confirmed fraud.
- Keep under 150 words. Flowing paragraphs, no markdown headers.
- Include specific numbers."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=512,
                top_p=1.0,
            )
            insight = response.choices[0].message.content.strip()
        except Exception as e:
            raise InsightGenerationError(f"Failed to generate insight: {e}")

        logger.info(f"Insight generated ({len(insight)} chars)")
        return insight

    def _summarize_dataframe(self, df: pd.DataFrame) -> str:
        if df.empty:
            return "No data returned from query."
        lines = [
            f"Result: {len(df)} rows x {len(df.columns)} columns",
            f"Columns: {', '.join(df.columns.tolist())}",
        ]
        if len(df) <= 20:
            lines.append("\nFull Data:")
            lines.append(df.to_string(index=False))
        else:
            lines.append(f"\nFirst 10 rows (of {len(df)}):")
            lines.append(df.head(10).to_string(index=False))
            numeric = df.select_dtypes(include=[np.number]).columns
            if len(numeric) > 0:
                lines.append("\nNumeric Summary:")
                for col in numeric:
                    lines.append(
                        f"  {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}"
                    )
        return "\n".join(lines)

    def generate_fallback_insight(self, df: pd.DataFrame) -> str:
        if df.empty:
            return "The query returned no results. Please try rephrasing."
        return f"Based on the data:\n\n{self._summarize_dataframe(df)}"
