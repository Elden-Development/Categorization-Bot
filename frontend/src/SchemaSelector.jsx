import React, { useState, useRef, useEffect } from "react";

/**
 * Component for selecting the appropriate JSON schema to use for document extraction
 */
const SchemaSelector = ({ selectedSchema, onSchemaChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const schemas = [
    { id: "generic", name: "Generic Document", icon: "📄", description: "General purpose extraction" },
    { id: "1040", name: "Form 1040", icon: "📋", description: "Individual Tax Return" },
    { id: "2848", name: "Form 2848", icon: "📝", description: "Power of Attorney" },
    { id: "8821", name: "Form 8821", icon: "🔐", description: "Tax Information Authorization" },
    { id: "941", name: "Form 941", icon: "💼", description: "Employer's Quarterly Tax" },
    { id: "payroll", name: "Payroll Data", icon: "💰", description: "Universal Payroll Schema" }
  ];

  const selectedSchemaData = schemas.find(s => s.id === selectedSchema) || schemas[0];

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (schemaId) => {
    onSchemaChange(schemaId);
    setIsOpen(false);
  };

  return (
    <div className="schema-selector-wrapper" ref={dropdownRef}>
      <label className="schema-label">Document Type</label>

      <button
        type="button"
        className={`schema-trigger ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <div className="schema-trigger-content">
          <span className="schema-trigger-icon">{selectedSchemaData.icon}</span>
          <div className="schema-trigger-text">
            <span className="schema-trigger-name">{selectedSchemaData.name}</span>
            <span className="schema-trigger-desc">{selectedSchemaData.description}</span>
          </div>
        </div>
        <svg
          className={`schema-trigger-arrow ${isOpen ? 'rotated' : ''}`}
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

      {isOpen && (
        <div className="schema-dropdown" role="listbox">
          {schemas.map(schema => (
            <button
              key={schema.id}
              type="button"
              className={`schema-option ${selectedSchema === schema.id ? 'selected' : ''}`}
              onClick={() => handleSelect(schema.id)}
              role="option"
              aria-selected={selectedSchema === schema.id}
            >
              <span className="schema-option-icon">{schema.icon}</span>
              <div className="schema-option-text">
                <span className="schema-option-name">{schema.name}</span>
                <span className="schema-option-desc">{schema.description}</span>
              </div>
              {selectedSchema === schema.id && (
                <svg
                  className="schema-option-check"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default SchemaSelector;
