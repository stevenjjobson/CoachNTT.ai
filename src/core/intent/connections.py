"""
Connection finding algorithms for discovering relationships between memories and intents.

Provides semantic similarity, temporal proximity, and usage pattern analysis
with safety validation and non-directive principles.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from uuid import UUID
from datetime import datetime, timedelta
from collections import defaultdict

from .models import (
    IntentType,
    IntentResult,
    ConnectionType,
    Connection,
    ConnectionResult,
    ExplanationReason,
    LearningFeedback,
    MIN_CONNECTION_STRENGTH
)
from ..validation.validator import SafetyValidator
from ..embeddings.service import EmbeddingService
from ..embeddings.models import ContentType

logger = logging.getLogger(__name__)


class ConnectionFinder:
    """
    Advanced connection finding system for discovering relationships between memories.
    
    Features:
    - Semantic similarity analysis using embeddings
    - Temporal proximity detection
    - Usage pattern recognition
    - Safety-validated connections
    - Non-directive explanations
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        safety_validator: Optional[SafetyValidator] = None,
        enable_temporal_analysis: bool = True,
        enable_pattern_detection: bool = True
    ):
        """
        Initialize connection finder.
        
        Args:
            embedding_service: Service for generating embeddings
            safety_validator: Safety validator for content
            enable_temporal_analysis: Whether to analyze temporal relationships
            enable_pattern_detection: Whether to detect usage patterns
        """
        self.embedding_service = embedding_service
        self.safety_validator = safety_validator or SafetyValidator()
        self.enable_temporal_analysis = enable_temporal_analysis
        self.enable_pattern_detection = enable_pattern_detection
        
        # Connection strength thresholds
        self.similarity_threshold = 0.7
        self.temporal_threshold_hours = 24
        self.pattern_threshold = 0.6
        
        # Learning data
        self._connection_feedback = defaultdict(list)
        self._user_patterns = defaultdict(list)
        self._temporal_sequences = defaultdict(list)
        
        # Statistics
        self._stats = {
            'connections_analyzed': 0,
            'semantic_connections_found': 0,
            'temporal_connections_found': 0,
            'pattern_connections_found': 0,
            'safety_filtered_connections': 0,
            'feedback_processed': 0,
            'total_processing_time_ms': 0
        }
        
        logger.info("ConnectionFinder initialized")
    
    async def find_connections(
        self,
        query: str,
        intent_result: IntentResult,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        max_connections: int = 10,
        candidate_memories: Optional[List[Dict[str, Any]]] = None
    ) -> ConnectionResult:
        """
        Find relevant connections for a query and intent.
        
        Args:
            query: User query
            intent_result: Classified intent
            context: Additional context information
            user_id: User ID for personalization
            max_connections: Maximum connections to return
            candidate_memories: Optional list of candidate memories
            
        Returns:
            Connection result with found relationships
        """
        start_time = time.time()
        query_id = UUID(int=int(time.time() * 1000000))  # Simple query ID
        
        try:
            logger.debug(f"Finding connections for intent: {intent_result.intent_type}")
            
            # Step 1: Get candidate memories (mock for now)
            if not candidate_memories:
                candidate_memories = await self._get_candidate_memories(
                    query, intent_result, user_id, context
                )
            
            all_connections = []
            
            # Step 2: Semantic similarity analysis
            semantic_connections = await self._find_semantic_connections(
                query, intent_result, candidate_memories
            )
            all_connections.extend(semantic_connections)
            self._stats['semantic_connections_found'] += len(semantic_connections)
            
            # Step 3: Temporal proximity analysis
            if self.enable_temporal_analysis:
                temporal_connections = await self._find_temporal_connections(
                    query, intent_result, candidate_memories, user_id
                )
                all_connections.extend(temporal_connections)
                self._stats['temporal_connections_found'] += len(temporal_connections)
            
            # Step 4: Usage pattern detection
            if self.enable_pattern_detection:
                pattern_connections = await self._find_pattern_connections(
                    query, intent_result, candidate_memories, user_id
                )
                all_connections.extend(pattern_connections)
                self._stats['pattern_connections_found'] += len(pattern_connections)
            
            # Step 5: Safety filtering
            safe_connections = await self._filter_connections_for_safety(all_connections)
            filtered_count = len(all_connections) - len(safe_connections)
            self._stats['safety_filtered_connections'] += filtered_count
            
            # Step 6: Ranking and selection
            ranked_connections = await self._rank_and_select_connections(
                safe_connections, intent_result, max_connections
            )
            
            # Step 7: Generate explanations
            await self._generate_connection_explanations(ranked_connections, intent_result)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Create result
            result = ConnectionResult(
                query_id=query_id,
                connections=ranked_connections,
                total_candidates=len(candidate_memories),
                processing_time_ms=int(processing_time),
                explanation=self._generate_overall_explanation(
                    ranked_connections, intent_result
                ),
                confidence=self._calculate_overall_confidence(ranked_connections)
            )
            
            # Update statistics
            self._stats['connections_analyzed'] += 1
            self._stats['total_processing_time_ms'] += int(processing_time)
            
            logger.info(
                f"Found {len(ranked_connections)} connections in {processing_time:.1f}ms "
                f"from {len(candidate_memories)} candidates"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Connection finding failed: {e}")
            return self._create_empty_result(query_id, str(e))
    
    async def _get_candidate_memories(
        self,
        query: str,
        intent_result: IntentResult,
        user_id: Optional[UUID],
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Get candidate memories for connection analysis.
        
        This is a mock implementation - in real system would query memory repository.
        """
        # Mock candidate memories for demonstration
        mock_memories = [
            {
                'id': UUID(int=1),
                'prompt': 'How to optimize database queries',
                'response': 'Use indexing and query optimization techniques',
                'intent_type': IntentType.OPTIMIZE,
                'created_at': datetime.utcnow() - timedelta(hours=2),
                'embeddings': {
                    'prompt': [0.1, 0.2, 0.3] * 128,  # Mock 384-dim embedding
                    'response': [0.2, 0.3, 0.4] * 128
                },
                'metadata': {'domain': 'database', 'complexity': 'intermediate'}
            },
            {
                'id': UUID(int=2),
                'prompt': 'Explain the difference between SQL joins',
                'response': 'INNER JOIN returns matching rows, LEFT JOIN includes all left rows',
                'intent_type': IntentType.EXPLANATION,
                'created_at': datetime.utcnow() - timedelta(hours=1),
                'embeddings': {
                    'prompt': [0.15, 0.25, 0.35] * 128,
                    'response': [0.25, 0.35, 0.45] * 128
                },
                'metadata': {'domain': 'database', 'complexity': 'beginner'}
            },
            {
                'id': UUID(int=3),
                'prompt': 'Debug slow API response times',
                'response': 'Check database queries, add caching, optimize algorithms',
                'intent_type': IntentType.DEBUG,
                'created_at': datetime.utcnow() - timedelta(hours=6),
                'embeddings': {
                    'prompt': [0.05, 0.15, 0.25] * 128,
                    'response': [0.1, 0.2, 0.3] * 128
                },
                'metadata': {'domain': 'api', 'complexity': 'advanced'}
            }
        ]
        
        # Filter by user if provided
        if user_id:
            # In real implementation, would filter by user_id
            pass
        
        return mock_memories
    
    async def _find_semantic_connections(
        self,
        query: str,
        intent_result: IntentResult,
        candidate_memories: List[Dict[str, Any]]
    ) -> List[Connection]:
        """
        Find connections based on semantic similarity.
        
        Args:
            query: User query
            intent_result: Classified intent
            candidate_memories: Candidate memories to analyze
            
        Returns:
            List of semantic connections
        """
        connections = []
        
        try:
            # Generate embedding for query
            query_embedding_result = await self.embedding_service.generate_embedding(
                content=query,
                content_type=ContentType.QUERY
            )
            query_embedding = query_embedding_result.vector
            
            for memory in candidate_memories:
                # Calculate similarity with prompt and response
                prompt_embedding = memory.get('embeddings', {}).get('prompt', [])
                response_embedding = memory.get('embeddings', {}).get('response', [])
                
                if not prompt_embedding or not response_embedding:
                    continue
                
                # Calculate similarities
                prompt_similarity = await self.embedding_service.calculate_similarity(
                    query_embedding, prompt_embedding
                )
                response_similarity = await self.embedding_service.calculate_similarity(
                    query_embedding, response_embedding
                )
                
                # Use weighted average (favor response similarity for most intents)
                if intent_result.intent_type in [IntentType.SEARCH, IntentType.QUESTION]:
                    weight_prompt, weight_response = 0.3, 0.7
                else:
                    weight_prompt, weight_response = 0.5, 0.5
                
                combined_similarity = (
                    prompt_similarity * weight_prompt + 
                    response_similarity * weight_response
                )
                
                # Create connection if similarity is high enough
                if combined_similarity >= self.similarity_threshold:
                    connection = Connection(
                        source_id=UUID(int=0),  # Query ID placeholder
                        target_id=memory['id'],
                        connection_type=ConnectionType.SEMANTIC,
                        strength=combined_similarity,
                        reasoning=ExplanationReason.SEMANTIC_SIMILARITY,
                        explanation="",  # Will be generated later
                        metadata={
                            'prompt_similarity': prompt_similarity,
                            'response_similarity': response_similarity,
                            'memory_intent': memory.get('intent_type'),
                            'memory_domain': memory.get('metadata', {}).get('domain')
                        }
                    )
                    connections.append(connection)
            
            logger.debug(f"Found {len(connections)} semantic connections")
            return connections
            
        except Exception as e:
            logger.error(f"Semantic connection finding failed: {e}")
            return []
    
    async def _find_temporal_connections(
        self,
        query: str,
        intent_result: IntentResult,
        candidate_memories: List[Dict[str, Any]],
        user_id: Optional[UUID]
    ) -> List[Connection]:
        """
        Find connections based on temporal proximity.
        
        Args:
            query: User query
            intent_result: Classified intent
            candidate_memories: Candidate memories to analyze
            user_id: User ID for personalization
            
        Returns:
            List of temporal connections
        """
        connections = []
        current_time = datetime.utcnow()
        
        try:
            for memory in candidate_memories:
                memory_time = memory.get('created_at')
                if not memory_time:
                    continue
                
                # Calculate time difference
                time_diff = current_time - memory_time
                hours_diff = time_diff.total_seconds() / 3600
                
                # Check if within temporal threshold
                if hours_diff <= self.temporal_threshold_hours:
                    # Calculate temporal strength (closer = stronger)
                    temporal_strength = max(0.0, 1.0 - (hours_diff / self.temporal_threshold_hours))
                    
                    # Boost strength for related intents
                    memory_intent = memory.get('intent_type')
                    if self._are_intents_related(intent_result.intent_type, memory_intent):
                        temporal_strength *= 1.2
                        temporal_strength = min(1.0, temporal_strength)
                    
                    if temporal_strength >= MIN_CONNECTION_STRENGTH:
                        connection = Connection(
                            source_id=UUID(int=0),  # Query ID placeholder
                            target_id=memory['id'],
                            connection_type=ConnectionType.TEMPORAL,
                            strength=temporal_strength,
                            reasoning=ExplanationReason.TEMPORAL_PROXIMITY,
                            explanation="",  # Will be generated later
                            metadata={
                                'hours_ago': hours_diff,
                                'memory_intent': memory_intent,
                                'related_intents': self._are_intents_related(
                                    intent_result.intent_type, memory_intent
                                )
                            }
                        )
                        connections.append(connection)
            
            logger.debug(f"Found {len(connections)} temporal connections")
            return connections
            
        except Exception as e:
            logger.error(f"Temporal connection finding failed: {e}")
            return []
    
    async def _find_pattern_connections(
        self,
        query: str,
        intent_result: IntentResult,
        candidate_memories: List[Dict[str, Any]],
        user_id: Optional[UUID]
    ) -> List[Connection]:
        """
        Find connections based on usage patterns.
        
        Args:
            query: User query
            intent_result: Classified intent
            candidate_memories: Candidate memories to analyze
            user_id: User ID for personalization
            
        Returns:
            List of pattern-based connections
        """
        connections = []
        
        try:
            # Analyze domain patterns
            query_domain = self._extract_domain(query)
            
            for memory in candidate_memories:
                memory_metadata = memory.get('metadata', {})
                memory_domain = memory_metadata.get('domain')
                memory_intent = memory.get('intent_type')
                
                # Domain matching
                domain_match = query_domain == memory_domain if query_domain and memory_domain else False
                
                # Intent sequence patterns
                sequence_match = self._check_intent_sequence_pattern(
                    intent_result.intent_type, memory_intent
                )
                
                # Calculate pattern strength
                pattern_strength = 0.0
                
                if domain_match:
                    pattern_strength += 0.4
                
                if sequence_match:
                    pattern_strength += 0.6
                
                # Complexity matching (similar complexity often related)
                query_complexity = self._estimate_complexity(query)
                memory_complexity = memory_metadata.get('complexity')
                
                if query_complexity and memory_complexity and query_complexity == memory_complexity:
                    pattern_strength += 0.2
                
                pattern_strength = min(1.0, pattern_strength)
                
                # Create connection if pattern strength is sufficient
                if pattern_strength >= self.pattern_threshold:
                    connection = Connection(
                        source_id=UUID(int=0),  # Query ID placeholder
                        target_id=memory['id'],
                        connection_type=ConnectionType.PATTERN,
                        strength=pattern_strength,
                        reasoning=ExplanationReason.PATTERN_MATCH,
                        explanation="",  # Will be generated later
                        metadata={
                            'domain_match': domain_match,
                            'sequence_match': sequence_match,
                            'complexity_match': query_complexity == memory_complexity,
                            'query_domain': query_domain,
                            'memory_domain': memory_domain
                        }
                    )
                    connections.append(connection)
            
            logger.debug(f"Found {len(connections)} pattern connections")
            return connections
            
        except Exception as e:
            logger.error(f"Pattern connection finding failed: {e}")
            return []
    
    def _are_intents_related(self, intent1: IntentType, intent2: IntentType) -> bool:
        """Check if two intents are related."""
        related_groups = [
            {IntentType.QUESTION, IntentType.EXPLANATION, IntentType.LEARN},
            {IntentType.DEBUG, IntentType.OPTIMIZE, IntentType.REVIEW},
            {IntentType.CREATE, IntentType.PLAN, IntentType.COMMAND},
            {IntentType.SEARCH, IntentType.REVIEW, IntentType.REFLECT}
        ]
        
        for group in related_groups:
            if intent1 in group and intent2 in group:
                return True
        
        return False
    
    def _extract_domain(self, query: str) -> Optional[str]:
        """Extract domain/technology from query (simplified)."""
        domain_keywords = {
            'database': ['sql', 'database', 'db', 'query', 'table', 'index', 'join'],
            'api': ['api', 'rest', 'endpoint', 'http', 'request', 'response'],
            'frontend': ['html', 'css', 'javascript', 'react', 'vue', 'angular'],
            'backend': ['server', 'backend', 'node', 'python', 'java', 'spring'],
            'devops': ['docker', 'kubernetes', 'deployment', 'ci/cd', 'pipeline']
        }
        
        query_lower = query.lower()
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return domain
        
        return None
    
    def _estimate_complexity(self, query: str) -> Optional[str]:
        """Estimate complexity level of query (simplified)."""
        complexity_indicators = {
            'beginner': ['what is', 'how to', 'basic', 'simple', 'introduction'],
            'intermediate': ['optimize', 'implement', 'integrate', 'configure'],
            'advanced': ['architecture', 'performance', 'scale', 'distribute', 'complex']
        }
        
        query_lower = query.lower()
        
        for level, indicators in complexity_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                return level
        
        return None
    
    def _check_intent_sequence_pattern(self, current_intent: IntentType, memory_intent: IntentType) -> bool:
        """Check if intents follow a common sequence pattern."""
        common_sequences = [
            [IntentType.QUESTION, IntentType.EXPLANATION, IntentType.CREATE],
            [IntentType.DEBUG, IntentType.SEARCH, IntentType.OPTIMIZE],
            [IntentType.LEARN, IntentType.QUESTION, IntentType.REVIEW],
            [IntentType.PLAN, IntentType.CREATE, IntentType.REVIEW]
        ]
        
        for sequence in common_sequences:
            try:
                current_idx = sequence.index(current_intent)
                memory_idx = sequence.index(memory_intent)
                # Related if in same sequence and reasonably close
                if abs(current_idx - memory_idx) <= 1:
                    return True
            except ValueError:
                continue
        
        return False
    
    async def _filter_connections_for_safety(self, connections: List[Connection]) -> List[Connection]:
        """
        Filter connections to ensure they meet safety requirements.
        
        Args:
            connections: List of connections to filter
            
        Returns:
            Filtered list of safe connections
        """
        safe_connections = []
        
        for connection in connections:
            # Check connection strength threshold
            if connection.strength < MIN_CONNECTION_STRENGTH:
                continue
            
            # Check for safety issues in metadata
            metadata = connection.metadata
            
            # Avoid connections that might leak concrete information
            if metadata.get('contains_concrete_refs', False):
                continue
            
            # Ensure non-manipulative reasoning
            if connection.reasoning in [ExplanationReason.PATTERN_MATCH]:
                # Pattern matches should be transparent and non-directive
                if not metadata.get('transparent_pattern', True):
                    continue
            
            safe_connections.append(connection)
        
        return safe_connections
    
    async def _rank_and_select_connections(
        self,
        connections: List[Connection],
        intent_result: IntentResult,
        max_connections: int
    ) -> List[Connection]:
        """
        Rank connections and select the best ones.
        
        Args:
            connections: List of connections to rank
            intent_result: Intent classification result
            max_connections: Maximum connections to return
            
        Returns:
            Ranked and filtered list of connections
        """
        # Calculate ranking scores
        for connection in connections:
            ranking_score = connection.strength
            
            # Boost score based on connection type preference for intent
            type_bonuses = {
                IntentType.QUESTION: {
                    ConnectionType.SEMANTIC: 0.2,
                    ConnectionType.CONTEXTUAL: 0.1
                },
                IntentType.DEBUG: {
                    ConnectionType.SOLUTION: 0.3,
                    ConnectionType.PATTERN: 0.2
                },
                IntentType.LEARN: {
                    ConnectionType.SEQUENTIAL: 0.2,
                    ConnectionType.TOPIC: 0.1
                }
            }
            
            intent_bonuses = type_bonuses.get(intent_result.intent_type, {})
            bonus = intent_bonuses.get(connection.connection_type, 0.0)
            ranking_score += bonus
            
            # Store in metadata for sorting
            connection.metadata['ranking_score'] = ranking_score
        
        # Sort by ranking score
        connections.sort(
            key=lambda c: c.metadata.get('ranking_score', c.strength),
            reverse=True
        )
        
        # Return top connections
        return connections[:max_connections]
    
    async def _generate_connection_explanations(
        self,
        connections: List[Connection],
        intent_result: IntentResult
    ) -> None:
        """
        Generate human-readable explanations for connections.
        
        Args:
            connections: List of connections to explain
            intent_result: Intent classification result
        """
        for connection in connections:
            explanation = self._create_connection_explanation(connection, intent_result)
            connection.explanation = explanation
    
    def _create_connection_explanation(
        self,
        connection: Connection,
        intent_result: IntentResult
    ) -> str:
        """Create explanation for a specific connection."""
        
        explanations = {
            ConnectionType.SEMANTIC: {
                ExplanationReason.SEMANTIC_SIMILARITY: "This content discusses similar concepts and might provide relevant insights."
            },
            ConnectionType.TEMPORAL: {
                ExplanationReason.TEMPORAL_PROXIMITY: "This was discussed recently and might be part of the same context."
            },
            ConnectionType.PATTERN: {
                ExplanationReason.PATTERN_MATCH: "This follows a similar pattern to your current query."
            }
        }
        
        base_explanation = explanations.get(
            connection.connection_type, {}
        ).get(
            connection.reasoning, 
            "This content might be relevant to your query."
        )
        
        # Add specific details from metadata
        metadata = connection.metadata
        
        if connection.connection_type == ConnectionType.SEMANTIC:
            similarity = metadata.get('response_similarity', 0)
            if similarity > 0.8:
                base_explanation += " (Very similar content)"
            elif similarity > 0.6:
                base_explanation += " (Similar content)"
        
        elif connection.connection_type == ConnectionType.TEMPORAL:
            hours_ago = metadata.get('hours_ago', 0)
            if hours_ago < 1:
                base_explanation += " (From less than an hour ago)"
            elif hours_ago < 6:
                base_explanation += f" (From {int(hours_ago)} hours ago)"
        
        elif connection.connection_type == ConnectionType.PATTERN:
            if metadata.get('domain_match'):
                base_explanation += " (Same domain/technology)"
            if metadata.get('sequence_match'):
                base_explanation += " (Part of common workflow)"
        
        return base_explanation
    
    def _generate_overall_explanation(
        self,
        connections: List[Connection],
        intent_result: IntentResult
    ) -> str:
        """Generate overall explanation for connection results."""
        
        if not connections:
            return "No relevant connections found for this query."
        
        count = len(connections)
        intent_name = intent_result.intent_type.value
        
        explanation = f"Found {count} relevant connection{'s' if count != 1 else ''} for your {intent_name} query. "
        
        # Categorize connections
        semantic_count = sum(1 for c in connections if c.connection_type == ConnectionType.SEMANTIC)
        temporal_count = sum(1 for c in connections if c.connection_type == ConnectionType.TEMPORAL)
        pattern_count = sum(1 for c in connections if c.connection_type == ConnectionType.PATTERN)
        
        details = []
        if semantic_count > 0:
            details.append(f"{semantic_count} based on content similarity")
        if temporal_count > 0:
            details.append(f"{temporal_count} from recent activity")
        if pattern_count > 0:
            details.append(f"{pattern_count} following similar patterns")
        
        if details:
            explanation += "This includes " + ", ".join(details) + "."
        
        return explanation
    
    def _calculate_overall_confidence(self, connections: List[Connection]) -> float:
        """Calculate overall confidence in connection results."""
        if not connections:
            return 0.0
        
        # Average of connection strengths, weighted by ranking
        total_weight = 0
        weighted_sum = 0
        
        for i, connection in enumerate(connections):
            weight = 1.0 / (i + 1)  # Decreasing weight for lower-ranked connections
            weighted_sum += connection.strength * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _create_empty_result(self, query_id: UUID, error: str) -> ConnectionResult:
        """Create empty result when connection finding fails."""
        return ConnectionResult(
            query_id=query_id,
            connections=[],
            total_candidates=0,
            processing_time_ms=0,
            explanation=f"Connection finding failed: {error}",
            confidence=0.0,
            non_directive_approved=True
        )
    
    async def process_feedback(self, feedback: LearningFeedback) -> bool:
        """
        Process user feedback to improve connection finding.
        
        Args:
            feedback: User feedback data
            
        Returns:
            Whether feedback was processed successfully
        """
        try:
            self._stats['feedback_processed'] += 1
            
            # Store feedback for learning
            if feedback.connection_helpful is not None:
                self._connection_feedback[feedback.query_id].append(feedback)
            
            # Learn from feedback (simplified implementation)
            if feedback.connection_helpful is False:
                # Could adjust connection thresholds or patterns
                logger.info("Learning from negative connection feedback")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process connection feedback: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection finder statistics."""
        stats = self._stats.copy()
        
        if stats['connections_analyzed'] > 0:
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['connections_analyzed']
            )
            stats['average_semantic_per_query'] = (
                stats['semantic_connections_found'] / stats['connections_analyzed']
            )
            stats['average_temporal_per_query'] = (
                stats['temporal_connections_found'] / stats['connections_analyzed']
            )
            stats['average_pattern_per_query'] = (
                stats['pattern_connections_found'] / stats['connections_analyzed']
            )
        else:
            stats['average_processing_time_ms'] = 0
            stats['average_semantic_per_query'] = 0
            stats['average_temporal_per_query'] = 0
            stats['average_pattern_per_query'] = 0
        
        stats.update({
            'temporal_analysis_enabled': self.enable_temporal_analysis,
            'pattern_detection_enabled': self.enable_pattern_detection,
            'similarity_threshold': self.similarity_threshold,
            'temporal_threshold_hours': self.temporal_threshold_hours,
            'pattern_threshold': self.pattern_threshold
        })
        
        return stats
    
    async def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down connection finder...")
        
        # Clear learning data
        self._connection_feedback.clear()
        self._user_patterns.clear()
        self._temporal_sequences.clear()
        
        logger.info("Connection finder shutdown completed")