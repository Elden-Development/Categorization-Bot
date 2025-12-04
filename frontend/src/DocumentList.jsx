import React, { useState } from "react";
import "./App.css";

const DocumentList = ({
  documents,
  onSelectDocument,
  onRemoveDocument,
  onClearAll,
  selectedDocumentId
}) => {
  const [expandedDocId, setExpandedDocId] = useState(null);

  if (!documents || documents.length === 0) {
    return null;
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return (
          <svg className="status-icon status-completed" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        );
      case 'processing':
        return (
          <svg className="status-icon status-processing spinner-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="2" x2="12" y2="6" />
            <line x1="12" y1="18" x2="12" y2="22" />
            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
            <line x1="2" y1="12" x2="6" y2="12" />
            <line x1="18" y1="12" x2="22" y2="12" />
            <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
            <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
          </svg>
        );
      case 'error':
        return (
          <svg className="status-icon status-error" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        );
      case 'pending':
      default:
        return (
          <svg className="status-icon status-pending" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        );
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'processing':
        return 'Processing...';
      case 'error':
        return 'Failed';
      case 'pending':
      default:
        return 'Pending';
    }
  };

  const getVendorName = (doc) => {
    if (!doc.parsedData) return 'Unknown';

    if (doc.parsedData.documentMetadata?.source?.name) {
      return doc.parsedData.documentMetadata.source.name;
    }
    if (doc.parsedData.partyInformation?.vendor?.name) {
      return doc.parsedData.partyInformation.vendor.name;
    }
    return 'Unknown Vendor';
  };

  const getDocumentAmount = (doc) => {
    if (!doc.parsedData) return null;

    if (doc.parsedData.financialData?.totalAmount) {
      return doc.parsedData.financialData.totalAmount;
    }
    if (doc.parsedData.totalAmount) {
      return doc.parsedData.totalAmount;
    }
    return null;
  };

  const getDocumentDate = (doc) => {
    if (!doc.parsedData) return null;

    if (doc.parsedData.documentMetadata?.documentDate) {
      return doc.parsedData.documentMetadata.documentDate;
    }
    if (doc.parsedData.documentDate) {
      return doc.parsedData.documentDate;
    }
    return null;
  };

  const formatCurrency = (amount) => {
    if (!amount) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
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

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  const getConfidenceClass = (confidence) => {
    if (confidence >= 85) return 'confidence-high';
    if (confidence >= 70) return 'confidence-medium';
    if (confidence >= 50) return 'confidence-low';
    return 'confidence-critical';
  };

  const completedCount = documents.filter(d => d.status === 'completed').length;
  const processingCount = documents.filter(d => d.status === 'processing').length;
  const errorCount = documents.filter(d => d.status === 'error').length;
  const pendingCount = documents.filter(d => d.status === 'pending').length;

  return (
    <div className="document-list-container">
      <div className="document-list-header">
        <div className="document-list-title">
          <h3>Processed Documents ({documents.length})</h3>
          <div className="document-stats">
            {completedCount > 0 && <span className="stat-completed">{completedCount} completed</span>}
            {processingCount > 0 && <span className="stat-processing">{processingCount} processing</span>}
            {pendingCount > 0 && <span className="stat-pending">{pendingCount} pending</span>}
            {errorCount > 0 && <span className="stat-error">{errorCount} failed</span>}
          </div>
        </div>
        {documents.length > 0 && (
          <button
            className="btn-clear-all"
            onClick={onClearAll}
            title="Clear all documents"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
            Clear All
          </button>
        )}
      </div>

      <div className="document-list">
        {documents.map((doc, index) => (
          <div
            key={doc.id}
            className={`document-item ${doc.id === selectedDocumentId ? 'selected' : ''} ${doc.status}`}
          >
            <div className="document-item-header" onClick={() => onSelectDocument(doc.id)}>
              <div className="document-item-left">
                <div className="document-number">#{index + 1}</div>
                <div className="document-status">
                  {getStatusIcon(doc.status)}
                  <span className="status-text">{getStatusText(doc.status)}</span>
                </div>
              </div>

              <div className="document-item-center">
                <div className="document-filename">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  {doc.fileName}
                  <span className="file-size">{formatFileSize(doc.file?.size)}</span>
                </div>

                {doc.status === 'completed' && (
                  <>
                    <div className="document-info-brief">
                      <span className="vendor-brief">{getVendorName(doc)}</span>
                      <span className="amount-brief">{formatCurrency(getDocumentAmount(doc))}</span>
                      <span className="date-brief">{formatDate(getDocumentDate(doc))}</span>
                      {doc.categorization?.confidence !== undefined && (
                        <span className={`confidence-badge-inline ${getConfidenceClass(doc.categorization.confidence)}`}>
                          {doc.categorization.confidence.toFixed(0)}%
                        </span>
                      )}
                    </div>
                    {doc.isBankStatement && (
                      <div className="document-warning-message">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10" />
                          <line x1="12" y1="8" x2="12" y2="12" />
                          <line x1="12" y1="16" x2="12.01" y2="16" />
                        </svg>
                        <span>Bank statement detected - upload in the Bank Statement section for better results</span>
                      </div>
                    )}
                  </>
                )}

                {doc.status === 'error' && doc.error && (
                  <div className="document-error-message">{doc.error}</div>
                )}

                {doc.status === 'processing' && (
                  <div className="processing-indicator">
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${doc.progress || 0}%` }}
                      />
                    </div>
                    <span className="progress-text">{doc.progress || 0}%</span>
                  </div>
                )}
              </div>

              <div className="document-item-right">
                <button
                  className="btn-expand"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedDocId(expandedDocId === doc.id ? null : doc.id);
                  }}
                  title="Toggle details"
                >
                  <svg
                    className={expandedDocId === doc.id ? 'rotated' : ''}
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>

                <button
                  className="btn-remove"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemoveDocument(doc.id);
                  }}
                  title="Remove document"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Expanded Details */}
            {expandedDocId === doc.id && doc.status === 'completed' && doc.parsedData && (
              <div className="document-item-details">
                <div className="detail-row">
                  <span className="detail-label">Vendor:</span>
                  <span className="detail-value">{getVendorName(doc)}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Amount:</span>
                  <span className="detail-value">{formatCurrency(getDocumentAmount(doc))}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Date:</span>
                  <span className="detail-value">{formatDate(getDocumentDate(doc))}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">Document Type:</span>
                  <span className="detail-value">{doc.parsedData.documentMetadata?.documentType || 'Unknown'}</span>
                </div>
                {doc.categorization && (
                  <>
                    <div className="detail-row">
                      <span className="detail-label">Category:</span>
                      <span className="detail-value">{doc.categorization.category || 'Not categorized'}</span>
                    </div>
                    <div className="detail-row">
                      <span className="detail-label">Subcategory:</span>
                      <span className="detail-value">{doc.categorization.subcategory || 'N/A'}</span>
                    </div>
                    {doc.categorization.confidence !== undefined && (
                      <div className="detail-row">
                        <span className="detail-label">Confidence:</span>
                        <span className={`detail-value confidence-score ${getConfidenceClass(doc.categorization.confidence)}`}>
                          {doc.categorization.confidence.toFixed(1)}%
                          {doc.categorization.confidence < 70 && <span className="needs-review-badge">Needs Review</span>}
                        </span>
                      </div>
                    )}
                  </>
                )}
                <div className="detail-row">
                  <span className="detail-label">Uploaded:</span>
                  <span className="detail-value">{new Date(doc.uploadedAt).toLocaleString()}</span>
                </div>
                {doc.processedAt && (
                  <div className="detail-row">
                    <span className="detail-label">Processed:</span>
                    <span className="detail-value">{new Date(doc.processedAt).toLocaleString()}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DocumentList;
