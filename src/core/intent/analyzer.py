"""
Intent classification and analysis component.

Provides intelligent query analysis and intent classification using embedding-based
similarity and pattern recognition with safety validation.
"""

import asyncio
import logging
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from uuid import UUID
from collections import defaultdict, Counter

from .models import (
    IntentType,
    IntentResult,
    IntentMetadata,
    IntentPattern,
    LearningFeedback,
    MIN_INTENT_CONFIDENCE,
    generate_content_hash
)
from ..validation.validator import SafetyValidator
from ..embeddings.service import EmbeddingService
from ..embeddings.models import ContentType

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """
    Intent classification system using embedding-based similarity and pattern recognition.
    
    Features:
    - Multi-pattern intent detection
    - Confidence scoring
    - Learning from feedback
    - Safety-validated classifications
    """
    
    # Intent classification patterns
    INTENT_PATTERNS = {
        IntentType.QUESTION: [
            r'\b(what|how|why|when|where|who|which)\b',
            r'\?',
            r'\b(explain|describe|tell me|clarify)\b',
            r'\b(is|are|can|could|would|should|do|does|did)\b.*\?'
        ],
        
        IntentType.COMMAND: [
            r'\b(create|make|build|generate|write|implement)\b',
            r'\b(fix|solve|resolve|correct|repair)\b',
            r'\b(add|remove|delete|update|modify|change)\b',
            r'\b(run|execute|start|stop|deploy)\b',
            r'\b(please|can you|could you)\b.*\b(do|make|create|fix)\b'
        ],
        
        IntentType.EXPLANATION: [
            r'\b(explain|elaborate|detail|clarify|walk through)\b',
            r'\b(understand|comprehend|grasp|learn about)\b',
            r'\b(how does|how do|why does|why do)\b',
            r'\b(breakdown|break down|step by step)\b'
        ],
        
        IntentType.SEARCH: [
            r'\b(find|search|look for|locate|discover)\b',
            r'\b(where is|where can|show me)\b',
            r'\b(list|enumerate|show all)\b',
            r'\b(examples|samples|instances)\b'
        ],
        
        IntentType.DEBUG: [
            r'\b(debug|troubleshoot|diagnose|investigate)\b',
            r'\b(error|bug|issue|problem|failure)\b',
            r'\b(not working|broken|failing|crashed)\b',
            r'\b(why isn\'t|why doesn\'t|what\'s wrong)\b'
        ],
        
        IntentType.OPTIMIZE: [
            r'\b(optimize|improve|enhance|refactor)\b',
            r'\b(faster|better|efficient|performance)\b',
            r'\b(reduce|minimize|streamline)\b',
            r'\b(best practice|recommendation)\b'
        ],
        
        IntentType.REVIEW: [
            r'\b(review|check|validate|verify|assess)\b',
            r'\b(feedback|opinion|thoughts|suggestions)\b',
            r'\b(correct|right|good|bad|better)\b',
            r'\b(code review|design review)\b'
        ],
        
        IntentType.LEARN: [
            r'\b(learn|study|understand|tutorial)\b',
            r'\b(teach me|show me how|guide me)\b',
            r'\b(concept|principle|theory|approach)\b',
            r'\b(beginner|introduction|basics)\b'
        ],
        
        IntentType.PLAN: [
            r'\b(plan|strategy|approach|roadmap)\b',
            r'\b(design|architecture|structure)\b',
            r'\b(organize|structure|layout)\b',
            r'\b(next steps|workflow|process)\b'
        ],
        
        IntentType.REFLECT: [
            r'\b(reflect|retrospective|analysis|review)\b',
            r'\b(lessons learned|what went|outcome)\b',
            r'\b(evaluate|assess|consider)\b',
            r'\b(thoughts|insights|observations)\b'
        ]
    }
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        safety_validator: Optional[SafetyValidator] = None,
        enable_pattern_learning: bool = True
    ):
        """
        Initialize intent analyzer.
        
        Args:
            embedding_service: Service for generating embeddings
            safety_validator: Safety validator for content
            enable_pattern_learning: Whether to learn new patterns
        """
        self.embedding_service = embedding_service
        self.safety_validator = safety_validator or SafetyValidator()
        self.enable_pattern_learning = enable_pattern_learning
        
        # Compile regex patterns for efficiency
        self._compiled_patterns = {}
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            self._compiled_patterns[intent_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        # Learning data
        self._pattern_feedback = defaultdict(list)
        self._intent_examples = defaultdict(list)
        self._user_patterns = defaultdict(list)
        
        # Statistics
        self._stats = {
            'intents_classified': 0,
            'patterns_matched': 0,
            'embedding_classifications': 0,
            'feedback_processed': 0,
            'total_processing_time_ms': 0,
            'pattern_accuracy': 0.0
        }
        
        logger.info("IntentAnalyzer initialized")
    
    async def classify_intent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        confidence_threshold: float = MIN_INTENT_CONFIDENCE
    ) -> IntentResult:
        """
        Classify the intent of a user query.
        
        Args:
            query: Query to classify
            context: Additional context information
            user_id: User ID for personalization
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            Intent classification result
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Classifying intent for query: {query[:100]}...")
            
            # Step 1: Pattern-based classification
            pattern_results = await self._classify_by_patterns(query)
            
            # Step 2: Embedding-based classification
            embedding_results = await self._classify_by_embedding(query, context)
            
            # Step 3: Combine results
            combined_result = await self._combine_classification_results(
                query, pattern_results, embedding_results, user_id
            )
            
            # Step 4: Validate safety
            await self._validate_intent_safety(combined_result, query)
            
            processing_time = (time.time() - start_time) * 1000
            combined_result.metadata.processing_time_ms = int(processing_time)
            
            # Update statistics
            self._stats['intents_classified'] += 1
            self._stats['total_processing_time_ms'] += int(processing_time)
            
            if pattern_results:
                self._stats['patterns_matched'] += 1
            if embedding_results:
                self._stats['embedding_classifications'] += 1
            
            logger.debug(
                f"Intent classified in {processing_time:.1f}ms: "
                f"{combined_result.intent_type} (confidence: {combined_result.metadata.confidence:.2f})"
            )
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # Return safe fallback
            return self._create_fallback_result(query, str(e))
    
    async def _classify_by_patterns(self, query: str) -> Dict[IntentType, float]:
        """
        Classify intent using regex patterns.
        
        Args:
            query: Query to classify
            
        Returns:
            Dictionary of intent types and confidence scores
        """
        scores = {}
        query_lower = query.lower()
        
        for intent_type, patterns in self._compiled_patterns.items():
            matches = 0
            total_patterns = len(patterns)
            
            for pattern in patterns:
                if pattern.search(query_lower):
                    matches += 1
            
            if matches > 0:
                # Calculate confidence based on pattern matches
                confidence = min(1.0, (matches / total_patterns) * 1.5)
                scores[intent_type] = confidence
        
        return scores
    
    async def _classify_by_embedding(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[IntentType, float]:
        """
        Classify intent using embedding similarity.
        
        Args:
            query: Query to classify
            context: Additional context
            
        Returns:
            Dictionary of intent types and confidence scores
        """
        try:
            # Generate embedding for query
            embedding_result = await self.embedding_service.generate_embedding(
                content=query,
                content_type=ContentType.QUERY
            )
            
            query_embedding = embedding_result.vector
            
            # Compare with known intent examples
            scores = {}
            
            for intent_type, examples in self._intent_examples.items():
                if not examples:
                    continue
                
                similarities = []
                for example_embedding in examples:
                    similarity = await self.embedding_service.calculate_similarity(
                        query_embedding, example_embedding
                    )
                    similarities.append(similarity)
                
                if similarities:
                    # Use highest similarity as confidence
                    max_similarity = max(similarities)
                    if max_similarity > 0.5:  # Minimum similarity threshold
                        scores[intent_type] = max_similarity
            
            return scores
            
        except Exception as e:
            logger.warning(f"Embedding-based classification failed: {e}")
            return {}
    
    async def _combine_classification_results(
        self,
        query: str,
        pattern_results: Dict[IntentType, float],
        embedding_results: Dict[IntentType, float],
        user_id: Optional[UUID] = None
    ) -> IntentResult:
        """
        Combine pattern and embedding classification results.
        
        Args:
            query: Original query
            pattern_results: Pattern-based classification scores
            embedding_results: Embedding-based classification scores
            user_id: User ID for personalization
            
        Returns:
            Combined intent result
        """
        # Combine scores with weighted average
        pattern_weight = 0.6  # Patterns are more reliable initially
        embedding_weight = 0.4
        
        combined_scores = {}
        all_intents = set(pattern_results.keys()) | set(embedding_results.keys())
        
        for intent_type in all_intents:
            pattern_score = pattern_results.get(intent_type, 0.0)
            embedding_score = embedding_results.get(intent_type, 0.0)
            
            combined_score = (
                pattern_score * pattern_weight + 
                embedding_score * embedding_weight
            )
            
            if combined_score > 0:
                combined_scores[intent_type] = combined_score
        
        # Determine best intent
        if combined_scores:
            best_intent = max(combined_scores.keys(), key=lambda x: combined_scores[x])
            confidence = combined_scores[best_intent]
            
            # Get alternative intents
            alternatives = sorted(
                [intent for intent in combined_scores.keys() if intent != best_intent],
                key=lambda x: combined_scores[x],
                reverse=True
            )[:3]  # Top 3 alternatives
        else:
            best_intent = IntentType.UNKNOWN
            confidence = 0.0
            alternatives = []
        
        # Create metadata
        metadata = IntentMetadata(
            confidence=confidence,
            safety_score=Decimal("0.9"),  # Will be validated later
            content_hash=generate_content_hash(query, "intent_analysis"),
            keywords=self._extract_keywords(query),
            entities=self._extract_entities(query)
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            best_intent, confidence, pattern_results, embedding_results
        )
        
        return IntentResult(
            intent_type=best_intent,
            metadata=metadata,
            reasoning=reasoning,
            alternative_intents=alternatives
        )
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query."""
        # Simple keyword extraction (could be enhanced with NLP)
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'can', 'may', 'might', 'this', 'that', 'these', 'those', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Return top 10 most relevant keywords
        return keywords[:10]
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities from query (simplified)."""
        # Simple entity extraction patterns
        entities = []
        
        # Code-related entities
        code_patterns = [
            r'\b[A-Z][a-zA-Z]*(?:[A-Z][a-zA-Z]*)*\b',  # CamelCase
            r'\b[a-z_]+\.[a-z_]+\b',                    # module.function
            r'\b[a-z_]+\(\)\b',                         # function()
            r'`[^`]+`',                                 # `code`
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, query)
            entities.extend(matches)
        
        return list(set(entities))[:5]  # Unique entities, max 5
    
    def _generate_reasoning(
        self,
        intent_type: IntentType,
        confidence: float,
        pattern_results: Dict[IntentType, float],
        embedding_results: Dict[IntentType, float]
    ) -> str:
        """Generate human-readable reasoning for classification."""
        
        if intent_type == IntentType.UNKNOWN:
            return "Unable to classify intent with sufficient confidence."
        
        reasoning_parts = []
        
        # Pattern-based reasoning
        if intent_type in pattern_results:
            reasoning_parts.append(f"Pattern analysis suggests {intent_type.value}")
        
        # Embedding-based reasoning
        if intent_type in embedding_results:
            reasoning_parts.append(f"Semantic analysis supports {intent_type.value}")
        
        # Confidence explanation
        if confidence >= 0.8:
            conf_desc = "high confidence"
        elif confidence >= 0.6:
            conf_desc = "moderate confidence"
        else:
            conf_desc = "low confidence"
        
        reasoning_parts.append(f"Classification made with {conf_desc} ({confidence:.2f})")
        
        return "; ".join(reasoning_parts)
    
    async def _validate_intent_safety(self, result: IntentResult, query: str) -> None:
        """
        Validate that intent classification is safe.
        
        Args:
            result: Intent result to validate
            query: Original query
        """
        try:
            # Check if query contains unsafe patterns for this intent
            safety_score = Decimal("0.9")  # Default high score
            
            # Reduce score for potentially unsafe combinations
            unsafe_combinations = {
                IntentType.COMMAND: ['delete', 'remove', 'destroy', 'kill'],
                IntentType.DEBUG: ['hack', 'crack', 'exploit', 'attack'],
            }
            
            if result.intent_type in unsafe_combinations:
                query_lower = query.lower()
                for unsafe_word in unsafe_combinations[result.intent_type]:
                    if unsafe_word in query_lower:
                        safety_score -= Decimal("0.1")
            
            result.metadata.safety_score = max(safety_score, Decimal("0.0"))
            
        except Exception as e:
            logger.warning(f"Intent safety validation failed: {e}")
            result.metadata.safety_score = Decimal("0.5")  # Conservative default
    
    def _create_fallback_result(self, query: str, error: str) -> IntentResult:
        """Create safe fallback result when classification fails."""
        metadata = IntentMetadata(
            confidence=0.0,
            safety_score=Decimal("0.8"),
            content_hash=generate_content_hash(query, "fallback"),
            keywords=[],
            entities=[]
        )
        
        return IntentResult(
            intent_type=IntentType.UNKNOWN,
            metadata=metadata,
            reasoning=f"Classification failed: {error}",
            alternative_intents=[]
        )
    
    async def process_feedback(self, feedback: LearningFeedback) -> bool:
        """
        Process user feedback to improve classification.
        
        Args:
            feedback: User feedback data
            
        Returns:
            Whether feedback was processed successfully
        """
        if not self.enable_pattern_learning:
            return False
        
        try:
            self._stats['feedback_processed'] += 1
            
            # Store feedback for pattern learning
            if feedback.intent_correct is not None:
                self._pattern_feedback[feedback.query_id].append(feedback)
            
            # If user suggested a different intent, learn from it
            if feedback.suggested_intent:
                # This would trigger learning new patterns (simplified for now)
                logger.info(f"Learning from feedback: suggested {feedback.suggested_intent}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process feedback: {e}")
            return False
    
    async def get_patterns(
        self,
        user_id: Optional[UUID] = None,
        min_frequency: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get detected intent patterns.
        
        Args:
            user_id: User ID to get patterns for
            min_frequency: Minimum pattern frequency
            
        Returns:
            List of detected patterns
        """
        # This would return learned patterns (simplified implementation)
        patterns = []
        
        # Return statistics about intent usage
        intent_counts = Counter()
        for intent_list in self._user_patterns.values():
            for intent in intent_list:
                intent_counts[intent] += 1
        
        for intent_type, count in intent_counts.items():
            if count >= min_frequency:
                patterns.append({
                    'intent_type': intent_type,
                    'frequency': count,
                    'confidence': min(1.0, count / 10.0)  # Simple confidence calc
                })
        
        return patterns
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        stats = self._stats.copy()
        
        if stats['intents_classified'] > 0:
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['intents_classified']
            )
            stats['pattern_match_rate'] = (
                stats['patterns_matched'] / stats['intents_classified']
            )
            stats['embedding_usage_rate'] = (
                stats['embedding_classifications'] / stats['intents_classified']
            )
        else:
            stats['average_processing_time_ms'] = 0
            stats['pattern_match_rate'] = 0
            stats['embedding_usage_rate'] = 0
        
        stats.update({
            'pattern_learning_enabled': self.enable_pattern_learning,
            'known_intent_types': len(self.INTENT_PATTERNS),
            'learned_examples': sum(len(examples) for examples in self._intent_examples.values())
        })
        
        return stats
    
    async def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down intent analyzer...")
        # Clear learning data if needed
        self._pattern_feedback.clear()
        self._intent_examples.clear()
        self._user_patterns.clear()
        logger.info("Intent analyzer shutdown completed")