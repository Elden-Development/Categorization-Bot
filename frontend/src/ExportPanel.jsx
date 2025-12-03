import React, { useState } from "react";
import { useAuth } from "./AuthContext";
import "./App.css";

/**
 * ExportPanel Component
 *
 * Allows users to export categorized bank statement transactions to CSV or Excel format.
 * Supports filtering by approval status, confidence level, etc.
 */
const ExportPanel = ({ bankStatementId, onExportComplete }) => {
  const { token } = useAuth();
  const [format, setFormat] = useState('csv');
  const [filter, setFilter] = useState('all');
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState(null);

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  const filterOptions = [
    { value: 'all', label: 'All Transactions', description: 'Export all transactions' },
    { value: 'approved', label: 'Approved Only', description: 'Only approved transactions' },
    { value: 'needs_review', label: 'Needs Review', description: 'Low confidence or not approved' },
    { value: 'uncategorized', label: 'Uncategorized', description: 'Transactions without categories' },
    { value: 'high_confidence', label: 'High Confidence', description: 'Above confidence threshold' },
    { value: 'low_confidence', label: 'Low Confidence', description: 'Below confidence threshold' },
  ];

  const handleExport = async () => {
    if (!bankStatementId || !token) return;

    setIsExporting(true);
    setError(null);

    try {
      // Build URL based on format
      const endpoint = format === 'excel'
        ? `${API_BASE_URL}/export-statement/${bankStatementId}/excel`
        : `${API_BASE_URL}/export-statement/${bankStatementId}`;

      const url = `${endpoint}?filter=${filter}`;

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Export failed: ${response.status}`);
      }

      // Get filename from Content-Disposition header or generate one
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `export_${bankStatementId}_${filter}.${format === 'excel' ? 'xlsx' : 'csv'}`;
      if (contentDisposition) {
        const matches = contentDisposition.match(/filename=(.+)/);
        if (matches && matches[1]) {
          filename = matches[1].replace(/"/g, '');
        }
      }

      // Download the file
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      if (onExportComplete) {
        onExportComplete({ format, filter, filename });
      }
    } catch (err) {
      console.error('Export error:', err);
      setError(err.message);
    } finally {
      setIsExporting(false);
    }
  };

  if (!bankStatementId) {
    return null;
  }

  return (
    <div className="export-panel">
      <div className="export-panel-header">
        <div className="export-panel-title">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          <span>Export Transactions</span>
        </div>
      </div>

      <div className="export-panel-content">
        {/* Format Selection */}
        <div className="export-option-group">
          <label className="export-option-label">Export Format</label>
          <div className="export-format-buttons">
            <button
              className={`export-format-btn ${format === 'csv' ? 'active' : ''}`}
              onClick={() => setFormat('csv')}
              type="button"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              <span>CSV</span>
            </button>
            <button
              className={`export-format-btn ${format === 'excel' ? 'active' : ''}`}
              onClick={() => setFormat('excel')}
              type="button"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <rect x="8" y="12" width="8" height="6" rx="1" />
              </svg>
              <span>Excel</span>
            </button>
          </div>
        </div>

        {/* Filter Selection */}
        <div className="export-option-group">
          <label className="export-option-label">Filter Transactions</label>
          <div className="export-filter-options">
            {filterOptions.map((option) => (
              <label
                key={option.value}
                className={`export-filter-option ${filter === option.value ? 'selected' : ''}`}
              >
                <input
                  type="radio"
                  name="export-filter"
                  value={option.value}
                  checked={filter === option.value}
                  onChange={(e) => setFilter(e.target.value)}
                />
                <div className="export-filter-content">
                  <span className="export-filter-label">{option.label}</span>
                  <span className="export-filter-description">{option.description}</span>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="export-error">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Export Button */}
      <div className="export-panel-actions">
        <button
          className="btn btn-primary export-btn"
          onClick={handleExport}
          disabled={isExporting}
        >
          {isExporting ? (
            <>
              <div className="export-spinner" />
              <span>Exporting...</span>
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              <span>Export {format === 'excel' ? 'Excel' : 'CSV'}</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default ExportPanel;
