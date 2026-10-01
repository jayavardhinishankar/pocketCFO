"""
Transaction routes for FastAPI application.

This module defines all HTTP endpoints for transaction management.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Request, Response
from datetime import date
from typing import Optional
from supabase import Client

from backend.app.models.transaction_models import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    PaginatedTransactionResponse,
    SingleTransactionResponse,
    DeleteTransactionResponse,
    ErrorResponse,
    ExportResponse
)
from backend.app.services.transaction_service import TransactionService
from backend.app.utils.supabase_client import (
    AuthenticatedContext,
    get_authenticated_context,
)
from backend.app.utils.export_utils import (
    generate_csv_content,
    generate_pdf_content,
    get_csv_filename,
    get_pdf_filename
)

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"]
)


def get_authenticated_context_dependency(request: Request) -> AuthenticatedContext:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "message": "A valid Supabase Bearer token is required",
                "error_code": "AUTHENTICATION_REQUIRED",
            },
        )

    try:
        return get_authenticated_context(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "message": "The Supabase session is invalid or expired",
                "error_code": "INVALID_AUTHENTICATION",
            },
        )


def get_transaction_service(
    context: AuthenticatedContext = Depends(get_authenticated_context_dependency)
) -> TransactionService:
    """Create a transaction service using the authenticated request client."""
    return TransactionService(context.client)


def get_user_id(
    context: AuthenticatedContext = Depends(get_authenticated_context_dependency),
) -> str:
    """
    Return the authenticated Supabase user's ID.
    """
    return context.user_id


@router.get("", response_model=PaginatedTransactionResponse)
async def get_transactions(
    service: TransactionService = Depends(get_transaction_service),
    user_id: str = Depends(get_user_id),
    search: Optional[str] = Query(None, description="Search keyword"),
    category: Optional[str] = Query(None, description="Filter by category"),
    type: Optional[str] = Query(None, description="Filter by type (income/expense)"),
    start_date: Optional[date] = Query(None, description="Start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="End date (inclusive)"),
    sort_by: str = Query("transaction_date", description="Sort by: transaction_date, amount, category, or is_personal"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Results per page")
) -> PaginatedTransactionResponse:
    """
    Get all transactions with filtering, sorting, and pagination.
    
    Supports dynamic filtering by:
    - Search keyword (description, category)
    - Category
    - Type (income/expense)
    - Date range
    
    Supports sorting by transaction_date, amount, category, or is_personal.
    
    Args:
        service: Transaction service
        user_id: Current user ID
        search: Search keyword
        category: Category filter
        type: Type filter
        start_date: Start date filter
        end_date: End date filter
        sort_by: Field to sort by
        order: Sort order
        page: Page number
        page_size: Page size
        
    Returns:
        PaginatedTransactionResponse with transactions and metadata
        
    Raises:
        HTTPException: If operation fails
    """
    try:
        transactions, total_count = await service.get_transactions(
            user_id=user_id,
            search=search,
            category=category,
            type_filter=type,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size
        )
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return PaginatedTransactionResponse(
            success=True,
            data=transactions,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            message="Transactions retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to retrieve transactions: {str(e)}",
                "error_code": "TRANSACTION_FETCH_ERROR"
            }
        )


@router.get("/summary")
async def get_transaction_summary(
    service: TransactionService = Depends(get_transaction_service),
    user_id: str = Depends(get_user_id),
    search: Optional[str] = Query(None, description="Search keyword"),
    category: Optional[str] = Query(None, description="Filter by category"),
    type: Optional[str] = Query(None, description="Filter by type (income/expense)"),
    start_date: Optional[date] = Query(None, description="Start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="End date (inclusive)")
):
    """
    Calculate summary totals across all matching transactions.

    This endpoint does not use pagination.
    """
    try:
        total_income, total_expense = await service.calculate_summary(
            user_id=user_id,
            search=search,
            category=category,
            type_filter=type,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "data": {
                "total_revenue": float(total_income),
                "total_expenses": float(total_expense),
                "net_profit": float(total_income - total_expense)
            },
            "message": "Transaction summary calculated successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to calculate transaction summary: {str(e)}",
                "error_code": "TRANSACTION_SUMMARY_ERROR"
            }
        )




@router.post("", response_model=SingleTransactionResponse, status_code=201)
async def create_transaction(
    transaction_data: TransactionCreate,
    service: TransactionService = Depends(get_transaction_service),
    user_id: str = Depends(get_user_id)
) -> SingleTransactionResponse:
    """
    Create a new transaction.
    
    Args:
        transaction_data: Transaction creation data
        service: Transaction service
        user_id: Current user ID
        
    Returns:
        SingleTransactionResponse with created transaction
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        transaction = await service.create_transaction(user_id, transaction_data)
        
        return SingleTransactionResponse(
            success=True,
            data=transaction,
            message="Transaction created successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": f"Failed to create transaction: {str(e)}",
                "error_code": "TRANSACTION_CREATE_ERROR"
            }
        )


@router.put("/{transaction_id:uuid}", response_model=SingleTransactionResponse)
async def update_transaction(
    transaction_id: str,
    update_data: TransactionUpdate,
    service: TransactionService = Depends(get_transaction_service),
    user_id: str = Depends(get_user_id)
) -> SingleTransactionResponse:
    """
    Update a transaction.
    
    Args:
        transaction_id: Transaction ID
        update_data: Partial transaction data to update
        service: Transaction service
        user_id: Current user ID
        
    Returns:
        SingleTransactionResponse with updated transaction
        
    Raises:
        HTTPException: If transaction not found or update fails
    """
    try:
        # Check if transaction exists
        existing = await service.get_transaction_by_id(user_id, transaction_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": "Transaction not found",
                    "error_code": "TRANSACTION_NOT_FOUND"
                }
            )
        
        transaction = await service.update_transaction(user_id, transaction_id, update_data)
        
        return SingleTransactionResponse(
            success=True,
            data=transaction,
            message="Transaction updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": f"Failed to update transaction: {str(e)}",
                "error_code": "TRANSACTION_UPDATE_ERROR"
            }
        )


@router.delete("/{transaction_id:uuid}", response_model=DeleteTransactionResponse)
async def delete_transaction(
    transaction_id: str,
    service: TransactionService = Depends(get_transaction_service),
    user_id: str = Depends(get_user_id)
) -> DeleteTransactionResponse:
    """
    Delete a transaction.
    
    Args:
        transaction_id: Transaction ID
        service: Transaction service
        user_id: Current user ID
        
    Returns:
        DeleteTransactionResponse with success status
        
    Raises:
        HTTPException: If transaction not found or deletion fails
    """
    try:
        # Check if transaction exists
        existing = await service.get_transaction_by_id(user_id, transaction_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": "Transaction not found",
                    "error_code": "TRANSACTION_NOT_FOUND"
                }
            )
        
        await service.delete_transaction(user_id, transaction_id)
        
        return DeleteTransactionResponse(
            success=True,
            message="Transaction deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "message": f"Failed to delete transaction: {str(e)}",
                "error_code": "TRANSACTION_DELETE_ERROR"
            }
        )


@router.get("/export/csv", response_class=Response)
async def export_csv(
    service: TransactionService = Depends(get_transaction_service),
    user_id: str = Depends(get_user_id),
    search: Optional[str] = Query(None, description="Search keyword"),
    category: Optional[str] = Query(None, description="Filter by category"),
    type: Optional[str] = Query(None, description="Filter by type"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date")
) -> Response:
    """
    Export filtered transactions to CSV.
    
    Supports same filters as GET /transactions endpoint.
    
    Args:
        service: Transaction service
        user_id: Current user ID
        search: Search keyword
        category: Category filter
        type: Type filter
        start_date: Start date filter
        end_date: End date filter
        
    Returns:
        CSV file as downloadable response
        
    Raises:
        HTTPException: If export fails
    """
    try:
        transactions = await service.get_transactions_for_export(
            user_id=user_id,
            search=search,
            category=category,
            type_filter=type,
            start_date=start_date,
            end_date=end_date
        )
        
        if not transactions:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": "No transactions found to export",
                    "error_code": "NO_DATA_FOR_EXPORT"
                }
            )
        
        csv_content = generate_csv_content(transactions)
        filename = get_csv_filename()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to export CSV: {str(e)}",
                "error_code": "EXPORT_CSV_ERROR"
            }
        )


@router.get("/export/pdf", response_class=Response)
async def export_pdf(
    service: TransactionService = Depends(get_transaction_service),
    user_id: str = Depends(get_user_id),
    search: Optional[str] = Query(None, description="Search keyword"),
    category: Optional[str] = Query(None, description="Filter by category"),
    type: Optional[str] = Query(None, description="Filter by type"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date")
) -> Response:
    """
    Export filtered transactions to PDF with summary.
    
    Supports same filters as GET /transactions endpoint.
    PDF includes transaction details and summary (income, expense, net profit).
    
    Args:
        service: Transaction service
        user_id: Current user ID
        search: Search keyword
        category: Category filter
        type: Type filter
        start_date: Start date filter
        end_date: End date filter
        
    Returns:
        PDF file as downloadable response
        
    Raises:
        HTTPException: If export fails
    """
    try:
        transactions = await service.get_transactions_for_export(
            user_id=user_id,
            search=search,
            category=category,
            type_filter=type,
            start_date=start_date,
            end_date=end_date
        )
        
        if not transactions:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": "No transactions found to export",
                    "error_code": "NO_DATA_FOR_EXPORT"
                }
            )
        
        pdf_content = generate_pdf_content(transactions)
        filename = get_pdf_filename()
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Failed to export PDF: {str(e)}",
                "error_code": "EXPORT_PDF_ERROR"
            }
        )
