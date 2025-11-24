import React, { useState, useEffect } from 'react';
import './ReviewQueue.css';

const ReviewQueue = () => {
  const [queueItems, setQueueItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState(null);
  const [correctionMode, setCorrectionMode] = useState(false);
  const [correctionData, setCorrectionData] = useState({
    category: '',
    subcategory: '',
    ledgerType: '',
    notes: ''
  });
  const [filterConfidence, setFilterConfidence] = useState({ min: 0, max: 70 });

  const API_BASE_URL = 'http://localhost:8000';

  // Fetch review queue items
  const fetchQueueItems = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `${API_BASE_URL}/review-queue?min_confidence=${filterConfidence.min}&max_confidence=${filterConfidence.max}`
      );
      if (response.ok) {
        const data = await response.json();
        setQueueItems(data);
      } else {
        console.error('Failed to fetch review queue');
      }
    } catch (error) {
      console.error('Error fetching review queue:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch queue statistics
  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/review-queue/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  useEffect(() => {
    fetchQueueItems();
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterConfidence]);

  // Handle approval
  const handleApprove = async (item) => {
    try {
      const response = await fetch(`${API_BASE_URL}/review-queue/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transaction_id: item.transaction_id,
          approved: true
        })
      });

      if (response.ok) {
        // Remove from queue
        setQueueItems(prev => prev.filter(i => i.id !== item.id));
        setSelectedItem(null);
        fetchStats(); // Refresh stats
        alert('Categorization approved!');
      } else {
        alert('Failed to approve categorization');
      }
    } catch (error) {
      console.error('Error approving:', error);
      alert('Error approving categorization');
    }
  };

  // Handle correction submission
  const handleCorrect = async (item) => {
    if (!correctionData.category || !correctionData.subcategory) {
      alert('Please fill in category and subcategory');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/review-queue/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transaction_id: item.transaction_id,
          approved: false,
          corrected_category: correctionData.category,
          corrected_subcategory: correctionData.subcategory,
          corrected_ledger_type: correctionData.ledgerType || item.ledger_type,
          review_notes: correctionData.notes
        })
      });

      if (response.ok) {
        // Remove from queue
        setQueueItems(prev => prev.filter(i => i.id !== item.id));
        setSelectedItem(null);
        setCorrectionMode(false);
        setCorrectionData({ category: '', subcategory: '', ledgerType: '', notes: '' });
        fetchStats();
        alert('Correction submitted! System will learn from this.');
      } else {
        alert('Failed to submit correction');
      }
    } catch (error) {
      console.error('Error submitting correction:', error);
      alert('Error submitting correction');
    }
  };

  // Get confidence badge color
  const getConfidenceBadge = (confidence) => {
    if (confidence >= 85) return 'confidence-high';
    if (confidence >= 70) return 'confidence-medium';
    if (confidence >= 50) return 'confidence-low';
    return 'confidence-critical';
  };

  // Get urgency level
  const getUrgencyLevel = (confidence) => {
    if (confidence < 50) return 'CRITICAL';
    return 'Low Priority';
  };

  return (
    <div className="review-queue-container">
      <div className="review-queue-header">
        <h2>Review Queue</h2>
        <p className="subtitle">Review and correct low-confidence categorizations</p>
      </div>

      {/* Statistics Dashboard */}
      {stats && (
        <div className="stats-dashboard">
          <div className="stat-card total">
            <h3>{stats.total_needs_review}</h3>
            <p>Total Items</p>
          </div>
          <div className="stat-card critical">
            <h3>{stats.by_urgency?.critical || 0}</h3>
            <p>Critical (&lt;50%)</p>
          </div>
          <div className="stat-card low">
            <h3>{stats.by_urgency?.low || 0}</h3>
            <p>Low Priority (50-70%)</p>
          </div>
          <div className="stat-card recent">
            <h3>{stats.recent_additions || 0}</h3>
            <p>Recent (7 days)</p>
          </div>
        </div>
      )}

      {/* Filter Controls */}
      <div className="filter-controls">
        <label>
          Min Confidence:
          <input
            type="number"
            value={filterConfidence.min}
            onChange={(e) => setFilterConfidence(prev => ({ ...prev, min: parseInt(e.target.value) }))}
            min="0"
            max="100"
          />
        </label>
        <label>
          Max Confidence:
          <input
            type="number"
            value={filterConfidence.max}
            onChange={(e) => setFilterConfidence(prev => ({ ...prev, max: parseInt(e.target.value) }))}
            min="0"
            max="100"
          />
        </label>
        <button onClick={fetchQueueItems} className="refresh-btn">Refresh</button>
      </div>

      {/* Queue Items List */}
      {loading ? (
        <div className="loading">Loading review queue...</div>
      ) : queueItems.length === 0 ? (
        <div className="empty-queue">
          <h3>All Clear!</h3>
          <p>No items need review at this confidence level.</p>
        </div>
      ) : (
        <div className="queue-items-list">
          {queueItems.map(item => (
            <div
              key={item.id}
              className={`queue-item ${selectedItem?.id === item.id ? 'selected' : ''}`}
              onClick={() => setSelectedItem(item)}
            >
              <div className="item-header">
                <div className="item-title">
                  <h4>{item.vendor_name}</h4>
                  <span className={`confidence-badge ${getConfidenceBadge(item.confidence_score)}`}>
                    {item.confidence_score.toFixed(1)}%
                  </span>
                  <span className={`urgency-badge ${item.confidence_score < 50 ? 'critical' : 'low'}`}>
                    {getUrgencyLevel(item.confidence_score)}
                  </span>
                </div>
                <div className="item-amount">${item.amount?.toFixed(2) || 'N/A'}</div>
              </div>

              <div className="item-details">
                <p><strong>Date:</strong> {item.transaction_date}</p>
                <p><strong>Description:</strong> {item.description || 'N/A'}</p>
                <p><strong>Current Category:</strong> {item.category} → {item.subcategory}</p>
                <p><strong>Reason:</strong> {item.needs_review_reason}</p>
              </div>

              {selectedItem?.id === item.id && (
                <div className="item-actions">
                  {!correctionMode ? (
                    <>
                      <button
                        className="approve-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleApprove(item);
                        }}
                      >
                        Approve as-is
                      </button>
                      <button
                        className="correct-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          setCorrectionMode(true);
                          setCorrectionData({
                            category: item.category,
                            subcategory: item.subcategory,
                            ledgerType: item.ledger_type || '',
                            notes: ''
                          });
                        }}
                      >
                        Correct Categorization
                      </button>
                    </>
                  ) : (
                    <div className="correction-form" onClick={(e) => e.stopPropagation()}>
                      <h4>Correct Categorization</h4>
                      <label>
                        Category:
                        <input
                          type="text"
                          value={correctionData.category}
                          onChange={(e) => setCorrectionData(prev => ({ ...prev, category: e.target.value }))}
                          placeholder="e.g., Operating Expenses"
                        />
                      </label>
                      <label>
                        Subcategory:
                        <input
                          type="text"
                          value={correctionData.subcategory}
                          onChange={(e) => setCorrectionData(prev => ({ ...prev, subcategory: e.target.value }))}
                          placeholder="e.g., Office Supplies"
                        />
                      </label>
                      <label>
                        Ledger Type:
                        <select
                          value={correctionData.ledgerType}
                          onChange={(e) => setCorrectionData(prev => ({ ...prev, ledgerType: e.target.value }))}
                        >
                          <option value="">Select...</option>
                          <option value="Debit">Debit</option>
                          <option value="Credit">Credit</option>
                        </select>
                      </label>
                      <label>
                        Notes (optional):
                        <textarea
                          value={correctionData.notes}
                          onChange={(e) => setCorrectionData(prev => ({ ...prev, notes: e.target.value }))}
                          placeholder="Why is this correction needed?"
                          rows="3"
                        />
                      </label>
                      <div className="correction-actions">
                        <button
                          className="submit-correction-btn"
                          onClick={() => handleCorrect(item)}
                        >
                          Submit Correction
                        </button>
                        <button
                          className="cancel-btn"
                          onClick={() => {
                            setCorrectionMode(false);
                            setCorrectionData({ category: '', subcategory: '', ledgerType: '', notes: '' });
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ReviewQueue;
