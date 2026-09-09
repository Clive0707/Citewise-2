"""
Global Rate Limiter for LLM Requests
"""
import asyncio
import time
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Global rate limiter for LLM API calls.
    Tracks requests per model and enforces rate limits.
    """

    def __init__(self):
        # Model -> (requests_per_minute, min_interval_seconds)
        # Google Gemini Free Tier is 20 RPM. We configure 14 RPM / 3.5s spacing for a safe ~30% buffer.
        self.limits: Dict[str, Tuple[int, float]] = {
            "gemini-3.5-flash": (14, 3.5),
            "gemini-3.5-flash-lite": (14, 3.5),
            "gemini-3.6-flash": (14, 3.5),
            "gemini-2.5-flash": (14, 3.5),
            "gemini-1.5-pro-001": (14, 3.5),
            "gemini-2.0-flash": (14, 3.5),
            "gpt-4o-mini": (60, 1.0),
            "gpt-5-nano": (60, 1.0),
        }
        
        # Model -> list of request timestamps
        self.request_history: Dict[str, list] = defaultdict(list)
        
        # Model -> last request time
        self.last_request: Dict[str, float] = {}
        
        self.lock = asyncio.Lock()

    async def wait_for_slot(self, model: str) -> None:
        """
        Wait until a rate limit slot is available for the given model.
        """
        async with self.lock:
            if model in self.limits:
                limit_tuple = self.limits[model]
            elif "gemini" in model.lower():
                limit_tuple = (14, 3.5)
            else:
                # Unknown model, use conservative defaults
                await asyncio.sleep(1.0)
                return

            _, min_interval = limit_tuple
            now = time.time()
            
            # Check if we need to wait based on minimum interval
            if model in self.last_request:
                time_since_last = now - self.last_request[model]
                if time_since_last < min_interval:
                    wait_time = min_interval - time_since_last
                    logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {model}")
                    await asyncio.sleep(wait_time)
                    now = time.time()

            # Clean old requests (older than 60 seconds)
            cutoff = now - 60.0
            self.request_history[model] = [
                ts for ts in self.request_history[model] if ts > cutoff
            ]

            # Check if we've hit the per-minute limit
            requests_per_min, _ = limit_tuple
            recent_requests = len(self.request_history[model])
            
            if recent_requests >= requests_per_min:
                # Wait until the oldest request is more than 60 seconds old
                oldest = min(self.request_history[model])
                wait_until = oldest + 60.0
                wait_time = max(0, wait_until - now)
                if wait_time > 0:
                    logger.info(
                        f"Rate limit reached for {model}: {recent_requests}/{requests_per_min} requests. "
                        f"Waiting {wait_time:.2f}s"
                    )
                    await asyncio.sleep(wait_time)
                    now = time.time()

            # Record this request
            self.request_history[model].append(now)
            self.last_request[model] = now

    async def handle_429(self, model: str, retry_count: int = 0) -> None:
        """
        Handle 429 rate limit error with exponential backoff.
        
        Args:
            model: Model name
            retry_count: Current retry attempt (0-indexed)
        """
        max_retries = 5
        if retry_count >= max_retries:
            raise Exception(f"Rate limit exceeded for {model} after {max_retries} retries")
        
        # Exponential backoff: 2^retry_count seconds
        wait_time = 2 ** retry_count
        logger.warning(
            f"429 error for {model}, retry {retry_count + 1}/{max_retries}, "
            f"waiting {wait_time}s"
        )
        await asyncio.sleep(wait_time)


# Global instance
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter

