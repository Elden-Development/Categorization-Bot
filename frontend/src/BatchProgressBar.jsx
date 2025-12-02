import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "./AuthContext";
import "./App.css";

/**
 * BatchProgressBar Component
 *
 * Shows progress for async batch categorization of bank statement transactions.
 * Polls the backend status endpoint and displays real-time progress.
 */
const BatchProgressBar = ({
  bankStatementId,
  onComplete,
  onCancel,
  confidenceThreshold = 70,
  autoStart = true
}) => {
  const { token } = useAuth();
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, starting, processing, completed, failed
  const [progress, setProgress] = useState({
    processed: 0,
    total: 0,
    percentage: 0
  });
  const [results, setResults] = useState(null);
  const [failedCount, setFailedCount] = useState(0);
  const [error, setError] = useState(null);
  const [startTime, setStartTime] = useState(null);
  const [elapsedTime, setElapsedTime] = useState(0);

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // Calculate elapsed time
  useEffect(() => {
    let interval;
    if (startTime && status === 'processing') {
      interval = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [startTime, status]);

  // Format elapsed time as MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Start batch categorization
  const startBatchCategorization = useCallback(async () => {
    if (!bankStatementId || !token) return;

    setStatus('starting');
    setError(null);
    setStartTime(Date.now());

    try {
      const response = await fetch(`${API_BASE_URL}/categorize-bank-statement/async`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          bank_statement_id: bankStatementId,
          confidence_threshold: confidenceThreshold
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to start batch categorization: ${response.status}`);
      }

      const data = await response.json();
      setJobId(data.job_id);
      setStatus('processing');
      setProgress({
        processed: 0,
        total: data.total_transactions || 0,
        percentage: 0
      });
    } catch (err) {
      console.error('Error starting batch categorization:', err);
      setError(err.message);
      setStatus('failed');
    }
  }, [bankStatementId, token, confidenceThreshold, API_BASE_URL]);

  // Poll for status
  useEffect(() => {
    if (!jobId || status !== 'processing') return;

    const pollStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/batch-job/${jobId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `Failed to get status: ${response.status}`);
        }

        const data = await response.json();

        // Update progress (using backend field names)
        setProgress({
          processed: data.processed_count || 0,
          total: data.total_transactions || 0,
          percentage: Math.round(data.progress_percent || 0)
        });

        // Check if completed
        if (data.status === 'completed') {
          setStatus('completed');
          setResults(data.summary);
          setFailedCount(data.failed_count || 0);
          if (onComplete) {
            onComplete(data);
          }
        } else if (data.status === 'failed') {
          setStatus('failed');
          setError(data.error_message || 'Batch categorization failed');
        }
      } catch (err) {
        console.error('Error polling status:', err);
        // Don't fail on poll errors, just keep trying
      }
    };

    // Poll every 1 second
    const interval = setInterval(pollStatus, 1000);

    // Also poll immediately
    pollStatus();

    return () => clearInterval(interval);
  }, [jobId, status, token, API_BASE_URL, onComplete]);

  // Auto-start if enabled
  useEffect(() => {
    if (autoStart && bankStatementId && status === 'idle') {
      startBatchCategorization();
    }
  }, [autoStart, bankStatementId, status, startBatchCategorization]);

  // Handle cancel
  const handleCancel = () => {
    setStatus('idle');
    setJobId(null);
    setProgress({ processed: 0, total: 0, percentage: 0 });
    setResults(null);
    setFailedCount(0);
    setError(null);
    if (onCancel) {
      onCancel();
    }
  };

  // Don't render if idle and not auto-starting
  if (status === 'idle' && !autoStart) {
    return (
      <div className="batch-progress-container">
        <button className="btn btn-primary" onClick={startBatchCategorization}>
          Start Batch Categorization
        </button>
      </div>
    );
  }

  return (
    <div className="batch-progress-container">
      <div className="batch-progress-header">
        <div className="batch-progress-title">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          <span>Batch Categorization</span>
        </div>
        {(status === 'processing' || status === 'starting') && (
          <div className="batch-progress-time">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span>{formatTime(elapsedTime)}</span>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="batch-progress-bar-container">
        <div
          className={`batch-progress-bar ${status === 'completed' ? 'completed' : ''} ${status === 'failed' ? 'failed' : ''}`}
          style={{ width: `${progress.percentage}%` }}
        />
      </div>

      {/* Status Text */}
      <div className="batch-progress-status">
        {status === 'starting' && (
          <div className="batch-progress-status-text">
            <div className="batch-spinner" />
            <span>Starting batch categorization...</span>
          </div>
        )}

        {status === 'processing' && (
          <div className="batch-progress-status-text">
            <div className="batch-spinner" />
            <span>Processing: {progress.processed} of {progress.total} transactions ({progress.percentage}%)</span>
          </div>
        )}

        {status === 'completed' && (
          <div className="batch-progress-status-text success">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <span>Completed! {progress.total} transactions categorized in {formatTime(elapsedTime)}</span>
          </div>
        )}

        {status === 'failed' && (
          <div className="batch-progress-status-text error">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <span>Failed: {error}</span>
          </div>
        )}
      </div>

      {/* Results Summary */}
      {status === 'completed' && results && (
        <div className="batch-progress-results">
          <div className="batch-result-item">
            <div className="batch-result-value success-text">{results.auto_approved_count || 0}</div>
            <div className="batch-result-label">Auto-Approved</div>
          </div>
          <div className="batch-result-item">
            <div className="batch-result-value warning-text">{results.needs_review_count || 0}</div>
            <div className="batch-result-label">Needs Review</div>
          </div>
          <div className="batch-result-item">
            <div className="batch-result-value error-text">{failedCount}</div>
            <div className="batch-result-label">Failed</div>
          </div>
          <div className="batch-result-item">
            <div className="batch-result-value">{Math.round(results.average_confidence || 0)}%</div>
            <div className="batch-result-label">Avg Confidence</div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="batch-progress-actions">
        {(status === 'processing' || status === 'starting') && (
          <button className="btn btn-secondary" onClick={handleCancel}>
            Cancel
          </button>
        )}
        {status === 'completed' && (
          <button className="btn btn-primary" onClick={handleCancel}>
            Done
          </button>
        )}
        {status === 'failed' && (
          <>
            <button className="btn btn-secondary" onClick={handleCancel}>
              Close
            </button>
            <button className="btn btn-primary" onClick={startBatchCategorization}>
              Retry
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default BatchProgressBar;
