import React, { useState, useRef, useEffect } from "react";
import "./App.css";
import VendorResearch from "./VendorResearch";
import SchemaSelector from "./SchemaSelector";
import BankReconciliation from "./BankReconciliation";
import DocumentList from "./DocumentList";
import BatchProgressBar from "./BatchProgressBar";
import ExportPanel from "./ExportPanel";
import { useAuth } from "./AuthContext";

const PDFProcessor = () => {
  // Auth context - always call the hook unconditionally
  const authContext = useAuth();
  const token = authContext?.token || null;
  // Note: user available via authContext?.user if needed

  // Batch processing state
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const [processingQueue, setProcessingQueue] = useState([]);
  const [isProcessingBatch, setIsProcessingBatch] = useState(false);

  // Bank reconciliation state
  const [bankFile, setBankFile] = useState(null);
  const [reconciliationResults, setReconciliationResults] = useState(null);
  const [reconciliationLoading, setReconciliationLoading] = useState(false);

  // Bank statement batch categorization state
  const [bankStatementId, setBankStatementId] = useState(null);
  const [showBatchProgress, setShowBatchProgress] = useState(false);
  const [batchCategorizationComplete, setBatchCategorizationComplete] = useState(false);

  // UI state
  const [dragActive, setDragActive] = useState(false);
  const [bankDragActive, setBankDragActive] = useState(false);
  const [overlayActive, setOverlayActive] = useState(false);
  const [selectedSchema, setSelectedSchema] = useState("generic");
  const [message, setMessage] = useState("");

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // Refs
  const fileInputRef = useRef(null);
  const bankFileInputRef = useRef(null);
  const dropContainerRef = useRef(null);
  const bankDropContainerRef = useRef(null);

  // Load documents from localStorage on mount
  useEffect(() => {
    const savedDocuments = localStorage.getItem('processedDocuments');
    if (savedDocuments) {
      try {
        const parsed = JSON.parse(savedDocuments);
        // Filter out file objects (can't be serialized)
        const documentsWithoutFiles = parsed.map(doc => ({
          ...doc,
          file: null
        }));
        setDocuments(documentsWithoutFiles);
      } catch (error) {
        console.error('Error loading saved documents:', error);
      }
    }
  }, []);

  // Save documents to localStorage whenever they change
  useEffect(() => {
    if (documents.length > 0) {
      // Remove file objects before saving (they can't be serialized)
      const documentsToSave = documents.map(doc => ({
        ...doc,
        file: null // Remove File object
      }));
      localStorage.setItem('processedDocuments', JSON.stringify(documentsToSave));
    } else {
      localStorage.removeItem('processedDocuments');
    }
  }, [documents]);

  // Get selected document
  const selectedDocument = documents.find(doc => doc.id === selectedDocumentId);

  // Add files to document queue
  const addFilesToQueue = (files) => {
    const newDocuments = files.map(file => ({
      id: `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      fileName: file.name,
      file: file,
      status: 'pending',
      progress: 0,
      parsedData: null,
      categorization: null,
      uploadedAt: new Date().toISOString(),
      processedAt: null,
      error: null
    }));

    setDocuments(prev => [...prev, ...newDocuments]);
    setProcessingQueue(prev => [...prev, ...newDocuments.map(d => d.id)]);
    setMessage(`${files.length} file(s) added to queue`);

    // Auto-select first document if none selected
    if (!selectedDocumentId && newDocuments.length > 0) {
      setSelectedDocumentId(newDocuments[0].id);
    }
  };

  // Process documents sequentially
  useEffect(() => {
    if (processingQueue.length > 0 && !isProcessingBatch) {
      const nextDocId = processingQueue[0];
      processDocument(nextDocId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processingQueue, isProcessingBatch]);

  // Process a single document
  const processDocument = async (docId) => {
    setIsProcessingBatch(true);

    const doc = documents.find(d => d.id === docId);
    if (!doc || !doc.file) {
      // Remove from queue and continue
      setProcessingQueue(prev => prev.filter(id => id !== docId));
      setIsProcessingBatch(false);
      return;
    }

    // Update status to processing
    updateDocumentStatus(docId, 'processing', 0);

    try {
      // Check if file object exists (it won't exist for documents loaded from localStorage)
      if (!doc.file) {
        throw new Error('File no longer available. Please re-upload the document to process it again.');
      }

      const formData = new FormData();
      formData.append("file", doc.file);
      formData.append("schema", selectedSchema);

      // Simulate progress
      updateDocumentStatus(docId, 'processing', 25);

      const res = await fetch(`${API_BASE_URL}/process-pdf`, {
        method: "POST",
        body: formData,
      });

      updateDocumentStatus(docId, 'processing', 75);

      // Handle HTTP errors
      if (!res.ok) {
        let errorMessage = `Server responded with status: ${res.status}`;
        try {
          const errorData = await res.json();
          // FastAPI returns error details in 'detail' field
          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (errorData.error) {
            errorMessage = errorData.error;
          }
        } catch (e) {
          // If we can't parse error response, use the status message
          console.warn('Could not parse error response:', e);
        }
        throw new Error(errorMessage);
      }

      const data = await res.json();

      // Validate that response field exists and is not undefined/null
      if (!data.response || data.response === 'undefined' || data.response === 'null') {
        throw new Error('Server returned empty or invalid response. The document may be unreadable.');
      }

      // Parse the JSON response with error handling
      let jsonData;
      try {
        jsonData = JSON.parse(data.response);
      } catch (parseError) {
        throw new Error(`Failed to parse server response: ${parseError.message}`);
      }

      // Check if the parsed data contains an error
      if (jsonData && jsonData.error) {
        throw new Error(jsonData.detail || jsonData.error);
      }

      updateDocumentStatus(docId, 'processing', 85);

      // Auto-categorize with smart categorization (confidence-aware)
      let categorization = null;
      try {
        const vendorName = jsonData.documentMetadata?.source?.name ||
                          jsonData.partyInformation?.vendor?.name ||
                          'Unknown Vendor';

        const catResponse = await fetch(`${API_BASE_URL}/categorize-transaction-smart`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            vendor_name: vendorName,
            document_data: jsonData,
            transaction_purpose: jsonData.documentMetadata?.documentType || '',
            confidence_threshold: 70,
            auto_research: true
          })
        });

        if (catResponse.ok) {
          const catData = await catResponse.json();
          categorization = {
            category: catData.final_categorization?.category || catData.initial_categorization?.category,
            subcategory: catData.final_categorization?.subcategory || catData.initial_categorization?.subcategory,
            ledgerType: catData.final_categorization?.ledgerType || catData.initial_categorization?.ledgerType,
            confidence: catData.confidence_metrics?.final_confidence || catData.initial_categorization?.confidence || 0,
            needsReview: catData.needs_manual_review || false,
            researchPerformed: catData.research_performed || false
          };
        }
      } catch (catError) {
        console.error('Error during smart categorization:', catError);
        // Continue without categorization if it fails
      }

      updateDocumentStatus(docId, 'processing', 100);

      // Check if this is a bank statement uploaded to the wrong section
      const detectedDocType = jsonData.documentMetadata?.documentType?.toLowerCase() || '';
      const isBankStatement = detectedDocType.includes('bank') ||
                              detectedDocType.includes('statement') ||
                              detectedDocType === 'bankstatement';

      // Update document with parsed data and categorization
      setDocuments(prev => prev.map(d =>
        d.id === docId
          ? {
              ...d,
              status: 'completed',
              progress: 100,
              parsedData: jsonData,
              categorization: categorization,
              processedAt: new Date().toISOString(),
              error: null,
              isBankStatement: isBankStatement // Flag for UI warning
            }
          : d
      ));

      // Show appropriate message based on document type
      if (isBankStatement) {
        setMessage(`"${doc.fileName}" appears to be a bank statement. For best results, please upload it in the Bank Statement section (right side) to parse individual transactions.`);
      } else {
        const confidenceMsg = categorization?.confidence
          ? ` (Confidence: ${categorization.confidence.toFixed(1)}%)`
          : '';
        setMessage(`Document "${doc.fileName}" processed successfully${confidenceMsg}`);
      }

    } catch (error) {
      console.error(`Error processing document ${doc.fileName}:`, error);
      setDocuments(prev => prev.map(d =>
        d.id === docId
          ? {
              ...d,
              status: 'error',
              progress: 0,
              error: error.message,
              processedAt: new Date().toISOString()
            }
          : d
      ));
      setMessage(`Error processing "${doc.fileName}": ${error.message}`);
    } finally {
      // Remove from queue and continue to next
      setProcessingQueue(prev => prev.filter(id => id !== docId));
      setIsProcessingBatch(false);
    }
  };

  // Update document status
  const updateDocumentStatus = (docId, status, progress = 0) => {
    setDocuments(prev => prev.map(d =>
      d.id === docId ? { ...d, status, progress } : d
    ));
  };

  // Select a document to view
  const handleSelectDocument = (docId) => {
    setSelectedDocumentId(docId);
  };

  // Remove a document
  const handleRemoveDocument = (docId) => {
    setDocuments(prev => prev.filter(d => d.id !== docId));

    if (selectedDocumentId === docId) {
      const remaining = documents.filter(d => d.id !== docId);
      setSelectedDocumentId(remaining.length > 0 ? remaining[0].id : null);
    }
  };

  // Clear all documents
  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear all documents? This cannot be undone.')) {
      setDocuments([]);
      setSelectedDocumentId(null);
      setProcessingQueue([]);
      setReconciliationResults(null);
      setMessage('All documents cleared');
    }
  };

  // Handle drag events for the entire page
  useEffect(() => {
    const handleDragEnter = (e) => {
      e.preventDefault();
      e.stopPropagation();
      setOverlayActive(true);
    };

    const handleDragOver = (e) => {
      e.preventDefault();
      e.stopPropagation();
    };

    const handleDragLeave = (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.currentTarget.contains(e.relatedTarget)) return;
      setOverlayActive(false);
    };

    const handleDrop = (e) => {
      e.preventDefault();
      e.stopPropagation();
      setOverlayActive(false);

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const droppedFiles = Array.from(e.dataTransfer.files);

        // Filter valid files (PDF or image)
        const validFiles = droppedFiles.filter(file =>
          file.type.includes('pdf') || file.type.includes('image/')
        );

        if (validFiles.length === 0) {
          alert("Please upload PDF or image files only.");
          return;
        }

        if (validFiles.length < droppedFiles.length) {
          alert(`${droppedFiles.length - validFiles.length} file(s) were skipped (invalid type).`);
        }

        // Add files to document queue
        addFilesToQueue(validFiles);
        e.dataTransfer.clearData();
      }
    };

    // Add event listeners to the document
    document.addEventListener("dragenter", handleDragEnter);
    document.addEventListener("dragover", handleDragOver);
    document.addEventListener("dragleave", handleDragLeave);
    document.addEventListener("drop", handleDrop);

    // Clean up
    return () => {
      document.removeEventListener("dragenter", handleDragEnter);
      document.removeEventListener("dragover", handleDragOver);
      document.removeEventListener("dragleave", handleDragLeave);
      document.removeEventListener("drop", handleDrop);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle drag events specifically for the first drop zone
  const handleDragEnterForZone = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeaveForZone = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (dropContainerRef.current && !dropContainerRef.current.contains(e.relatedTarget)) {
      setDragActive(false);
    }
  };

  const handleDropForZone = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);

      // Filter valid files (PDF or image)
      const validFiles = droppedFiles.filter(file =>
        file.type.includes('pdf') || file.type.includes('image/')
      );

      if (validFiles.length === 0) {
        alert("Please upload PDF or image files only.");
        return;
      }

      if (validFiles.length < droppedFiles.length) {
        alert(`${droppedFiles.length - validFiles.length} file(s) were skipped (invalid type).`);
      }

      // Add files to document queue
      addFilesToQueue(validFiles);
      e.dataTransfer.clearData();
    }
  };

  // Handle drag events specifically for the bank statement drop zone
  const handleBankDragEnterForZone = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setBankDragActive(true);
  };

  const handleBankDragLeaveForZone = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (bankDropContainerRef.current && !bankDropContainerRef.current.contains(e.relatedTarget)) {
      setBankDragActive(false);
    }
  };

  const handleBankDropForZone = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setBankDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      // Check if file type is valid (CSV or PDF)
      if (droppedFile.type.includes('csv') || droppedFile.type.includes('pdf')) {
        setBankFile(droppedFile);
        
        // Make the file input element reference the dropped file
        if (bankFileInputRef.current) {
          // Create a new DataTransfer object
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(droppedFile);
          
          // Assign the DataTransfer files to the file input
          bankFileInputRef.current.files = dataTransfer.files;
        }
        
        e.dataTransfer.clearData();
      } else {
        alert("Please upload a CSV or PDF bank statement.");
      }
    }
  };

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length > 0) {
      // Filter valid files
      const validFiles = selectedFiles.filter(file =>
        file.type.includes('pdf') || file.type.includes('image/')
      );

      if (validFiles.length === 0) {
        alert("Please select PDF or image files only.");
        return;
      }

      addFilesToQueue(validFiles);
    }
  };

  const handleBankFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setBankFile(selectedFile);
    }
  };

  const handleSchemaChange = (schema) => {
    setSelectedSchema(schema);
  };

  // Documents are now auto-processed when added to queue via processDocument()

  // Bank statement reconciliation function (works with ALL completed documents)
  const handleReconcile = async (e) => {
    e.preventDefault();
    if (!bankFile) {
      alert("Please select a bank statement file.");
      return;
    }

    const completedDocs = documents.filter(d => d.status === 'completed' && d.parsedData);
    if (completedDocs.length === 0) {
      alert("Please process at least one document before reconciling.");
      return;
    }

    setReconciliationLoading(true);
    setReconciliationResults(null);

    try {
      // Step 1: Parse bank statement
      const formData = new FormData();
      formData.append("file", bankFile);

      const parseRes = await fetch(`${API_BASE_URL}/parse-bank-statement`, {
        method: "POST",
        body: formData,
      });

      if (!parseRes.ok) {
        throw new Error(`Failed to parse bank statement: ${parseRes.status}`);
      }

      const parseData = await parseRes.json();

      if (!parseData.success || !parseData.transactions) {
        throw new Error("Failed to extract transactions from bank statement");
      }

      // Step 2: Reconcile ALL completed documents with bank transactions
      const allParsedData = completedDocs.map(d => d.parsedData);

      const reconcileRes = await fetch(`${API_BASE_URL}/reconcile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          documents: allParsedData, // Reconcile ALL completed documents
          bank_transactions: parseData.transactions,
          auto_match_threshold: 90 // Auto-match if score >= 90%
        }),
      });

      if (!reconcileRes.ok) {
        throw new Error(`Reconciliation failed: ${reconcileRes.status}`);
      }

      const reconcileData = await reconcileRes.json();

      if (!reconcileData.success) {
        throw new Error("Reconciliation returned unsuccessful status");
      }

      setReconciliationResults(reconcileData.results);
      setMessage(`Reconciled ${completedDocs.length} document(s) against bank statement`);

    } catch (error) {
      console.error("Reconciliation error:", error);
      alert("Reconciliation error: " + error.message);
    } finally {
      setReconciliationLoading(false);
    }
  };

  // Handle accepting a suggested match
  const handleAcceptSuggestion = async (suggestion) => {
    try {
      const res = await fetch(`${API_BASE_URL}/manual-match`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document: suggestion.document,
          transaction: suggestion.transaction
        }),
      });

      if (!res.ok) {
        throw new Error(`Manual match failed: ${res.status}`);
      }

      const data = await res.json();

      if (data.success) {
        // Update reconciliation results by moving from suggested to matched
        setReconciliationResults(prev => {
          const newMatched = [...prev.matched, data.match];
          const newSuggested = prev.suggested_matches.filter(s =>
            s.transaction.transaction_id !== suggestion.transaction.transaction_id
          );

          return {
            ...prev,
            matched: newMatched,
            suggested_matches: newSuggested,
            summary: {
              ...prev.summary,
              matched_count: newMatched.length,
              suggested_matches_count: newSuggested.length,
              reconciliation_rate: Math.round(
                (newMatched.length / prev.summary.total_documents) * 100 * 100
              ) / 100
            }
          };
        });

        alert("Match accepted successfully!");
      }
    } catch (error) {
      console.error("Error accepting match:", error);
      alert("Failed to accept match: " + error.message);
    }
  };

  // Handle manual matching
  const handleManualMatch = async (document, transaction) => {
    try {
      const res = await fetch(`${API_BASE_URL}/manual-match`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document: document,
          transaction: transaction
        }),
      });

      if (!res.ok) {
        throw new Error(`Manual match failed: ${res.status}`);
      }

      const data = await res.json();

      if (data.success) {
        // Refresh reconciliation - re-run the reconciliation
        alert("Manual match created successfully! Refreshing reconciliation...");
        // You might want to re-trigger reconciliation here
      }
    } catch (error) {
      console.error("Error creating manual match:", error);
      alert("Failed to create manual match: " + error.message);
    }
  };

  // Upload bank statement to database and get statement ID (requires auth)
  const uploadBankStatementToDatabase = async () => {
    if (!bankFile || !token) {
      return null;
    }

    try {
      const formData = new FormData();
      formData.append("file", bankFile);

      // Use the parse-bank-statement endpoint which saves to DB when authenticated
      const response = await fetch(`${API_BASE_URL}/parse-bank-statement`, {
        method: "POST",
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Upload failed: ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "Failed to parse bank statement");
      }

      // The endpoint returns statement_id when user is authenticated
      if (!data.statement_id) {
        throw new Error("No statement ID returned. Please ensure you are logged in.");
      }

      return data.statement_id;
    } catch (error) {
      console.error("Error uploading bank statement:", error);
      throw error;
    }
  };

  // Handle batch categorize button click
  const handleBatchCategorize = async () => {
    if (!token) {
      alert("Please log in to use batch categorization.");
      return;
    }

    if (!bankFile) {
      alert("Please select a bank statement file first.");
      return;
    }

    try {
      setMessage("Uploading bank statement...");

      // Upload bank statement to database if not already uploaded
      let statementId = bankStatementId;
      if (!statementId) {
        statementId = await uploadBankStatementToDatabase();
        setBankStatementId(statementId);
      }

      if (statementId) {
        setShowBatchProgress(true);
        setBatchCategorizationComplete(false);
        setMessage("Starting batch categorization...");
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
      alert("Failed to start batch categorization: " + error.message);
    }
  };

  // Handle batch categorization completion
  const handleBatchComplete = (data) => {
    setBatchCategorizationComplete(true);
    setMessage(`Batch categorization complete! ${data.processed || 0} transactions processed.`);

    // Optionally refresh the page or update state to show results
    if (data.results) {
      console.log("Batch results:", data.results);
    }
  };

  // Handle batch categorization cancel
  const handleBatchCancel = () => {
    setShowBatchProgress(false);
    setBankStatementId(null);
    setMessage("Batch categorization cancelled.");
  };

  return (
    <div className="app-container">
      {/* Full-screen drop overlay */}
      <div className={`drop-overlay ${overlayActive ? 'active' : ''}`}>
        <svg className="drop-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <div className="drop-text">Drop your file here to process</div>
      </div>
    
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
              <polyline points="14 2 14 8 20 8" />
              <path d="M8 13h2" />
              <path d="M8 17h2" />
              <path d="M14 13h2" />
              <path d="M14 17h2" />
            </svg>
            <span>DocuExtract</span>
          </div>
        </div>
      </header>

      <div className="container">
        <div className="section-title">Document Processing</div>
        <h1>Extract & Reconcile Financial Document Data</h1>
        <p className="description">
          Upload your financial documents to extract structured information, then reconcile with your bank statements for complete financial verification.
        </p>

        <div className="two-column-layout">
          {/* LEFT COLUMN - DOCUMENT UPLOAD */}
          <div className="card extraction-card">
            <div className="extraction-header">
              <div className="extraction-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
              </div>
              <div>
                <div className="section-title">1. Document Extraction</div>
                <h2>Upload Document</h2>
              </div>
            </div>

            <p className="description">
              Upload invoices, receipts, or financial documents to automatically extract and categorize data.
            </p>

            {/* Schema selector */}
            <SchemaSelector
              selectedSchema={selectedSchema}
              onSchemaChange={handleSchemaChange}
            />

            <div
              ref={dropContainerRef}
              className={`document-upload-zone ${dragActive ? 'drag-active' : ''}`}
              onDragEnter={handleDragEnterForZone}
              onDragOver={(e) => e.preventDefault()}
              onDragLeave={handleDragLeaveForZone}
              onDrop={handleDropForZone}
            >
              <div className="document-upload-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <div className="document-upload-text">
                <span className="document-upload-title">Drop your documents here</span>
                <span className="document-upload-subtitle">or click to browse</span>
              </div>
              <div className="document-upload-formats">
                <span className="format-badge">PDF</span>
                <span className="format-badge">JPG</span>
                <span className="format-badge">PNG</span>
                <span className="format-size">Max 10MB each</span>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                id="pdfFile"
                accept="application/pdf, image/*"
                className="file-input"
                onChange={handleFileChange}
                multiple
              />
            </div>

            {/* Document Processing Status */}
            <div className="extraction-status">
              <div className="status-item">
                <span className="status-label">In Queue</span>
                <span className="status-value">{documents.filter(d => d.status === 'pending' || d.status === 'processing').length}</span>
              </div>
              <div className="status-divider"></div>
              <div className="status-item">
                <span className="status-label">Completed</span>
                <span className={`status-value ${documents.filter(d => d.status === 'completed').length > 0 ? 'ready' : ''}`}>
                  {documents.filter(d => d.status === 'completed').length}
                </span>
              </div>
              <div className="status-divider"></div>
              <div className="status-item">
                <span className="status-label">Failed</span>
                <span className={`status-value ${documents.filter(d => d.status === 'error').length > 0 ? 'error' : ''}`}>
                  {documents.filter(d => d.status === 'error').length}
                </span>
              </div>
            </div>

            {isProcessingBatch && (
              <div className="processing-indicator">
                <div className="processing-spinner">
                  <svg className="spinner-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" opacity="0.25" />
                    <path d="M12 2a10 10 0 0 1 10 10" />
                  </svg>
                </div>
                <span>Processing documents...</span>
              </div>
            )}

            {message && !isProcessingBatch && (
              <div className="extraction-message">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                <span>{message}</span>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN - BANK STATEMENT */}
          <div className="card reconciliation-card">
            <div className="reconciliation-header">
              <div className="reconciliation-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="3" y1="9" x2="21" y2="9"></line>
                  <line x1="9" y1="21" x2="9" y2="9"></line>
                </svg>
              </div>
              <div>
                <div className="section-title">2. Reconciliation</div>
                <h2>Bank Statement</h2>
              </div>
            </div>

            <p className="description">
              Upload your bank statement to reconcile against your processed documents and verify transactions.
            </p>

            <form onSubmit={handleReconcile}>
              <div
                ref={bankDropContainerRef}
                className={`bank-upload-zone ${bankDragActive ? 'drag-active' : ''} ${bankFile ? 'has-file' : ''}`}
                onDragEnter={handleBankDragEnterForZone}
                onDragOver={(e) => e.preventDefault()}
                onDragLeave={handleBankDragLeaveForZone}
                onDrop={handleBankDropForZone}
              >
                {!bankFile ? (
                  <>
                    <div className="bank-upload-icon">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                      </svg>
                    </div>
                    <div className="bank-upload-text">
                      <span className="bank-upload-title">Drop your bank statement here</span>
                      <span className="bank-upload-subtitle">or click to browse</span>
                    </div>
                    <div className="bank-upload-formats">
                      <span className="format-badge">CSV</span>
                      <span className="format-badge">PDF</span>
                      <span className="format-size">Max 10MB</span>
                    </div>
                  </>
                ) : (
                  <div className="bank-file-selected">
                    <div className="bank-file-icon">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                      </svg>
                    </div>
                    <div className="bank-file-info">
                      <span className="bank-file-name">{bankFile.name}</span>
                      <span className="bank-file-size">{(bankFile.size / 1024).toFixed(1)} KB</span>
                    </div>
                    <button
                      type="button"
                      className="bank-file-remove"
                      onClick={(e) => { e.stopPropagation(); setBankFile(null); }}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                )}
                <input
                  ref={bankFileInputRef}
                  type="file"
                  id="bankFile"
                  accept=".csv, application/pdf"
                  className="file-input"
                  onChange={handleBankFileChange}
                />
              </div>

              <div className="reconciliation-status">
                <div className="status-item">
                  <span className="status-label">Documents Ready</span>
                  <span className="status-value">{documents.filter(d => d.status === 'completed').length}</span>
                </div>
                <div className="status-divider"></div>
                <div className="status-item">
                  <span className="status-label">Statement</span>
                  <span className={`status-value ${bankFile ? 'ready' : 'pending'}`}>
                    {bankFile ? 'Uploaded' : 'Pending'}
                  </span>
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-reconcile"
                disabled={!bankFile || documents.filter(d => d.status === 'completed').length === 0 || reconciliationLoading}
              >
                {reconciliationLoading ? (
                  <div className="spinner-button">
                    <svg className="spinner-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" opacity="0.25" />
                      <path d="M12 2a10 10 0 0 1 10 10" />
                    </svg>
                    <span>Reconciling Transactions...</span>
                  </div>
                ) : (
                  <>
                    <svg className="btn-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 11l3 3L22 4" />
                      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                    </svg>
                    <span>Reconcile Transactions</span>
                  </>
                )}
              </button>
            </form>

            {/* Batch Categorize Button - only shown when user is authenticated */}
            {token && bankFile && !showBatchProgress && (
              <button
                type="button"
                className="btn"
                style={{ marginTop: '0.75rem', backgroundColor: '#7c3aed' }}
                onClick={handleBatchCategorize}
              >
                <svg className="btn-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
                Batch Categorize All Transactions
              </button>
            )}

            {/* Batch Progress Bar */}
            {showBatchProgress && bankStatementId && (
              <BatchProgressBar
                bankStatementId={bankStatementId}
                onComplete={handleBatchComplete}
                onCancel={handleBatchCancel}
                confidenceThreshold={70}
                autoStart={true}
              />
            )}

            {/* Export Panel - shows when batch categorization is complete */}
            {token && bankStatementId && batchCategorizationComplete && (
              <ExportPanel
                bankStatementId={bankStatementId}
                onExportComplete={(result) => {
                  setMessage(`Successfully exported ${result.filename}`);
                }}
              />
            )}
          </div>
        </div>

        {/* Document List - shows all processed documents */}
        {documents.length > 0 && (
          <DocumentList
            documents={documents}
            selectedDocumentId={selectedDocumentId}
            onSelectDocument={handleSelectDocument}
            onRemoveDocument={handleRemoveDocument}
            onClearAll={handleClearAll}
          />
        )}

        {/* Vendor Research section - for selected document */}
        {selectedDocument && selectedDocument.parsedData && (
          <VendorResearch
            vendorName={
              selectedDocument.parsedData.documentMetadata?.source?.name ||
              selectedDocument.parsedData.partyInformation?.vendor?.name ||
              'Unknown Vendor'
            }
            jsonData={selectedDocument.parsedData}
          />
        )}

        {/* Bank Reconciliation Results section */}
        {reconciliationResults && (
          <BankReconciliation
            reconciliationResults={reconciliationResults}
            onManualMatch={handleManualMatch}
            onAcceptSuggestion={handleAcceptSuggestion}
          />
        )}
      </div>

      <footer className="footer">
        <p>© {new Date().getFullYear()} DocuExtract. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default PDFProcessor;