import hashlib
import hmac
import json
from urllib.parse import parse_qsl

def validate_telegram_data(init_data: str, bot_token: str) -> dict | None:
    """
    Validates the Telegram WebApp initData string using HMAC-SHA256.
    
    Args:
        init_data: The raw initData string from Telegram WebApp.
        bot_token: The Telegram Bot Token.
        
    Returns:
        A dictionary containing the parsed user data if validation succeeds,
        otherwise None.
    """
    try:
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data:
            return None

        received_hash = parsed_data.pop("hash")
        
        # Data-check-string is a chain of all received fields, sorted alphabetically
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )
        
        # Secret key is the HMAC-SHA256 of the bot token using "WebAppData" as key
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()
        
        # Calculate the hash of the data-check-string
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if calculated_hash == received_hash:
            # Validation successful, return parsed user data
            # The 'user' field is a JSON string, parse it as well
            if 'user' in parsed_data:
                parsed_data['user'] = json.loads(parsed_data['user'])
            return parsed_data
        else:
            return None
            
    except Exception as e:
        print(f"Error validating Telegram data: {e}")
        return None
