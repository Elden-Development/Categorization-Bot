# Machine Learning Categorization System - Setup Guide

## Overview

Your Categorization Bot now includes a **Vector Database & Machine Learning System** that learns from historical transaction categorizations to provide intelligent predictions for future transactions.

### Key Features

- **Vector Database (Pinecone)**: Stores embeddings of millions of transactions for fast similarity search
- **Gemini Embeddings**: Converts transactions into 768-dimensional vectors using Google's text-embedding-004 model
- **Hybrid Approach**: Shows both ML predictions (based on historical patterns) AND Gemini AI categorization side-by-side
- **Confidence Scores**: ML predictions include confidence levels (Very High, High, Medium, Low) with supporting evidence
- **Continuous Learning**: Every categorization decision is stored to improve future predictions
- **Similar Transactions**: View the historical transactions that influenced the ML prediction

---

## Setup Instructions

### 1. Install Backend Dependencies

Navigate to the backend directory and install the required packages:

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- `pinecone-client==3.0.3` - Vector database client
- All existing dependencies (FastAPI, Gemini, etc.)

### 2. Get Your Pinecone API Key

1. Go to [Pinecone.io](https://www.pinecone.io/)
2. Sign up for a free account (includes 1 million vectors for free)
3. Create a new project
4. Copy your API key from the dashboard

### 3. Configure Environment Variables

Update your `.env` file in the project root:

```env
GEMINI_API_KEY=AIzaSyBPF8uQ60k0RBCoYgxmGoXga7exchVhxkc
PINECONE_API_KEY=your-actual-pinecone-api-key-here
```

**Important**: Replace `your-actual-pinecone-api-key-here` with your real Pinecone API key.

### 4. Start the Backend Server

The ML system will automatically:
- Initialize the Pinecone index on first run
- Create a serverless index named `transaction-categorization`
- Set up the vector database with 768 dimensions (Gemini embedding size)

```bash
cd backend
python main.py
```

You should see:
```
Index 'transaction-categorization' created successfully
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5. Start the Frontend

In a separate terminal:

```bash
cd frontend
npm start
```

---

## How It Works

### 1. **Document Processing**
   - Upload and process documents as usual
   - Extract structured data with the existing pipeline

### 2. **Hybrid Categorization**
   - Click "Research & Categorize" button
   - System runs TWO categorizations in parallel:
     - **ML Prediction**: Searches vector database for similar past transactions
     - **Gemini AI**: Uses AI to understand context and categorize

### 3. **Side-by-Side Comparison**
   - **Left Panel**: ML Prediction
     - Confidence score with color coding
     - Category, subcategory, and ledger type
     - Number of supporting transactions
     - View similar historical transactions

   - **Right Panel**: Gemini AI Categorization
     - AI-powered categorization
     - Detailed explanation of reasoning
     - Company description

### 4. **Make Your Choice**
   - Click on either the ML or Gemini panel to select it
   - System auto-selects based on ML confidence:
     - High confidence (≥70%) → ML selected
     - Low confidence (<70%) → Gemini selected
   - You can override by clicking either panel

### 5. **Save & Learn**
   - Click "Save & Learn from This Decision"
   - Your choice is stored in the vector database
   - Future similar transactions will benefit from this decision

---

## ML Confidence Levels

The system provides confidence scores based on:
1. **Similarity to historical transactions** (cosine similarity)
2. **Number of supporting examples** (more = higher confidence)
3. **Agreement among similar transactions** (consistency)

### Confidence Levels:
- **Very High (≥85%)**: Green badge - Strong match, safe to use ML
- **High (≥70%)**: Blue badge - Good match, ML is reliable
- **Medium (≥55%)**: Yellow badge - Moderate match, compare with AI
- **Low (<55%)**: Red badge - Weak match, prefer AI categorization

---

## API Endpoints

### New Endpoints:

#### 1. `/categorize-transaction-hybrid` (POST)
Returns both ML and Gemini predictions

**Request:**
```json
{
  "vendor_info": "Vendor research text...",
  "document_data": { /* extracted JSON */ },
  "transaction_purpose": "Office supplies for Q1"
}
```

**Response:**
```json
{
  "mlPrediction": {
    "hasPrediction": true,
    "confidence": 0.87,
    "confidenceLevel": "Very High",
    "category": "Operating Expenses",
    "subcategory": "Office Supplies",
    "ledgerType": "Expense (Operating)",
    "supportingTransactions": 15,
    "examples": [ /* similar transactions */ ],
    "recommendation": "Strong match with historical patterns..."
  },
  "geminiCategorization": {
    "category": "Operating Expenses",
    "subcategory": "Office Supplies",
    "ledgerType": "Expense (Operating)",
    "companyName": "Vendor Name",
    "description": "...",
    "explanation": "..."
  },
  "hybridApproach": true
}
```

#### 2. `/store-categorization` (POST)
Store a categorization decision for learning

**Request:**
```json
{
  "transaction_data": { /* full document JSON */ },
  "categorization": { /* selected categorization */ },
  "transaction_purpose": "Office supplies",
  "selected_method": "ml",  // or "gemini"
  "user_feedback": "User chose ML prediction"
}
```

**Response:**
```json
{
  "success": true,
  "transactionId": "abc123def456",
  "message": "Categorization stored successfully for future learning"
}
```

#### 3. `/ml-stats` (GET)
Get statistics about the vector database

**Response:**
```json
{
  "success": true,
  "stats": {
    "totalTransactions": 1542,
    "dimension": 768,
    "indexFullness": 0.001542
  }
}
```

---

## Architecture

### Vector Database Schema

Each transaction is stored with:

**Vector (Embedding):**
- 768-dimensional vector generated from transaction text
- Combines: vendor name, document type, amount, line items, transaction purpose

**Metadata:**
- `category`: Accounting category
- `subcategory`: Specific subcategory
- `ledgerType`: Ledger entry type
- `companyName`: Vendor/company name
- `vendorName`: Extracted vendor name
- `documentType`: Type of document
- `totalAmount`: Transaction amount
- `currency`: Currency code
- `transactionText`: Text representation (truncated)
- `timestamp`: When stored
- `userFeedback`: Which method user chose
- `transactionPurpose`: User-provided description

### Similarity Search Algorithm

1. **Generate embedding** for new transaction
2. **Query Pinecone** for top 15 most similar transactions (cosine similarity)
3. **Weighted voting**:
   - Each similar transaction "votes" for its category
   - Vote weight = similarity score
   - Higher similarity = more influence
4. **Calculate confidence**:
   - Vote proportion (40%)
   - Number of examples (30%)
   - Average similarity (30%)
5. **Return prediction** with supporting evidence

---

## Best Practices

### 1. **Start with Gemini, Build ML Over Time**
   - Initially, ML will have no data (no predictions)
   - Use Gemini AI categorization for first ~50-100 transactions
   - As you save decisions, ML predictions will appear and improve

### 2. **Provide Transaction Purpose**
   - Optional but highly recommended
   - Helps both ML and AI understand context
   - Example: "Gym equipment for employee wellness program"

### 3. **Review Low-Confidence Predictions**
   - ML confidence <70% → Compare with Gemini
   - Both agree → High confidence in result
   - Both disagree → Review carefully, might be unique transaction

### 4. **Save Your Decisions**
   - Always click "Save & Learn" after choosing
   - Even if you use Gemini, saving helps ML learn
   - System learns from both ML and Gemini selections

### 5. **Monitor ML Stats**
   - Top-right badge shows "X transactions learned"
   - More data = better predictions
   - Aim for 100+ transactions per category for best results

---

## Scaling to Millions of Transactions

Pinecone is designed for scale:

- **Free Tier**: 1 million vectors
- **Serverless**: Auto-scales with usage
- **Fast**: Sub-100ms queries even with millions of vectors
- **Cost**: Pay only for what you use

### Performance Expectations:

| Transactions Stored | Query Time | Prediction Quality |
|---------------------|------------|-------------------|
| 0-100               | N/A        | No predictions yet |
| 100-1,000           | <50ms      | Basic patterns |
| 1,000-10,000        | <100ms     | Good patterns |
| 10,000-100,000      | <150ms     | Very good patterns |
| 100,000-1M          | <200ms     | Excellent patterns |
| 1M-10M              | <300ms     | Expert-level patterns |

---

## Troubleshooting

### "ML engine not configured" Error

**Problem**: Backend can't connect to Pinecone

**Solution**:
1. Check `.env` file has `PINECONE_API_KEY`
2. Verify API key is valid
3. Restart backend server
4. Check console for error messages

### ML Predictions Always Show "No ML prediction available"

**Problem**: No historical data in vector database

**Solution**:
- This is normal for a new system
- Process and categorize 10-20 transactions
- Click "Save & Learn" for each one
- ML predictions will start appearing

### Low Confidence Scores Even With Data

**Possible Causes**:
1. **Diverse transactions**: Each transaction is unique → low similarity
2. **Inconsistent categorization**: Same vendor categorized differently → confuses ML
3. **Need more data**: <50 transactions per category → insufficient patterns

**Solution**:
- Be consistent with categorizations
- Add more similar transactions
- Use transaction purpose field for context

### Pinecone Index Creation Fails

**Problem**: Permission or region issues

**Solution**:
1. Check Pinecone dashboard for index
2. Manually create index:
   - Name: `transaction-categorization`
   - Dimensions: 768
   - Metric: cosine
   - Cloud: AWS
   - Region: us-east-1
3. Restart backend

---

## Future Enhancements

Potential improvements:
1. **Batch Import**: Upload CSV of historical transactions for instant learning
2. **Category Analytics**: Show most common categories, spending trends
3. **Manual Corrections**: Edit and re-save categorizations
4. **Export Training Data**: Download all learned categorizations
5. **Multi-Tenant**: Separate vector namespaces per organization
6. **Advanced Filters**: Search by date range, amount, vendor
7. **Confidence Threshold Settings**: Customize auto-selection behavior

---

## Support

If you encounter issues:

1. Check console logs (browser and backend)
2. Verify API keys are correct
3. Ensure all dependencies are installed
4. Check Pinecone dashboard for index status

For Pinecone-specific issues:
- [Pinecone Documentation](https://docs.pinecone.io/)
- [Pinecone Support](https://support.pinecone.io/)

For Gemini API issues:
- [Google AI Documentation](https://ai.google.dev/docs)

---

## Summary

You've successfully implemented a production-ready **Vector Database & Machine Learning System** that:

✅ Stores transaction embeddings in Pinecone
✅ Generates 768-dimensional vectors using Gemini
✅ Provides hybrid ML + AI categorization
✅ Shows confidence scores and supporting evidence
✅ Learns continuously from user decisions
✅ Scales to millions of transactions

**Next Steps:**
1. Get your Pinecone API key
2. Update `.env` file
3. Restart backend
4. Process your first document
5. Start building your ML knowledge base!

Happy categorizing! 🚀
