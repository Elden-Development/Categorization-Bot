import React from "react";
import "./App.css";

const BankReconciliation = ({
  reconciliationResults,
  onManualMatch,
  onAcceptSuggestion
}) => {
  if (!reconciliationResults) {
    return null;
  }

  const { matched, unmatched_documents, unmatched_transactions, suggested_matches, summary } = reconciliationResults;

  const getConfidenceBadgeClass = (confidence) => {
    switch (confidence) {
      case 'high':
        return 'confidence-badge-high';
      case 'medium':
        return 'confidence-badge-medium';
      case 'low':
        return 'confidence-badge-low';
      default:
        return 'confidence-badge-none';
    }
  };

  const getMatchTypeBadgeClass = (matchType) => {
    switch (matchType) {
      case 'automatic':
        return 'match-type-auto';
      case 'manual':
        return 'match-type-manual';
      default:
        return 'match-type-suggested';
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(Math.abs(amount));
  };

  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch (e) {
      return dateStr;
    }
  };

  const getVendorName = (doc) => {
    if (doc.documentMetadata?.source?.name) {
      return doc.documentMetadata.source.name;
    }
    if (doc.partyInformation?.vendor?.name) {
      return doc.partyInformation.vendor.name;
    }
    return 'Unknown Vendor';
  };

  const getDocumentAmount = (doc) => {
    if (doc.financialData?.totalAmount) {
      return doc.financialData.totalAmount;
    }
    if (doc.totalAmount) {
      return doc.totalAmount;
    }
    return 0;
  };

  const getDocumentDate = (doc) => {
    if (doc.documentMetadata?.documentDate) {
      return doc.documentMetadata.documentDate;
    }
    if (doc.documentDate) {
      return doc.documentDate;
    }
    return 'N/A';
  };

  return (
    <div className="reconciliation-container">
      <div className="section-title">Reconciliation Results</div>
      <h2>Bank Statement Reconciliation</h2>

      {/* Summary Stats */}
      <div className="reconciliation-summary">
        <div className="summary-card">
          <div className="summary-icon success-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <div className="summary-content">
            <div className="summary-value">{summary.matched_count}</div>
            <div className="summary-label">Matched</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon warning-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <div className="summary-content">
            <div className="summary-value">{summary.suggested_matches_count}</div>
            <div className="summary-label">Needs Review</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon error-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          </div>
          <div className="summary-content">
            <div className="summary-value">{summary.unmatched_documents_count}</div>
            <div className="summary-label">Unmatched Docs</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon info-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
          </div>
          <div className="summary-content">
            <div className="summary-value">{summary.unmatched_transactions_count}</div>
            <div className="summary-label">Unmatched Txns</div>
          </div>
        </div>

        <div className="summary-card summary-card-wide">
          <div className="summary-icon percentage-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div className="summary-content">
            <div className="summary-value">{summary.reconciliation_rate}%</div>
            <div className="summary-label">Reconciliation Rate</div>
          </div>
        </div>
      </div>

      {/* Matched Transactions */}
      {matched && matched.length > 0 && (
        <div className="reconciliation-section">
          <h3 className="section-subtitle">
            <span className="status-indicator status-success"></span>
            Matched Transactions ({matched.length})
          </h3>
          <div className="match-list">
            {matched.map((match, idx) => (
              <div key={idx} className="match-card match-card-success">
                <div className="match-header">
                  <div className="match-info">
                    <div className="match-vendor">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                      {getVendorName(match.document)}
                    </div>
                    <div className="match-description">{match.transaction.description}</div>
                  </div>
                  <div className="match-badges">
                    <span className={`confidence-badge ${getConfidenceBadgeClass(match.confidence)}`}>
                      {match.match_score}% Match
                    </span>
                    <span className={`match-type-badge ${getMatchTypeBadgeClass(match.match_type)}`}>
                      {match.match_type}
                    </span>
                  </div>
                </div>

                <div className="match-details">
                  <div className="detail-group">
                    <div className="detail-label">Document Amount</div>
                    <div className="detail-value">{formatCurrency(getDocumentAmount(match.document))}</div>
                  </div>
                  <div className="detail-group">
                    <div className="detail-label">Transaction Amount</div>
                    <div className="detail-value">{formatCurrency(match.transaction.amount)}</div>
                  </div>
                  <div className="detail-group">
                    <div className="detail-label">Document Date</div>
                    <div className="detail-value">{formatDate(getDocumentDate(match.document))}</div>
                  </div>
                  <div className="detail-group">
                    <div className="detail-label">Transaction Date</div>
                    <div className="detail-value">{formatDate(match.transaction.date)}</div>
                  </div>
                </div>

                {match.match_details && (
                  <div className="match-breakdown">
                    <div className="breakdown-item">
                      <span className="breakdown-label">Name Match:</span>
                      <span className="breakdown-value">{match.match_details.name_score}%</span>
                    </div>
                    <div className="breakdown-item">
                      <span className="breakdown-label">Amount Match:</span>
                      <span className="breakdown-value">{match.match_details.amount_score}%</span>
                    </div>
                    <div className="breakdown-item">
                      <span className="breakdown-label">Date Match:</span>
                      <span className="breakdown-value">{match.match_details.date_score}%</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggested Matches */}
      {suggested_matches && suggested_matches.length > 0 && (
        <div className="reconciliation-section">
          <h3 className="section-subtitle">
            <span className="status-indicator status-warning"></span>
            Suggested Matches - Review Required ({suggested_matches.length})
          </h3>
          <div className="match-list">
            {suggested_matches.map((suggestion, idx) => (
              <div key={idx} className="match-card match-card-warning">
                <div className="match-header">
                  <div className="match-info">
                    <div className="match-vendor">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                      {getVendorName(suggestion.document)}
                    </div>
                    <div className="match-description">{suggestion.transaction.description}</div>
                  </div>
                  <div className="match-badges">
                    <span className={`confidence-badge ${getConfidenceBadgeClass(suggestion.confidence)}`}>
                      {suggestion.match_score}% Match
                    </span>
                  </div>
                </div>

                <div className="match-details">
                  <div className="detail-group">
                    <div className="detail-label">Document Amount</div>
                    <div className="detail-value">{formatCurrency(getDocumentAmount(suggestion.document))}</div>
                  </div>
                  <div className="detail-group">
                    <div className="detail-label">Transaction Amount</div>
                    <div className="detail-value">{formatCurrency(suggestion.transaction.amount)}</div>
                  </div>
                  <div className="detail-group">
                    <div className="detail-label">Document Date</div>
                    <div className="detail-value">{formatDate(getDocumentDate(suggestion.document))}</div>
                  </div>
                  <div className="detail-group">
                    <div className="detail-label">Transaction Date</div>
                    <div className="detail-value">{formatDate(suggestion.transaction.date)}</div>
                  </div>
                </div>

                {suggestion.match_details && (
                  <div className="match-breakdown">
                    <div className="breakdown-item">
                      <span className="breakdown-label">Name Match:</span>
                      <span className="breakdown-value">{suggestion.match_details.name_score}%</span>
                    </div>
                    <div className="breakdown-item">
                      <span className="breakdown-label">Amount Match:</span>
                      <span className="breakdown-value">{suggestion.match_details.amount_score}%</span>
                    </div>
                    <div className="breakdown-item">
                      <span className="breakdown-label">Date Match:</span>
                      <span className="breakdown-value">{suggestion.match_details.date_score}%</span>
                    </div>
                  </div>
                )}

                <div className="match-actions">
                  <button
                    className="btn-accept"
                    onClick={() => onAcceptSuggestion && onAcceptSuggestion(suggestion)}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    Accept Match
                  </button>
                  <button
                    className="btn-reject"
                    onClick={() => {/* Handle reject */}}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unmatched Documents */}
      {unmatched_documents && unmatched_documents.length > 0 && (
        <div className="reconciliation-section">
          <h3 className="section-subtitle">
            <span className="status-indicator status-error"></span>
            Unmatched Documents ({unmatched_documents.length})
          </h3>
          <div className="match-list">
            {unmatched_documents.map((doc, idx) => (
              <div key={idx} className="match-card match-card-error">
                <div className="match-header">
                  <div className="match-info">
                    <div className="match-vendor">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      {getVendorName(doc)}
                    </div>
                  </div>
                  <div className="match-badges">
                    <span className="confidence-badge confidence-badge-none">No Match</span>
                  </div>
                </div>

                <div className="match-details">
                  <div className="detail-group">
                    <div className="detail-label">Amount</div>
                    <div className="detail-value">{formatCurrency(getDocumentAmount(doc))}</div>
                  </div>
                  <div className="detail-group">
                    <div className="detail-label">Date</div>
                    <div className="detail-value">{formatDate(getDocumentDate(doc))}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unmatched Transactions */}
      {unmatched_transactions && unmatched_transactions.length > 0 && (
        <div className="reconciliation-section">
          <h3 className="section-subtitle">
            <span className="status-indicator status-info"></span>
            Unmatched Bank Transactions ({unmatched_transactions.length})
          </h3>
          <div className="match-list">
            {unmatched_transactions.map((item, idx) => (
              <div key={idx} className="match-card match-card-info">
                <div className="match-header">
                  <div className="match-info">
                    <div className="match-vendor">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
                        <line x1="1" y1="10" x2="23" y2="10" />
                      </svg>
                      {item.transaction.description}
                    </div>
                  </div>
                  <div className="match-badges">
                    <span className="confidence-badge confidence-badge-none">No Match</span>
                  </div>
                </div>

                <div className="match-details">
                  <div className="detail-group">
                    <div className="detail-label">Amount</div>
                    <div className="detail-value">{formatCurrency(item.transaction.amount)}</div>
                  </div>
                  <div className="detail-group">
                    <div className="detail-label">Date</div>
                    <div className="detail-value">{formatDate(item.transaction.date)}</div>
                  </div>
                </div>

                {/* Show possible matches if available */}
                {item.possible_matches && item.possible_matches.length > 0 && (
                  <div className="possible-matches">
                    <div className="possible-matches-header">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="11" cy="11" r="8" />
                        <path d="m21 21-4.35-4.35" />
                      </svg>
                      Possible Matches Found
                    </div>
                    {item.possible_matches.map((possibleMatch, pmIdx) => (
                      <div key={pmIdx} className="possible-match-item">
                        <div className="possible-match-info">
                          <span className="possible-match-vendor">{getVendorName(possibleMatch.document)}</span>
                          <span className="possible-match-amount">{formatCurrency(getDocumentAmount(possibleMatch.document))}</span>
                          <span className="possible-match-score">{possibleMatch.score}% match</span>
                        </div>
                        <button
                          className="btn-link-small"
                          onClick={() => onManualMatch && onManualMatch(possibleMatch.document, item.transaction)}
                        >
                          Manual Match
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default BankReconciliation;
