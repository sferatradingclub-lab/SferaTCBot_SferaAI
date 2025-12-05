"""
Utility to convert numbers to Russian text for better TTS pronunciation.
Converts digits like "90000" to "девяносто тысяч" so Gemini speaks them in Russian.
"""

import re
from typing import Union


def number_to_russian(n: int) -> str:
    """
    Convert integer to Russian text.
    Examples:
        90000 → "девяносто тысяч"
        2025 → "две тысячи двадцать пять"
        1 → "один"
    """
    if n == 0:
        return "ноль"
    
    # Negative numbers
    if n < 0:
        return "минус " + number_to_russian(-n)
    
    # Basic numbers 0-19
    ones = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять",
            "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
            "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
    
    # Tens 20-90
    tens = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
    
    # Hundreds
    hundreds = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот"]
    
    # Thousands (with proper declension)
    def thousands_form(n: int) -> str:
        if n % 10 == 1 and n % 100 != 11:
            return "тысяча"
        elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
            return "тысячи"
        else:
            return "тысяч"
    
    # Millions
    def millions_form(n: int) -> str:
        if n % 10 == 1 and n % 100 != 11:
            return "миллион"
        elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
            return "миллиона"
        else:
            return "миллионов"
    
    # Billions
    def billions_form(n: int) -> str:
        if n % 10 == 1 and n % 100 != 11:
            return "миллиард"
        elif 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
            return "миллиарда"
        else:
            return "миллиардов"
    
    def convert_group(n: int, feminine: bool = False) -> str:
        """Convert 1-999 to text. If feminine=True, use "одна/две" instead of "один/два"."""
        if n == 0:
            return ""
        
        result = []
        
        # Hundreds
        h = n // 100
        if h > 0:
            result.append(hundreds[h])
        
        # Tens and ones
        remainder = n % 100
        if 10 <= remainder <= 19:
            result.append(ones[remainder])
        else:
            t = remainder // 10
            o = remainder % 10
            if t > 0:
                result.append(tens[t])
            if o > 0:
                if feminine and o == 1:
                    result.append("одна")
                elif feminine and o == 2:
                    result.append("две")
                else:
                    result.append(ones[o])
        
        return " ".join(result)
    
    # Split into groups
    billions = n // 1_000_000_000
    millions = (n % 1_000_000_000) // 1_000_000
    thousands = (n % 1_000_000) // 1_000
    remainder = n % 1_000
    
    parts = []
    
    if billions > 0:
        parts.append(convert_group(billions))
        parts.append(billions_form(billions))
    
    if millions > 0:
        parts.append(convert_group(millions))
        parts.append(millions_form(millions))
    
    if thousands > 0:
        parts.append(convert_group(thousands, feminine=True))
        parts.append(thousands_form(thousands))
    
    if remainder > 0:
        parts.append(convert_group(remainder))
    
    return " ".join(parts)


def price_to_russian(price: float, currency: str = "USDT") -> str:
    """
    Convert price to Russian text with currency.
    Examples:
        90000.0, "USDT" → "девяносто тысяч долларов"
        0.0025, "USDT" → "ноль целых двадцать пять десятитысячных долларов"
    """
    # Map currency codes to Russian
    currency_map = {
        "USDT": "долларов",
        "USD": "долларов",
        "BTC": "биткоинов",
        "ETH": "эфириумов",
        "TRY": "лир",
        "EUR": "евро",
        "RUB": "рублей"
    }
    
    currency_text = currency_map.get(currency.upper(), currency.lower())
    
    # Handle small decimals (< 1)
    if price < 1:
        # For very small numbers, use text representation
        price_str = f"{price:.6f}".rstrip('0').rstrip('.')
        return f"{price_str} {currency_text}"
    
    # Handle large numbers
    if price >= 1:
        integer_part = int(price)
        decimal_part = round((price - integer_part) * 100)
        
        integer_text = number_to_russian(integer_part)
        
        if decimal_part > 0:
            decimal_text = number_to_russian(decimal_part)
            # Add currency with proper declension
            if currency == "USDT" or currency == "USD":
                return f"{integer_text} {currency_text} {decimal_text} центов"
            else:
                return f"{integer_text} целых {decimal_text} сотых {currency_text}"
        else:
            return f"{integer_text} {currency_text}"


def replace_numbers_in_text(text: str) -> str:
    """
    Replace all standalone numbers in text with Russian words.
    Examples:
        "Bitcoin 90000 USD" → "Bitcoin девяносто тысяч USD"
        "Video 2025 year" → "Video две тысячи двадцать пять year"
    """
    def replace_match(match):
        num_str = match.group(0)
        # Remove commas/spaces from number
        num_str_clean = num_str.replace(',', '').replace(' ', '')
        try:
            num = int(num_str_clean)
            return number_to_russian(num)
        except ValueError:
            return num_str
    
    # Match numbers (including those with commas/spaces like "90,000" or "90 000")
    pattern = r'\b\d{1,3}(?:[,\s]\d{3})*\b|\b\d+\b'
    return re.sub(pattern, replace_match, text)


# Quick tests
if __name__ == "__main__":
    print("Testing number_to_russian:")
    print(f"90000 → {number_to_russian(90000)}")
    print(f"2025 → {number_to_russian(2025)}")
    print(f"1 → {number_to_russian(1)}")
    print(f"42 → {number_to_russian(42)}")
    print(f"100 → {number_to_russian(100)}")
    print(f"1234567 → {number_to_russian(1234567)}")
    
    print("\nTesting price_to_russian:")
    print(f"90000 USDT → {price_to_russian(90000, 'USDT')}")
    print(f"0.0025 USDT → {price_to_russian(0.0025, 'USDT')}")
    print(f"42.50 USD → {price_to_russian(42.50, 'USD')}")
    
    print("\nTesting replace_numbers_in_text:")
    print(f"'Bitcoin 90000 USD' → '{replace_numbers_in_text('Bitcoin 90000 USD')}'")
    print(f"'Video 2025 year' → '{replace_numbers_in_text('Video 2025 year')}'")
