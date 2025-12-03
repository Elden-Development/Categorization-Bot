import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import './StatementResults.css';

const StatementResults = () => {
  const { token } = useAuth();
  const [statements, setStatements] = useState([]);
  const [selectedStatementId, setSelectedStatementId] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [statementsLoading, setStatementsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Sorting and filtering
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterCategory, setFilterCategory] = useState('');

  // Editing state
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({ category: '', subcategory: '', ledgerType: '' });
  const [categories, setCategories] = useState([]);

  // Bulk selection
  const [selectedTxIds, setSelectedTxIds] = useState(new Set());
  const [bulkActionLoading, setBulkActionLoading] = useState(false);

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // Fetch user's bank statements
  const fetchStatements = useCallback(async () => {
    try {
      setStatementsLoading(true);
      const response = await fetch(`${API_BASE_URL}/bank-statements`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStatements(data);
        // Auto-select most recent if available
        if (data.length > 0 && !selectedStatementId) {
          setSelectedStatementId(data[0].id);
        }
      }
    } catch (err) {
      console.error('Error fetching statements:', err);
    } finally {
      setStatementsLoading(false);
    }
  }, [API_BASE_URL, token, selectedStatementId]);

  // Fetch categories for editing
  const fetchCategories = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/categories`);
      if (response.ok) {
        const data = await response.json();
        // Transform grouped data into the format we need: [{name, subcategories: []}]
        if (data.grouped) {
          const transformedCategories = Object.entries(data.grouped).map(([name, subs]) => ({
            name,
            subcategories: subs.map(s => s.subcategory)
          }));
          setCategories(transformedCategories);
        } else {
          setCategories([]);
        }
      }
    } catch (err) {
      console.error('Error fetching categories:', err);
    }
  }, [API_BASE_URL]);

  // Fetch results for selected statement
  const fetchResults = useCallback(async () => {
    if (!selectedStatementId) return;

    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        sort_by: sortBy,
        sort_order: sortOrder
      });
      if (filterStatus) params.append('filter_status', filterStatus);
      if (filterCategory) params.append('filter_category', filterCategory);

      const response = await fetch(
        `${API_BASE_URL}/bank-statement/${selectedStatementId}/results?${params}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );

      if (response.ok) {
        const data = await response.json();
        setResults(data);
        setSelectedTxIds(new Set());
      } else {
        const err = await response.json();
        setError(err.detail || 'Failed to fetch results');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [API_BASE_URL, token, selectedStatementId, sortBy, sortOrder, filterStatus, filterCategory]);

  useEffect(() => {
    fetchStatements();
    fetchCategories();
  }, [fetchStatements, fetchCategories]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  // Handle single transaction approval
  const handleApprove = async (tx) => {
    try {
      const response = await fetch(`${API_BASE_URL}/bank-transaction/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          bank_transaction_id: tx.id,
          approved: true
        })
      });

      if (response.ok) {
        fetchResults();
      } else {
        const err = await response.json();
        alert(err.detail || 'Failed to approve');
      }
    } catch (err) {
      alert('Error approving transaction');
    }
  };

  // Handle inline edit save
  const handleSaveEdit = async (tx) => {
    if (!editData.category) {
      alert('Please select a category');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/bank-transaction/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          bank_transaction_id: tx.id,
          approved: false,
          corrected_category: editData.category,
          corrected_subcategory: editData.subcategory || '',
          corrected_ledger_type: editData.ledgerType || 'Expense'
        })
      });

      if (response.ok) {
        setEditingId(null);
        setEditData({ category: '', subcategory: '', ledgerType: '' });
        fetchResults();
      } else {
        const err = await response.json();
        alert(err.detail || 'Failed to save correction');
      }
    } catch (err) {
      alert('Error saving correction');
    }
  };

  // Handle bulk approve
  const handleBulkApprove = async (mode) => {
    setBulkActionLoading(true);
    try {
      let body = {};

      if (mode === 'selected') {
        body = { bank_transaction_ids: Array.from(selectedTxIds) };
      } else if (mode === 'high_confidence') {
        body = {
          bank_statement_id: selectedStatementId,
          approve_all_high_confidence: true
        };
      } else if (mode === 'all') {
        body = { bank_statement_id: selectedStatementId };
      }

      const response = await fetch(`${API_BASE_URL}/bank-transaction/bulk-approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
      });

      if (response.ok) {
        const data = await response.json();
        alert(`Approved ${data.approved_count} transactions`);
        setSelectedTxIds(new Set());
        fetchResults();
      } else {
        const err = await response.json();
        alert(err.detail || 'Bulk approve failed');
      }
    } catch (err) {
      alert('Error during bulk approve');
    } finally {
      setBulkActionLoading(false);
    }
  };

  // Toggle transaction selection
  const toggleSelection = (txId) => {
    const newSet = new Set(selectedTxIds);
    if (newSet.has(txId)) {
      newSet.delete(txId);
    } else {
      newSet.add(txId);
    }
    setSelectedTxIds(newSet);
  };

  // Select all visible transactions
  const selectAll = () => {
    if (!results) return;
    const allIds = results.transactions
      .filter(tx => tx.status !== 'approved')
      .map(tx => tx.id);
    setSelectedTxIds(new Set(allIds));
  };

  // Clear selection
  const clearSelection = () => setSelectedTxIds(new Set());

  // Get confidence badge class
  const getConfidenceBadge = (confidence) => {
    if (!confidence) return 'confidence-none';
    if (confidence >= 85) return 'confidence-high';
    if (confidence >= 70) return 'confidence-medium';
    if (confidence >= 50) return 'confidence-low';
    return 'confidence-critical';
  };

  // Get status badge class
  const getStatusBadge = (status) => {
    switch (status) {
      case 'approved': return 'status-approved';
      case 'needs_review': return 'status-review';
      case 'uncategorized': return 'status-uncategorized';
      default: return '';
    }
  };

  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  // Handle sort column click
  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  // Get subcategories for selected category
  const getSubcategories = (categoryName) => {
    const cat = categories.find(c => c.name === categoryName);
    return cat?.subcategories || [];
  };

  if (statementsLoading) {
    return (
      <div className="statement-results-container">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading statements...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="statement-results-container">
      <div className="results-header">
        <h2>Statement Results</h2>
        <p className="subtitle">View and manage categorization results for your bank statements</p>
      </div>

      {/* Statement Selector */}
      <div className="statement-selector">
        <label>Select Statement:</label>
        <select
          value={selectedStatementId || ''}
          onChange={(e) => setSelectedStatementId(Number(e.target.value))}
        >
          <option value="">-- Select a statement --</option>
          {statements.map(stmt => (
            <option key={stmt.id} value={stmt.id}>
              {stmt.file_name} ({stmt.transaction_count} transactions)
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading results...</p>
        </div>
      ) : error ? (
        <div className="error-state">
          <p>{error}</p>
          <button onClick={fetchResults}>Retry</button>
        </div>
      ) : results ? (
        <>
          {/* Summary Stats */}
          <div className="stats-dashboard">
            <div className="stat-card total">
              <h3>{results.summary.total}</h3>
              <p>Total Transactions</p>
            </div>
            <div className="stat-card categorized">
              <h3>{results.summary.categorized}</h3>
              <p>Categorized</p>
            </div>
            <div className="stat-card approved">
              <h3>{results.summary.approved}</h3>
              <p>Approved</p>
            </div>
            <div className="stat-card review">
              <h3>{results.summary.needs_review}</h3>
              <p>Needs Review</p>
            </div>
            <div className="stat-card high-conf">
              <h3>{results.summary.high_confidence}</h3>
              <p>High Confidence</p>
            </div>
            <div className="stat-card amount">
              <h3>{formatCurrency(results.summary.total_amount)}</h3>
              <p>Total Amount</p>
            </div>
          </div>

          {/* Category Breakdown */}
          {results.category_breakdown.length > 0 && (
            <div className="category-breakdown">
              <h3>Category Breakdown</h3>
              <div className="breakdown-grid">
                {results.category_breakdown.slice(0, 8).map(cat => (
                  <div key={cat.category} className="breakdown-item">
                    <span className="cat-name">{cat.category}</span>
                    <span className="cat-count">{cat.count} txns</span>
                    <span className="cat-amount">{formatCurrency(cat.amount)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Filters and Bulk Actions */}
          <div className="results-toolbar">
            <div className="filters">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="">All Status</option>
                <option value="approved">Approved</option>
                <option value="needs_review">Needs Review</option>
                <option value="uncategorized">Uncategorized</option>
              </select>
              <select
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
              >
                <option value="">All Categories</option>
                {results.category_breakdown.map(cat => (
                  <option key={cat.category} value={cat.category}>{cat.category}</option>
                ))}
              </select>
            </div>
            <div className="bulk-actions">
              {selectedTxIds.size > 0 && (
                <>
                  <span className="selection-count">{selectedTxIds.size} selected</span>
                  <button
                    className="btn-bulk approve"
                    onClick={() => handleBulkApprove('selected')}
                    disabled={bulkActionLoading}
                  >
                    Approve Selected
                  </button>
                  <button className="btn-bulk clear" onClick={clearSelection}>
                    Clear
                  </button>
                </>
              )}
              <button
                className="btn-bulk"
                onClick={() => handleBulkApprove('high_confidence')}
                disabled={bulkActionLoading}
              >
                Approve High Confidence
              </button>
              <button className="btn-bulk select-all" onClick={selectAll}>
                Select All Pending
              </button>
            </div>
          </div>

          {/* Transactions Table */}
          <div className="transactions-table-container">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th className="col-select">
                    <input
                      type="checkbox"
                      checked={selectedTxIds.size > 0 && selectedTxIds.size === results.transactions.filter(t => t.status !== 'approved').length}
                      onChange={(e) => e.target.checked ? selectAll() : clearSelection()}
                    />
                  </th>
                  <th className="col-date sortable" onClick={() => handleSort('date')}>
                    Date {sortBy === 'date' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="col-desc">Description</th>
                  <th className="col-amount sortable" onClick={() => handleSort('amount')}>
                    Amount {sortBy === 'amount' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="col-category sortable" onClick={() => handleSort('category')}>
                    Category {sortBy === 'category' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="col-confidence sortable" onClick={() => handleSort('confidence')}>
                    Confidence {sortBy === 'confidence' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="col-status sortable" onClick={() => handleSort('status')}>
                    Status {sortBy === 'status' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="col-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {results.transactions.map(tx => (
                  <tr key={tx.id} className={selectedTxIds.has(tx.id) ? 'selected' : ''}>
                    <td className="col-select">
                      <input
                        type="checkbox"
                        checked={selectedTxIds.has(tx.id)}
                        onChange={() => toggleSelection(tx.id)}
                        disabled={tx.status === 'approved'}
                      />
                    </td>
                    <td className="col-date">{tx.transaction_date}</td>
                    <td className="col-desc" title={tx.description}>
                      {tx.description?.length > 40
                        ? tx.description.substring(0, 40) + '...'
                        : tx.description}
                    </td>
                    <td className="col-amount">
                      <span className={tx.amount < 0 ? 'amount-negative' : 'amount-positive'}>
                        {formatCurrency(tx.amount)}
                      </span>
                    </td>
                    <td className="col-category">
                      {editingId === tx.id ? (
                        <div className="inline-edit">
                          <select
                            value={editData.category}
                            onChange={(e) => setEditData({...editData, category: e.target.value, subcategory: ''})}
                          >
                            <option value="">Select...</option>
                            {categories.map(cat => (
                              <option key={cat.name} value={cat.name}>{cat.name}</option>
                            ))}
                          </select>
                          {editData.category && (
                            <select
                              value={editData.subcategory}
                              onChange={(e) => setEditData({...editData, subcategory: e.target.value})}
                            >
                              <option value="">Subcategory...</option>
                              {getSubcategories(editData.category).map(sub => (
                                <option key={sub} value={sub}>{sub}</option>
                              ))}
                            </select>
                          )}
                        </div>
                      ) : (
                        <div className="category-display">
                          <span className="cat-main">{tx.category || '—'}</span>
                          {tx.subcategory && <span className="cat-sub">{tx.subcategory}</span>}
                        </div>
                      )}
                    </td>
                    <td className="col-confidence">
                      {tx.confidence ? (
                        <span className={`confidence-badge ${getConfidenceBadge(tx.confidence)}`}>
                          {tx.confidence.toFixed(0)}%
                        </span>
                      ) : '—'}
                    </td>
                    <td className="col-status">
                      <span className={`status-badge ${getStatusBadge(tx.status)}`}>
                        {tx.status === 'needs_review' ? 'Review' :
                         tx.status === 'uncategorized' ? 'Uncat.' :
                         tx.status.charAt(0).toUpperCase() + tx.status.slice(1)}
                      </span>
                    </td>
                    <td className="col-actions">
                      {editingId === tx.id ? (
                        <>
                          <button className="btn-action save" onClick={() => handleSaveEdit(tx)}>
                            Save
                          </button>
                          <button className="btn-action cancel" onClick={() => {
                            setEditingId(null);
                            setEditData({ category: '', subcategory: '', ledgerType: '' });
                          }}>
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          {tx.status !== 'approved' && (
                            <button className="btn-action approve" onClick={() => handleApprove(tx)}>
                              Approve
                            </button>
                          )}
                          <button
                            className="btn-action edit"
                            onClick={() => {
                              setEditingId(tx.id);
                              setEditData({
                                category: tx.category || '',
                                subcategory: tx.subcategory || '',
                                ledgerType: tx.ledger_type || ''
                              });
                            }}
                          >
                            Edit
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {results.transactions.length === 0 && (
              <div className="empty-state">
                <p>No transactions match your filters</p>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="empty-state">
          <p>Select a bank statement to view results</p>
        </div>
      )}
    </div>
  );
};

export default StatementResults;
