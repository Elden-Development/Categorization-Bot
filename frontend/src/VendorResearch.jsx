import React, { useState, useEffect } from "react";
import "./App.css";
import CategoryEditor from "./CategoryEditor";

const VendorResearch = ({ vendorName, jsonData }) => {
  const [vendorInfo, setVendorInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [transactionPurpose, setTransactionPurpose] = useState("");
  const [categorization, setCategorization] = useState(null);
  const [categorizationLoading, setCategorizationLoading] = useState(false);
  const [categorizationError, setCategorizationError] = useState("");
  const [selectedMethod, setSelectedMethod] = useState(null); // "ml" or "gemini"
  const [mlStats, setMlStats] = useState(null);
  const [savedTransactionId, setSavedTransactionId] = useState(null);

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // Load ML stats on component mount
  useEffect(() => {
    loadMLStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadMLStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/ml-stats`);
      const data = await response.json();
      if (data.success) {
        setMlStats(data.stats);
      }
    } catch (err) {
      console.error("Error loading ML stats:", err);
    }
  };

  const researchVendor = async () => {
    if (!vendorName) return;

    setLoading(true);
    setError("");
    setVendorInfo("");
    setCategorization(null);
    setSelectedMethod(null);

    try {
      console.log("Sending request to research vendor:", vendorName);

      const response = await fetch(`${API_BASE_URL}/research-vendor`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ vendor_name: vendorName }),
      });

      console.log("Received response:", response);

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const data = await response.json();
      console.log("Response data:", data);

      if (data.error) {
        setError(data.error);
        return;
      }

      if (!data.response) {
        setError("Invalid response from server");
        return;
      }

      // Simply use the text response directly
      setVendorInfo(data.response);

      // After getting vendor info, categorize the transaction using HYBRID approach
      if (jsonData) {
        categorizeTransactionHybrid(data.response);
      }

    } catch (err) {
      console.error("Error in vendor research:", err);
      setError(`Failed to research vendor: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const categorizeTransactionHybrid = async (vendorDetails) => {
    if (!vendorDetails || !jsonData) return;

    setCategorizationLoading(true);
    setCategorizationError("");
    setCategorization(null);
    setSelectedMethod(null);

    try {
      console.log("Sending request to categorize transaction (hybrid)");

      const response = await fetch(`${API_BASE_URL}/categorize-transaction-hybrid`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          vendor_info: vendorDetails,
          document_data: jsonData,
          transaction_purpose: transactionPurpose
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        setCategorizationError(data.error);
        return;
      }

      setCategorization(data);

      // Auto-select based on ML confidence if available
      if (data.mlPrediction && data.mlPrediction.hasPrediction) {
        const confidence = data.mlPrediction.confidence;
        if (confidence >= 0.7) {
          setSelectedMethod("ml"); // High confidence ML
        } else {
          setSelectedMethod("gemini"); // Low confidence, prefer Gemini
        }
      } else {
        setSelectedMethod("gemini"); // No ML prediction, use Gemini
      }

    } catch (err) {
      console.error("Error in transaction categorization:", err);
      setCategorizationError(`Failed to categorize transaction: ${err.message}`);
    } finally {
      setCategorizationLoading(false);
    }
  };

  const saveCategorizationDecision = async () => {
    if (!categorization || !selectedMethod) return;

    try {
      const selectedCategorization = selectedMethod === "ml"
        ? categorization.mlPrediction
        : categorization.geminiCategorization;

      const response = await fetch(`${API_BASE_URL}/store-categorization`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          transaction_data: jsonData,
          categorization: selectedCategorization,
          transaction_purpose: transactionPurpose,
          selected_method: selectedMethod,
          user_feedback: `User chose ${selectedMethod} prediction`
        }),
      });

      const data = await response.json();

      if (data.success) {
        alert("✓ Categorization saved! The system will learn from this decision.");
        // Store transaction ID for correction functionality
        setSavedTransactionId(data.transactionId);
        // Reload ML stats to show updated count
        loadMLStats();
      } else {
        alert("⚠ Could not save categorization: " + (data.error || "Unknown error"));
      }
    } catch (err) {
      console.error("Error saving categorization:", err);
      alert("⚠ Error saving categorization: " + err.message);
    }
  };

  const handleCorrectionSubmitted = (correctedCategorization, result) => {
    // Reload ML stats after correction
    loadMLStats();

    // Update the UI to show the corrected categorization
    alert(`✓ Correction submitted successfully!\n\nThe ML system has learned from your correction.`);
  };

  // Helper function to strip markdown formatting and clean up text
  const stripMarkdown = (text) => {
    if (!text) return '';

    return text
      // Remove bold markdown (**text** or __text__)
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/__(.+?)__/g, '$1')
      // Remove italic markdown (*text* or _text_)
      .replace(/\*(.+?)\*/g, '$1')
      .replace(/_(.+?)_/g, '$1')
      // Remove strikethrough markdown (~~text~~)
      .replace(/~~(.+?)~~/g, '$1')
      // Remove inline code markdown (`text`)
      .replace(/`(.+?)`/g, '$1')
      // Remove headers (# text)
      .replace(/^#+\s+/gm, '')
      // Clean up excessive whitespace
      .replace(/[ \t]+/g, ' ')
      .trim();
  };

  // Helper function to convert plain text with line breaks to formatted HTML
  const formatTextWithBreaks = (text) => {
    // If the text is empty, return nothing
    if (!text) return null;

    // First, strip markdown formatting
    const cleanText = stripMarkdown(text);

    // Split text by line breaks and create paragraphs
    const paragraphs = cleanText.split(/\n\n+/);

    return (
      <>
        {paragraphs.map((paragraph, index) => {
          // Check if this paragraph looks like a heading (short and ends with a colon)
          const isHeading = paragraph.length < 50 && paragraph.trim().endsWith(':');

          if (isHeading) {
            return <h4 key={index} style={{
              marginTop: '1.5rem',
              marginBottom: '0.75rem',
              fontSize: '1.125rem',
              fontWeight: '600',
              color: '#1f2937'
            }}>{paragraph}</h4>;
          }

          // For regular paragraphs, handle internal line breaks
          const lines = paragraph.split(/\n/);

          return (
            <p key={index} style={{
              marginBottom: '1rem',
              lineHeight: '1.6',
              color: '#374151'
            }}>
              {lines.map((line, lineIndex) => (
                <React.Fragment key={lineIndex}>
                  {line}
                  {lineIndex < lines.length - 1 && <br />}
                </React.Fragment>
              ))}
            </p>
          );
        })}
      </>
    );
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.85) return "#10b981"; // green
    if (confidence >= 0.7) return "#3b82f6"; // blue
    if (confidence >= 0.55) return "#f59e0b"; // yellow
    return "#ef4444"; // red
  };

  const renderMLPrediction = (mlPrediction) => {
    if (!mlPrediction || !mlPrediction.hasPrediction) {
      return (
        <div className="ml-not-available">
          <p>{mlPrediction?.reason || "No ML prediction available"}</p>
        </div>
      );
    }

    const isSelected = selectedMethod === "ml";
    const confidencePercent = (mlPrediction.confidence * 100).toFixed(1);

    return (
      <div
        className={`categorization-option ${isSelected ? "selected" : ""}`}
        onClick={() => setSelectedMethod("ml")}
        style={{
          cursor: "pointer",
          border: isSelected ? "3px solid #4f46e5" : "2px solid #e5e7eb",
          borderRadius: "0.5rem",
          padding: "1.5rem",
          backgroundColor: isSelected ? "#f0f9ff" : "white",
          transition: "all 0.2s"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h4 style={{ margin: 0, color: "#1f2937" }}>
            {isSelected && "✓ "} ML Prediction
          </h4>
          <div style={{
            padding: "0.25rem 0.75rem",
            borderRadius: "9999px",
            backgroundColor: getConfidenceColor(mlPrediction.confidence),
            color: "white",
            fontSize: "0.875rem",
            fontWeight: "600"
          }}>
            {confidencePercent}% confident
          </div>
        </div>

        <div className="categorization-header">
          <span className="category-name">
            {mlPrediction.category} - {mlPrediction.subcategory}
          </span>
          <span className="category-tag" data-type={mlPrediction.ledgerType}>
            {mlPrediction.ledgerType}
          </span>
        </div>

        <div style={{ marginTop: "1rem" }}>
          <p style={{ fontSize: "0.875rem", color: "#6b7280" }}>
            <strong>Confidence Level:</strong> {mlPrediction.confidenceLevel}
          </p>
          <p style={{ fontSize: "0.875rem", color: "#6b7280" }}>
            {mlPrediction.recommendation}
          </p>
          <p style={{ fontSize: "0.875rem", color: "#6b7280" }}>
            <strong>Based on:</strong> {mlPrediction.supportingTransactions} similar transactions
          </p>
        </div>

        {mlPrediction.examples && mlPrediction.examples.length > 0 && (
          <details style={{ marginTop: "1rem" }}>
            <summary style={{ cursor: "pointer", fontWeight: "600", color: "#4f46e5" }}>
              View Similar Transactions
            </summary>
            <div style={{ marginTop: "0.5rem" }}>
              {mlPrediction.examples.map((example, idx) => (
                <div key={idx} style={{
                  padding: "0.5rem",
                  backgroundColor: "#f9fafb",
                  borderRadius: "0.25rem",
                  marginTop: "0.5rem",
                  fontSize: "0.875rem"
                }}>
                  <p style={{ margin: "0.25rem 0" }}>
                    <strong>Vendor:</strong> {example.vendor || "Unknown"}
                  </p>
                  <p style={{ margin: "0.25rem 0" }}>
                    <strong>Amount:</strong> ${example.amount}
                  </p>
                  <p style={{ margin: "0.25rem 0" }}>
                    <strong>Similarity:</strong> {(example.score * 100).toFixed(1)}%
                  </p>
                  {example.text && (
                    <p style={{ margin: "0.25rem 0", color: "#6b7280" }}>
                      {example.text}...
                    </p>
                  )}
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    );
  };

  const renderGeminiPrediction = (geminiCategorization) => {
    if (!geminiCategorization || geminiCategorization.error) {
      return (
        <div className="gemini-not-available">
          <p>{geminiCategorization?.error || "No Gemini categorization available"}</p>
        </div>
      );
    }

    const isSelected = selectedMethod === "gemini";

    return (
      <div
        className={`categorization-option ${isSelected ? "selected" : ""}`}
        onClick={() => setSelectedMethod("gemini")}
        style={{
          cursor: "pointer",
          border: isSelected ? "3px solid #4f46e5" : "2px solid #e5e7eb",
          borderRadius: "0.5rem",
          padding: "1.5rem",
          backgroundColor: isSelected ? "#f0f9ff" : "white",
          transition: "all 0.2s"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h4 style={{ margin: 0, color: "#1f2937" }}>
            {isSelected && "✓ "} Gemini AI Categorization
          </h4>
          <div style={{
            padding: "0.25rem 0.75rem",
            borderRadius: "9999px",
            backgroundColor: "#8b5cf6",
            color: "white",
            fontSize: "0.875rem",
            fontWeight: "600"
          }}>
            AI Powered
          </div>
        </div>

        <div className="categorization-header">
          <span className="category-name">
            {geminiCategorization.category} - {geminiCategorization.subcategory}
          </span>
          <span className="category-tag" data-type={geminiCategorization.ledgerType}>
            {geminiCategorization.ledgerType}
          </span>
        </div>

        <div className="categorization-details" style={{ marginTop: "1rem" }}>
          <p><strong>Company:</strong> {geminiCategorization.companyName}</p>
          <p><strong>Description:</strong> {geminiCategorization.description}</p>

          {geminiCategorization.explanation && (
            <div className="explanation-section" style={{ marginTop: "1rem" }}>
              <h4 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>Explanation</h4>
              <div className="explanation-content" style={{ fontSize: "0.875rem", color: "#374151" }}>
                {geminiCategorization.explanation.split('\n').map((paragraph, i) => (
                  <p key={i}>{paragraph}</p>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="vendor-research">
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "1rem"
      }}>
        <h3 className="section-title">Vendor Information</h3>
        {mlStats && mlStats.totalTransactions > 0 && (
          <div style={{
            padding: "0.5rem 1rem",
            backgroundColor: "#ecfdf5",
            border: "1px solid #6ee7b7",
            borderRadius: "0.375rem",
            fontSize: "0.875rem",
            color: "#047857",
            fontWeight: "600"
          }}>
            📚 {mlStats.totalTransactions.toLocaleString()} transactions learned
          </div>
        )}
      </div>

      <div className="vendor-details">
        <p>
          <strong>Vendor Name:</strong> {vendorName || "Not available"}
        </p>

        {jsonData && jsonData.partyInformation && jsonData.partyInformation.vendor && (
          <>
            <p>
              <strong>Address:</strong> {jsonData.partyInformation.vendor.address || "Not available"}
            </p>
            <p>
              <strong>Contact:</strong> {jsonData.partyInformation.vendor.contact || "Not available"}
            </p>
            <p>
              <strong>Tax ID:</strong> {jsonData.partyInformation.vendor.taxID || "Not available"}
            </p>
          </>
        )}
      </div>

      {/* Transaction Purpose Input */}
      <div className="form-group">
        <label htmlFor="transactionPurpose" className="form-label">Transaction Purpose (Optional)</label>
        <textarea
          id="transactionPurpose"
          value={transactionPurpose}
          onChange={(e) => setTransactionPurpose(e.target.value)}
          placeholder="Describe what this invoice is for (e.g., 'gym equipment', 'office supplies', 'consulting services'). This helps with accurate categorization."
          className="form-control"
          rows="3"
          style={{
            width: '100%',
            padding: '0.75rem',
            borderRadius: '0.375rem',
            border: '1px solid #d1d5db',
            fontSize: '1rem',
            marginBottom: '1rem',
            fontFamily: 'inherit',
            resize: 'vertical'
          }}
        />
      </div>

      <div className="info-message" style={{
        padding: '0.75rem',
        backgroundColor: '#f0f9ff',
        border: '1px solid #bae6fd',
        borderRadius: '0.375rem',
        marginBottom: '1rem',
        fontSize: '0.875rem',
        color: '#0369a1'
      }}>
        <strong>🤖 Hybrid AI + ML:</strong> This system uses both Machine Learning (patterns from historical data)
        and Gemini AI (contextual understanding) to provide the best categorization.
      </div>

      <button
        onClick={researchVendor}
        className="btn research-btn"
        disabled={loading || !vendorName}
      >
        {loading ? (
          <span className="spinner-button">
            <svg className="spinner-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="2" x2="12" y2="6" />
              <line x1="12" y1="18" x2="12" y2="22" />
              <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
              <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
              <line x1="2" y1="12" x2="6" y2="12" />
              <line x1="18" y1="12" x2="22" y2="12" />
              <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
              <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
            </svg>
            Researching...
          </span>
        ) : (
          <>
            <svg className="btn-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            Research & Categorize
          </>
        )}
      </button>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {vendorInfo && (
        <div className="vendor-info-wrapper">
          <div className="vendor-info">
            {formatTextWithBreaks(vendorInfo)}
          </div>
        </div>
      )}

      {/* Financial Categorization Results */}
      {categorizationLoading && (
        <div className="financial-categorization">
          <h3 className="section-title">Financial Categorization</h3>
          <div className="loading-indicator">
            <svg className="spinner-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="2" x2="12" y2="6" />
              <line x1="12" y1="18" x2="12" y2="22" />
              <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
              <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
              <line x1="2" y1="12" x2="6" y2="12" />
              <line x1="18" y1="12" x2="22" y2="12" />
              <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
              <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
            </svg>
            Analyzing with ML and AI...
          </div>
        </div>
      )}

      {categorizationError && (
        <div className="financial-categorization">
          <h3 className="section-title">Financial Categorization</h3>
          <div className="error-message">
            {categorizationError}
          </div>
        </div>
      )}

      {categorization && (
        <div className="financial-categorization">
          <h3 className="section-title">
            Financial Categorization - Choose Your Preferred Method
          </h3>

          <div style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "1.5rem",
            marginBottom: "1.5rem"
          }}>
            {renderMLPrediction(categorization.mlPrediction)}
            {renderGeminiPrediction(categorization.geminiCategorization)}
          </div>

          {selectedMethod && (
            <div style={{ textAlign: "center" }}>
              <button
                onClick={saveCategorizationDecision}
                style={{
                  padding: "0.75rem 2rem",
                  backgroundColor: "#10b981",
                  color: "white",
                  border: "none",
                  borderRadius: "0.5rem",
                  fontSize: "1rem",
                  fontWeight: "600",
                  cursor: "pointer",
                  boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
                  transition: "all 0.2s"
                }}
                onMouseOver={(e) => e.target.style.backgroundColor = "#059669"}
                onMouseOut={(e) => e.target.style.backgroundColor = "#10b981"}
              >
                💾 Save & Learn from This Decision
              </button>
              <p style={{ marginTop: "0.5rem", fontSize: "0.875rem", color: "#6b7280" }}>
                Your choice will improve future predictions
              </p>
            </div>
          )}

          {/* Category Editor for corrections - shown after saving */}
          {savedTransactionId && selectedMethod && (
            <div style={{ marginTop: "2rem" }}>
              <CategoryEditor
                currentCategorization={
                  selectedMethod === "ml"
                    ? categorization.mlPrediction
                    : categorization.geminiCategorization
                }
                onSubmitCorrection={handleCorrectionSubmitted}
                transactionData={jsonData}
                transactionPurpose={transactionPurpose}
                transactionId={savedTransactionId}
              />
              <div style={{
                marginTop: "1rem",
                padding: "0.75rem",
                backgroundColor: "#dbeafe",
                border: "1px solid #60a5fa",
                borderRadius: "0.375rem",
                fontSize: "0.875rem",
                color: "#1e40af"
              }}>
                <strong>💡 Tip:</strong> Found a mistake? Use the editor above to correct the categorization.
                Your corrections help the ML system learn and improve!
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VendorResearch;
