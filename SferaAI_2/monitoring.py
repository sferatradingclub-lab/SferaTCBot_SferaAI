"""
Monitoring and Health Checks for Sfera AI
Provides error tracking with Sentry and system health checks
"""
import os
import logging
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger(__name__)


def init_monitoring():
    """Initialize monitoring and error tracking with Sentry"""
    sentry_dsn = os.getenv("SENTRY_DSN")
    
    if sentry_dsn:
        # Initialize Sentry with logging integration
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[sentry_logging],
            traces_sample_rate=0.1,  # Sample 10% of transactions for performance monitoring
            environment=os.getenv("ENVIRONMENT", "development"),
            # Set a custom release version (optional)
            release=os.getenv("RELEASE_VERSION", "1.0.0")
        )
        logger.info("✅ Sentry monitoring initialized")
    else:
        logger.warning("⚠️  SENTRY_DSN not set, error monitoring disabled")


async def health_check() -> dict:
    """
    Perform health check on all critical services
    
    Returns:
        dict: Health status with check results for each service
    """
    status = {
        "status": "healthy",
        "checks": {}
    }
    
    # Check Qdrant (Memory) connectivity
    try:
        from qdrant_memory_client import QdrantMemoryClient
        client = QdrantMemoryClient()
        await client._ensure_initialized()
        status["checks"]["qdrant_memory"] = "healthy"
    except Exception as e:
        status["status"] = "unhealthy"
        status["checks"]["qdrant_memory"] = f"error: {str(e)}"
        logger.error(f"Qdrant memory health check failed: {e}")
    
    # Check Redis (Session Registry) connectivity
    try:
        from session_registry_redis import get_session_registry
        registry = get_session_registry()
        is_healthy = await registry.health_check()
        if is_healthy:
            status["checks"]["redis"] = "healthy"
        else:
            status["status"] = "unhealthy"
            status["checks"]["redis"] = "error: connection failed"
    except Exception as e:
        status["status"] = "unhealthy"
        status["checks"]["redis"] = f"error: {str(e)}"
        logger.error(f"Redis health check failed: {e}")
    
    # Check UnifiedUserState (Qdrant user state)
    try:
        from unified_user_state import get_unified_instance
        state = get_unified_instance()
        await state._ensure_initialized()
        status["checks"]["user_state"] = "healthy"
    except Exception as e:
        status["status"] = "unhealthy"
        status["checks"]["user_state"] = f"error: {str(e)}"
        logger.error(f"User state health check failed: {e}")
    
    return status


if __name__ == "__main__":
    import asyncio
    
    # Test health check
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("  SFERA AI - HEALTH CHECK")
    print("="*60 + "\n")
    
    result = asyncio.run(health_check())
    
    print(f"Overall Status: {result['status'].upper()}")
    print("\nService Checks:")
    for service, check_status in result['checks'].items():
        icon = "✅" if check_status == "healthy" else "❌"
        print(f"  {icon} {service}: {check_status}")
    
    print("\n" + "="*60 + "\n")
