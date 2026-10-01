import os
import logging
import json
from decimal import Decimal

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.app.services.transaction_service import TransactionService
from backend.app.utils.supabase_client import AuthenticatedContext
from backend.app.routes.transactions import get_authenticated_context_dependency


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

EXPENSE_QUERY_PHRASES = (
    "how much did i spend",
    "what did i spend",
    "what are my expenses",
    "total expenses",
    "my spending",
)
INCOME_QUERY_PHRASES = (
    "how much did i earn",
    "how much income did i have",
    "what is my income",
    "total income",
    "my earnings",
)
BALANCE_QUERY_PHRASES = (
    "whats my net profit",
    "what is my net profit",
    "whats my profit",
    "what is my profit",
    "whats my net income",
    "what is my net income",
    "whats my balance in hand",
    "what is my balance in hand",
    "whats my balance",
    "what is my balance",
    "how much money do i have",
    "how much cash do i have",
)
TRANSACTION_HISTORY_PHRASES = (
    "last transaction",
    "latest transaction",
    "recent transaction",
    "most recent transaction",
    "my transactions",
    "show my transactions",
    "transaction history",
    "recent transactions",
)


def normalize_message(message: str) -> str:
    return " ".join(message.lower().replace("'", "").split())


def contains_phrase(message: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in message for phrase in phrases)


def is_net_profit_question(message: str) -> bool:
    return contains_phrase(normalize_message(message), BALANCE_QUERY_PHRASES)


def is_latest_transaction_question(message: str) -> bool:
    return contains_phrase(
        normalize_message(message),
        (
            "last transaction",
            "latest transaction",
            "recent transaction",
            "most recent transaction",
        ),
    )


def is_transaction_question(message: str) -> bool:
    normalized_message = normalize_message(message)
    return (
        contains_phrase(normalized_message, EXPENSE_QUERY_PHRASES)
        or contains_phrase(normalized_message, INCOME_QUERY_PHRASES)
        or contains_phrase(normalized_message, BALANCE_QUERY_PHRASES)
        or contains_phrase(normalized_message, TRANSACTION_HISTORY_PHRASES)
    )


async def get_transaction_context(context: AuthenticatedContext) -> list[dict[str, str]]:
    service = TransactionService(context.client)
    transactions, _ = await service.get_transactions(
        user_id=context.user_id,
        page=1,
        page_size=100,
    )
    return [
        {
            "description": transaction.description,
            "amount": str(transaction.amount),
            "type": transaction.type,
            "category": transaction.category,
            "transaction_date": transaction.transaction_date.isoformat(),
        }
        for transaction in transactions
    ]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value


class ChatResponse(BaseModel):
    success: bool
    response: str


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    context: AuthenticatedContext = Depends(get_authenticated_context_dependency),
) -> ChatResponse:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "message": "Groq service is not configured",
            },
        )

    try:
        transaction_context = None
        profit_summary = None
        latest_transaction = None
        if is_transaction_question(request.message):
            transaction_context = await get_transaction_context(context)
            if not transaction_context:
                return ChatResponse(
                    success=True,
                    response="There is no transaction data available.",
                )
            if is_latest_transaction_question(request.message):
                latest_transaction = max(
                    transaction_context,
                    key=lambda transaction: transaction["transaction_date"],
                )
            if is_net_profit_question(request.message):
                total_income = sum(
                    (
                        Decimal(transaction["amount"])
                        for transaction in transaction_context
                        if transaction["type"] == "income"
                    ),
                    Decimal("0"),
                )
                total_expenses = sum(
                    (
                        Decimal(transaction["amount"])
                        for transaction in transaction_context
                        if transaction["type"] == "expense"
                    ),
                    Decimal("0"),
                )
                profit_summary = {
                    "total_income": str(total_income),
                    "total_expenses": str(total_expenses),
                    "net_profit": str(total_income - total_expenses),
                }

        system_message = "You are a concise and helpful PocketCFO assistant."
        user_message = request.message
        if transaction_context is not None:
            system_message += (
                " Use only the provided transaction data when answering financial "
                "questions. Do not invent or assume any financial data."
            )
            context_label = "Transaction data"
            context_data = transaction_context
            if latest_transaction is not None:
                context_label = "Most recent transaction"
                context_data = latest_transaction
                system_message += (
                    " For a latest-transaction question, report the date, "
                    "description, category, amount, and type from the provided "
                    "transaction."
                )
            elif profit_summary is not None:
                context_label = "Calculated transaction summary"
                context_data = profit_summary
            user_message = (
                f"{request.message}\n\n"
                f"{context_label}:\n"
                f"{json.dumps(context_data)}"
            )

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-oss-20b",
                "messages": [
                    {
                        "role": "system",
                        "content": system_message,
                    },
                    {"role": "user", "content": user_message},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        response_text = response.json()["choices"][0]["message"]["content"]
        return ChatResponse(success=True, response=response_text)
    except requests.exceptions.Timeout:
        logger.exception("Groq request timed out")
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "message": "The Groq service timed out",
            },
        )
    except requests.exceptions.RequestException:
        logger.exception("Groq request error")
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "message": "The Groq service is temporarily unavailable",
            },
        )
    except Exception as exc:
        logger.exception("Unexpected chat error")
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "message": "Unexpected chat error",
            },
        )
