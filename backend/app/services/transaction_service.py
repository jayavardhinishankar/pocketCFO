"""
Transaction service layer for database operations.

This module contains all business logic for transaction management,
including CRUD operations, filtering, sorting, and pagination.
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import date
from decimal import Decimal
from supabase import Client
from backend.app.models.transaction_models import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse
)


class TransactionService:
    """
    Service class for transaction database operations.
    
    Handles all interactions with the Supabase database for transactions,
    including filtering, sorting, pagination, and CRUD operations.
    """
    
    TABLE_NAME = "transactions"
    
    def __init__(self, supabase_client: Client):
        """
        Initialize TransactionService.
        
        Args:
            supabase_client: Supabase client instance
        """
        self.db = supabase_client
    
    async def get_transactions(
        self,
        user_id: str,
        search: Optional[str] = None,
        category: Optional[str] = None,
        type_filter: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sort_by: str = "transaction_date",
        order: str = "desc",
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[TransactionResponse], int]:
        """
        Fetch paginated transactions with filters and sorting.

        Search and all filters are applied at the database level
        before counting and pagination.
        """

        valid_sort_fields = [
            "transaction_date",
            "amount",
            "category",
            "is_personal"
        ]

        valid_orders = ["asc", "desc"]

        if sort_by not in valid_sort_fields:
            sort_by = "transaction_date"

        if order.lower() not in valid_orders:
            order = "desc"

        try:
            # Build main query
            query = (
                self.db
                .table(self.TABLE_NAME)
                .select("*")
                .eq("user_id", user_id)
            )

            # Search description OR category at database level
            if search:
                search_value = search.strip()

                if search_value:
                    query = query.or_(
                        f"description.ilike.%{search_value}%,"
                        f"category.ilike.%{search_value}%"
                    )

            # Category filter
            if category:
                query = query.ilike(
                    "category",
                    f"%{category}%"
                )

            # Type filter
            if type_filter:
                query = query.eq(
                    "type",
                    type_filter.lower()
                )

            # Start date filter
            if start_date:
                query = query.gte(
                    "transaction_date",
                    str(start_date)
                )

            # End date filter
            if end_date:
                query = query.lte(
                    "transaction_date",
                    str(end_date)
                )

            # Build count query using the same filters
            count_query = (
                self.db
                .table(self.TABLE_NAME)
                .select("id", count="exact")
                .eq("user_id", user_id)
            )

            # Search filter for count
            if search:
                search_value = search.strip()

                if search_value:
                    count_query = count_query.or_(
                        f"description.ilike.%{search_value}%,"
                        f"category.ilike.%{search_value}%"
                    )

            # Category filter for count
            if category:
                count_query = count_query.ilike(
                    "category",
                    f"%{category}%"
                )

            # Type filter for count
            if type_filter:
                count_query = count_query.eq(
                    "type",
                    type_filter.lower()
                )

            # Start date filter for count
            if start_date:
                count_query = count_query.gte(
                    "transaction_date",
                    str(start_date)
                )

            # End date filter for count
            if end_date:
                count_query = count_query.lte(
                    "transaction_date",
                    str(end_date)
                )

            # Execute count query
            count_response = count_query.execute()

            total_count = (
                count_response.count
                if hasattr(count_response, "count")
                else 0
            )

            # Sort after filtering
            query = query.order(
                sort_by,
                desc=(order.lower() == "desc")
            )

            # Pagination is applied LAST
            offset = (page - 1) * page_size

            query = query.range(
                offset,
                offset + page_size - 1
            )

            # Execute final query
            response = query.execute()

            transactions_data = response.data or []

            # Convert database rows to response models
            transactions = [
                self._add_warning_flag(
                    TransactionResponse(**transaction)
                )
                for transaction in transactions_data
            ]

            return transactions, total_count

        except Exception as e:
            raise Exception(
                f"Error fetching transactions: {str(e)}"
            )
    async def get_transaction_by_id(self, user_id: str, transaction_id: str) -> Optional[TransactionResponse]:
        """
        Fetch a single transaction by ID.
        
        Args:
            user_id: Current user ID (for authorization)
            transaction_id: Transaction ID to fetch
            
        Returns:
            TransactionResponse if found, None otherwise
        """
        try:
            response = (
                self.db.table(self.TABLE_NAME)
                .select("*")
                .eq("id", transaction_id)
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            
            if response.data:
                transaction = TransactionResponse(**response.data)
                transaction = self._add_warning_flag(transaction)
                return transaction
            return None
            
        except Exception as e:
            raise Exception(f"Error fetching transaction: {str(e)}")
    
    async def create_transaction(
        self,
        user_id: str,
        transaction_data: TransactionCreate
    ) -> TransactionResponse:
        """
        Create a new transaction.
        
        Args:
            user_id: User ID for the transaction owner
            transaction_data: Transaction creation data
            
        Returns:
            Created TransactionResponse
            
        Raises:
            Exception: If database operation fails
        """
        try:
            insert_data = {
                "user_id": user_id,
                "description": transaction_data.description,
                "amount": str(transaction_data.amount),
                "type": transaction_data.type,
                "category": transaction_data.category,
                "transaction_date": str(transaction_data.transaction_date),
                "is_personal": transaction_data.is_personal,
            }
            
            response = (
                self.db.table(self.TABLE_NAME)
                .insert(insert_data)
                .execute()
            )
            
            if response.data:
                transaction = TransactionResponse(**response.data[0])
                transaction = self._add_warning_flag(transaction)
                return transaction
            
            raise Exception("Failed to create transaction")
            
        except Exception as e:
            raise Exception(f"Error creating transaction: {str(e)}")
    
    async def update_transaction(
        self,
        user_id: str,
        transaction_id: str,
        update_data: TransactionUpdate
    ) -> TransactionResponse:
        """
        Update an existing transaction.
        
        Args:
            user_id: Current user ID (for authorization)
            transaction_id: Transaction ID to update
            update_data: Partial transaction data to update
            
        Returns:
            Updated TransactionResponse
            
        Raises:
            Exception: If transaction not found or update fails
        """
        try:
            # Build update dictionary with only provided fields
            update_dict = {}
            
            if update_data.description is not None:
                update_dict["description"] = update_data.description
            if update_data.amount is not None:
                update_dict["amount"] = str(update_data.amount)
            if update_data.type is not None:
                update_dict["type"] = update_data.type
            if update_data.category is not None:
                update_dict["category"] = update_data.category
            if update_data.transaction_date is not None:
                update_dict["transaction_date"] = str(update_data.transaction_date)
            if update_data.is_personal is not None:
                update_dict["is_personal"] = update_data.is_personal
            
            if not update_dict:
                # If no fields to update, fetch and return current transaction
                return await self.get_transaction_by_id(user_id, transaction_id)
            
            response = (
                self.db.table(self.TABLE_NAME)
                .update(update_dict)
                .eq("id", transaction_id)
                .eq("user_id", user_id)
                .execute()
            )
            
            if response.data:
                transaction = TransactionResponse(**response.data[0])
                transaction = self._add_warning_flag(transaction)
                return transaction
            
            raise Exception("Transaction not found or not authorized")
            
        except Exception as e:
            raise Exception(f"Error updating transaction: {str(e)}")
    
    async def delete_transaction(self, user_id: str, transaction_id: str) -> bool:
        """
        Delete a transaction.
        
        Args:
            user_id: Current user ID (for authorization)
            transaction_id: Transaction ID to delete
            
        Returns:
            True if deletion successful
            
        Raises:
            Exception: If transaction not found or deletion fails
        """
        try:
            response = (
                self.db.table(self.TABLE_NAME)
                .delete()
                .eq("id", transaction_id)
                .eq("user_id", user_id)
                .execute()
            )
            
            # Supabase returns empty data on successful delete
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting transaction: {str(e)}")
    
    async def get_transactions_for_export(
        self,
        user_id: str,
        search: Optional[str] = None,
        category: Optional[str] = None,
        type_filter: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all matching transactions for export (no pagination).
        
        Args:
            user_id: Current user ID
            search: Search keyword
            category: Filter by category
            type_filter: Filter by type
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            List of transaction dictionaries
        """
        try:
            query = self.db.table(self.TABLE_NAME).select("*").eq("user_id", user_id)
            
            if category:
                query = query.ilike("category", f"%{category}%")
            if type_filter:
                query = query.eq("type", type_filter.lower())
            if start_date:
                query = query.gte("transaction_date", str(start_date))
            if end_date:
                query = query.lte("transaction_date", str(end_date))
            
            # Order by date for export
            query = query.order("transaction_date", desc=True)
            
            response = query.execute()
            transactions_data = response.data
            
            # Apply search filter in memory
            if search:
                search_lower = search.lower()
                transactions_data = [
                    t for t in transactions_data
                    if search_lower in t.get("description", "").lower() or
                       search_lower in t.get("category", "").lower()
                ]
            
            return transactions_data
            
        except Exception as e:
            raise Exception(f"Error fetching transactions for export: {str(e)}")
    
    async def calculate_summary(
        self,
        user_id: str,
        search: Optional[str] = None,
        category: Optional[str] = None,
        type_filter: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate total income and expense for filtered transactions.
        
        Args:
            user_id: Current user ID
            search: Search keyword
            category: Filter by category
            type_filter: Filter by type
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Tuple of (total_income, total_expense)
        """
        transactions = await self.get_transactions_for_export(
            user_id=user_id,
            search=search,
            category=category,
            type_filter=type_filter,
            start_date=start_date,
            end_date=end_date
        )
        
        total_income = Decimal("0")
        total_expense = Decimal("0")
        
        for transaction in transactions:
            amount = Decimal(str(transaction.get("amount", 0)))
            if transaction.get("type") == "income":
                total_income += amount
            else:
                total_expense += amount
        
        return total_income, total_expense
    
    @staticmethod
    def _add_warning_flag(transaction: TransactionResponse) -> TransactionResponse:
        """
        Add personal expense warning flag if applicable.
        
        Args:
            transaction: TransactionResponse object
            
        Returns:
            Transaction with warning flag set if applicable
        """
        if (transaction.type == "expense" and 
            (transaction.category.lower() == "personal" or transaction.is_personal)):
            transaction.warning = "This expense is marked as personal and may affect business profit clarity."
        
        return transaction

