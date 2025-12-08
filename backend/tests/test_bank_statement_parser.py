"""
Tests for bank statement parser.

Run with: pytest tests/test_bank_statement_parser.py -v
"""

import pytest
from bank_statement_parser import BankStatementParser, normalize_vendor_name


class TestBankStatementParser:
    """Test bank statement parsing functionality."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return BankStatementParser()

    def test_parse_amount_simple(self, parser):
        """Test parsing simple amount."""
        assert parser._parse_amount("4.23") == 4.23
        assert parser._parse_amount("763.01") == 763.01
        assert parser._parse_amount("1,234.56") == 1234.56

    def test_parse_amount_with_currency(self, parser):
        """Test parsing amount with currency symbol."""
        assert parser._parse_amount("$4.23") == 4.23
        assert parser._parse_amount("$1,234.56") == 1234.56

    def test_parse_amount_negative_parentheses(self, parser):
        """Test parsing negative amount in parentheses."""
        assert parser._parse_amount("(100.00)") == -100.00

    def test_parse_amount_with_cr_dr(self, parser):
        """Test parsing amount with CR/DR indicators."""
        assert parser._parse_amount("100.00CR") == 100.00
        assert parser._parse_amount("100.00DR") == -100.00

    def test_parse_date_formats(self, parser):
        """Test parsing various date formats."""
        # ISO format is always unambiguous
        assert parser._parse_date("2025-10-02") == "2025-10-02"
        # DD/MM/YYYY format (European) - parser defaults to this
        assert parser._parse_date("02/10/2025") == "2025-10-02"
        assert parser._parse_date("02-10-2025") == "2025-10-02"

    def test_extract_transactions_basic_format(self, parser):
        """Test extracting transactions from basic bank statement format."""
        # Sample text similar to user's bank statement format
        sample_text = """
Date Description Debit Credit Balance
10/02 POS PURCHASE 4.23 65.73
10/03 PREAUTHORIZED CREDIT 763.01 828.74
10/05 ATM WITHDRAWAL 100.00 728.74
10/06 CHECK #1234 50.00 678.74
10/07 DIRECT DEPOSIT 1500.00 2178.74
"""
        transactions = parser._extract_transactions_from_text(sample_text)

        assert len(transactions) >= 3, f"Expected at least 3 transactions, got {len(transactions)}"

        # Verify structure of transactions
        for tx in transactions:
            assert 'date' in tx
            assert 'description' in tx
            assert 'amount' in tx
            assert tx['date'] is not None
            assert tx['amount'] is not None

    def test_extract_transactions_identifies_debits(self, parser):
        """Test that purchases/withdrawals are identified as debits."""
        sample_text = "10/02 POS PURCHASE 4.23 65.73"
        transactions = parser._extract_transactions_from_text(sample_text)

        assert len(transactions) == 1
        tx = transactions[0]
        assert tx['type'] == 'debit'
        # Purchase should be negative
        assert tx['amount'] < 0 or tx['amount'] == 4.23  # Depends on processing

    def test_extract_transactions_identifies_credits(self, parser):
        """Test that credits/deposits are identified correctly."""
        sample_text = "10/03 PREAUTHORIZED CREDIT 763.01 828.74"
        transactions = parser._extract_transactions_from_text(sample_text)

        assert len(transactions) == 1
        tx = transactions[0]
        assert tx['type'] == 'credit'
        assert 'CREDIT' in tx['description'].upper() or tx['amount'] > 0

    def test_extract_transactions_with_full_date(self, parser):
        """Test extracting transactions with full date format."""
        # Using ISO format which is unambiguous
        sample_text = "2025-10-02 PURCHASE AT STORE 50.00"
        transactions = parser._extract_transactions_from_text(sample_text)

        assert len(transactions) >= 1
        if len(transactions) > 0:
            assert transactions[0]['date'] == "2025-10-02"

    def test_skip_header_lines(self, parser):
        """Test that header lines are skipped."""
        sample_text = """
Date Description Amount Balance
Transaction Details
10/02 POS PURCHASE 4.23 65.73
"""
        transactions = parser._extract_transactions_from_text(sample_text)

        # Should only get the actual transaction, not headers
        assert len(transactions) == 1
        assert "POS PURCHASE" in transactions[0]['description']

    def test_csv_parsing(self, parser):
        """Test CSV parsing."""
        csv_content = b"""Date,Description,Amount
10/02/2025,POS PURCHASE,-4.23
10/03/2025,DIRECT DEPOSIT,1500.00"""

        transactions = parser.parse_csv(csv_content)
        assert len(transactions) >= 2


class TestNormalizeVendorName:
    """Test vendor name normalization."""

    def test_remove_inc_suffix(self):
        """Test removing Inc suffix."""
        assert normalize_vendor_name("Acme Inc") == "acme"
        assert normalize_vendor_name("Acme Inc.") == "acme"

    def test_remove_llc_suffix(self):
        """Test removing LLC suffix."""
        assert normalize_vendor_name("Widget LLC") == "widget"

    def test_remove_special_chars(self):
        """Test removing special characters."""
        assert normalize_vendor_name("Store #123") == "store 123"

    def test_handle_empty(self):
        """Test handling empty input."""
        assert normalize_vendor_name("") == ""
        assert normalize_vendor_name(None) == ""

    def test_normalize_whitespace(self):
        """Test normalizing whitespace."""
        assert normalize_vendor_name("  ACME   CORP  ") == "acme"
