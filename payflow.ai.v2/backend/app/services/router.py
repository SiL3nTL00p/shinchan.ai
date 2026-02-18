"""
router.py - Query Router

Classifies incoming user queries as either:
  - "data"   → requires SQL generation & execution against the dataset
  - "general" → can be answered directly by the LLM (greetings, explanations, etc.)

Uses a fast LLM call for classification, with keyword-based fallback.
"""

import os
import re
from typing import Optional
from groq import Groq
from loguru import logger


class QueryRouter:
    """Route user queries to the appropriate pipeline (data vs. general)."""

    # Keywords that strongly suggest a data/analytics query
    DATA_KEYWORDS = {
        "how many", "count", "total", "average", "mean", "median",
        "sum", "max", "min", "highest", "lowest", "top", "bottom",
        "rate", "percentage", "percent", "ratio", "trend", "growth",
        "compare", "comparison", "breakdown", "distribution",
        "transaction", "transactions", "payment", "payments",
        "fraud", "failure", "success", "failed", "upi",
        "merchant", "bank", "state", "device", "network",
        "p2p", "p2m", "bill", "recharge", "amount",
        "revenue", "volume", "frequency", "monthly", "weekly",
        "daily", "hourly", "weekend", "weekday",
        "sender", "receiver", "age group", "age_group",
        "android", "ios", "wifi", "3g", "4g", "5g",
        "show me", "list", "find", "fetch", "get",
        "which", "what is the", "what are the", "what's the",
        "calculate", "analyse", "analyze", "query",
        "chart", "graph", "plot", "visualize",
        "group by", "sort by", "order by", "filter",
    }

    # Keywords that strongly suggest a general/conversational query
    GENERAL_KEYWORDS = {
        "hello", "hi", "hey", "thanks", "thank you", "bye",
        "good morning", "good evening", "good night",
        "who are you", "what are you", "your name",
        "help me", "what can you do", "how do you work",
        "explain", "tell me about yourself", "introduce",
    }

    # Follow-up indicators — words that suggest the query refers to something prior
    FOLLOWUP_INDICATORS = {
        "both", "either", "which one", "out of", "between them",
        "the first", "the second", "the same", "those", "these",
        "that", "them", "it", "its", "their", "they",
        "more", "less", "better", "worse", "higher", "lower",
        "instead", "also", "as well", "too", "again",
        "now show", "now compare", "now filter", "what about",
        "and what", "and how", "but what", "but how",
        "same thing", "same query", "same data",
        "break it down", "drill down", "go deeper",
        "previous", "last question", "earlier",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
    ):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key required for QueryRouter.")
        self.client = Groq(api_key=self.api_key)
        self.model = model
        logger.info("QueryRouter initialized.")

    def classify(
        self,
        user_query: str,
        has_data_history: bool = False,
    ) -> str:
        """
        Classify a query as 'data' or 'general'.
        If the conversation has prior data queries, follow-up references
        are treated as data queries.
        """
        query_lower = user_query.lower().strip()

        # If there's prior data history, check for follow-up indicators
        if has_data_history and self._is_followup(query_lower):
            logger.info(f"Router (follow-up): '{user_query[:60]}' → data")
            return "data"

        # Quick keyword classification
        keyword_result = self._keyword_classify(query_lower)
        if keyword_result is not None:
            # If keyword says general but there's data history and query is
            # short/ambiguous, prefer data
            if (
                keyword_result == "general"
                and has_data_history
                and len(query_lower.split()) <= 10
                and "?" in query_lower
            ):
                logger.info(
                    f"Router (general→data override): '{user_query[:60]}' → data"
                )
                return "data"
            logger.info(f"Router (keyword): '{user_query[:60]}' → {keyword_result}")
            return keyword_result

        # Ambiguous — use LLM to classify (with history hint)
        return self._llm_classify(user_query, has_data_history)

    def _is_followup(self, query_lower: str) -> bool:
        """Check if query contains follow-up reference indicators."""
        for indicator in self.FOLLOWUP_INDICATORS:
            if indicator in query_lower:
                return True
        return False

    def _keyword_classify(self, query_lower: str) -> Optional[str]:
        """Fast keyword-based classification. Returns None if ambiguous."""
        # Check general keywords first (they're more specific)
        for kw in self.GENERAL_KEYWORDS:
            if re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
                return "general"

        # Check data keywords
        data_score = sum(
            1 for kw in self.DATA_KEYWORDS
            if re.search(r'\b' + re.escape(kw) + r'\b', query_lower)
        )
        if data_score >= 2:
            return "data"

        # Single data keyword with question mark → likely data
        if data_score == 1 and "?" in query_lower:
            return "data"

        return None  # ambiguous

    def _llm_classify(self, user_query: str, has_data_history: bool = False) -> str:
        """Use LLM for difficult classification cases."""
        history_hint = ""
        if has_data_history:
            history_hint = (
                "\n\nIMPORTANT: The user has previously asked data analysis questions "
                "in this conversation. If the message seems like a follow-up or "
                "continuation of data analysis (even if vague), classify as DATA."
            )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a query classifier for a UPI digital payments analytics system. "
                            "Classify the user's message into exactly one category:\n"
                            "- DATA: The user wants to query, analyze, or explore UPI transaction data "
                            "(e.g., statistics, trends, comparisons, counts, rates, amounts, etc.) "
                            "OR is asking a follow-up question about previous data results.\n"
                            "- GENERAL: The user is having a normal conversation, asking for help, "
                            "greeting, or asking something completely unrelated to data analysis.\n"
                            f"{history_hint}\n\n"
                            "Respond with ONLY the single word: DATA or GENERAL"
                        ),
                    },
                    {"role": "user", "content": user_query},
                ],
                temperature=0.0,
                max_tokens=10,
                top_p=1.0,
            )
            classification = response.choices[0].message.content.strip().upper()

            if "DATA" in classification:
                result = "data"
            elif "GENERAL" in classification:
                result = "general"
            else:
                result = "data"  # default to data for safety

            logger.info(f"Router (LLM): '{user_query[:60]}' → {result}")
            return result

        except Exception as e:
            logger.warning(f"Router LLM call failed: {e}. Defaulting to 'data'.")
            return "data"
