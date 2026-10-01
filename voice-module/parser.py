import os
import json
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
import pytz
import re

load_dotenv()

def parse_transaction(text: str) -> list[dict]:
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("ERROR: GROQ_API_KEY not found")
            return []
        
        print(f"[PARSE] Key check: {'✓' if api_key else '✗'}")
        client = Groq(api_key=api_key)
        
        today = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d')
        
        prompt = f"""You are a financial transaction parser.
Extract ALL transactions from the text below.
Return ONLY a raw JSON array. No markdown. No backticks. No explanation.

Each item must have:
{{
  "description": "short description",
  "amount": 200,
  "type": "expense or income",
  "category": "Inventory or Revenue or Utilities or Rent or Personal or Transport or Salaries or Marketing or Maintenance or Food or Other",
  "currency": "INR",
  "date": "{today}",
  "payment_mode": "unknown",
  "confidence_score": 0.85
}}

CRITICAL RULES for type and category:
- If text contains: sold, selling, received, earned, got paid, income, sale, profit, got money
  ΓåÆ type = 'income' AND category = 'Revenue'

- If text contains: bought, purchasing, paid, spent, cost, bill, rent, salary, expense
  ΓåÆ type = 'expense'

- 'sold juice' = income, Revenue
- 'sold cakes' = income, Revenue  
- 'sold anything' = income, Revenue
- NEVER put sold/received items as Food or Inventory

Rules:
- "bought/purchased/paid" = expense
- "sold/received/earned/got" = income
- Convert word amounts: "fifty" = 50, "hundred" = 100
- If multiple transactions in one sentence, return multiple objects

Text: {text}

Return ONLY the JSON array starting with [ and ending with ]"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()
        print(f"[PARSE] Groq response length: {len(raw)} chars")
        print(f"[PARSE] First 200 chars: {raw[:200]}")
        
        # Clean response
        raw = re.sub(r'```json', '', raw)
        raw = re.sub(r'```', '', raw)
        raw = raw.strip()
        
        # Find JSON array in response
        start = raw.find('[')
        end = raw.rfind(']') + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        
        result = json.loads(raw)
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return [result]
        return []
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw response was: {raw}")
        return []
    except Exception as e:
        print(f"Parse error: {e}")
        return []
