"""
Machine Learning Categorization Module

This module handles:
1. Vector database operations with Pinecone
2. Embedding generation using Google Gemini
3. Similarity search for historical transactions
4. ML-based category prediction with confidence scores
5. Learning loop for continuous improvement
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime
try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    # Fallback for older versions
    from pinecone import Pinecone
    from pinecone import ServerlessSpec
from google import genai
import asyncio


class MLCategorizationEngine:
    """
    Machine Learning engine for transaction categorization using vector similarity search.
    """

    def __init__(self, pinecone_api_key: str, gemini_api_key: str, environment: str = "production"):
        """
        Initialize the ML Categorization Engine.

        Parameters:
        pinecone_api_key (str): Pinecone API key
        gemini_api_key (str): Google Gemini API key
        environment (str): Environment name (production, development, etc.)
        """
        # Initialize Pinecone
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index_name = "transaction-categorization"
        self.dimension = 768  # Gemini text-embedding-004 produces 768-dimensional vectors

        # Initialize Gemini client for embeddings
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        self.embedding_model = "models/text-embedding-004"

        # Ensure index exists
        self._initialize_index()

        # Get index instance
        self.index = self.pc.Index(self.index_name)

    def _initialize_index(self):
        """
        Create Pinecone index if it doesn't exist.
        """
        existing_indexes = [index.name for index in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            print(f"Creating new Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",  # Cosine similarity for text embeddings
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"  # Change based on your preferred region
                )
            )
            print(f"Index '{self.index_name}' created successfully")
        else:
            print(f"Index '{self.index_name}' already exists")

    def _generate_transaction_text(self, transaction_data: Dict) -> str:
        """
        Convert transaction data into a comprehensive text representation for embedding.

        Combines vendor info, document metadata, financial data, and line items
        into a coherent text that captures the transaction's essence.

        Parameters:
        transaction_data (dict): The complete transaction/document data

        Returns:
        str: Text representation of the transaction
        """
        parts = []

        # Extract vendor/source information
        doc_metadata = transaction_data.get("documentMetadata", {})
        source = doc_metadata.get("source", {})

        if source.get("name"):
            parts.append(f"Vendor: {source['name']}")

        if doc_metadata.get("documentType"):
            parts.append(f"Document Type: {doc_metadata['documentType']}")

        # Extract financial data
        financial_data = transaction_data.get("financialData", {})
        if financial_data.get("totalAmount"):
            parts.append(f"Amount: ${financial_data['totalAmount']}")

        if financial_data.get("currency"):
            parts.append(f"Currency: {financial_data['currency']}")

        # Extract party information
        party_info = transaction_data.get("partyInformation", {})
        vendor_info = party_info.get("vendor", {})

        if vendor_info.get("name"):
            parts.append(f"Supplier: {vendor_info['name']}")

        # Extract line items and create description
        line_items = transaction_data.get("lineItems", [])
        if line_items:
            item_descriptions = []
            for item in line_items[:5]:  # Limit to first 5 items to avoid too long text
                desc = item.get("description", "")
                if desc:
                    item_descriptions.append(desc)

            if item_descriptions:
                parts.append(f"Items: {', '.join(item_descriptions)}")

        # Additional notes
        additional = transaction_data.get("additionalData", {})
        if additional.get("notes"):
            parts.append(f"Notes: {additional['notes']}")

        # Combine all parts
        transaction_text = " | ".join(parts)

        return transaction_text

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for given text using Gemini.

        Parameters:
        text (str): Text to embed

        Returns:
        List[float]: 768-dimensional embedding vector
        """
        try:
            # Use Gemini's embedding API
            response = await asyncio.to_thread(
                self.gemini_client.models.embed_content,
                model=self.embedding_model,
                content=text
            )

            # Extract the embedding vector
            embedding = response.embeddings[0].values
            return embedding

        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            raise

    def _generate_transaction_id(self, transaction_data: Dict) -> str:
        """
        Generate a unique ID for a transaction based on its content.

        Parameters:
        transaction_data (dict): Transaction data

        Returns:
        str: Unique transaction ID
        """
        # Create a hash of key transaction attributes
        doc_metadata = transaction_data.get("documentMetadata", {})
        financial_data = transaction_data.get("financialData", {})

        unique_string = f"{doc_metadata.get('documentNumber', '')}_" \
                       f"{doc_metadata.get('documentDate', '')}_" \
                       f"{financial_data.get('totalAmount', '')}_" \
                       f"{doc_metadata.get('source', {}).get('name', '')}"

        # Add timestamp to ensure uniqueness
        unique_string += f"_{datetime.utcnow().isoformat()}"

        # Generate hash
        transaction_id = hashlib.sha256(unique_string.encode()).hexdigest()[:16]
        return transaction_id

    async def store_transaction(
        self,
        transaction_data: Dict,
        categorization: Dict,
        transaction_purpose: str = "",
        user_feedback: Optional[str] = None
    ) -> str:
        """
        Store a transaction with its categorization in Pinecone for future learning.

        Parameters:
        transaction_data (dict): Complete transaction/document data
        categorization (dict): Categorization result (category, subcategory, ledgerType, etc.)
        transaction_purpose (str): Optional description of transaction purpose
        user_feedback (str): Optional user feedback (e.g., "correct", "corrected_to_X")

        Returns:
        str: Transaction ID
        """
        try:
            # Generate transaction ID
            transaction_id = self._generate_transaction_id(transaction_data)

            # Generate text representation
            transaction_text = self._generate_transaction_text(transaction_data)

            # Add transaction purpose if provided
            if transaction_purpose:
                transaction_text += f" | Purpose: {transaction_purpose}"

            # Generate embedding
            embedding = await self.generate_embedding(transaction_text)

            # Prepare metadata (Pinecone has limits on metadata size)
            metadata = {
                "category": categorization.get("category", ""),
                "subcategory": categorization.get("subcategory", ""),
                "ledgerType": categorization.get("ledgerType", ""),
                "companyName": categorization.get("companyName", ""),
                "vendorName": transaction_data.get("documentMetadata", {}).get("source", {}).get("name", ""),
                "documentType": transaction_data.get("documentMetadata", {}).get("documentType", ""),
                "totalAmount": str(transaction_data.get("financialData", {}).get("totalAmount", "")),
                "currency": transaction_data.get("financialData", {}).get("currency", "USD"),
                "transactionText": transaction_text[:500],  # Truncate to fit metadata limits
                "timestamp": datetime.utcnow().isoformat(),
                "userFeedback": user_feedback or "none",
                "transactionPurpose": transaction_purpose[:200] if transaction_purpose else ""
            }

            # Store in Pinecone
            self.index.upsert(
                vectors=[
                    {
                        "id": transaction_id,
                        "values": embedding,
                        "metadata": metadata
                    }
                ]
            )

            print(f"Stored transaction {transaction_id} in vector database")
            return transaction_id

        except Exception as e:
            print(f"Error storing transaction: {str(e)}")
            raise

    async def find_similar_transactions(
        self,
        transaction_data: Dict,
        transaction_purpose: str = "",
        top_k: int = 10
    ) -> List[Dict]:
        """
        Find similar historical transactions using vector similarity search.

        Parameters:
        transaction_data (dict): New transaction to find matches for
        transaction_purpose (str): Optional transaction purpose description
        top_k (int): Number of similar transactions to return

        Returns:
        List[Dict]: List of similar transactions with scores and metadata
        """
        try:
            # Generate text representation
            transaction_text = self._generate_transaction_text(transaction_data)

            if transaction_purpose:
                transaction_text += f" | Purpose: {transaction_purpose}"

            # Generate embedding
            embedding = await self.generate_embedding(transaction_text)

            # Query Pinecone
            results = self.index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True
            )

            # Format results
            similar_transactions = []
            for match in results.matches:
                similar_transactions.append({
                    "id": match.id,
                    "score": match.score,  # Cosine similarity (0-1, higher is more similar)
                    "metadata": match.metadata
                })

            return similar_transactions

        except Exception as e:
            print(f"Error finding similar transactions: {str(e)}")
            # Return empty list if search fails
            return []

    async def predict_category(
        self,
        transaction_data: Dict,
        transaction_purpose: str = "",
        min_confidence: float = 0.6
    ) -> Dict:
        """
        Predict transaction category based on similar historical transactions.

        Uses weighted voting from similar transactions to predict category.
        Confidence score is based on similarity scores and agreement among results.

        Parameters:
        transaction_data (dict): Transaction to categorize
        transaction_purpose (str): Optional transaction purpose
        min_confidence (float): Minimum confidence threshold (0-1)

        Returns:
        Dict: Prediction result with category, confidence, and supporting evidence
        """
        try:
            # Find similar transactions
            similar_transactions = await self.find_similar_transactions(
                transaction_data,
                transaction_purpose,
                top_k=15
            )

            if not similar_transactions:
                return {
                    "hasPrediction": False,
                    "confidence": 0.0,
                    "reason": "No historical transactions found for comparison",
                    "category": None,
                    "subcategory": None,
                    "ledgerType": None
                }

            # Count votes weighted by similarity score
            category_votes = {}
            subcategory_votes = {}
            ledger_votes = {}

            total_weight = 0
            for tx in similar_transactions:
                score = tx["score"]
                metadata = tx["metadata"]

                # Create composite key
                key = (
                    metadata.get("category", ""),
                    metadata.get("subcategory", ""),
                    metadata.get("ledgerType", "")
                )

                if key not in category_votes:
                    category_votes[key] = {
                        "weight": 0,
                        "count": 0,
                        "category": metadata.get("category", ""),
                        "subcategory": metadata.get("subcategory", ""),
                        "ledgerType": metadata.get("ledgerType", ""),
                        "examples": []
                    }

                category_votes[key]["weight"] += score
                category_votes[key]["count"] += 1
                category_votes[key]["examples"].append({
                    "vendor": metadata.get("vendorName", ""),
                    "amount": metadata.get("totalAmount", ""),
                    "score": round(score, 3),
                    "text": metadata.get("transactionText", "")[:100]
                })

                total_weight += score

            if not category_votes:
                return {
                    "hasPrediction": False,
                    "confidence": 0.0,
                    "reason": "Could not extract categories from similar transactions",
                    "category": None,
                    "subcategory": None,
                    "ledgerType": None
                }

            # Find the winning category (highest weighted vote)
            winner = max(category_votes.values(), key=lambda x: x["weight"])

            # Calculate confidence score
            # Factors: weighted vote proportion, number of supporting transactions, average similarity
            vote_proportion = winner["weight"] / total_weight if total_weight > 0 else 0
            count_factor = min(winner["count"] / 5, 1.0)  # Bonus for multiple supporting examples
            avg_similarity = winner["weight"] / winner["count"] if winner["count"] > 0 else 0

            # Confidence is a combination of these factors
            confidence = (vote_proportion * 0.4 + count_factor * 0.3 + avg_similarity * 0.3)

            # Prepare result
            prediction = {
                "hasPrediction": True,
                "confidence": round(confidence, 3),
                "category": winner["category"],
                "subcategory": winner["subcategory"],
                "ledgerType": winner["ledgerType"],
                "supportingTransactions": winner["count"],
                "examples": winner["examples"][:5],  # Top 5 examples
                "allSimilarTransactions": len(similar_transactions),
                "votingBreakdown": {
                    k: {
                        "category": v["category"],
                        "subcategory": v["subcategory"],
                        "count": v["count"],
                        "weight": round(v["weight"], 3)
                    }
                    for k, v in sorted(
                        category_votes.items(),
                        key=lambda x: x[1]["weight"],
                        reverse=True
                    )[:3]  # Top 3 alternatives
                }
            }

            # Add confidence level description
            if confidence >= 0.85:
                prediction["confidenceLevel"] = "Very High"
                prediction["recommendation"] = "Strong match with historical patterns. Safe to use ML prediction."
            elif confidence >= 0.7:
                prediction["confidenceLevel"] = "High"
                prediction["recommendation"] = "Good match with historical patterns. ML prediction is reliable."
            elif confidence >= 0.55:
                prediction["confidenceLevel"] = "Medium"
                prediction["recommendation"] = "Moderate match. Consider comparing with AI categorization."
            else:
                prediction["confidenceLevel"] = "Low"
                prediction["recommendation"] = "Weak match. Prefer AI categorization or manual review."

            return prediction

        except Exception as e:
            print(f"Error predicting category: {str(e)}")
            return {
                "hasPrediction": False,
                "confidence": 0.0,
                "reason": f"Error during prediction: {str(e)}",
                "category": None,
                "subcategory": None,
                "ledgerType": None
            }

    async def get_database_stats(self) -> Dict:
        """
        Get statistics about the vector database.

        Returns:
        Dict: Database statistics
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "totalTransactions": stats.total_vector_count,
                "dimension": stats.dimension,
                "indexFullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            print(f"Error getting database stats: {str(e)}")
            return {
                "totalTransactions": 0,
                "error": str(e)
            }

    async def submit_correction(
        self,
        transaction_id: str,
        original_categorization: Dict,
        corrected_categorization: Dict,
        transaction_data: Dict,
        transaction_purpose: str = "",
        correction_reason: str = ""
    ) -> Dict:
        """
        Submit a user correction to improve the ML model.

        This method handles both rejection and manual corrections by:
        1. Storing the corrected version with higher weight
        2. Marking the original prediction as corrected
        3. Enabling incremental learning

        Parameters:
        transaction_id (str): ID of the original transaction
        original_categorization (dict): The original (incorrect) categorization
        corrected_categorization (dict): The corrected categorization
        transaction_data (dict): Complete transaction data
        transaction_purpose (str): Transaction purpose description
        correction_reason (str): Why the correction was made

        Returns:
        Dict: Correction result with new transaction ID
        """
        try:
            # Generate new transaction ID for the corrected version
            correction_id = f"{transaction_id}_corrected_{datetime.utcnow().timestamp()}"

            # Generate text representation
            transaction_text = self._generate_transaction_text(transaction_data)
            if transaction_purpose:
                transaction_text += f" | Purpose: {transaction_purpose}"

            # Generate embedding
            embedding = await self.generate_embedding(transaction_text)

            # Prepare metadata for corrected version
            # Mark this as a user correction with higher learning weight
            metadata = {
                "category": corrected_categorization.get("category", ""),
                "subcategory": corrected_categorization.get("subcategory", ""),
                "ledgerType": corrected_categorization.get("ledgerType", ""),
                "companyName": corrected_categorization.get("companyName", ""),
                "vendorName": transaction_data.get("documentMetadata", {}).get("source", {}).get("name", ""),
                "documentType": transaction_data.get("documentMetadata", {}).get("documentType", ""),
                "totalAmount": str(transaction_data.get("financialData", {}).get("totalAmount", "")),
                "currency": transaction_data.get("financialData", {}).get("currency", "USD"),
                "transactionText": transaction_text[:500],
                "timestamp": datetime.utcnow().isoformat(),
                "userFeedback": "user_correction",
                "transactionPurpose": transaction_purpose[:200] if transaction_purpose else "",
                "isCorrected": "true",
                "originalTransactionId": transaction_id,
                "correctionReason": correction_reason[:200] if correction_reason else "",
                "learningWeight": "2.0"  # Higher weight for corrections
            }

            # Store the corrected version in Pinecone
            self.index.upsert(
                vectors=[
                    {
                        "id": correction_id,
                        "values": embedding,
                        "metadata": metadata
                    }
                ]
            )

            print(f"Stored correction {correction_id} for transaction {transaction_id}")

            # Update the original transaction metadata to mark it as corrected
            # Note: Pinecone doesn't support partial updates, so we need to fetch and re-upsert
            try:
                # Fetch original vector
                original_vectors = self.index.fetch(ids=[transaction_id])

                if original_vectors and 'vectors' in original_vectors and transaction_id in original_vectors['vectors']:
                    original_vector = original_vectors['vectors'][transaction_id]
                    original_metadata = original_vector.get('metadata', {})

                    # Update metadata to mark as corrected
                    original_metadata['wasCorrected'] = 'true'
                    original_metadata['correctedTo'] = correction_id
                    original_metadata['learningWeight'] = '0.5'  # Lower weight for corrected transactions

                    # Re-upsert with updated metadata
                    self.index.upsert(
                        vectors=[
                            {
                                "id": transaction_id,
                                "values": original_vector['values'],
                                "metadata": original_metadata
                            }
                        ]
                    )
                    print(f"Updated original transaction {transaction_id} metadata")
            except Exception as update_error:
                print(f"Could not update original transaction metadata: {str(update_error)}")
                # Continue anyway - the correction is still stored

            return {
                "success": True,
                "correctionId": correction_id,
                "originalTransactionId": transaction_id,
                "message": "Correction stored successfully. Future predictions will learn from this.",
                "learningImpact": "high"
            }

        except Exception as e:
            print(f"Error submitting correction: {str(e)}")
            return {
                "success": False,
                "error": f"Error submitting correction: {str(e)}"
            }

    async def get_correction_stats(self) -> Dict:
        """
        Get statistics about corrections and learning improvements.

        Returns:
        Dict: Correction statistics including total corrections, correction rate, etc.
        """
        try:
            # Query for all transactions
            stats = self.index.describe_index_stats()
            total_transactions = stats.total_vector_count

            # Note: Pinecone doesn't support filtering queries in free tier efficiently
            # We'll return basic stats and estimate correction rate

            return {
                "totalTransactions": total_transactions,
                "estimatedCorrections": "Use metadata filtering for accurate count",
                "learningStatus": "active" if total_transactions > 0 else "waiting_for_data",
                "recommendedActions": self._get_learning_recommendations(total_transactions)
            }

        except Exception as e:
            print(f"Error getting correction stats: {str(e)}")
            return {
                "error": str(e),
                "totalTransactions": 0
            }

    def _get_learning_recommendations(self, total_transactions: int) -> List[str]:
        """
        Provide recommendations based on current learning state.

        Parameters:
        total_transactions (int): Total number of transactions in the database

        Returns:
        List[str]: Recommendations for improving the system
        """
        recommendations = []

        if total_transactions == 0:
            recommendations.append("Start by processing and categorizing your first transactions")
            recommendations.append("Save at least 20 transactions to begin seeing ML predictions")
        elif total_transactions < 50:
            recommendations.append(f"You have {total_transactions} transactions. Add {50 - total_transactions} more for better predictions")
            recommendations.append("Focus on common vendors and transaction types first")
        elif total_transactions < 200:
            recommendations.append("Good progress! Continue categorizing diverse transactions")
            recommendations.append("Review and correct any low-confidence predictions")
        else:
            recommendations.append("Excellent! Your system has substantial training data")
            recommendations.append("Focus on correcting edge cases and unusual transactions")
            recommendations.append("Review ML predictions with medium confidence for improvements")

        return recommendations


# Singleton instance
_ml_engine_instance: Optional[MLCategorizationEngine] = None


def get_ml_engine(pinecone_api_key: str = None, gemini_api_key: str = None) -> MLCategorizationEngine:
    """
    Get or create the ML categorization engine singleton.

    Parameters:
    pinecone_api_key (str): Pinecone API key (required on first call)
    gemini_api_key (str): Gemini API key (required on first call)

    Returns:
    MLCategorizationEngine: The ML engine instance
    """
    global _ml_engine_instance

    if _ml_engine_instance is None:
        if pinecone_api_key is None or gemini_api_key is None:
            raise ValueError("API keys required for first initialization")

        _ml_engine_instance = MLCategorizationEngine(
            pinecone_api_key=pinecone_api_key,
            gemini_api_key=gemini_api_key
        )

    return _ml_engine_instance
