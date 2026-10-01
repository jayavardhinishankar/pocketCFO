import os
import re
from typing import List, Tuple

from groq import Groq


CATEGORY_RULES = {
    "Revenue": [
        "sold", "received", "earned", "sale", "payment received",
        "got paid", "income", "profit"
    ],
    "Personal": [
        "myself", "personal", "family", "groceries for home",
        "medical", "clothes", "shoes", "movie", "outing", "personal use"
    ],
    "Inventory": [
        "bought", "purchased", "flour", "rice", "vegetables",
        "stock", "supplies", "raw material", "ingredients", "wholesale"
    ],
    "Utilities": [
        "electricity", "wifi", "internet", "water bill", "gas bill",
        "phone bill", "recharge", "broadband", "EB bill"
    ],
    "Rent": [
        "rent", "shop rent", "office rent", "lease", "rental"
    ],
    "Salaries": [
        "salary", "paid staff", "paid employee", "wages",
        "paid worker", "delivery boy", "helper", "staff payment"
    ],
    "Transport": [
        "uber", "auto", "petrol", "fuel", "travel", "cab",
        "bus", "transport", "delivery charge", "shipping"
    ],
    "Marketing": [
        "ad", "advertisement", "promotion", "poster", "pamphlet",
        "social media", "banner", "flyer"
    ],
    "Maintenance": [
        "repair", "fixed", "maintenance", "service", "cleaning",
        "paint", "plumber", "electrician"
    ],
    "Food": [
        "lunch", "dinner", "breakfast", "tea", "coffee",
        "snacks", "hotel", "restaurant", "meals", "food"
    ],
    "Other": []
}


VALID_CATEGORIES = set(CATEGORY_RULES.keys())


def get_category_from_groq(description: str) -> str:
    """
    Use Groq AI to categorize a transaction.
    Returns only a valid category.
    """

    try:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            return "Other"

        client = Groq(api_key=api_key)

        prompt = (
            "Categorize this business transaction into EXACTLY one "
            "of these categories: Revenue, Inventory, Utilities, Rent, "
            "Salaries, Transport, Marketing, Maintenance, Personal, "
            "Food, Other.\n\n"
            f"Transaction: '{description}'\n\n"
            "Reply with ONLY the category name. "
            "Do not provide an explanation."
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        text = response.choices[0].message.content

        if not text:
            return "Other"

        category = text.strip()

        # Strict validation of AI output
        if category not in VALID_CATEGORIES:
            return "Other"

        return category

    except Exception as e:
        print("Groq categorization failed:", e)
        return "Other"


def get_category_from_rules(description: str) -> Tuple[str, float]:
    """
    First try local keyword rules.
    If no rule matches, use Groq.
    """

    if not description:
        return ("Other", 0.50)

    desc = description.lower().strip()

    # Local rule-based categorization
    for category, keywords in CATEGORY_RULES.items():

        if not keywords:
            continue

        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"

            if re.search(pattern, desc):
                return (category, 0.90)

    # No rule matched -> use Groq
    category = get_category_from_groq(description)

    if category in VALID_CATEGORIES:
        return (category, 0.75)

    return ("Other", 0.50)


def apply_categorization(transactions: List[dict]) -> List[dict]:
    """
    Categorize and validate every transaction before saving.
    """

    updated = []

    for tx in transactions:

        if not isinstance(tx, dict):
            continue

        description = tx.get("description", "")

        category, score = get_category_from_rules(description)

        # Strict final validation
        if category not in VALID_CATEGORIES:
            category = "Other"

        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.50

        # Keep confidence between 0 and 1
        score = max(0.0, min(1.0, score))

        tx["category"] = category
        tx["confidence_score"] = score

        updated.append(tx)

    return updated