"""
analytics.py - Insight Engine for InsightX

Responsibility: Transform DataFrames into business insights using
signal extraction, hypothesis scoring, and LLM-powered insight generation.
Follows the "What / Why / So What" framework.
"""

import json
import os
from typing import Dict, List, Set, Tuple, Optional
import pandas as pd
import numpy as np
from groq import Groq
from loguru import logger


class InsightGenerationError(Exception):
    """Raised when insight generation fails."""
    pass


class InsightEngine:
    """Transform query results into business insights using hypothesis scoring."""

    def __init__(self, hypothesis_library_path: str, api_key: Optional[str] = None):
        """
        Initialize the insight engine with a hypothesis library.

        Args:
            hypothesis_library_path: Path to hypotheses.json.
            api_key: Groq API key. Falls back to GROQ_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.1-70b-versatile"

        # Load hypothesis library
        with open(hypothesis_library_path, 'r') as f:
            data = json.load(f)
        self.hypotheses = data.get('hypotheses', [])
        logger.info(f"InsightEngine initialized with {len(self.hypotheses)} hypotheses.")

    def extract_signals(self, df: pd.DataFrame, query_context: str) -> Set[str]:
        """
        Apply signal detection rules to DataFrame to extract business signals.

        Does NOT just check column values - derives knowledge signals by analyzing
        patterns, correlations, and segments in the data.

        Args:
            df: Query result DataFrame.
            query_context: Original user query for contextual signal detection.

        Returns:
            Set of detected signal names.
        """
        signals = set()

        if df.empty:
            logger.warning("Empty DataFrame - no signals to extract.")
            return signals

        columns = set(df.columns.str.lower())

        # --- HIGH_FAILURE_RATE ---
        # Detect if any failure rate metric exceeds 5%
        failure_detected = False
        for col in df.columns:
            col_lower = col.lower()
            if 'failure' in col_lower or 'fail' in col_lower:
                if 'rate' in col_lower or 'pct' in col_lower or 'percent' in col_lower:
                    if df[col].dtype in ['float64', 'int64', 'float32']:
                        max_val = df[col].max()
                        if pd.notna(max_val) and max_val > 5.0:
                            signals.add("HIGH_FAILURE_RATE")
                            failure_detected = True

        # Also check if we can derive failure rate from status columns
        if not failure_detected and 'transaction_status' in columns:
            total = len(df)
            if total > 0:
                failed = (df['transaction_status'].str.upper() == 'FAILED').sum()
                rate = (failed / total) * 100
                if rate > 5.0:
                    signals.add("HIGH_FAILURE_RATE")

        # Check from computed columns with 'failed' and total counts
        if not failure_detected:
            for col in df.columns:
                col_lower = col.lower()
                if ('failed' in col_lower or 'failures' in col_lower) and df[col].dtype in ['float64', 'int64']:
                    total_col = None
                    for tc in df.columns:
                        if 'total' in tc.lower() or 'count' in tc.lower():
                            total_col = tc
                            break
                    if total_col and df[total_col].dtype in ['float64', 'int64']:
                        try:
                            rates = df[col] / df[total_col] * 100
                            if rates.max() > 5.0:
                                signals.add("HIGH_FAILURE_RATE")
                        except Exception:
                            pass

        # --- PEAK_SENSITIVE ---
        # Check if there's a significant variation across hours/time periods
        if 'hour_of_day' in columns:
            for val_col in df.columns:
                if df[val_col].dtype in ['float64', 'int64'] and val_col.lower() != 'hour_of_day':
                    try:
                        vals = df[val_col].dropna()
                        if len(vals) > 1:
                            mean_val = vals.mean()
                            max_val = vals.max()
                            if mean_val > 0 and (max_val - mean_val) / mean_val > 0.5:
                                signals.add("PEAK_SENSITIVE")
                                break
                    except Exception:
                        pass

        # --- NETWORK_FRAGILITY ---
        # Detect if network type correlates with failures
        if 'network_type' in columns:
            signals.add("NETWORK_FRAGILITY")
            # Check if there's meaningful variation by network type
            for val_col in df.columns:
                val_lower = val_col.lower()
                if ('fail' in val_lower or 'rate' in val_lower) and df[val_col].dtype in ['float64', 'int64']:
                    try:
                        vals = df[val_col].dropna()
                        if len(vals) > 1 and vals.std() / vals.mean() > 0.3:
                            signals.add("NETWORK_FRAGILITY")
                    except Exception:
                        pass

        # --- DEVICE_SENSITIVITY ---
        # Detect if device type shows in the data with variation
        if 'device_type' in columns:
            for val_col in df.columns:
                val_lower = val_col.lower()
                if ('fail' in val_lower or 'rate' in val_lower) and df[val_col].dtype in ['float64', 'int64']:
                    try:
                        vals = df[val_col].dropna()
                        if len(vals) > 1 and vals.std() > 0:
                            signals.add("DEVICE_SENSITIVITY")
                            break
                    except Exception:
                        pass

        # --- MAINTENANCE_WINDOW_PATTERN ---
        # Detect weekend-specific failure patterns
        if 'is_weekend' in columns:
            for val_col in df.columns:
                val_lower = val_col.lower()
                if ('fail' in val_lower or 'rate' in val_lower) and df[val_col].dtype in ['float64', 'int64']:
                    try:
                        weekend_rows = df[df['is_weekend'] == 1]
                        weekday_rows = df[df['is_weekend'] == 0]
                        if not weekend_rows.empty and not weekday_rows.empty:
                            weekend_rate = weekend_rows[val_col].mean()
                            weekday_rate = weekday_rows[val_col].mean()
                            if weekday_rate > 0 and weekend_rate > weekday_rate * 1.5:
                                signals.add("MAINTENANCE_WINDOW_PATTERN")
                    except Exception:
                        pass

        # --- EXTERNAL_DEPENDENCY ---
        # Bill Payments and Recharges depend on external biller systems
        if 'transaction_type' in columns:
            types_in_data = set(df['transaction_type'].dropna().unique())
            external_types = {'Bill Payment', 'Recharge'}
            if types_in_data & external_types:
                signals.add("EXTERNAL_DEPENDENCY")

        # Contextual signal from query text
        query_lower = query_context.lower()
        if 'bill' in query_lower or 'recharge' in query_lower or 'biller' in query_lower:
            signals.add("EXTERNAL_DEPENDENCY")
            signals.add("HEAVY_VALIDATION")

        # --- HEAVY_VALIDATION ---
        # Bill Payment and Recharge have multi-step validation
        if 'transaction_type' in columns:
            types_in_data = set(df['transaction_type'].dropna().unique())
            heavy_types = {'Bill Payment', 'Recharge'}
            if types_in_data & heavy_types:
                signals.add("HEAVY_VALIDATION")

        # --- HIGH_RETRIES ---
        # Infer high retry potential from failure patterns
        for col in df.columns:
            col_lower = col.lower()
            if 'retry' in col_lower:
                if df[col].dtype in ['float64', 'int64']:
                    if df[col].max() > 2.0:
                        signals.add("HIGH_RETRIES")

        # If high failure rate + external dependency, infer retries likely
        if "HIGH_FAILURE_RATE" in signals and "EXTERNAL_DEPENDENCY" in signals:
            signals.add("HIGH_RETRIES")

        # --- HIGH_VALUE_RISK ---
        # Detect patterns with high-value transactions
        if 'amount_inr' in columns:
            if 'fraud_flag' in columns:
                try:
                    high_val = df[df['amount_inr'] > df['amount_inr'].median()]
                    if not high_val.empty:
                        flag_rate = high_val['fraud_flag'].mean()
                        if flag_rate > 0.05:
                            signals.add("HIGH_VALUE_RISK")
                except Exception:
                    pass

        if 'fraud' in query_lower or 'flag' in query_lower or 'risk' in query_lower:
            signals.add("FRAUD_CONCENTRATION")

        # --- BANK_CONCENTRATION ---
        # Detect bank-specific patterns
        if 'sender_bank' in columns or 'receiver_bank' in columns:
            bank_col = 'sender_bank' if 'sender_bank' in columns else 'receiver_bank'
            for val_col in df.columns:
                val_lower = val_col.lower()
                if ('fail' in val_lower or 'rate' in val_lower) and df[val_col].dtype in ['float64', 'int64']:
                    try:
                        vals = df[val_col].dropna()
                        if len(vals) > 1 and vals.std() / vals.mean() > 0.3:
                            signals.add("BANK_CONCENTRATION")
                            break
                    except Exception:
                        pass

        logger.info(f"Extracted signals: {signals}")
        return signals

    def score_hypotheses(self, signals: Set[str]) -> List[Tuple[Dict, float]]:
        """
        Score all hypotheses against observed signals and return ranked list.

        Scoring Formula:
            score = 0.7 * (required_matched / total_required) +
                    0.3 * (supporting_matched / total_supporting)

        Args:
            signals: Set of detected signal names.

        Returns:
            List of (hypothesis_dict, confidence_score) sorted by score descending.
        """
        scored = []

        for hypothesis in self.hypotheses:
            required = set(hypothesis.get('required_signals', []))
            supporting = set(hypothesis.get('supporting_signals', []))

            if not required:
                continue

            required_score = len(required & signals) / len(required)
            supporting_score = (
                len(supporting & signals) / len(supporting) if supporting else 0
            )

            score = 0.7 * required_score + 0.3 * supporting_score
            scored.append((hypothesis, round(score, 3)))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            f"Hypothesis scores: "
            + ", ".join(f"{h['id']}={s:.2f}" for h, s in scored[:5])
        )

        return scored

    def generate_insight(
        self,
        user_query: str,
        df: pd.DataFrame,
        top_hypotheses: List[Tuple[Dict, float]],
    ) -> str:
        """
        Use LLM to generate a natural language insight following the
        What / Why / So What framework.

        Args:
            user_query: Original user question.
            df: Query result DataFrame.
            top_hypotheses: List of (hypothesis_dict, confidence_score).

        Returns:
            Formatted insight string.

        Raises:
            InsightGenerationError: If insight generation fails.
        """
        # Prepare data summary
        data_summary = self._summarize_dataframe(df)

        # Prepare hypothesis context
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
                    f"\n\nAlternative Hypothesis: {h2['name']} (Confidence: {s2:.2f})\n"
                    f"Description: {h2['description']}"
                )
        else:
            hypothesis_context = (
                "No strong hypothesis match found. "
                "Provide a factual summary of the data without speculating on root causes."
            )

        prompt = f"""You are a Leadership Analyst for a digital payments company. 
Provide clear, concise insights for non-technical executive stakeholders.

USER QUERY: "{user_query}"

DATA EVIDENCE:
{data_summary}

HYPOTHESIS ANALYSIS:
{hypothesis_context}

OUTPUT STRUCTURE (The "What, Why, So What" Framework):

1. THE "WHAT" (Lead with facts):
   State the exact numbers from the data evidence. Be precise with figures.

2. THE "WHY" (Hypothesis mapping):
   Explain the result using the provided hypothesis (if confidence >= 0.5).
   If confidence is low, acknowledge the data pattern without forcing a causal explanation.

3. THE "SO WHAT" (Business implication):
   Suggest actionable context using CAUTIOUS language.

CRITICAL RULES:
- If data evidence does NOT strongly support the hypothesis, state "Analysis suggests..." rather than definitive claims.
- Use phrases like "likely due to", "suggests that", "may indicate" - never claim absolute certainty.
- Never invent data points not present in the evidence.
- fraud_flag=1 means "flagged for manual review", NOT confirmed fraud. Never say "fraud" definitively.
- Keep response under 150 words.
- Do not use markdown headers or bullet point formatting. Write in flowing paragraphs.
- Include specific numbers from the data in your response."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=512,
                top_p=1.0,
            )
            insight = response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Insight generation API call failed: {e}")
            raise InsightGenerationError(f"Failed to generate insight: {e}")

        logger.info(f"Insight generated ({len(insight)} chars)")
        return insight

    def _summarize_dataframe(self, df: pd.DataFrame) -> str:
        """
        Create a concise text summary of a DataFrame for LLM consumption.

        Args:
            df: Query result DataFrame.

        Returns:
            Formatted string summary of the data.
        """
        if df.empty:
            return "No data returned from query."

        lines = []

        # Basic shape
        lines.append(f"Result: {len(df)} rows x {len(df.columns)} columns")
        lines.append(f"Columns: {', '.join(df.columns.tolist())}")

        # If small enough, show full data
        if len(df) <= 20:
            lines.append("\nFull Data:")
            lines.append(df.to_string(index=False))
        else:
            # Show first 10 rows
            lines.append(f"\nFirst 10 rows (of {len(df)}):")
            lines.append(df.head(10).to_string(index=False))

            # Add statistical summary for numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                lines.append("\nNumeric Summary:")
                for col in numeric_cols:
                    lines.append(
                        f"  {col}: min={df[col].min():.2f}, "
                        f"max={df[col].max():.2f}, "
                        f"mean={df[col].mean():.2f}"
                    )

        return "\n".join(lines)

    def generate_fallback_insight(self, df: pd.DataFrame) -> str:
        """
        Generate a basic data summary when hypothesis-based insight fails.

        Args:
            df: Query result DataFrame.

        Returns:
            Plain-text data summary.
        """
        if df.empty:
            return "The query returned no results. Please try rephrasing your question."

        summary = self._summarize_dataframe(df)
        return f"Based on the data:\n\n{summary}"
