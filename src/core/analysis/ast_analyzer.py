"""
Main AST analysis engine for code understanding and pattern detection.

Provides comprehensive abstract syntax tree analysis with safety-first abstraction.
"""

import ast
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

from .models import (
    AnalysisResult,
    AnalysisMetadata,
    LanguageType,
    FunctionSignature,
    ClassStructure,
    ComplexityMetrics,
    DependencyNode,
    MIN_SAFETY_SCORE
)
from .language_detector import LanguageDetector
from .pattern_detector import PatternDetector
from .complexity_analyzer import ComplexityAnalyzer
from ..validation.validator import SafetyValidator
from ..embeddings.service import EmbeddingService

logger = logging.getLogger(__name__)


class ASTAnalyzer:
    """
    Main AST analysis engine for comprehensive code understanding.
    
    Provides language detection, syntax analysis, pattern detection,
    and complexity measurement with safety-first abstraction.
    """
    
    def __init__(
        self,
        safety_validator: Optional[SafetyValidator] = None,
        embedding_service: Optional[EmbeddingService] = None,
        enable_pattern_detection: bool = True,
        enable_complexity_analysis: bool = True
    ):
        """
        Initialize AST analyzer.
        
        Args:
            safety_validator: Safety validator for content abstraction
            embedding_service: Embedding service for semantic analysis
            enable_pattern_detection: Whether to enable pattern detection
            enable_complexity_analysis: Whether to enable complexity analysis
        """
        self.safety_validator = safety_validator or SafetyValidator()
        self.embedding_service = embedding_service
        self.enable_pattern_detection = enable_pattern_detection
        self.enable_complexity_analysis = enable_complexity_analysis
        
        # Initialize components
        self.language_detector = LanguageDetector(self.safety_validator)
        
        if self.enable_pattern_detection:
            self.pattern_detector = PatternDetector(self.safety_validator)
        
        if self.enable_complexity_analysis:
            self.complexity_analyzer = ComplexityAnalyzer()
        
        # Statistics
        self._stats = {
            'analyses_performed': 0,
            'python_analyses': 0,
            'javascript_analyses': 0,
            'typescript_analyses': 0,
            'total_processing_time_ms': 0,
            'safety_violations': 0,
            'functions_analyzed': 0,
            'classes_analyzed': 0,
            'patterns_detected': 0
        }
        
        logger.info("ASTAnalyzer initialized")
    
    async def analyze_code(
        self,
        content: str,
        filename: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Perform comprehensive AST analysis of code content.
        
        Args:
            content: Source code content to analyze
            filename: Optional filename for language detection
            context: Additional context for analysis
            
        Returns:
            Complete analysis result with abstracted information
            
        Raises:
            ValueError: If content is unsafe or invalid
            RuntimeError: If analysis fails
        """
        start_time = time.time()
        
        try:
            # Initialize result
            result = AnalysisResult()
            result.metadata = AnalysisMetadata()
            
            # Step 1: Language detection and safety validation
            language, confidence, lang_metadata = self.language_detector.detect_language(
                content, filename
            )
            
            result.language = language
            result.metadata.safety_score = Decimal(str(lang_metadata.safety_score))
            result.metadata.concrete_references_found = lang_metadata.concrete_references_found
            result.metadata.abstraction_performed = lang_metadata.abstraction_performed
            
            # Validate safety score
            if result.metadata.safety_score < MIN_SAFETY_SCORE:
                self._stats['safety_violations'] += 1
                raise ValueError(
                    f"Content failed safety validation (score: {result.metadata.safety_score})"
                )
            
            # Abstract content for safe processing
            abstracted_content, concrete_refs = self.safety_validator.auto_abstract_content(content)
            result.abstracted_content = abstracted_content
            result.concrete_references_removed = len(concrete_refs)
            
            logger.debug(f"Analyzing {language.value} code (confidence: {confidence:.2f})")
            
            # Step 2: Language-specific AST analysis
            if language == LanguageType.PYTHON:
                await self._analyze_python_ast(result, abstracted_content)
            elif language == LanguageType.JAVASCRIPT:
                await self._analyze_javascript_basic(result, abstracted_content)
            elif language == LanguageType.TYPESCRIPT:
                await self._analyze_typescript_basic(result, abstracted_content)
            else:
                logger.warning(f"Unsupported language for AST analysis: {language}")
            
            # Step 3: Pattern detection (if enabled and supported)
            if (self.enable_pattern_detection and 
                language in [LanguageType.PYTHON, LanguageType.JAVASCRIPT, LanguageType.TYPESCRIPT]):
                result.design_patterns = await self.pattern_detector.detect_patterns(
                    result, abstracted_content
                )
                self._stats['patterns_detected'] += len(result.design_patterns)
            
            # Step 4: Dependency graph building
            if result.functions or result.classes:
                result.dependency_graph = await self._build_dependency_graph(
                    result, abstracted_content
                )
            
            # Step 5: Complexity analysis (if enabled)
            if self.enable_complexity_analysis and result.functions:
                result.complexity_metrics = await self.complexity_analyzer.calculate_metrics(
                    result, abstracted_content
                )
            
            # Finalize analysis
            total_time = (time.time() - start_time) * 1000
            result.metadata.processing_time_ms = int(total_time)
            
            # Update statistics
            self._update_stats(result, total_time)
            
            logger.info(
                f"AST analysis completed in {total_time:.1f}ms: "
                f"{len(result.functions)} functions, {len(result.classes)} classes, "
                f"{len(result.design_patterns)} patterns"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"AST analysis failed: {e}")
            raise RuntimeError(f"Failed to analyze code: {e}")
    
    async def _analyze_python_ast(self, result: AnalysisResult, content: str) -> None:
        """
        Analyze Python AST to extract structure information.
        
        Args:
            result: Analysis result to populate
            content: Abstracted Python code content
        """
        try:
            # Parse Python AST
            tree = ast.parse(content)
            
            # Extract functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_sig = await self._extract_python_function(node, content)
                    result.functions.append(func_sig)
                    self._stats['functions_analyzed'] += 1
                
                elif isinstance(node, ast.ClassDef):
                    class_struct = await self._extract_python_class(node, content)
                    result.classes.append(class_struct)
                    self._stats['classes_analyzed'] += 1
            
            logger.debug(f"Python AST parsed: {len(result.functions)} functions, {len(result.classes)} classes")
            
        except SyntaxError as e:
            logger.warning(f"Python syntax error: {e}")
            # Continue with partial analysis
        except Exception as e:
            logger.error(f"Python AST analysis failed: {e}")
            raise
    
    async def _extract_python_function(self, node: ast.FunctionDef, content: str) -> FunctionSignature:
        """
        Extract function signature information from Python AST node.
        
        Args:
            node: Python function AST node
            content: Source content for context
            
        Returns:
            Abstracted function signature
        """
        # Abstract function name
        name_pattern = self._abstract_identifier(node.name)
        
        # Extract parameters
        param_count = len(node.args.args)
        param_types = []
        
        for arg in node.args.args:
            if arg.annotation:
                param_types.append(self._extract_type_annotation(arg.annotation))
            else:
                param_types.append("Any")
        
        # Extract return type
        return_type = None
        if node.returns:
            return_type = self._extract_type_annotation(node.returns)
        
        # Check for async
        is_async = isinstance(node, ast.AsyncFunctionDef)
        
        # Check for decorators
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(self._abstract_identifier(decorator.id))
        
        # Check for docstring
        docstring_present = (
            len(node.body) > 0 and
            isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)
        )
        
        return FunctionSignature(
            name_pattern=name_pattern,
            parameter_count=param_count,
            parameter_types=param_types,
            return_type=return_type,
            is_async=is_async,
            decorators=decorators,
            docstring_present=docstring_present
        )
    
    async def _extract_python_class(self, node: ast.ClassDef, content: str) -> ClassStructure:
        """
        Extract class structure information from Python AST node.
        
        Args:
            node: Python class AST node
            content: Source content for context
            
        Returns:
            Abstracted class structure
        """
        # Abstract class name
        name_pattern = self._abstract_identifier(node.name)
        
        # Extract base classes
        base_class_patterns = []
        inheritance_depth = len(node.bases)
        
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_class_patterns.append(self._abstract_identifier(base.id))
        
        # Count methods and properties
        method_count = 0
        property_count = 0
        methods = []
        has_init = False
        has_str = False
        has_repr = False
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_count += 1
                method_sig = await self._extract_python_function(item, content)
                methods.append(method_sig)
                
                # Check for special methods
                if item.name == "__init__":
                    has_init = True
                elif item.name == "__str__":
                    has_str = True
                elif item.name == "__repr__":
                    has_repr = True
            
            elif isinstance(item, ast.Assign):
                # Count class attributes as properties
                property_count += len(item.targets)
        
        return ClassStructure(
            name_pattern=name_pattern,
            method_count=method_count,
            property_count=property_count,
            inheritance_depth=inheritance_depth,
            base_class_patterns=base_class_patterns,
            methods=methods,
            has_init=has_init,
            has_str=has_str,
            has_repr=has_repr
        )
    
    async def _analyze_javascript_basic(self, result: AnalysisResult, content: str) -> None:
        """
        Basic JavaScript analysis (without full AST parsing).
        
        Args:
            result: Analysis result to populate
            content: Abstracted JavaScript content
        """
        # Basic pattern-based analysis for JavaScript
        # This is a simplified version - full JS AST would require additional dependencies
        
        import re
        
        # Find function declarations
        func_patterns = [
            r'function\s+(\w+)\s*\([^)]*\)',  # function name()
            r'(\w+)\s*:\s*function\s*\([^)]*\)',  # name: function()
            r'(\w+)\s*=>\s*',  # arrow functions
        ]
        
        for pattern in func_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                func_name = match.group(1) if match.group(1) else "<anonymous>"
                name_pattern = self._abstract_identifier(func_name)
                
                func_sig = FunctionSignature(
                    name_pattern=name_pattern,
                    parameter_count=0,  # Would need proper parsing for accurate count
                    parameter_types=[],
                    is_async=False  # Would need to detect async keyword
                )
                result.functions.append(func_sig)
                self._stats['functions_analyzed'] += 1
        
        # Find class declarations
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        class_matches = re.finditer(class_pattern, content)
        
        for match in class_matches:
            class_name = match.group(1)
            base_class = match.group(2) if match.group(2) else None
            
            name_pattern = self._abstract_identifier(class_name)
            base_patterns = [self._abstract_identifier(base_class)] if base_class else []
            
            class_struct = ClassStructure(
                name_pattern=name_pattern,
                base_class_patterns=base_patterns,
                inheritance_depth=1 if base_class else 0
            )
            result.classes.append(class_struct)
            self._stats['classes_analyzed'] += 1
        
        logger.debug(f"JavaScript basic analysis: {len(result.functions)} functions, {len(result.classes)} classes")
    
    async def _analyze_typescript_basic(self, result: AnalysisResult, content: str) -> None:
        """
        Basic TypeScript analysis (extends JavaScript analysis).
        
        Args:
            result: Analysis result to populate
            content: Abstracted TypeScript content
        """
        # Start with JavaScript analysis
        await self._analyze_javascript_basic(result, content)
        
        import re
        
        # Additional TypeScript-specific patterns
        interface_pattern = r'interface\s+(\w+)'
        interface_matches = re.finditer(interface_pattern, content)
        
        for match in interface_matches:
            interface_name = match.group(1)
            name_pattern = self._abstract_identifier(interface_name)
            
            # Treat interfaces as a special type of class structure
            interface_struct = ClassStructure(
                name_pattern=f"<interface_{name_pattern}>",
                method_count=0,
                property_count=0
            )
            result.classes.append(interface_struct)
        
        logger.debug(f"TypeScript basic analysis completed")
    
    def _extract_type_annotation(self, annotation_node: ast.AST) -> str:
        """Extract type annotation as abstracted string."""
        try:
            if isinstance(annotation_node, ast.Name):
                return self._abstract_identifier(annotation_node.id)
            elif isinstance(annotation_node, ast.Constant):
                return str(type(annotation_node.value).__name__)
            else:
                return "ComplexType"
        except Exception:
            return "Any"
    
    def _abstract_identifier(self, identifier: str) -> str:
        """
        Abstract an identifier (function/class/variable name) for safety.
        
        Args:
            identifier: Original identifier
            
        Returns:
            Abstracted identifier pattern
        """
        # Use safety validator to create safe patterns
        if len(identifier) <= 3:
            return f"<{identifier.lower()}>"
        
        # Create semantic patterns based on common naming conventions
        if identifier.startswith('get_'):
            return "<getter_method>"
        elif identifier.startswith('set_'):
            return "<setter_method>"
        elif identifier.startswith('is_') or identifier.startswith('has_'):
            return "<predicate_method>"
        elif identifier.startswith('_'):
            return "<private_member>"
        elif identifier.isupper():
            return "<constant>"
        elif identifier[0].isupper():
            return "<class_name>"
        else:
            return "<identifier>"
    
    def _update_stats(self, result: AnalysisResult, processing_time: float) -> None:
        """Update analysis statistics."""
        self._stats['analyses_performed'] += 1
        self._stats['total_processing_time_ms'] += processing_time
        
        if result.language == LanguageType.PYTHON:
            self._stats['python_analyses'] += 1
        elif result.language == LanguageType.JAVASCRIPT:
            self._stats['javascript_analyses'] += 1
        elif result.language == LanguageType.TYPESCRIPT:
            self._stats['typescript_analyses'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        stats = self._stats.copy()
        
        if stats['analyses_performed'] > 0:
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['analyses_performed']
            )
            stats['average_functions_per_analysis'] = (
                stats['functions_analyzed'] / stats['analyses_performed']
            )
            stats['average_classes_per_analysis'] = (
                stats['classes_analyzed'] / stats['analyses_performed']
            )
        else:
            stats.update({
                'average_processing_time_ms': 0,
                'average_functions_per_analysis': 0,
                'average_classes_per_analysis': 0
            })
        
        # Add component stats
        stats['component_stats'] = {
            'language_detector': self.language_detector.get_stats()
        }
        
        if self.enable_pattern_detection:
            stats['component_stats']['pattern_detector'] = self.pattern_detector.get_stats()
        
        if self.enable_complexity_analysis:
            stats['component_stats']['complexity_analyzer'] = self.complexity_analyzer.get_stats()
        
        return stats
    
    async def _build_dependency_graph(
        self,
        result: AnalysisResult,
        content: str
    ) -> Dict[str, DependencyNode]:
        """
        Build a dependency graph for functions and classes.
        
        Args:
            result: Analysis result with functions and classes
            content: Abstracted source code content
            
        Returns:
            Dictionary mapping node IDs to dependency nodes
        """
        dependency_graph = {}
        
        try:
            # Create nodes for all functions and classes
            for func in result.functions:
                node_id = f"func_{func.name_pattern}"
                dependency_graph[node_id] = DependencyNode(
                    node_id=node_id,
                    node_type="function",
                    name_pattern=func.name_pattern
                )
            
            for cls in result.classes:
                node_id = f"class_{cls.name_pattern}"
                dependency_graph[node_id] = DependencyNode(
                    node_id=node_id,
                    node_type="class",
                    name_pattern=cls.name_pattern
                )
                
                # Add method nodes for class methods
                for method in cls.methods:
                    method_id = f"method_{cls.name_pattern}_{method.name_pattern}"
                    dependency_graph[method_id] = DependencyNode(
                        node_id=method_id,
                        node_type="function",
                        name_pattern=method.name_pattern
                    )
                    
                    # Method depends on its class
                    dependency_graph[method_id].dependencies.add(node_id)
                    dependency_graph[node_id].dependents.add(method_id)
            
            # Basic dependency detection (simplified)
            if result.language == LanguageType.PYTHON:
                await self._detect_python_dependencies(dependency_graph, content)
            
            logger.debug(f"Built dependency graph with {len(dependency_graph)} nodes")
            
        except Exception as e:
            logger.warning(f"Dependency graph building failed: {e}")
        
        return dependency_graph
    
    async def _detect_python_dependencies(self, graph: Dict[str, DependencyNode], content: str) -> None:
        """
        Detect dependencies in Python code using simple pattern matching.
        
        Args:
            graph: Dependency graph to populate
            content: Source code content
        """
        import re
        
        # Find function calls - simplified detection
        for node_id, node in graph.items():
            if node.node_type == "function":
                # Look for calls to other functions in the graph
                for other_id, other_node in graph.items():
                    if node_id != other_id and other_node.node_type == "function":
                        # Simple pattern: look for function_name( in content
                        pattern = rf"\\b{re.escape(other_node.name_pattern)}\\s*\\("
                        if re.search(pattern, content, re.IGNORECASE):
                            node.dependencies.add(other_id)
                            other_node.dependents.add(node_id)
    
    def get_dependency_analysis(self, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """
        Get dependency analysis summary.
        
        Args:
            analysis_result: Complete analysis result
            
        Returns:
            Dependency analysis summary
        """
        if not analysis_result.dependency_graph:
            return {}
        
        graph = analysis_result.dependency_graph
        
        # Calculate metrics
        total_nodes = len(graph)
        total_dependencies = sum(len(node.dependencies) for node in graph.values())
        
        # Find highly coupled nodes
        high_coupling_nodes = [
            node.node_id for node in graph.values()
            if node.get_coupling_score() > 0.7
        ]
        
        # Find isolated nodes (no dependencies or dependents)
        isolated_nodes = [
            node.node_id for node in graph.values()
            if len(node.dependencies) == 0 and len(node.dependents) == 0
        ]
        
        return {
            'total_nodes': total_nodes,
            'total_dependencies': total_dependencies,
            'average_coupling': total_dependencies / max(1, total_nodes),
            'high_coupling_nodes': high_coupling_nodes,
            'isolated_nodes': isolated_nodes,
            'coupling_distribution': {
                'low': len([n for n in graph.values() if n.get_coupling_score() <= 0.3]),
                'medium': len([n for n in graph.values() if 0.3 < n.get_coupling_score() <= 0.7]),
                'high': len([n for n in graph.values() if n.get_coupling_score() > 0.7])
            }
        }

    async def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down AST analyzer...")
        # Cleanup if needed
        logger.info("AST analyzer shutdown completed")