"""Heleket crypto payment gateway client."""

import aiohttp
import hashlib
import hmac
import json
import time
import logging
from typing import Optional, Dict
from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class HeleketClient:
    """Client for Heleket cryptocurrency payment gateway."""
    
    def __init__(self):
        self.api_key = settings.HELEKET_API_KEY if hasattr(settings, 'HELEKET_API_KEY') else None
        self.api_secret = settings.HELEKET_API_SECRET if hasattr(settings, 'HELEKET_API_SECRET') else None
        self.base_url = "https://api.heleket.com/api/v1"  # Official Heleket API
        self.webhook_url = "https://sferatc.club/api/heleket/callback"
        
        if not self.api_key or not self.api_secret:
            logger.warning("Heleket API credentials not configured. Payment system will use mock mode.")
    
    async def create_payment(
        self,
        amount: float,
        currency: str,
        user_id: int,
        tier: str,
        promo_code: Optional[str] = None
    ) -> Dict:
        """
        Create new payment request.
        
        Args:
            amount: Payment amount in USD
            currency: Cryptocurrency (USDT)
            user_id: Telegram user ID
            tier: Subscription tier (pro)
            promo_code: Optional promo code
        
        Returns:
            dict with payment_id, address, qr_code, expires_at
        """
        order_id = f"sfera_{user_id}_{tier}_{int(time.time())}"
        
        payload = {
            "amount": amount,
            "currency": currency,
            "order_id": order_id,
            "callback_url": self.webhook_url,
            "success_url": f"{settings.WEBHOOK_URL}/payment/success",
            "fail_url": f"{settings.WEBHOOK_URL}/payment/failed",
            "metadata": {
                "user_id": user_id,
                "tier": tier,
                "promo_code": promo_code
            }
        }
        
        if not self.api_key:
            # Mock mode for development
            logger.info(f"MOCK: Creating payment for user {user_id}, amount ${amount}")
            return {
                "payment_id": f"mock_payment_{int(time.time())}",
                "address": "TXMockAddressForTestingPurposes123456789",
                "qr_code": f"https://api.qrserver.com/v1/create-qr-code/?data=TXMockAddress&size=200x200",
                "expires_at": int(time.time()) + 1800  # 30 minutes
            }
        
        try:
            headers = self._get_headers(payload)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/payment/create",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Heleket API error: {response.status} - {error_text}")
                        raise Exception(f"Payment creation failed: {response.status}")
                    
                    data = await response.json()
                    return {
                        "payment_id": data.get('id') or data.get('payment_id'),
                        "address": data.get('address') or data.get('wallet_address'),
                        "qr_code": data.get('qr_code_url') or data.get('qr_code'),
                        "expires_at": data.get('expires_at') or data.get('expiry_time')
                    }
        except Exception as e:
            logger.error(f"Error creating Heleket payment: {e}")
            raise
    
    async def check_payment_status(self, payment_id: str) -> Dict:
        """
        Check payment status.
        
        Args:
            payment_id: Payment ID from create_payment
        
        Returns:
            dict with status, amount, currency, metadata
        """
        if not self.api_key or payment_id.startswith("mock_"):
            # Mock mode
            logger.info(f"MOCK: Checking payment status for {payment_id}")
            return {
                "status": "pending",
                "amount": 24.99,
                "currency": "USDT",
                "metadata": {}
            }
        
        try:
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/payment/{payment_id}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to check payment status: {response.status}")
                        return {"status": "unknown"}
                    
                    return await response.json()
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return {"status": "error"}
    
    def verify_webhook_signature(self, payload: dict, signature: str) -> bool:
        """
        Verify webhook signature from Heleket.
        
        Args:
            payload: Webhook payload
            signature: X-Signature header value
        
        Returns:
            True if signature is valid
        """
        if not self.api_secret:
            logger.warning("MOCK: Skipping webhook signature verification (no API secret)")
            return True  # Allow in development
        
        try:
            expected_signature = hmac.new(
                self.api_secret.encode(),
                json.dumps(payload, separators=(',', ':')).encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def _get_headers(self, payload: Optional[dict] = None) -> Dict[str, str]:
        """Generate authentication headers."""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        if payload and self.api_secret:
            # Sign the payload
            signature = hmac.new(
                self.api_secret.encode(),
                json.dumps(payload, separators=(',', ':')).encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Signature"] = signature
        
        return headers
