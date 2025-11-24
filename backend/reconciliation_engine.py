"""
Reconciliation Engine Module

This module handles reconciliation of invoices/documents against bank statements
using intelligent matching algorithms.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
from bank_statement_parser import normalize_vendor_name


class ReconciliationEngine:
    """
    Engine for reconciling documents with bank statements.

    Uses multi-factor matching:
    - Vendor name matching (fuzzy)
    - Amount matching (exact or tolerance)
    - Date matching (exact or range)
    """

    def __init__(
        self,
        name_threshold: int = 80,
        amount_tolerance: float = 0.01,
        date_range_days: int = 3
    ):
        """
        Initialize the reconciliation engine.

        Parameters:
        name_threshold (int): Minimum fuzzy match score for names (0-100)
        amount_tolerance (float): Maximum difference for amount matching
        date_range_days (int): Maximum days difference for date matching
        """
        self.name_threshold = name_threshold
        self.amount_tolerance = amount_tolerance
        self.date_range_days = date_range_days

    def reconcile(
        self,
        documents: List[Dict],
        bank_transactions: List[Dict],
        auto_match_threshold: int = 90
    ) -> Dict:
        """
        Reconcile documents against bank transactions.

        Parameters:
        documents (List[Dict]): List of processed documents (invoices, etc.)
        bank_transactions (List[Dict]): List of bank statement transactions
        auto_match_threshold (int): Score threshold for automatic matching (0-100)

        Returns:
        Dict: Reconciliation results with matches, unmatched, and suggestions
        """
        results = {
            "matched": [],
            "unmatched_documents": [],
            "unmatched_transactions": [],
            "suggested_matches": [],
            "summary": {
                "total_documents": len(documents),
                "total_transactions": len(bank_transactions),
                "matched_count": 0,
                "unmatched_documents_count": 0,
                "unmatched_transactions_count": 0,
                "suggested_matches_count": 0
            }
        }

        # Track which transactions have been matched
        matched_transaction_ids = set()
        matched_document_ids = set()

        # First pass: Find high-confidence matches
        for doc in documents:
            best_match = None
            best_score = 0

            for tx in bank_transactions:
                if tx.get('transaction_id') in matched_transaction_ids:
                    continue  # Already matched

                # Calculate match score
                match_result = self._calculate_match_score(doc, tx)

                if match_result['total_score'] > best_score:
                    best_score = match_result['total_score']
                    best_match = {
                        'transaction': tx,
                        'score_details': match_result
                    }

            # Auto-match if score is high enough
            if best_score >= auto_match_threshold:
                match_entry = {
                    "document": doc,
                    "transaction": best_match['transaction'],
                    "match_score": best_score,
                    "match_details": best_match['score_details'],
                    "match_type": "automatic",
                    "confidence": "high" if best_score >= 95 else "medium"
                }

                results["matched"].append(match_entry)
                matched_transaction_ids.add(best_match['transaction']['transaction_id'])
                matched_document_ids.add(doc.get('document_id', id(doc)))

            # Suggest if score is moderate
            elif best_score >= self.name_threshold:
                suggestion = {
                    "document": doc,
                    "transaction": best_match['transaction'],
                    "match_score": best_score,
                    "match_details": best_match['score_details'],
                    "requires_review": True,
                    "confidence": "low"
                }

                results["suggested_matches"].append(suggestion)

        # Find unmatched documents and transactions
        for doc in documents:
            doc_id = doc.get('document_id', id(doc))
            if doc_id not in matched_document_ids:
                results["unmatched_documents"].append(doc)

        for tx in bank_transactions:
            if tx.get('transaction_id') not in matched_transaction_ids:
                # Try to find possible matches for this transaction
                possible_matches = self._find_possible_matches_for_transaction(
                    tx,
                    documents,
                    matched_document_ids
                )

                results["unmatched_transactions"].append({
                    "transaction": tx,
                    "possible_matches": possible_matches
                })

        # Update summary
        results["summary"]["matched_count"] = len(results["matched"])
        results["summary"]["unmatched_documents_count"] = len(results["unmatched_documents"])
        results["summary"]["unmatched_transactions_count"] = len(results["unmatched_transactions"])
        results["summary"]["suggested_matches_count"] = len(results["suggested_matches"])

        # Calculate reconciliation percentage
        if results["summary"]["total_documents"] > 0:
            results["summary"]["reconciliation_rate"] = round(
                (results["summary"]["matched_count"] / results["summary"]["total_documents"]) * 100,
                2
            )
        else:
            results["summary"]["reconciliation_rate"] = 0

        return results

    def _calculate_match_score(self, document: Dict, transaction: Dict) -> Dict:
        """
        Calculate match score between a document and a bank transaction.

        Uses weighted scoring:
        - Name match: 50%
        - Amount match: 35%
        - Date match: 15%

        Parameters:
        document (Dict): Document data
        transaction (Dict): Bank transaction data

        Returns:
        Dict: Match score details
        """
        scores = {
            "name_score": 0,
            "amount_score": 0,
            "date_score": 0,
            "total_score": 0,
            "details": {}
        }

        # 1. Name matching (50% weight)
        doc_vendor = self._extract_vendor_name(document)
        tx_description = transaction.get('description', '')

        if doc_vendor and tx_description:
            name_match = self._fuzzy_match_names(doc_vendor, tx_description)
            scores["name_score"] = name_match
            scores["details"]["name_match"] = {
                "document_vendor": doc_vendor,
                "transaction_description": tx_description,
                "similarity": name_match
            }

        # 2. Amount matching (35% weight)
        doc_amount = self._extract_amount(document)
        tx_amount = transaction.get('amount')

        if doc_amount is not None and tx_amount is not None:
            # Bank transactions may be negative for debits
            tx_amount_abs = abs(tx_amount)
            amount_match = self._match_amounts(doc_amount, tx_amount_abs)
            scores["amount_score"] = amount_match
            scores["details"]["amount_match"] = {
                "document_amount": doc_amount,
                "transaction_amount": tx_amount_abs,
                "difference": abs(doc_amount - tx_amount_abs),
                "match": amount_match == 100
            }

        # 3. Date matching (15% weight)
        doc_date = self._extract_date(document)
        tx_date = transaction.get('date')

        if doc_date and tx_date:
            date_match = self._match_dates(doc_date, tx_date)
            scores["date_score"] = date_match
            scores["details"]["date_match"] = {
                "document_date": doc_date,
                "transaction_date": tx_date,
                "days_difference": self._date_difference_days(doc_date, tx_date),
                "match": date_match == 100
            }

        # Calculate weighted total score
        scores["total_score"] = round(
            (scores["name_score"] * 0.50) +
            (scores["amount_score"] * 0.35) +
            (scores["date_score"] * 0.15)
        )

        return scores

    def _fuzzy_match_names(self, name1: str, name2: str) -> int:
        """
        Fuzzy match two names/descriptions.

        Uses multiple fuzzy matching techniques for best results.

        Parameters:
        name1 (str): First name
        name2 (str): Second name

        Returns:
        int: Match score (0-100)
        """
        # Normalize names
        norm1 = normalize_vendor_name(name1)
        norm2 = normalize_vendor_name(name2)

        # Try multiple fuzzy matching algorithms
        ratio = fuzz.ratio(norm1, norm2)
        partial_ratio = fuzz.partial_ratio(norm1, norm2)
        token_sort_ratio = fuzz.token_sort_ratio(norm1, norm2)
        token_set_ratio = fuzz.token_set_ratio(norm1, norm2)

        # Return the best score
        return max(ratio, partial_ratio, token_sort_ratio, token_set_ratio)

    def _match_amounts(self, amount1: float, amount2: float) -> int:
        """
        Match two amounts.

        Returns 100 if exact match or within tolerance, 0 otherwise.

        Parameters:
        amount1 (float): First amount
        amount2 (float): Second amount

        Returns:
        int: Match score (0 or 100)
        """
        difference = abs(amount1 - amount2)

        if difference <= self.amount_tolerance:
            return 100
        else:
            # Partial credit for close matches
            # If within 1%, give some score
            percent_diff = (difference / max(amount1, amount2)) * 100
            if percent_diff <= 1.0:
                return 80
            elif percent_diff <= 5.0:
                return 50
            else:
                return 0

    def _match_dates(self, date1_str: str, date2_str: str) -> int:
        """
        Match two dates.

        Returns 100 if exact match or within range, 0 otherwise.

        Parameters:
        date1_str (str): First date (YYYY-MM-DD)
        date2_str (str): Second date (YYYY-MM-DD)

        Returns:
        int: Match score (0 or 100)
        """
        try:
            date1 = datetime.strptime(date1_str, '%Y-%m-%d')
            date2 = datetime.strptime(date2_str, '%Y-%m-%d')

            diff_days = abs((date1 - date2).days)

            if diff_days == 0:
                return 100
            elif diff_days <= self.date_range_days:
                # Partial credit for dates within range
                score = 100 - (diff_days * 20)  # Reduce by 20 points per day
                return max(score, 50)
            else:
                return 0

        except Exception as e:
            print(f"Error matching dates: {str(e)}")
            return 0

    def _date_difference_days(self, date1_str: str, date2_str: str) -> int:
        """Calculate difference in days between two dates."""
        try:
            date1 = datetime.strptime(date1_str, '%Y-%m-%d')
            date2 = datetime.strptime(date2_str, '%Y-%m-%d')
            return abs((date1 - date2).days)
        except:
            return 999

    def _extract_vendor_name(self, document: Dict) -> str:
        """
        Extract vendor name from document.

        Parameters:
        document (Dict): Document data

        Returns:
        str: Vendor name
        """
        # Try various paths to find vendor name
        vendor_name = None

        if 'documentMetadata' in document:
            source = document['documentMetadata'].get('source', {})
            vendor_name = source.get('name')

        if not vendor_name and 'partyInformation' in document:
            vendor = document['partyInformation'].get('vendor', {})
            vendor_name = vendor.get('name')

        if not vendor_name and 'companyName' in document:
            vendor_name = document.get('companyName')

        return vendor_name or ""

    def _extract_amount(self, document: Dict) -> Optional[float]:
        """
        Extract total amount from document.

        Parameters:
        document (Dict): Document data

        Returns:
        float or None: Total amount
        """
        # Try various paths to find amount
        amount = None

        if 'financialData' in document:
            amount = document['financialData'].get('totalAmount')

        if not amount and 'totalAmount' in document:
            amount = document.get('totalAmount')

        # Convert to float if string
        if isinstance(amount, str):
            try:
                amount = float(amount.replace(',', '').replace('$', ''))
            except:
                amount = None

        return amount

    def _extract_date(self, document: Dict) -> Optional[str]:
        """
        Extract date from document.

        Parameters:
        document (Dict): Document data

        Returns:
        str or None: Date in YYYY-MM-DD format
        """
        # Try various paths to find date
        date_str = None

        if 'documentMetadata' in document:
            date_str = document['documentMetadata'].get('documentDate')

        if not date_str and 'documentDate' in document:
            date_str = document.get('documentDate')

        return date_str

    def _find_possible_matches_for_transaction(
        self,
        transaction: Dict,
        documents: List[Dict],
        exclude_document_ids: set,
        top_n: int = 3
    ) -> List[Dict]:
        """
        Find possible document matches for an unmatched transaction.

        Parameters:
        transaction (Dict): Bank transaction
        documents (List[Dict]): All documents
        exclude_document_ids (set): Document IDs to exclude
        top_n (int): Number of top matches to return

        Returns:
        List[Dict]: Top possible matches
        """
        possible_matches = []

        for doc in documents:
            doc_id = doc.get('document_id', id(doc))
            if doc_id in exclude_document_ids:
                continue

            match_result = self._calculate_match_score(doc, transaction)

            if match_result['total_score'] >= 50:  # Minimum threshold for suggestions
                possible_matches.append({
                    "document": doc,
                    "score": match_result['total_score'],
                    "details": match_result
                })

        # Sort by score and return top N
        possible_matches.sort(key=lambda x: x['score'], reverse=True)
        return possible_matches[:top_n]

    def manual_match(
        self,
        document: Dict,
        transaction: Dict
    ) -> Dict:
        """
        Manually match a document with a transaction.

        Provides detailed match information for user review.

        Parameters:
        document (Dict): Document to match
        transaction (Dict): Transaction to match

        Returns:
        Dict: Match details
        """
        match_score = self._calculate_match_score(document, transaction)

        return {
            "document": document,
            "transaction": transaction,
            "match_score": match_score['total_score'],
            "match_details": match_score,
            "match_type": "manual",
            "confidence": "user_verified"
        }
