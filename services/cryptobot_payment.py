"""CryptoBot payment gateway client for Telegram crypto payments.

Official API: https://help.crypt.bot/crypto-pay-api
"""

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


class CryptoBotClient:
    """Client for CryptoBot (Crypto Pay API) payment gateway."""
    
    def __init__(self):
        self.api_token = settings.CRYPTOBOT_API_TOKEN if hasattr(settings, 'CRYPTOBOT_API_TOKEN') else None
        self.base_url = "https://pay.crypt.bot/api"
        self.testnet_url = "https://testnet-pay.crypt.bot/api"
        
        # Use testnet if no API token
        self.api_url = self.base_url if self.api_token else self.testnet_url
        
        if not self.api_token:
            logger.warning("CryptoBot API token not configured. Using testnet mode.")
    
    async def create_invoice(
        self,
        amount: float,
        currency: str,
        description: str,
        user_id: int,
        tier: str,
        promo_code: Optional[str] = None
    ) -> Dict:
        """
        Create new payment invoice.
        
        Args:
            amount: Payment amount
            currency: Cryptocurrency (USDT, TON, BTC, ETH, etc.)
            description: Payment description
            user_id: Telegram user ID
            tier: Subscription tier (pro)
            promo_code: Optional promo code
        
        Returns:
            dict with invoice_id, pay_url, mini_app_invoice_url, web_app_invoice_url
        """
        payload = {
            "amount": str(amount),
            "currency_type": "crypto",
            "asset": currency,
            "description": description,
            "paid_btn_name": "callback",
            "paid_btn_url": "https://t.me/your_bot",  # Will be updated
            "payload": json.dumps({
                "user_id": user_id,
                "tier": tier,
                "promo_code": promo_code
            }),
            "allow_comments": False,
            "allow_anonymous": False,
        }
        
        if not self.api_token:
            # Mock mode for development
            logger.info(f"MOCK: Creating CryptoBot invoice for user {user_id}, amount {amount} {currency}")
            return {
                "invoice_id": f"mock_invoice_{int(time.time())}",
                "pay_url": f"https://t.me/CryptoBot?start=pay_MOCK{int(time.time())}",
                "mini_app_invoice_url": f"https://t.me/CryptoBot/pay?startapp=MOCK{int(time.time())}",
                "web_app_invoice_url": f"https://pay.crypt.bot/i/MOCK{int(time.time())}",
                "amount": amount,
                "asset": currency,
                "description": description,
                "status": "active",
            }
        
        try:
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/createInvoice",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"CryptoBot API error: {response.status} - {error_text}")
                        raise Exception(f"Invoice creation failed: {response.status}")
                    
                    data = await response.json()
                    
                    if not data.get('ok'):
                        error_msg = data.get('error', {}).get('name', 'Unknown error')
                        logger.error(f"CryptoBot error: {error_msg}")
                        raise Exception(f"Invoice creation failed: {error_msg}")
                    
                    result = data.get('result', {})
                    return {
                        "invoice_id": result.get('invoice_id'),
                        "pay_url": result.get('bot_invoice_url'),
                        "mini_app_invoice_url": result.get('mini_app_invoice_url'),
                        "web_app_invoice_url": result.get('web_app_invoice_url'),
                        "amount": result.get('amount'),
                        "asset": result.get('asset'),
                        "description": result.get('description'),
                        "status": result.get('status'),
                    }
        except Exception as e:
            logger.error(f"Error creating CryptoBot invoice: {e}")
            raise
    
    async def get_invoice(self, invoice_id: str) -> Dict:
        """
        Get invoice status.
        
        Args:
            invoice_id: Invoice ID from create_invoice
        
        Returns:
            dict with status, amount, currency, etc.
        """
        if not self.api_token or invoice_id.startswith("mock_"):
            # Mock mode
            logger.info(f"MOCK: Checking CryptoBot invoice status for {invoice_id}")
            return {
                "invoice_id": invoice_id,
                "status": "active",
                "amount": "24.99",
                "asset": "USDT",
            }
        
        try:
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/getInvoices",
                    params={"invoice_ids": invoice_id},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get invoice status: {response.status}")
                        return {"status": "unknown"}
                    
                    data = await response.json()
                    if data.get('ok') and data.get('result', {}).get('items'):
                        invoice = data['result']['items'][0]
                        return {
                            "invoice_id": invoice.get('invoice_id'),
                            "status": invoice.get('status'),
                            "amount": invoice.get('amount'),
                            "asset": invoice.get('asset'),
                            "payload": invoice.get('payload'),
                        }
                    
                    return {"status": "not_found"}
        except Exception as e:
            logger.error(f"Error getting invoice status: {e}")
            return {"status": "error"}
    
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """
        Verify webhook signature from CryptoBot.
        
        Args:
            body: Raw request body (bytes)
            signature: Crypto-Pay-API-Signature header value
        
        Returns:
            True if signature is valid
        """
        if not self.api_token:
            logger.warning("MOCK: Skipping CryptoBot webhook signature verification (no API token)")
            return True  # Allow in development
        
        try:
            # CryptoBot uses HMAC-SHA256
            secret_bytes = hashlib.sha256(self.api_token.encode()).digest()
            expected_signature = hmac.new(
                secret_bytes,
                body,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Error verifying CryptoBot webhook signature: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Generate authentication headers."""
        headers = {
            "Crypto-Pay-API-Token": self.api_token or "testnet_token",
            "Content-Type": "application/json"
        }
        return headers


__all__ = ["CryptoBotClient"]
