import React, { useState, useEffect } from "react";
import "./App.css";

const CategoryEditor = ({
  currentCategorization,
  onSubmitCorrection,
  transactionData,
  transactionPurpose,
  transactionId
}) => {
  const [categories, setCategories] = useState([]);
  const [groupedCategories, setGroupedCategories] = useState({});
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedSubcategory, setSelectedSubcategory] = useState("");
  const [selectedLedgerType, setSelectedLedgerType] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load categories from backend
  useEffect(() => {
    loadCategories();
  }, []);

  // Initialize with current categorization
  useEffect(() => {
    if (currentCategorization) {
      setSelectedCategory(currentCategorization.category || "");
      setSelectedSubcategory(currentCategorization.subcategory || "");
      setSelectedLedgerType(currentCategorization.ledgerType || "");
    }
  }, [currentCategorization]);

  const loadCategories = async () => {
    try {
      const response = await fetch("http://localhost:8000/categories");
      const data = await response.json();

      if (data.success) {
        setCategories(data.categories);
        setGroupedCategories(data.grouped);
      }
    } catch (err) {
      console.error("Error loading categories:", err);
    }
  };

  const handleCategoryChange = (e) => {
    const newCategory = e.target.value;
    setSelectedCategory(newCategory);

    // Reset subcategory when category changes
    setSelectedSubcategory("");
    setSelectedLedgerType("");
  };

  const handleSubcategoryChange = (e) => {
    const subcategoryValue = e.target.value;
    setSelectedSubcategory(subcategoryValue);

    // Find the matching categorization to get the ledger type
    const matching = categories.find(
      cat => cat.category === selectedCategory && cat.subcategory === subcategoryValue
    );

    if (matching) {
      setSelectedLedgerType(matching.ledgerType);
    }
  };

  const handleSubmitCorrection = async () => {
    if (!selectedCategory || !selectedSubcategory) {
      alert("Please select both category and subcategory");
      return;
    }

    setLoading(true);

    const correctedCategorization = {
      category: selectedCategory,
      subcategory: selectedSubcategory,
      ledgerType: selectedLedgerType,
      companyName: currentCategorization.companyName || "",
      description: currentCategorization.description || ""
    };

    try {
      const response = await fetch("http://localhost:8000/submit-correction", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          transaction_id: transactionId,
          original_categorization: currentCategorization,
          corrected_categorization: correctedCategorization,
          transaction_data: transactionData,
          transaction_purpose: transactionPurpose,
          correction_reason: correctionReason
        }),
      });

      const data = await response.json();

      if (data.success) {
        alert("✓ Correction submitted! The system will learn from this.");
        setIsEditing(false);
        setCorrectionReason("");

        // Call parent callback if provided
        if (onSubmitCorrection) {
          onSubmitCorrection(correctedCategorization, data);
        }
      } else {
        alert("⚠ Error submitting correction: " + (data.error || "Unknown error"));
      }
    } catch (err) {
      console.error("Error submitting correction:", err);
      alert("⚠ Error submitting correction: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const availableSubcategories = selectedCategory && groupedCategories[selectedCategory]
    ? groupedCategories[selectedCategory]
    : [];

  const hasChanges =
    selectedCategory !== currentCategorization?.category ||
    selectedSubcategory !== currentCategorization?.subcategory;

  return (
    <div style={{
      border: "2px solid #e5e7eb",
      borderRadius: "0.5rem",
      padding: "1.5rem",
      marginTop: "1rem",
      backgroundColor: "white"
    }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "1rem"
      }}>
        <h4 style={{ margin: 0, color: "#1f2937" }}>
          {isEditing ? "✏️ Edit Categorization" : "Current Categorization"}
        </h4>

        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            style={{
              padding: "0.5rem 1rem",
              backgroundColor: "#f59e0b",
              color: "white",
              border: "none",
              borderRadius: "0.375rem",
              fontSize: "0.875rem",
              fontWeight: "600",
              cursor: "pointer"
            }}
          >
            ✏️ Edit / Correct
          </button>
        )}
      </div>

      {!isEditing ? (
        // Display mode
        <div>
          <div style={{ marginBottom: "0.75rem" }}>
            <strong>Category:</strong> {currentCategorization?.category || "Not set"}
          </div>
          <div style={{ marginBottom: "0.75rem" }}>
            <strong>Subcategory:</strong> {currentCategorization?.subcategory || "Not set"}
          </div>
          <div>
            <strong>Ledger Type:</strong>{" "}
            <span style={{
              padding: "0.25rem 0.5rem",
              backgroundColor: "#e0e7ff",
              color: "#4f46e5",
              borderRadius: "0.25rem",
              fontSize: "0.875rem",
              fontWeight: "600"
            }}>
              {currentCategorization?.ledgerType || "Not set"}
            </span>
          </div>
        </div>
      ) : (
        // Edit mode
        <div>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{
              display: "block",
              fontSize: "0.875rem",
              fontWeight: "600",
              color: "#374151",
              marginBottom: "0.5rem"
            }}>
              Parent Category *
            </label>
            <select
              value={selectedCategory}
              onChange={handleCategoryChange}
              style={{
                width: "100%",
                padding: "0.5rem",
                borderRadius: "0.375rem",
                border: "1px solid #d1d5db",
                fontSize: "1rem"
              }}
            >
              <option value="">Select a category...</option>
              {Object.keys(groupedCategories).map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: "1rem" }}>
            <label style={{
              display: "block",
              fontSize: "0.875rem",
              fontWeight: "600",
              color: "#374151",
              marginBottom: "0.5rem"
            }}>
              Subcategory *
            </label>
            <select
              value={selectedSubcategory}
              onChange={handleSubcategoryChange}
              disabled={!selectedCategory}
              style={{
                width: "100%",
                padding: "0.5rem",
                borderRadius: "0.375rem",
                border: "1px solid #d1d5db",
                fontSize: "1rem",
                backgroundColor: !selectedCategory ? "#f9fafb" : "white"
              }}
            >
              <option value="">
                {selectedCategory ? "Select a subcategory..." : "Select category first"}
              </option>
              {availableSubcategories.map((sub) => (
                <option key={sub.subcategory} value={sub.subcategory}>
                  {sub.subcategory}
                </option>
              ))}
            </select>
          </div>

          {selectedLedgerType && (
            <div style={{ marginBottom: "1rem" }}>
              <label style={{
                display: "block",
                fontSize: "0.875rem",
                fontWeight: "600",
                color: "#374151",
                marginBottom: "0.5rem"
              }}>
                Ledger Type
              </label>
              <div style={{
                padding: "0.5rem",
                backgroundColor: "#e0e7ff",
                color: "#4f46e5",
                borderRadius: "0.375rem",
                fontWeight: "600"
              }}>
                {selectedLedgerType}
              </div>
            </div>
          )}

          <div style={{ marginBottom: "1rem" }}>
            <label style={{
              display: "block",
              fontSize: "0.875rem",
              fontWeight: "600",
              color: "#374151",
              marginBottom: "0.5rem"
            }}>
              Reason for Correction (Optional)
            </label>
            <textarea
              value={correctionReason}
              onChange={(e) => setCorrectionReason(e.target.value)}
              placeholder="Why are you changing this categorization? (helps the system learn)"
              rows="3"
              style={{
                width: "100%",
                padding: "0.5rem",
                borderRadius: "0.375rem",
                border: "1px solid #d1d5db",
                fontSize: "0.875rem",
                fontFamily: "inherit",
                resize: "vertical"
              }}
            />
          </div>

          {hasChanges && (
            <div style={{
              padding: "0.75rem",
              backgroundColor: "#fef3c7",
              border: "1px solid #fbbf24",
              borderRadius: "0.375rem",
              marginBottom: "1rem",
              fontSize: "0.875rem",
              color: "#92400e"
            }}>
              <strong>⚠️ Changes detected:</strong> You've modified the categorization.
              Submit to teach the system the correct category.
            </div>
          )}

          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button
              onClick={handleSubmitCorrection}
              disabled={!hasChanges || loading}
              style={{
                flex: 1,
                padding: "0.75rem",
                backgroundColor: hasChanges ? "#10b981" : "#9ca3af",
                color: "white",
                border: "none",
                borderRadius: "0.375rem",
                fontSize: "1rem",
                fontWeight: "600",
                cursor: hasChanges ? "pointer" : "not-allowed",
                opacity: loading ? 0.6 : 1
              }}
            >
              {loading ? "Submitting..." : "✓ Submit Correction"}
            </button>

            <button
              onClick={() => {
                setIsEditing(false);
                // Reset to original values
                setSelectedCategory(currentCategorization?.category || "");
                setSelectedSubcategory(currentCategorization?.subcategory || "");
                setSelectedLedgerType(currentCategorization?.ledgerType || "");
                setCorrectionReason("");
              }}
              disabled={loading}
              style={{
                padding: "0.75rem 1.5rem",
                backgroundColor: "white",
                color: "#6b7280",
                border: "2px solid #d1d5db",
                borderRadius: "0.375rem",
                fontSize: "1rem",
                fontWeight: "600",
                cursor: loading ? "not-allowed" : "pointer"
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CategoryEditor;
