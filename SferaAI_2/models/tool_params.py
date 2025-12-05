"""
Pydantic models for validating tool parameters.
Ensures type safety and automatic normalization of inputs.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal
import json


class StartPlanParams(BaseModel):
    """Parameters for starting a new plan"""
    plan_type: str = Field(..., min_length=3, max_length=100, description="Plan identifier")
    diagnosis: str = Field(..., min_length=3, max_length=500, description="Reason for starting plan")
    
    @field_validator('plan_type')
    @classmethod
    def validate_plan_type(cls, v: str) -> str:
        """Validate plan type format"""
        # Remove spaces, ensure alphanumeric with - or _
        v = v.strip()
        if not v.replace('-', '').replace('_', '').replace(' ', '').isalnum():
            raise ValueError("Plan type must be alphanumeric with allowed chars: - _")
        return v


class SaveUserNameParams(BaseModel):
    """Parameters for saving user name"""
    name: str = Field(..., min_length=1, max_length=100, description="User's name")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Trim and validate name"""
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class SearchKnowledgeBaseParams(BaseModel):
    """Parameters for knowledge base search"""
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    persona: Literal["partner", "mentor", "psychologist"] = Field(
        default="partner", 
        description="Search persona context"
    )
    filters: str = Field(default="{}", description="JSON filters for search")
    
    @field_validator('filters')
    @classmethod
    def validate_filters(cls, v: str) -> str:
        """Validate JSON format"""
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError:
            raise ValueError("Filters must be valid JSON string")


class CryptoPriceParams(BaseModel):
    """Parameters for cryptocurrency price lookup"""
    symbol: str = Field(..., min_length=3, max_length=20, description="Trading pair symbol")
    
    @field_validator('symbol')
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        """Normalize crypto symbol to Binance format"""
        # Convert to uppercase, remove spaces and slashes
        v = v.upper().replace(" ", "").replace("/", "")
        
        # Common crypto name mappings - do this BEFORE checking for quote currency
        name_mappings = {
            "BITCOIN": "BTC",
            "ETHEREUM": "ETH",
            "SOLANA": "SOL",
            "CARDANO": "ADA",
            "RIPPLE": "XRP",
            "POLKADOT": "DOT",
            "DOGECOIN": "DOGE",
            "AVALANCHE": "AVAX",
        }
        
        # Replace full names with symbols
        for name, symbol in name_mappings.items():
            if v == name:  # Exact match only
                v = symbol
                break
        
        # Auto-append USDT if no quote currency specified
        # Check if it's a short symbol (likely just base currency like BTC, ETH, SOL)
        # Or if it doesn't end with any known quote currency
        quote_currencies = ["USDT", "BUSD", "EUR", "TRY"]
        has_quote = any(v.endswith(q) for q in quote_currencies)
        
        # If symbol is short (3-5 chars) OR doesn't have quote currency, add USDT
        if len(v) <= 5 or not has_quote:
            # But don't add if it already ends with a quote currency
            if not has_quote:
                v += "USDT"
        
        return v


class WeatherParams(BaseModel):
    """Parameters for weather lookup"""
    city: str = Field(..., min_length=2, max_length=100, description="City name")
    
    @field_validator('city')
    @classmethod
    def validate_city(cls, v: str) -> str:
        """Trim city name"""
        v = v.strip()
        if not v:
            raise ValueError("City name cannot be empty")
        return v


class SearchInternetParams(BaseModel):
    """Parameters for internet search"""
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    result_type: Literal["text", "link"] = Field(
        default="text", 
        description="Result format: text for spoken answers, link for URLs"
    )
    multiple: bool = Field(default=False, description="Return multiple results (3) vs single result")


class SearchVideoParams(BaseModel):
    """Parameters for video search"""
    query: str = Field(..., min_length=3, max_length=200, description="Video search query")
    multiple: bool = Field(default=False, description="Return 3 videos vs 1 video")
