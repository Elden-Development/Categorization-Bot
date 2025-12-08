"""
Bank Statement Parser Module

This module handles parsing bank statements from various sources
(CSV, PDF) and extracting transaction data for reconciliation.
"""

import io
import csv
import re
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from PyPDF2 import PdfReader

# Try to import pdfplumber for better table extraction
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("pdfplumber not available, using PyPDF2 for PDF parsing")


class BankStatementParser:
    """
    Parser for bank statements in various formats.

    Supports:
    - CSV files (various bank formats)
    - PDF bank statements (text extraction)
    """

    def __init__(self):
        """Initialize the parser."""
        self.supported_formats = ['csv', 'pdf']
        self.date_formats = [
            '%m/%d/%Y',
            '%Y-%m-%d',
            '%m-%d-%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%m/%d/%y',
            '%d-%m-%Y',
            '%b %d, %Y',
            '%B %d, %Y'
        ]

    def parse_csv(self, file_content: bytes) -> List[Dict]:
        """
        Parse a CSV bank statement.

        Parameters:
        file_content (bytes): CSV file content

        Returns:
        List[Dict]: List of transactions
        """
        try:
            # Try to read CSV with pandas for better handling
            df = pd.read_csv(io.BytesIO(file_content))

            # Try to auto-detect column names
            transactions = self._extract_transactions_from_dataframe(df)

            return transactions

        except Exception as e:
            print(f"Error parsing CSV: {str(e)}")
            # Fallback to manual CSV parsing
            return self._parse_csv_manual(file_content)

    def _parse_csv_manual(self, file_content: bytes) -> List[Dict]:
        """
        Manual CSV parsing as fallback.

        Parameters:
        file_content (bytes): CSV file content

        Returns:
        List[Dict]: List of transactions
        """
        try:
            content = file_content.decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))

            transactions = []
            for row in reader:
                transaction = self._normalize_transaction(row)
                if transaction:
                    transactions.append(transaction)

            return transactions

        except Exception as e:
            print(f"Error in manual CSV parsing: {str(e)}")
            return []

    def _extract_transactions_from_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """
        Extract transactions from a pandas DataFrame.

        Attempts to auto-detect column names for date, description, and amount.

        Parameters:
        df (pd.DataFrame): Bank statement dataframe

        Returns:
        List[Dict]: List of normalized transactions
        """
        transactions = []

        # Detect column names (case-insensitive)
        columns = {col.lower(): col for col in df.columns}

        # Find date column
        date_col = None
        for name in ['date', 'transaction date', 'posting date', 'trans date', 'value date']:
            if name in columns:
                date_col = columns[name]
                break

        # Find description column
        desc_col = None
        for name in ['description', 'memo', 'details', 'transaction details', 'payee', 'merchant']:
            if name in columns:
                desc_col = columns[name]
                break

        # Find amount column (or separate debit/credit)
        amount_col = None
        debit_col = None
        credit_col = None

        for name in ['amount', 'transaction amount', 'value']:
            if name in columns:
                amount_col = columns[name]
                break

        for name in ['debit', 'withdrawal', 'withdrawals', 'debits']:
            if name in columns:
                debit_col = columns[name]
                break

        for name in ['credit', 'deposit', 'deposits', 'credits']:
            if name in columns:
                credit_col = columns[name]
                break

        # Find balance column (optional)
        balance_col = None
        for name in ['balance', 'running balance', 'ending balance']:
            if name in columns:
                balance_col = columns[name]
                break

        # Extract transactions
        for idx, row in df.iterrows():
            try:
                transaction = {}

                # Extract date
                if date_col:
                    transaction['date'] = self._parse_date(str(row[date_col]))

                # Extract description
                if desc_col:
                    transaction['description'] = str(row[desc_col]).strip()

                # Extract amount
                if amount_col:
                    transaction['amount'] = self._parse_amount(row[amount_col])
                elif debit_col and credit_col:
                    # Handle separate debit/credit columns
                    debit = self._parse_amount(row[debit_col]) if pd.notna(row[debit_col]) else 0
                    credit = self._parse_amount(row[credit_col]) if pd.notna(row[credit_col]) else 0

                    if debit > 0:
                        transaction['amount'] = -debit  # Debits are negative
                        transaction['type'] = 'debit'
                    elif credit > 0:
                        transaction['amount'] = credit  # Credits are positive
                        transaction['type'] = 'credit'

                # Extract balance (optional)
                if balance_col and pd.notna(row[balance_col]):
                    transaction['balance'] = self._parse_amount(row[balance_col])

                # Add transaction ID
                transaction['transaction_id'] = f"bank_tx_{idx}"

                # Only add if we have minimum required fields
                if 'date' in transaction and 'description' in transaction and 'amount' in transaction:
                    transactions.append(transaction)

            except Exception as e:
                print(f"Error parsing row {idx}: {str(e)}")
                continue

        return transactions

    def _normalize_transaction(self, row_dict: Dict) -> Optional[Dict]:
        """
        Normalize a transaction dictionary from CSV row.

        Parameters:
        row_dict (dict): Raw CSV row

        Returns:
        Dict or None: Normalized transaction
        """
        try:
            # Try to find date, description, and amount in various formats
            transaction = {}

            # Find date
            for key in row_dict:
                if 'date' in key.lower():
                    transaction['date'] = self._parse_date(row_dict[key])
                    break

            # Find description
            for key in row_dict:
                if any(term in key.lower() for term in ['description', 'memo', 'details', 'payee']):
                    transaction['description'] = row_dict[key].strip()
                    break

            # Find amount
            for key in row_dict:
                if 'amount' in key.lower():
                    transaction['amount'] = self._parse_amount(row_dict[key])
                    break

            return transaction if len(transaction) >= 3 else None

        except Exception as e:
            print(f"Error normalizing transaction: {str(e)}")
            return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse date string to standard format (YYYY-MM-DD).

        Parameters:
        date_str (str): Date string in various formats

        Returns:
        str or None: Date in YYYY-MM-DD format
        """
        if not date_str or date_str.lower() in ['nan', 'none', '']:
            return None

        date_str = str(date_str).strip()

        for fmt in self.date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        print(f"Could not parse date: {date_str}")
        return None

    def _parse_amount(self, amount_str) -> Optional[float]:
        """
        Parse amount string to float.

        Handles:
        - Currency symbols ($, €, £, etc.)
        - Thousands separators (,)
        - Parentheses for negative numbers
        - Credit/debit indicators

        Parameters:
        amount_str: Amount as string or number

        Returns:
        float or None: Parsed amount
        """
        if pd.isna(amount_str) or amount_str == '' or str(amount_str).lower() == 'nan':
            return None

        amount_str = str(amount_str).strip()

        # Check if wrapped in parentheses (negative)
        is_negative = False
        if amount_str.startswith('(') and amount_str.endswith(')'):
            is_negative = True
            amount_str = amount_str[1:-1]

        # Remove currency symbols and spaces
        amount_str = re.sub(r'[$€£¥,\s]', '', amount_str)

        # Check for CR/DR indicators
        if amount_str.upper().endswith('CR'):
            amount_str = amount_str[:-2]
        elif amount_str.upper().endswith('DR'):
            is_negative = True
            amount_str = amount_str[:-2]

        try:
            amount = float(amount_str)
            return -amount if is_negative else amount
        except ValueError:
            print(f"Could not parse amount: {amount_str}")
            return None

    def parse_pdf(self, file_content: bytes) -> List[Dict]:
        """
        Parse a PDF bank statement.

        Uses pdfplumber for table extraction (preferred) or PyPDF2 for text extraction.

        Parameters:
        file_content (bytes): PDF file content

        Returns:
        List[Dict]: List of transactions
        """
        transactions = []

        # Try pdfplumber first (better for tabular data)
        if PDFPLUMBER_AVAILABLE:
            try:
                transactions = self._parse_pdf_with_pdfplumber(file_content)
                if transactions:
                    print(f"pdfplumber extracted {len(transactions)} transactions")
                    return transactions
            except Exception as e:
                print(f"pdfplumber parsing failed: {str(e)}")

        # Fall back to PyPDF2 text extraction
        try:
            pdf_reader = PdfReader(io.BytesIO(file_content))

            # Extract text from all pages
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"

            # Try to extract transactions from text
            transactions = self._extract_transactions_from_text(full_text)
            if transactions:
                print(f"PyPDF2 text extraction found {len(transactions)} transactions")

            return transactions

        except Exception as e:
            print(f"Error parsing PDF: {str(e)}")
            return []

    def _parse_pdf_with_pdfplumber(self, file_content: bytes) -> List[Dict]:
        """
        Parse PDF using pdfplumber for better table extraction.

        Parameters:
        file_content (bytes): PDF file content

        Returns:
        List[Dict]: List of transactions
        """
        transactions = []

        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Try to extract tables first
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        table_transactions = self._process_table(table, page_num)
                        transactions.extend(table_transactions)

                # If no tables found, try text extraction
                if not tables:
                    text = page.extract_text()
                    if text:
                        text_transactions = self._extract_transactions_from_text(text)
                        transactions.extend(text_transactions)

        return transactions

    def _process_table(self, table: List[List], page_num: int) -> List[Dict]:
        """
        Process a table extracted from PDF and convert to transactions.

        Parameters:
        table: 2D list of table cells
        page_num: Page number for transaction IDs

        Returns:
        List[Dict]: List of transactions
        """
        transactions = []

        if not table or len(table) < 2:
            return transactions

        # Try to identify header row
        header = table[0] if table else []
        header_lower = [str(h).lower() if h else '' for h in header]

        # Find column indices
        date_col = None
        desc_col = None
        amount_col = None
        debit_col = None
        credit_col = None

        for i, h in enumerate(header_lower):
            if any(kw in h for kw in ['date', 'posted']):
                date_col = i
            elif any(kw in h for kw in ['description', 'details', 'memo', 'payee']):
                desc_col = i
            elif 'amount' in h or 'value' in h:
                amount_col = i
            elif any(kw in h for kw in ['debit', 'withdrawal', 'withdrawals']):
                debit_col = i
            elif any(kw in h for kw in ['credit', 'deposit', 'deposits']):
                credit_col = i

        # If we couldn't identify columns from header, try to infer from data
        if date_col is None:
            # Look for date-like values in first few rows
            for i in range(min(len(table[0]), 5)):
                for row in table[1:3]:
                    if i < len(row) and row[i]:
                        if self._parse_date(str(row[i])):
                            date_col = i
                            break
                if date_col is not None:
                    break

        # Process data rows (skip header)
        start_row = 1 if any(h for h in header_lower if h) else 0

        for row_idx, row in enumerate(table[start_row:], start=start_row):
            try:
                transaction = {}

                # Extract date
                if date_col is not None and date_col < len(row) and row[date_col]:
                    parsed_date = self._parse_date(str(row[date_col]))
                    if parsed_date:
                        transaction['date'] = parsed_date
                    else:
                        continue  # Skip rows without valid date

                # Extract description
                if desc_col is not None and desc_col < len(row) and row[desc_col]:
                    transaction['description'] = str(row[desc_col]).strip()
                else:
                    # Try to use any non-numeric, non-date column as description
                    for i, cell in enumerate(row):
                        if i != date_col and cell:
                            cell_str = str(cell).strip()
                            if cell_str and not self._parse_amount(cell_str) and not self._parse_date(cell_str):
                                transaction['description'] = cell_str
                                break

                # Extract amount
                if amount_col is not None and amount_col < len(row) and row[amount_col]:
                    transaction['amount'] = self._parse_amount(row[amount_col])
                elif debit_col is not None or credit_col is not None:
                    debit = 0
                    credit = 0
                    if debit_col is not None and debit_col < len(row) and row[debit_col]:
                        debit = self._parse_amount(row[debit_col]) or 0
                    if credit_col is not None and credit_col < len(row) and row[credit_col]:
                        credit = self._parse_amount(row[credit_col]) or 0

                    if debit > 0:
                        transaction['amount'] = -debit
                        transaction['type'] = 'debit'
                    elif credit > 0:
                        transaction['amount'] = credit
                        transaction['type'] = 'credit'
                else:
                    # Try to find amount in any column
                    for i, cell in enumerate(row):
                        if i != date_col and i != desc_col and cell:
                            amt = self._parse_amount(cell)
                            if amt is not None:
                                transaction['amount'] = amt
                                break

                # Add transaction ID
                transaction['transaction_id'] = f'pdf_table_{page_num}_{row_idx}'

                # Only add if we have required fields
                if 'date' in transaction and 'amount' in transaction:
                    if 'description' not in transaction:
                        transaction['description'] = 'Unknown'
                    transactions.append(transaction)

            except Exception as e:
                print(f"Error processing table row {row_idx}: {str(e)}")
                continue

        return transactions

    def _extract_transactions_from_text(self, text: str) -> List[Dict]:
        """
        Extract transactions from bank statement text.

        Uses multiple regex patterns to identify transaction lines from various bank formats.

        Parameters:
        text (str): Full bank statement text

        Returns:
        List[Dict]: List of transactions
        """
        transactions = []
        lines = text.split('\n')

        # Try multiple patterns
        patterns = [
            # Pattern 1: MM/DD Description Debit Credit Balance (common bank format)
            # e.g., "10/02 POS PURCHASE 4.23 65.73"
            r'^(\d{1,2}/\d{1,2})\s+(.+?)\s+([\d,]+\.\d{2})\s*([\d,]+\.\d{2})?\s*([\d,]+\.\d{2})?$',

            # Pattern 2: MM/DD/YYYY or MM/DD/YY format with amount at end
            r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+([-+]?\$?[\d,]+\.\d{2})\s*$',

            # Pattern 3: Date Description Amount (amount can be anywhere)
            r'(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\s+([A-Z][A-Za-z0-9\s\-\*#]+?)\s+([\d,]+\.\d{2})',
        ]

        # First, try the line-by-line approach for tabular data
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Skip header lines
            if any(header in line.lower() for header in ['date', 'description', 'balance', 'debit', 'credit', 'amount', 'transaction']):
                if 'date' in line.lower() and 'description' in line.lower():
                    continue

            # Try Pattern 1: MM/DD with multiple amounts (debit/credit/balance)
            match = re.match(r'^(\d{1,2}/\d{1,2})\s+(.+)', line)
            if match:
                date_str = match.group(1)
                rest = match.group(2)

                # Extract all amounts from the rest of the line
                amounts = re.findall(r'([\d,]+\.\d{2})', rest)

                if amounts:
                    # Remove amounts from description
                    description = re.sub(r'\s*[\d,]+\.\d{2}\s*', ' ', rest).strip()

                    # Determine debit/credit based on position or value
                    # Usually: first amount is debit OR credit, last is balance
                    if len(amounts) >= 1:
                        # Get the first non-balance amount (usually debit or credit)
                        amount = self._parse_amount(amounts[0])

                        # If there are multiple amounts, check context
                        # In many formats: debit is first, credit is second, balance is last
                        transaction_type = 'debit'  # default
                        if len(amounts) >= 2:
                            # If first amount position is after "credit" keyword, it's a credit
                            if 'credit' in description.lower() or 'deposit' in description.lower():
                                transaction_type = 'credit'
                            else:
                                # Check if it looks like a debit (has debit keywords)
                                if any(kw in description.lower() for kw in ['purchase', 'withdrawal', 'debit', 'check', 'payment']):
                                    transaction_type = 'debit'
                                    amount = -abs(amount) if amount else amount

                        # Add current year to date
                        current_year = datetime.now().year
                        full_date = f"{date_str}/{current_year}"

                        transaction = {
                            'transaction_id': f'pdf_tx_{idx}',
                            'date': self._parse_date(full_date),
                            'description': description,
                            'amount': amount,
                            'type': transaction_type
                        }

                        if transaction['date'] and transaction['amount'] is not None:
                            transactions.append(transaction)
                        continue

            # Try other patterns
            for pattern in patterns[1:]:
                match = re.search(pattern, line)
                if match:
                    try:
                        date_str = match.group(1)
                        # Add year if not present
                        if len(date_str) <= 5:  # MM/DD format
                            date_str = f"{date_str}/{datetime.now().year}"

                        transaction = {
                            'transaction_id': f'pdf_tx_{idx}',
                            'date': self._parse_date(date_str),
                            'description': match.group(2).strip(),
                            'amount': self._parse_amount(match.group(3))
                        }

                        if transaction['date'] and transaction['amount'] is not None:
                            transactions.append(transaction)
                            break  # Found a match, move to next line

                    except Exception as e:
                        print(f"Error parsing transaction from PDF line: {str(e)}")
                        continue

        print(f"PDF parser extracted {len(transactions)} transactions")
        return transactions

    def parse(self, file_content: bytes, file_type: str) -> List[Dict]:
        """
        Parse bank statement based on file type.

        Parameters:
        file_content (bytes): File content
        file_type (str): File type ('csv' or 'pdf')

        Returns:
        List[Dict]: List of transactions
        """
        file_type = file_type.lower()

        if file_type == 'csv' or file_type == 'text/csv':
            return self.parse_csv(file_content)
        elif file_type == 'pdf' or file_type == 'application/pdf':
            return self.parse_pdf(file_content)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")


def normalize_vendor_name(name: str) -> str:
    """
    Normalize vendor name for better matching.

    Removes common suffixes, extra spaces, and converts to lowercase.

    Parameters:
    name (str): Vendor name

    Returns:
    str: Normalized name
    """
    if not name:
        return ""

    name = name.lower().strip()

    # Remove common business suffixes
    suffixes = [
        r'\s+inc\.?$',
        r'\s+llc\.?$',
        r'\s+ltd\.?$',
        r'\s+corp\.?$',
        r'\s+co\.?$',
        r'\s+&\s+co\.?$',
        r'\s+company$',
        r'\s+corporation$',
        r'\s+limited$'
    ]

    for suffix in suffixes:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)

    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()

    # Remove special characters except spaces
    name = re.sub(r'[^\w\s]', '', name)

    return name
