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
            '%Y-%m-%d',      # 2025-09-06
            '%d/%m/%Y',      # 12/01/2025
            '%m/%d/%Y',      # 01/12/2025
            '%d-%m-%Y',      # 12-01-2025
            '%m-%d-%Y',      # 01-12-2025
            '%Y/%m/%d',      # 2025/01/12
            '%m/%d/%y',      # 01/12/25
            '%d/%m/%y',      # 12/01/25
            '%d %B %Y',      # 1 February 2025
            '%d %b %Y',      # 1 Feb 2025
            '%B %d, %Y',     # February 1, 2025
            '%b %d, %Y',     # Feb 1, 2025
            '%d %B',         # 1 February (no year)
            '%d %b',         # 1 Feb (no year)
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
        current_year = datetime.now().year

        for fmt in self.date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # If year is 1900 (default when no year in format), use current year
                if dt.year == 1900:
                    dt = dt.replace(year=current_year)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # Try adding current year for short date formats
        for short_fmt, full_fmt in [
            ('%m/%d', '%m/%d/%Y'),
            ('%d/%m', '%d/%m/%Y'),
            ('%m-%d', '%m-%d-%Y'),
            ('%d-%m', '%d-%m-%Y'),
        ]:
            try:
                dt = datetime.strptime(f"{date_str}/{current_year}", f"{short_fmt}/%Y")
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
        total_text_length = 0

        # Try pdfplumber first (better for tabular data)
        if PDFPLUMBER_AVAILABLE:
            try:
                transactions, text_len = self._parse_pdf_with_pdfplumber_v2(file_content)
                total_text_length = text_len
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
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

            total_text_length = len(full_text)
            print(f"[PyPDF2] Extracted {total_text_length} characters of text")

            if total_text_length < 50:
                print("[PyPDF2] WARNING: Very little text extracted - PDF may be image-based/scanned")

            # Try to extract transactions from text
            transactions = self._extract_transactions_from_text(full_text)
            if transactions:
                print(f"PyPDF2 text extraction found {len(transactions)} transactions")

            return transactions

        except Exception as e:
            print(f"Error parsing PDF: {str(e)}")
            return []

    def _parse_pdf_with_pdfplumber_v2(self, file_content: bytes) -> tuple:
        """
        Parse PDF using pdfplumber, returns transactions and text length.
        """
        table_transactions = []
        text_transactions = []
        total_text_length = 0

        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            print(f"[pdfplumber] PDF has {len(pdf.pages)} pages")

            for page_num, page in enumerate(pdf.pages):
                # Try to extract tables
                tables = page.extract_tables()
                print(f"[pdfplumber] Page {page_num}: found {len(tables) if tables else 0} tables")

                if tables:
                    for table_idx, table in enumerate(tables):
                        if table and len(table) > 1:  # Need at least 2 rows
                            print(f"[pdfplumber] Table {table_idx} has {len(table)} rows")
                            if table[0]:
                                print(f"[pdfplumber] First row sample: {str(table[0])[:200]}")
                            page_table_txns = self._process_table(table, page_num)
                            print(f"[pdfplumber] Extracted {len(page_table_txns)} transactions from table {table_idx}")
                            table_transactions.extend(page_table_txns)

                # Also try text extraction
                text = page.extract_text()
                if text:
                    total_text_length += len(text)
                    # Show first 500 chars of text for debugging
                    if page_num == 0:
                        print(f"[pdfplumber] Page {page_num} text ({len(text)} chars): {text[:500].replace(chr(10), ' | ')}")

                    page_text_txns = self._extract_transactions_from_text(text)
                    print(f"[pdfplumber] Extracted {len(page_text_txns)} transactions from text on page {page_num}")
                    text_transactions.extend(page_text_txns)

        print(f"[pdfplumber] Total text extracted: {total_text_length} characters")
        print(f"[pdfplumber] Table transactions: {len(table_transactions)}, Text transactions: {len(text_transactions)}")

        if total_text_length < 100:
            print("[pdfplumber] WARNING: Very little text - PDF may be scanned/image-based")

        # Use whichever method found more transactions
        if len(text_transactions) > len(table_transactions):
            print(f"[pdfplumber] Using text extraction results ({len(text_transactions)} > {len(table_transactions)})")
            return text_transactions, total_text_length
        else:
            print(f"[pdfplumber] Using table extraction results ({len(table_transactions)} >= {len(text_transactions)})")
            return table_transactions, total_text_length

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

        if not table or len(table) < 1:
            return transactions

        print(f"[table_process] Processing table with {len(table)} rows, {len(table[0]) if table else 0} cols")

        # Try to identify header row
        header = table[0] if table else []
        header_lower = [str(h).lower().strip() if h else '' for h in header]

        # Find column indices from header
        date_col = None
        desc_col = None
        amount_col = None
        debit_col = None
        credit_col = None
        type_col = None
        balance_col = None

        for i, h in enumerate(header_lower):
            if not h:
                continue
            if date_col is None and any(kw in h for kw in ['date', 'posted', 'trans']):
                date_col = i
            elif desc_col is None and any(kw in h for kw in ['description', 'details', 'memo', 'payee', 'particulars', 'narration']):
                desc_col = i
            elif type_col is None and h == 'type':
                type_col = i
            elif amount_col is None and ('amount' in h or h == 'value'):
                amount_col = i
            elif debit_col is None and any(kw in h for kw in ['debit', 'withdrawal', 'withdrawals', 'dr', 'money out']):
                debit_col = i
            elif credit_col is None and any(kw in h for kw in ['credit', 'deposit', 'deposits', 'cr', 'money in']):
                credit_col = i
            elif balance_col is None and 'balance' in h:
                balance_col = i

        print(f"[table_process] Header cols - date:{date_col}, desc:{desc_col}, amount:{amount_col}, debit:{debit_col}, credit:{credit_col}, type:{type_col}")

        # Check if first row looks like a header or data
        has_header = any(h for h in header_lower if h and not self._parse_date(header[header_lower.index(h)] if h else ''))

        # If we couldn't identify columns from header, try to infer from data
        if date_col is None:
            # Look for date-like values in first few rows
            check_rows = table[1:4] if has_header else table[:3]
            for row in check_rows:
                for i, cell in enumerate(row):
                    if cell and self._parse_date(str(cell)):
                        date_col = i
                        print(f"[table_process] Inferred date column: {i} from value '{cell}'")
                        break
                if date_col is not None:
                    break

        # Process data rows
        start_row = 1 if has_header else 0

        for row_idx, row in enumerate(table[start_row:], start=start_row):
            try:
                # Skip empty rows
                if not row or all(not cell for cell in row):
                    continue

                transaction = {}

                # Extract date
                if date_col is not None and date_col < len(row) and row[date_col]:
                    parsed_date = self._parse_date(str(row[date_col]))
                    if parsed_date:
                        transaction['date'] = parsed_date
                    else:
                        continue  # Skip rows without valid date
                else:
                    # Try to find date in any column
                    for i, cell in enumerate(row):
                        if cell:
                            parsed_date = self._parse_date(str(cell))
                            if parsed_date:
                                transaction['date'] = parsed_date
                                if date_col is None:
                                    date_col = i
                                break
                    if 'date' not in transaction:
                        continue

                # Extract description
                if desc_col is not None and desc_col < len(row) and row[desc_col]:
                    transaction['description'] = str(row[desc_col]).strip()
                else:
                    # Try to use any text column as description
                    for i, cell in enumerate(row):
                        if i != date_col and i != balance_col and cell:
                            cell_str = str(cell).strip()
                            # Check if it's not a number and not a date
                            if cell_str and len(cell_str) > 2:
                                amt = self._parse_amount(cell_str)
                                dt = self._parse_date(cell_str)
                                if amt is None and dt is None:
                                    transaction['description'] = cell_str
                                    break

                # Extract transaction type if available
                tx_type = None
                if type_col is not None and type_col < len(row) and row[type_col]:
                    type_val = str(row[type_col]).upper().strip()
                    if type_val in ['CREDIT', 'CR', 'C']:
                        tx_type = 'credit'
                    elif type_val in ['DEBIT', 'DR', 'D']:
                        tx_type = 'debit'

                # Extract amount - try multiple strategies
                amount_found = False

                # Strategy 1: Use amount column
                if amount_col is not None and amount_col < len(row) and row[amount_col]:
                    amt = self._parse_amount(row[amount_col])
                    if amt is not None:
                        transaction['amount'] = amt
                        amount_found = True

                # Strategy 2: Use debit/credit columns
                if not amount_found and (debit_col is not None or credit_col is not None):
                    debit = 0
                    credit = 0
                    if debit_col is not None and debit_col < len(row) and row[debit_col]:
                        debit = self._parse_amount(row[debit_col]) or 0
                    if credit_col is not None and credit_col < len(row) and row[credit_col]:
                        credit = self._parse_amount(row[credit_col]) or 0

                    if debit > 0:
                        transaction['amount'] = -debit
                        transaction['type'] = 'debit'
                        amount_found = True
                    elif credit > 0:
                        transaction['amount'] = credit
                        transaction['type'] = 'credit'
                        amount_found = True

                # Strategy 3: Find any amount in remaining columns
                if not amount_found:
                    amounts_found = []
                    for i, cell in enumerate(row):
                        if i != date_col and i != desc_col and i != type_col and cell:
                            amt = self._parse_amount(cell)
                            if amt is not None and amt != 0:
                                amounts_found.append((i, amt))

                    # If we have amounts, use the first non-balance one
                    if amounts_found:
                        # If balance column is known, exclude it
                        if balance_col is not None:
                            amounts_found = [(i, a) for i, a in amounts_found if i != balance_col]
                        if amounts_found:
                            transaction['amount'] = amounts_found[0][1]
                            amount_found = True

                # Apply type if known
                if tx_type:
                    transaction['type'] = tx_type
                    # Adjust amount sign based on type
                    if 'amount' in transaction:
                        if tx_type == 'debit' and transaction['amount'] > 0:
                            transaction['amount'] = -transaction['amount']
                        elif tx_type == 'credit' and transaction['amount'] < 0:
                            transaction['amount'] = abs(transaction['amount'])

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

        print(f"[text_extract] Processing {len(lines)} lines")

        # Try multiple patterns - order matters, more specific first
        patterns = [
            # Pattern 1: MM/DD Description Debit Credit Balance (common bank format)
            # e.g., "10/02 POS PURCHASE 4.23 65.73"
            r'^(\d{1,2}/\d{1,2})\s+(.+?)\s+([\d,]+\.\d{2})\s*([\d,]+\.\d{2})?\s*([\d,]+\.\d{2})?$',

            # Pattern 2: MM/DD/YYYY or MM/DD/YY format with amount at end
            r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+([-+]?\$?[\d,]+\.\d{2})\s*$',

            # Pattern 3: Date Description Amount (amount can be anywhere)
            r'(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\s+([A-Za-z][A-Za-z0-9\s\-\*#]+?)\s+([\d,]+\.\d{2})',

            # Pattern 4: More flexible - any line starting with date-like pattern
            r'^(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\s+(.+)',
        ]

        # Show some sample lines for debugging
        sample_lines = [l.strip() for l in lines[:20] if l.strip()]
        print(f"[text_extract] First 20 non-empty lines: {sample_lines}")

        # First, try the line-by-line approach for tabular data
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Skip header lines - but be careful not to skip too much
            lower_line = line.lower()
            if 'date' in lower_line and ('description' in lower_line or 'balance' in lower_line):
                print(f"[text_extract] Skipping header line: {line[:80]}")
                continue

            # Skip summary/total lines
            if lower_line.startswith('total') or lower_line.startswith('ending balance'):
                continue

            # Try multiple date patterns
            date_patterns = [
                # Numeric date formats
                r'^(\d{4}-\d{2}-\d{2})\s+(.+)',         # YYYY-MM-DD (ISO format)
                r'^(\d{1,2}/\d{1,2}/\d{2,4})\s+(.+)',   # MM/DD/YYYY or DD/MM/YYYY
                r'^(\d{1,2}-\d{1,2}-\d{2,4})\s+(.+)',   # MM-DD-YYYY or DD-MM-YYYY
                r'^(\d{1,2}/\d{1,2})\s+(.+)',           # MM/DD or DD/MM
                r'^(\d{1,2}-\d{1,2})\s+(.+)',           # MM-DD or DD-MM
                # Text date formats (e.g., "1 February", "3 Feb")
                r'^(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December))\s+(.+)',
                r'^(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))\s+(.+)',
            ]

            match = None
            for dp in date_patterns:
                match = re.match(dp, line, re.IGNORECASE)
                if match:
                    break

            if not match:
                # Also try to find date anywhere in the line
                date_search = re.search(r'(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)', line)
                if date_search:
                    # Try to split around the date
                    date_str = date_search.group(1)
                    rest = line[date_search.end():].strip()
                    if rest and re.search(r'[\d,]+\.\d{2}', rest):
                        match = type('Match', (), {'group': lambda self, n: date_str if n == 1 else rest})()

            if not match:
                continue

            # Re-extract using the generic pattern for consistency
            generic_match = re.match(r'^(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))\s+(.+)', line, re.IGNORECASE)
            if generic_match:
                match = generic_match
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

                        # Add current year to date if not already present
                        if len(date_str) <= 5:  # MM/DD format without year
                            current_year = datetime.now().year
                            full_date = f"{date_str}/{current_year}"
                        else:
                            full_date = date_str

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
