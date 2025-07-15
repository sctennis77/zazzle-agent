"""
OpenAI API Usage Tracker

This module provides comprehensive tracking and logging of OpenAI API usage,
including rate limits, usage statistics, and cost monitoring.

Features:
- Real-time usage tracking
- Rate limit monitoring
- Cost estimation
- Detailed logging
- Usage statistics
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, List, Optional

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class APIUsage:
    """Data class for tracking API usage statistics."""

    timestamp: datetime
    model: str
    operation: str
    tokens_used: int
    cost_usd: float
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None


@dataclass
class RateLimitInfo:
    """Data class for rate limit information."""

    requests_per_minute: int
    tokens_per_minute: int
    requests_remaining: int
    tokens_remaining: int
    reset_time: datetime


class OpenAIUsageTracker:
    """
    Tracks OpenAI API usage, rate limits, and costs.

    This class provides comprehensive monitoring of OpenAI API calls,
    including usage statistics, rate limit tracking, and cost estimation.
    """

    # OpenAI API pricing (as of 2024, update as needed)
    PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "dall-e-3": {"1024x1024": 0.04, "1024x1792": 0.08, "1792x1024": 0.08},
        "dall-e-2": {"1024x1024": 0.02, "512x512": 0.018, "256x256": 0.016},
    }

    # Rate limits (requests per minute)
    RATE_LIMITS = {
        "gpt-4": {"requests": 500, "tokens": 40000},
        "gpt-4-turbo": {"requests": 500, "tokens": 40000},
        "gpt-3.5-turbo": {"requests": 3500, "tokens": 90000},
        "dall-e-3": {"requests": 50, "tokens": 0},
        "dall-e-2": {"requests": 50, "tokens": 0},
    }

    def __init__(self):
        """Initialize the usage tracker."""
        self.usage_history: List[APIUsage] = []
        self.current_usage: Dict[str, Dict[str, int]] = {}
        self.rate_limit_info: Dict[str, RateLimitInfo] = {}
        self.session_start = datetime.now(timezone.utc)

        # Initialize current usage tracking
        for model in self.RATE_LIMITS.keys():
            self.current_usage[model] = {
                "requests": 0,
                "tokens": 0,
                "last_reset": datetime.now(timezone.utc),
            }

    def log_api_call(
        self,
        model: str,
        operation: str,
        tokens_used: int = 0,
        response_time_ms: float = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        rate_limit_remaining: Optional[int] = None,
        rate_limit_reset: Optional[datetime] = None,
    ) -> None:
        """
        Log an API call with detailed information.

        Args:
            model: The OpenAI model used
            operation: The type of operation (chat, image, etc.)
            tokens_used: Number of tokens used
            response_time_ms: Response time in milliseconds
            success: Whether the call was successful
            error_message: Error message if call failed
            rate_limit_remaining: Remaining requests in current window
            rate_limit_reset: When the rate limit resets
        """
        # Calculate cost
        cost_usd = self._calculate_cost(model, operation, tokens_used)

        # Create usage record
        usage = APIUsage(
            timestamp=datetime.now(timezone.utc),
            model=model,
            operation=operation,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            response_time_ms=response_time_ms,
            success=success,
            error_message=error_message,
            rate_limit_remaining=rate_limit_remaining,
            rate_limit_reset=rate_limit_reset,
        )

        # Add to history
        self.usage_history.append(usage)

        # Update current usage
        self._update_current_usage(model, tokens_used)

        # Log the usage
        self._log_usage_summary(usage)

    def _calculate_cost(self, model: str, operation: str, tokens_used: int) -> float:
        """Calculate the cost of an API call."""
        if model not in self.PRICING:
            return 0.0

        pricing = self.PRICING[model]

        if operation == "chat":
            # For chat models, assume 80% input, 20% output tokens
            input_tokens = int(tokens_used * 0.8)
            output_tokens = tokens_used - input_tokens

            input_cost = (input_tokens / 1000) * pricing.get("input", 0)
            output_cost = (output_tokens / 1000) * pricing.get("output", 0)

            return input_cost + output_cost

        elif operation == "image":
            # For image generation, use the size-based pricing
            size = "1024x1024"  # Default size
            return pricing.get(size, 0)

        return 0.0

    def _update_current_usage(self, model: str, tokens_used: int) -> None:
        """Update current usage statistics."""
        if model not in self.current_usage:
            return

        now = datetime.now(timezone.utc)
        last_reset = self.current_usage[model]["last_reset"]

        # Reset counters if a minute has passed
        if (now - last_reset).total_seconds() >= 60:
            self.current_usage[model]["requests"] = 0
            self.current_usage[model]["tokens"] = 0
            self.current_usage[model]["last_reset"] = now

        # Update counters
        self.current_usage[model]["requests"] += 1
        self.current_usage[model]["tokens"] += tokens_used

    def _log_usage_summary(self, usage: APIUsage) -> None:
        """Log a comprehensive usage summary."""
        # Get current usage for this model
        current = self.current_usage.get(usage.model, {})
        rate_limits = self.RATE_LIMITS.get(usage.model, {})

        # Calculate remaining capacity
        requests_remaining = rate_limits.get("requests", 0) - current.get("requests", 0)
        tokens_remaining = rate_limits.get("tokens", 0) - current.get("tokens", 0)

        # Create detailed log message
        log_data = {
            "timestamp": usage.timestamp.isoformat(),
            "model": usage.model,
            "operation": usage.operation,
            "tokens_used": usage.tokens_used,
            "cost_usd": f"${usage.cost_usd:.4f}",
            "response_time_ms": f"{usage.response_time_ms:.2f}ms",
            "success": usage.success,
            "current_session": {
                "requests_this_minute": current.get("requests", 0),
                "tokens_this_minute": current.get("tokens", 0),
                "requests_remaining": max(0, requests_remaining),
                "tokens_remaining": max(0, tokens_remaining),
            },
            "rate_limit_info": {
                "requests_per_minute": rate_limits.get("requests", 0),
                "tokens_per_minute": rate_limits.get("tokens", 0),
            },
        }

        if usage.error_message:
            log_data["error"] = usage.error_message

        if usage.rate_limit_remaining is not None:
            log_data["api_rate_limit_remaining"] = usage.rate_limit_remaining

        # Log with appropriate level
        if usage.success:
            logger.info(f"OpenAI API Call: {json.dumps(log_data, indent=2)}")
        else:
            logger.error(f"OpenAI API Error: {json.dumps(log_data, indent=2)}")

        # Log warning if approaching rate limits
        if requests_remaining <= 10:
            logger.warning(
                f"⚠️  Rate limit warning for {usage.model}: "
                f"{requests_remaining} requests remaining this minute"
            )

        if tokens_remaining <= 1000 and tokens_remaining > 0:
            logger.warning(
                f"⚠️  Token limit warning for {usage.model}: "
                f"{tokens_remaining} tokens remaining this minute"
            )

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session's API usage."""
        if not self.usage_history:
            return {"message": "No API calls recorded in this session"}

        total_calls = len(self.usage_history)
        successful_calls = sum(1 for u in self.usage_history if u.success)
        failed_calls = total_calls - successful_calls

        total_cost = sum(u.cost_usd for u in self.usage_history if u.success)
        total_tokens = sum(u.tokens_used for u in self.usage_history if u.success)

        avg_response_time = (
            sum(u.response_time_ms for u in self.usage_history) / total_calls
            if total_calls > 0
            else 0
        )

        # Group by model
        model_usage = {}
        for usage in self.usage_history:
            if usage.model not in model_usage:
                model_usage[usage.model] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "errors": 0,
                    "error_types": [],
                }

            model_usage[usage.model]["calls"] += 1
            if usage.success:
                model_usage[usage.model]["tokens"] += usage.tokens_used
                model_usage[usage.model]["cost"] += usage.cost_usd
            else:
                model_usage[usage.model]["errors"] += 1
                if usage.error_message:
                    # Extract error type from error message
                    error_type = "unknown"
                    if (
                        "429" in usage.error_message
                        or "rate limit" in usage.error_message.lower()
                    ):
                        error_type = "rate_limit"
                    elif (
                        "quota" in usage.error_message.lower()
                        or "insufficient_quota" in usage.error_message.lower()
                    ):
                        error_type = "quota_exceeded"
                    elif "invalid_api_key" in usage.error_message.lower():
                        error_type = "invalid_api_key"
                    elif "timeout" in usage.error_message.lower():
                        error_type = "timeout"

                    if error_type not in model_usage[usage.model]["error_types"]:
                        model_usage[usage.model]["error_types"].append(error_type)

        session_duration = datetime.now(timezone.utc) - self.session_start

        summary = {
            "session_duration_seconds": session_duration.total_seconds(),
            "total_api_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": (
                f"{(successful_calls/total_calls)*100:.1f}%"
                if total_calls > 0
                else "0%"
            ),
            "total_tokens_used": total_tokens,
            "total_cost_usd": f"${total_cost:.4f}",
            "average_response_time_ms": f"{avg_response_time:.2f}ms",
            "model_breakdown": model_usage,
            "current_rate_limits": self.current_usage,
        }

        # Add specific error information if there were failures
        if failed_calls > 0:
            summary["error_summary"] = {
                "total_failures": failed_calls,
                "failure_rate": f"{(failed_calls/total_calls)*100:.1f}%",
                "common_errors": [],
            }

            # Collect common error types
            all_error_types = []
            for model_data in model_usage.values():
                all_error_types.extend(model_data.get("error_types", []))

            if all_error_types:
                from collections import Counter

                error_counts = Counter(all_error_types)
                summary["error_summary"]["common_errors"] = [
                    {"type": error_type, "count": count}
                    for error_type, count in error_counts.most_common()
                ]

        return summary

    def log_session_summary(self) -> None:
        """Log a comprehensive session summary."""
        summary = self.get_session_summary()
        logger.info("=" * 80)
        logger.info("OPENAI API USAGE SESSION SUMMARY")
        logger.info("=" * 80)
        logger.info(json.dumps(summary, indent=2, default=str))
        logger.info("=" * 80)


# Global tracker instance
_usage_tracker = OpenAIUsageTracker()


def get_usage_tracker() -> OpenAIUsageTracker:
    """Get the global usage tracker instance."""
    return _usage_tracker


def track_openai_call(model: str, operation: str = "chat"):
    """
    Decorator to track OpenAI API calls.

    Args:
        model: The OpenAI model being used
        operation: The type of operation (chat, image, etc.)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            error_message = None
            tokens_used = 0
            rate_limit_remaining = None
            rate_limit_reset = None

            try:
                result = func(*args, **kwargs)
                success = True

                # Try to extract token usage from response
                if hasattr(result, "usage") and result.usage:
                    tokens_used = result.usage.total_tokens

                # Try to extract rate limit info from response headers
                if hasattr(result, "_headers"):
                    headers = result._headers
                    if "x-ratelimit-remaining-requests" in headers:
                        rate_limit_remaining = int(
                            headers["x-ratelimit-remaining-requests"]
                        )
                    if "x-ratelimit-reset-requests" in headers:
                        reset_timestamp = int(headers["x-ratelimit-reset-requests"])
                        rate_limit_reset = datetime.fromtimestamp(
                            reset_timestamp, timezone.utc
                        )

                return result

            except Exception as e:
                error_message = str(e)

                # Check for specific error types and log appropriate warnings
                if "429" in error_message or "rate limit" in error_message.lower():
                    logger.warning(f"🚨 Rate limit exceeded for {model} - {operation}")
                elif "quota" in error_message.lower():
                    logger.error(f"💳 API quota exceeded for {model} - {operation}")
                elif "insufficient_quota" in error_message.lower():
                    logger.error(f"💳 Insufficient quota for {model} - {operation}")
                elif "invalid_api_key" in error_message.lower():
                    logger.error(f"🔑 Invalid API key for {model} - {operation}")
                else:
                    logger.error(
                        f"❌ API call failed for {model} - {operation}: {error_message}"
                    )

                raise
            finally:
                response_time_ms = (time.time() - start_time) * 1000

                # Always log the API call attempt, even if it failed
                _usage_tracker.log_api_call(
                    model=model,
                    operation=operation,
                    tokens_used=tokens_used,
                    response_time_ms=response_time_ms,
                    success=success,
                    error_message=error_message,
                    rate_limit_remaining=rate_limit_remaining,
                    rate_limit_reset=rate_limit_reset,
                )

        return wrapper

    return decorator


def log_session_summary():
    """Log the current session's API usage summary."""
    _usage_tracker.log_session_summary()
