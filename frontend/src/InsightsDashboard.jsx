import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "./AuthContext";
import "./InsightsDashboard.css";

const InsightsDashboard = () => {
  const { token } = useAuth();
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  const fetchInsights = useCallback(async () => {
    if (!token) return;

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/insights/dashboard`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch insights');
      }

      const data = await response.json();
      if (data.success) {
        setInsights(data.insights);
      } else {
        throw new Error(data.detail || 'Unknown error');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token, API_BASE_URL]);

  useEffect(() => {
    fetchInsights();
  }, [fetchInsights]);

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toLocaleString();
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(Math.abs(amount));
  };

  const getConfidenceColor = (level) => {
    switch (level) {
      case 'high': return 'var(--success-color)';
      case 'medium': return 'var(--primary-color)';
      case 'low': return 'var(--warning-color)';
      default: return 'var(--danger-color)';
    }
  };

  const getMethodLabel = (method) => {
    switch (method) {
      case 'ml': return 'Machine Learning';
      case 'vendor_mapping': return 'ML (Vendor Mapping)';
      case 'gemini': return 'Gemini AI';
      case 'hybrid': return 'Hybrid';
      case 'manual': return 'Manual';
      default: return method;
    }
  };

  if (loading) {
    return (
      <div className="insights-dashboard">
        <div className="insights-loading">
          <div className="loading-spinner"></div>
          <p>Loading insights...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="insights-dashboard">
        <div className="insights-error">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <p>Error loading insights: {error}</p>
          <button onClick={fetchInsights} className="retry-btn">Retry</button>
        </div>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="insights-dashboard">
        <div className="insights-empty">
          <p>No insights available yet. Start categorizing transactions to see statistics.</p>
        </div>
      </div>
    );
  }

  const { overview, bank_statements, method_distribution, category_distribution, confidence_distribution, recent_activity, ml_stats } = insights;

  // Calculate max for category bar chart
  const maxCategoryCount = Math.max(...(category_distribution?.map(c => c.count) || [1]));

  return (
    <div className="insights-dashboard">
      <div className="insights-header">
        <h2>Categorization Insights</h2>
        <p>Overview of your transaction categorization performance and statistics</p>
        <button onClick={fetchInsights} className="refresh-btn">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Overview Stats */}
      <div className="stats-grid">
        <div className="stat-card primary">
          <div className="stat-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <div className="stat-content">
            <span className="stat-value">{formatNumber(overview.total_categorizations)}</span>
            <span className="stat-label">Total Categorizations</span>
          </div>
        </div>

        <div className="stat-card success">
          <div className="stat-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 6L9 17l-5-5" />
            </svg>
          </div>
          <div className="stat-content">
            <span className="stat-value">{formatNumber(overview.approved_count)}</span>
            <span className="stat-label">Approved</span>
          </div>
        </div>

        <div className="stat-card warning">
          <div className="stat-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div className="stat-content">
            <span className="stat-value">{formatNumber(overview.pending_count)}</span>
            <span className="stat-label">Pending Review</span>
          </div>
        </div>

        <div className="stat-card info">
          <div className="stat-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </div>
          <div className="stat-content">
            <span className="stat-value">{formatNumber(overview.corrections_count)}</span>
            <span className="stat-label">User Corrections</span>
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="metrics-section">
        <h3>Performance Metrics</h3>
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-header">
              <span className="metric-title">Approval Rate</span>
              <span className="metric-value">{overview.approval_rate}%</span>
            </div>
            <div className="metric-bar">
              <div
                className="metric-fill success"
                style={{ width: `${Math.min(overview.approval_rate, 100)}%` }}
              ></div>
            </div>
            <p className="metric-description">Percentage of categorizations approved by users</p>
          </div>

          <div className="metric-card">
            <div className="metric-header">
              <span className="metric-title">Accuracy Estimate</span>
              <span className="metric-value">{overview.accuracy_estimate}%</span>
            </div>
            <div className="metric-bar">
              <div
                className="metric-fill primary"
                style={{ width: `${Math.min(overview.accuracy_estimate, 100)}%` }}
              ></div>
            </div>
            <p className="metric-description">Approved without corrections (auto-approved accuracy)</p>
          </div>

          <div className="metric-card">
            <div className="metric-header">
              <span className="metric-title">Average Confidence</span>
              <span className="metric-value">{overview.average_confidence}%</span>
            </div>
            <div className="metric-bar">
              <div
                className="metric-fill info"
                style={{ width: `${Math.min(overview.average_confidence, 100)}%` }}
              ></div>
            </div>
            <p className="metric-description">Mean confidence score across all categorizations</p>
          </div>
        </div>
      </div>

      <div className="insights-row">
        {/* Category Distribution */}
        <div className="insights-card category-distribution">
          <h3>Top Categories</h3>
          {category_distribution && category_distribution.length > 0 ? (
            <div className="category-list">
              {category_distribution.map((cat, index) => (
                <div key={cat.category} className="category-item">
                  <div className="category-info">
                    <span className="category-rank">#{index + 1}</span>
                    <span className="category-name">{cat.category}</span>
                  </div>
                  <div className="category-stats">
                    <span className="category-count">{cat.count} txns</span>
                    <span className="category-amount">{formatCurrency(cat.total_amount)}</span>
                  </div>
                  <div className="category-bar-container">
                    <div
                      className="category-bar"
                      style={{ width: `${(cat.count / maxCategoryCount) * 100}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No category data available</p>
          )}
        </div>

        {/* Method Distribution */}
        <div className="insights-card method-distribution">
          <h3>Categorization Methods</h3>
          {method_distribution && Object.keys(method_distribution).length > 0 ? (
            <div className="method-chart">
              {Object.entries(method_distribution).map(([method, count]) => {
                const total = Object.values(method_distribution).reduce((a, b) => a + b, 0);
                const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                return (
                  <div key={method} className="method-item">
                    <div className="method-label">
                      <span className={`method-dot ${method}`}></span>
                      <span>{getMethodLabel(method)}</span>
                    </div>
                    <div className="method-stats">
                      <span className="method-count">{count}</span>
                      <span className="method-percent">{percentage}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="no-data">No method data available</p>
          )}
        </div>

        {/* Confidence Distribution */}
        <div className="insights-card confidence-distribution">
          <h3>Confidence Levels</h3>
          {confidence_distribution && Object.keys(confidence_distribution).length > 0 ? (
            <div className="confidence-chart">
              {['high', 'medium', 'low', 'very_low'].map((level) => {
                const count = confidence_distribution[level] || 0;
                const total = Object.values(confidence_distribution).reduce((a, b) => a + b, 0);
                const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                return (
                  <div key={level} className="confidence-item">
                    <div className="confidence-label">
                      <span
                        className="confidence-dot"
                        style={{ backgroundColor: getConfidenceColor(level) }}
                      ></span>
                      <span>{level === 'very_low' ? 'Very Low' : level.charAt(0).toUpperCase() + level.slice(1)}</span>
                      <span className="confidence-range">
                        {level === 'high' && '(90%+)'}
                        {level === 'medium' && '(70-89%)'}
                        {level === 'low' && '(50-69%)'}
                        {level === 'very_low' && '(<50%)'}
                      </span>
                    </div>
                    <div className="confidence-stats">
                      <span className="confidence-count">{count}</span>
                      <span className="confidence-percent">{percentage}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="no-data">No confidence data available</p>
          )}
        </div>
      </div>

      {/* Bank Statement & ML Stats */}
      <div className="insights-row">
        <div className="insights-card bank-stats">
          <h3>Bank Statement Processing</h3>
          <div className="bank-stats-grid">
            <div className="bank-stat">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span className="bank-stat-value">{bank_statements.total_statements}</span>
              <span className="bank-stat-label">Statements Processed</span>
            </div>
            <div className="bank-stat">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="1" x2="12" y2="23" />
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
              <span className="bank-stat-value">{formatNumber(bank_statements.total_transactions)}</span>
              <span className="bank-stat-label">Transactions</span>
            </div>
            <div className="bank-stat">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
              <span className="bank-stat-value">{recent_activity.last_7_days}</span>
              <span className="bank-stat-label">Last 7 Days Activity</span>
            </div>
          </div>
        </div>

        {ml_stats && (
          <div className="insights-card ml-stats">
            <h3>Machine Learning Database</h3>
            <div className="ml-stats-content">
              <div className="ml-stat-item">
                <span className="ml-stat-label">Total Learned Transactions</span>
                <span className="ml-stat-value">{formatNumber(ml_stats.totalTransactions || 0)}</span>
              </div>
              <div className="ml-stat-item">
                <span className="ml-stat-label">Unique Categories</span>
                <span className="ml-stat-value">{ml_stats.uniqueCategories || 0}</span>
              </div>
              <div className="ml-stat-item">
                <span className="ml-stat-label">Database Status</span>
                <span className={`ml-status ${ml_stats.totalTransactions > 0 ? 'active' : 'empty'}`}>
                  {ml_stats.totalTransactions > 0 ? 'Active' : 'Empty'}
                </span>
              </div>
            </div>
            <div className="ml-info">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <p>The ML system learns from your approved categorizations to improve future predictions.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default InsightsDashboard;
