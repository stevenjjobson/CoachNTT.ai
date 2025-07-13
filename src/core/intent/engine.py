"""
Main intent analysis engine for cognitive memory system.

Provides comprehensive query analysis, intent classification, and connection finding
with safety validation and non-directive principles.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from uuid import UUID, uuid4

from .models import (
    IntentType,
    IntentResult,
    IntentMetadata,
    ConnectionResult,
    QueryAnalysis,
    LearningFeedback,
    MIN_INTENT_CONFIDENCE,
    MIN_SAFETY_SCORE
)
from .analyzer import IntentAnalyzer
from .connections import ConnectionFinder
from ..validation.validator import SafetyValidator
from ..embeddings.service import EmbeddingService
from ..embeddings.models import ContentType
from ..analysis.ast_analyzer import ASTAnalyzer

logger = logging.getLogger(__name__)


class IntentEngine:
    """
    Main engine for intent analysis and connection finding.
    
    Integrates intent classification, connection discovery, and safety validation
    into a unified system that respects non-directive principles.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        safety_validator: Optional[SafetyValidator] = None,
        intent_analyzer: Optional[IntentAnalyzer] = None,
        connection_finder: Optional[ConnectionFinder] = None,
        ast_analyzer: Optional[ASTAnalyzer] = None,
        enable_learning: bool = True,
        non_directive_mode: bool = True,
        enable_code_analysis: bool = True
    ):
        """
        Initialize intent engine.
        
        Args:
            embedding_service: Service for generating embeddings
            safety_validator: Safety validator for content
            intent_analyzer: Intent classification component
            connection_finder: Connection discovery component
            ast_analyzer: AST analysis component for code understanding
            enable_learning: Whether to enable learning from feedback
            non_directive_mode: Whether to enforce non-directive principles
            enable_code_analysis: Whether to enable code analysis features
        """
        self.embedding_service = embedding_service
        self.safety_validator = safety_validator or SafetyValidator()
        self.enable_learning = enable_learning
        self.non_directive_mode = non_directive_mode
        self.enable_code_analysis = enable_code_analysis
        
        # Initialize components
        self.intent_analyzer = intent_analyzer or IntentAnalyzer(
            embedding_service=embedding_service,
            safety_validator=self.safety_validator
        )
        
        self.connection_finder = connection_finder or ConnectionFinder(
            embedding_service=embedding_service,
            safety_validator=self.safety_validator
        )
        
        # Initialize AST analyzer if code analysis is enabled
        if self.enable_code_analysis:
            self.ast_analyzer = ast_analyzer or ASTAnalyzer(
                safety_validator=self.safety_validator,
                embedding_service=embedding_service
            )
        else:
            self.ast_analyzer = None
        
        # Statistics and state
        self._stats = {
            'queries_analyzed': 0,
            'intents_classified': 0,
            'connections_found': 0,
            'safety_rejections': 0,
            'total_processing_time_ms': 0,
            'learning_feedback_received': 0,
            'code_analyses_performed': 0,
            'code_patterns_detected': 0
        }
        
        logger.info("IntentEngine initialized")
    
    async def analyze_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        include_connections: bool = True,
        max_connections: int = 10,
        code_content: Optional[str] = None,
        filename: Optional[str] = None
    ) -> QueryAnalysis:
        """
        Perform comprehensive analysis of a user query.
        
        Args:
            query: User query to analyze
            context: Additional context information
            user_id: User ID for personalization
            include_connections: Whether to find connections
            max_connections: Maximum connections to return
            code_content: Optional code content for analysis
            filename: Optional filename for code content
            
        Returns:
            Complete query analysis with intent and connections
            
        Raises:
            ValueError: If query is unsafe or invalid
            RuntimeError: If analysis fails
        """
        start_time = time.time()
        
        try:
            # Initialize analysis
            analysis = QueryAnalysis(original_query=query)
            
            # Step 1: Safety validation and abstraction
            logger.debug(f"Analyzing query: {query[:100]}...")
            
            abstracted_query, safety_metadata = await self._validate_and_abstract_query(query)
            analysis.abstracted_query = abstracted_query
            analysis.safety_score = safety_metadata.get('safety_score', Decimal("0.0"))
            
            # Check if query is safe for processing
            if not analysis.is_safe_for_processing():
                self._stats['safety_rejections'] += 1
                raise ValueError(
                    f"Query failed safety validation (score: {analysis.safety_score})"
                )
            
            # Step 2: Intent classification
            logger.debug("Classifying intent...")
            intent_start = time.time()
            
            analysis.intent_result = await self.intent_analyzer.classify_intent(
                abstracted_query,
                context=context,
                user_id=user_id
            )
            
            intent_time = (time.time() - intent_start) * 1000
            logger.debug(f"Intent classified in {intent_time:.1f}ms: {analysis.intent_result.intent_type}")
            
            # Step 3: Connection finding (if requested and intent is confident)
            if (include_connections and 
                analysis.intent_result and 
                analysis.intent_result.is_confident()):
                
                logger.debug("Finding connections...")
                connection_start = time.time()
                
                analysis.connection_result = await self.connection_finder.find_connections(
                    query=abstracted_query,
                    intent_result=analysis.intent_result,
                    context=context,
                    user_id=user_id,
                    max_connections=max_connections
                )
                
                connection_time = (time.time() - connection_start) * 1000
                logger.debug(f"Found {len(analysis.connection_result.connections)} connections in {connection_time:.1f}ms")
                
                # Step 4: Non-directive filtering
                if self.non_directive_mode:
                    await self._apply_non_directive_filter(analysis)
            
            # Step 5: Code analysis (if provided and enabled)
            if (code_content and self.enable_code_analysis and self.ast_analyzer):
                try:
                    code_analysis = await self.ast_analyzer.analyze_code(
                        content=code_content,
                        filename=filename,
                        context=context
                    )
                    
                    # Store code analysis in context for connection finding
                    if not analysis.connection_result:
                        analysis.connection_result = ConnectionResult(
                            query_id=analysis.intent_result.metadata.analysis_id if analysis.intent_result else uuid4(),
                            connections=[],
                            total_candidates=0,
                            processing_time_ms=0,
                            explanation="Code analysis performed",
                            confidence=1.0
                        )
                    
                    # Add code insights to analysis context
                    if not context:
                        context = {}
                    context['code_analysis'] = code_analysis.get_summary_stats()
                    context['detected_patterns'] = code_analysis.get_detected_patterns()
                    
                    self._stats['code_analyses_performed'] += 1
                    self._stats['code_patterns_detected'] += len(code_analysis.get_detected_patterns())
                    
                    logger.debug(f"Code analysis completed: {len(code_analysis.functions)} functions, "
                               f"{len(code_analysis.classes)} classes, {len(code_analysis.design_patterns)} patterns")
                
                except Exception as e:
                    logger.warning(f"Code analysis failed: {e}")
                    # Continue without code analysis
            
            # Finalize analysis
            total_time = (time.time() - start_time) * 1000
            analysis.total_processing_time_ms = int(total_time)
            
            # Update statistics
            self._stats['queries_analyzed'] += 1
            if analysis.intent_result:
                self._stats['intents_classified'] += 1
            if analysis.connection_result:
                self._stats['connections_found'] += len(analysis.connection_result.connections)
            self._stats['total_processing_time_ms'] += int(total_time)
            
            logger.info(
                f"Query analysis completed in {total_time:.1f}ms: "
                f"intent={analysis.intent_result.intent_type if analysis.intent_result else 'none'}, "
                f"connections={len(analysis.connection_result.connections) if analysis.connection_result else 0}"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            raise RuntimeError(f"Failed to analyze query: {e}")
    
    async def _validate_and_abstract_query(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Validate query safety and perform abstraction.
        
        Args:
            query: Original query
            
        Returns:
            Tuple of (abstracted_query, safety_metadata)
        """
        try:
            # Use safety validator to abstract content
            abstracted_query, concrete_refs = self.safety_validator.auto_abstract_content(query)
            
            # Calculate safety score
            safety_score = await self._calculate_query_safety_score(query, abstracted_query, concrete_refs)
            
            safety_metadata = {
                'safety_score': safety_score,
                'concrete_references_found': len(concrete_refs),
                'abstraction_performed': len(concrete_refs) > 0
            }
            
            return abstracted_query, safety_metadata
            
        except Exception as e:
            logger.error(f"Query validation failed: {e}")
            return query, {'safety_score': Decimal("0.0")}
    
    async def _calculate_query_safety_score(
        self,
        original: str,
        abstracted: str,
        concrete_refs: Dict[str, Any]
    ) -> Decimal:
        """
        Calculate safety score for query.
        
        Args:
            original: Original query
            abstracted: Abstracted query
            concrete_refs: Found concrete references
            
        Returns:
            Safety score (0.0-1.0)
        """
        # Base score starts high
        score = Decimal("1.0")
        
        # Penalize based on concrete references found
        if concrete_refs:
            # More concrete references = lower score
            penalty = Decimal(str(min(0.3, len(concrete_refs) * 0.1)))
            score -= penalty
        
        # Penalize if abstraction significantly changed the query
        if len(abstracted) < len(original) * 0.5:
            score -= Decimal("0.2")
        
        # Ensure minimum safety score
        return max(score, Decimal("0.0"))
    
    async def _apply_non_directive_filter(self, analysis: QueryAnalysis) -> None:
        """
        Apply non-directive filtering to ensure user autonomy.
        
        Args:
            analysis: Query analysis to filter
        """
        if not analysis.connection_result:
            return
        
        # Check for manipulation patterns
        manipulation_keywords = [
            'must', 'should', 'have to', 'need to', 'required',
            'mandatory', 'essential', 'critical', 'urgent'
        ]
        
        # Filter connections that might be directive
        safe_connections = []
        
        for connection in analysis.connection_result.connections:
            # Check explanation for directive language
            explanation_lower = connection.explanation.lower()
            is_directive = any(keyword in explanation_lower for keyword in manipulation_keywords)
            
            if not is_directive:
                safe_connections.append(connection)
            else:
                logger.debug(f"Filtered directive connection: {connection.explanation[:50]}...")
        
        # Update connection result
        analysis.connection_result.connections = safe_connections
        analysis.connection_result.non_directive_approved = True
        
        logger.debug(f"Non-directive filter applied: {len(safe_connections)} connections approved")
    
    async def provide_feedback(
        self,
        feedback: LearningFeedback
    ) -> bool:
        """
        Process user feedback for learning improvement.
        
        Args:
            feedback: User feedback data
            
        Returns:
            Whether feedback was processed successfully
        """
        if not self.enable_learning:
            logger.debug("Learning disabled, ignoring feedback")
            return False
        
        try:
            # Update statistics
            self._stats['learning_feedback_received'] += 1
            
            # Pass feedback to components for learning
            if feedback.intent_correct is not None:
                await self.intent_analyzer.process_feedback(feedback)
            
            if feedback.connection_helpful is not None:
                await self.connection_finder.process_feedback(feedback)
            
            logger.info(f"Processed feedback: {feedback.feedback_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process feedback: {e}")
            return False
    
    async def get_intent_patterns(
        self,
        user_id: Optional[UUID] = None,
        min_frequency: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get detected intent patterns for a user.
        
        Args:
            user_id: User ID to get patterns for
            min_frequency: Minimum pattern frequency
            
        Returns:
            List of detected patterns
        """
        try:
            return await self.intent_analyzer.get_patterns(
                user_id=user_id,
                min_frequency=min_frequency
            )
        except Exception as e:
            logger.error(f"Failed to get intent patterns: {e}")
            return []
    
    async def analyze_code_with_intent(
        self,
        code_content: str,
        query: Optional[str] = None,
        filename: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform code analysis with intent-aware insights.
        
        Args:
            code_content: Source code to analyze
            query: Optional query to guide analysis focus
            filename: Optional filename for language detection
            context: Additional context for analysis
            
        Returns:
            Combined analysis result with code insights and intent context
        """
        if not self.enable_code_analysis or not self.ast_analyzer:
            return {'error': 'Code analysis not enabled'}
        
        try:
            # Perform AST analysis
            code_analysis = await self.ast_analyzer.analyze_code(
                content=code_content,
                filename=filename,
                context=context
            )
            
            # If query provided, analyze it for context
            intent_context = {}
            if query:
                query_analysis = await self.analyze_query(
                    query=query,
                    context=context,
                    include_connections=False
                )
                
                if query_analysis.intent_result:
                    intent_context = {
                        'intent_type': query_analysis.intent_result.intent_type.value,
                        'confidence': query_analysis.intent_result.metadata.confidence,
                        'reasoning': query_analysis.intent_result.reasoning
                    }
            
            # Generate insights based on intent and code analysis
            insights = await self._generate_code_insights(code_analysis, intent_context)
            
            # Update statistics
            self._stats['code_analyses_performed'] += 1
            self._stats['code_patterns_detected'] += len(code_analysis.get_detected_patterns())
            
            return {
                'code_analysis': code_analysis.get_summary_stats(),
                'detected_patterns': code_analysis.get_detected_patterns(),
                'quality_assessment': code_analysis.quality_metrics.__dict__ if code_analysis.quality_metrics else None,
                'complexity_metrics': code_analysis.complexity_metrics.__dict__ if code_analysis.complexity_metrics else None,
                'dependency_analysis': self.ast_analyzer.get_dependency_analysis(code_analysis),
                'intent_context': intent_context,
                'insights': insights,
                'safety_score': float(code_analysis.metadata.safety_score)
            }
            
        except Exception as e:
            logger.error(f"Code analysis with intent failed: {e}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    async def _generate_code_insights(
        self,
        code_analysis,
        intent_context: Dict[str, Any]
    ) -> List[str]:
        """
        Generate contextual insights based on code analysis and intent.
        
        Args:
            code_analysis: AST analysis result
            intent_context: Intent analysis context
            
        Returns:
            List of insight strings
        """
        insights = []
        
        try:
            # Intent-specific insights
            intent_type = intent_context.get('intent_type', '')
            
            if intent_type == 'DEBUG':
                # Focus on complexity and potential issues
                if code_analysis.complexity_metrics:
                    if code_analysis.complexity_metrics.cyclomatic_complexity > 10:
                        insights.append("High complexity detected - consider breaking down complex functions for easier debugging")
                
                if code_analysis.quality_metrics:
                    critical_issues = code_analysis.quality_metrics.get_critical_issues()
                    if critical_issues:
                        insights.append(f"Found {len(critical_issues)} critical quality issues that may affect debugging")
            
            elif intent_type == 'OPTIMIZE':
                # Focus on performance and efficiency
                if code_analysis.dependency_graph:
                    dep_analysis = self.ast_analyzer.get_dependency_analysis(code_analysis)
                    if dep_analysis.get('high_coupling_nodes'):
                        insights.append("High coupling detected - consider reducing dependencies for better performance")
                
                if len(code_analysis.functions) > 20:
                    insights.append("Large number of functions detected - consider modular organization for optimization")
            
            elif intent_type == 'REVIEW':
                # Focus on code quality and patterns
                patterns = code_analysis.get_detected_patterns()
                if patterns:
                    insights.append(f"Detected design patterns: {', '.join([p.value for p in patterns])}")
                
                if code_analysis.quality_metrics:
                    quality_level = code_analysis.quality_metrics.get_quality_level().value
                    insights.append(f"Overall code quality assessed as: {quality_level}")
            
            # General insights
            if code_analysis.classes and not any(cls.has_init for cls in code_analysis.classes):
                insights.append("Classes detected without __init__ methods - consider proper initialization")
            
            if len(code_analysis.functions) == 0 and len(code_analysis.classes) == 0:
                insights.append("No functions or classes detected - file may contain only script-level code")
            
        except Exception as e:
            logger.warning(f"Insight generation failed: {e}")
            insights.append("Code analysis completed successfully")
        
        return insights
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get engine statistics.
        
        Returns:
            Dictionary of statistics
        """
        stats = self._stats.copy()
        
        # Calculate derived metrics
        if stats['queries_analyzed'] > 0:
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['queries_analyzed']
            )
            stats['intent_classification_rate'] = (
                stats['intents_classified'] / stats['queries_analyzed']
            )
            stats['average_connections_per_query'] = (
                stats['connections_found'] / stats['queries_analyzed']
            )
        else:
            stats['average_processing_time_ms'] = 0
            stats['intent_classification_rate'] = 0
            stats['average_connections_per_query'] = 0
        
        stats.update({
            'learning_enabled': self.enable_learning,
            'non_directive_mode': self.non_directive_mode,
            'code_analysis_enabled': self.enable_code_analysis,
            'component_stats': {
                'intent_analyzer': self.intent_analyzer.get_stats(),
                'connection_finder': self.connection_finder.get_stats()
            }
        })
        
        # Add AST analyzer stats if enabled
        if self.ast_analyzer:
            stats['component_stats']['ast_analyzer'] = self.ast_analyzer.get_stats()
        
        return stats
    
    async def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down intent engine...")
        
        if self.intent_analyzer:
            await self.intent_analyzer.shutdown()
        
        if self.connection_finder:
            await self.connection_finder.shutdown()
        
        if self.ast_analyzer:
            await self.ast_analyzer.shutdown()
        
        logger.info("Intent engine shutdown completed")