"""
Code complexity analysis for quality assessment.

Calculates cyclomatic complexity, cognitive complexity, and other quality metrics.
"""

import ast
import re
import logging
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

from .models import (
    ComplexityMetrics,
    QualityMetrics,
    QualityIssue,
    QualityLevel,
    AnalysisResult,
    LanguageType,
    FunctionSignature
)

logger = logging.getLogger(__name__)


class ComplexityAnalyzer:
    """
    Code complexity analysis for quality assessment.
    
    Calculates various complexity metrics while maintaining safety through abstraction.
    """
    
    def __init__(self):
        """Initialize complexity analyzer."""
        # Complexity thresholds
        self.cyclomatic_thresholds = {
            'excellent': 5,
            'good': 10,
            'fair': 20,
            'poor': 30
        }
        
        self.cognitive_thresholds = {
            'excellent': 10,
            'good': 15,
            'fair': 25,
            'poor': 40
        }
        
        # Statistics
        self._stats = {
            'analyses_performed': 0,
            'total_functions_analyzed': 0,
            'total_complexity_calculated': 0,
            'total_processing_time_ms': 0,
            'high_complexity_functions': 0
        }
        
        logger.info("ComplexityAnalyzer initialized")
    
    async def calculate_metrics(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> ComplexityMetrics:
        """
        Calculate comprehensive complexity metrics.
        
        Args:
            analysis_result: AST analysis result
            content: Abstracted source code content
            
        Returns:
            Complete complexity metrics
        """
        import time
        start_time = time.time()
        
        try:
            if analysis_result.language == LanguageType.PYTHON:
                metrics = await self._calculate_python_complexity(analysis_result, content)
            elif analysis_result.language in [LanguageType.JAVASCRIPT, LanguageType.TYPESCRIPT]:
                metrics = await self._calculate_javascript_complexity(analysis_result, content)
            else:
                metrics = await self._calculate_basic_complexity(analysis_result, content)
            
            # Update function-level complexity
            await self._update_function_complexity(analysis_result, content)
            
            # Update statistics
            processing_time = (time.time() - start_time) * 1000
            self._update_stats(analysis_result, processing_time)
            
            logger.debug(f"Complexity analysis completed in {processing_time:.1f}ms")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")
            return ComplexityMetrics()
    
    async def _calculate_python_complexity(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> ComplexityMetrics:
        """Calculate complexity metrics for Python code."""
        try:
            tree = ast.parse(content)
            
            # Calculate cyclomatic complexity
            cyclomatic = self._calculate_cyclomatic_complexity_ast(tree)
            
            # Calculate cognitive complexity
            cognitive = self._calculate_cognitive_complexity_ast(tree)
            
            # Calculate lines of code
            lines = len([line for line in content.split('\n') if line.strip()])
            
            # Calculate maintainability index (simplified)
            maintainability = self._calculate_maintainability_index(
                cyclomatic, lines, len(content)
            )
            
            # Calculate Halstead difficulty (simplified)
            halstead = self._calculate_halstead_difficulty(content)
            
            return ComplexityMetrics(
                cyclomatic_complexity=cyclomatic,
                cognitive_complexity=cognitive,
                lines_of_code=lines,
                maintainability_index=maintainability,
                halstead_difficulty=halstead
            )
            
        except SyntaxError:
            logger.warning("Python syntax error in complexity analysis")
            return await self._calculate_basic_complexity(analysis_result, content)
        except Exception as e:
            logger.error(f"Python complexity calculation failed: {e}")
            return ComplexityMetrics()
    
    async def _calculate_javascript_complexity(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> ComplexityMetrics:
        """Calculate complexity metrics for JavaScript/TypeScript code."""
        # Pattern-based complexity analysis for JavaScript
        cyclomatic = self._calculate_cyclomatic_complexity_patterns(content)
        cognitive = self._calculate_cognitive_complexity_patterns(content)
        
        lines = len([line for line in content.split('\n') if line.strip()])
        maintainability = self._calculate_maintainability_index(
            cyclomatic, lines, len(content)
        )
        halstead = self._calculate_halstead_difficulty(content)
        
        return ComplexityMetrics(
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            lines_of_code=lines,
            maintainability_index=maintainability,
            halstead_difficulty=halstead
        )
    
    async def _calculate_basic_complexity(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> ComplexityMetrics:
        """Calculate basic complexity metrics for any language."""
        # Pattern-based analysis
        cyclomatic = self._calculate_cyclomatic_complexity_patterns(content)
        cognitive = cyclomatic * 1.2  # Estimate cognitive as slightly higher
        
        lines = len([line for line in content.split('\n') if line.strip()])
        maintainability = self._calculate_maintainability_index(
            cyclomatic, lines, len(content)
        )
        
        return ComplexityMetrics(
            cyclomatic_complexity=int(cyclomatic),
            cognitive_complexity=int(cognitive),
            lines_of_code=lines,
            maintainability_index=maintainability,
            halstead_difficulty=0.0  # Not calculated for unknown languages
        )
    
    def _calculate_cyclomatic_complexity_ast(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity using Python AST."""
        complexity = 1  # Base complexity
        
        # Decision points that increase complexity
        decision_nodes = (
            ast.If, ast.While, ast.For, ast.AsyncFor,
            ast.ExceptHandler, ast.With, ast.AsyncWith,
            ast.Assert, ast.BoolOp
        )
        
        for node in ast.walk(tree):
            if isinstance(node, decision_nodes):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # Count additional complexity for boolean operators
                complexity += len(node.values) - 1
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                # Comprehensions add complexity
                complexity += 1
        
        return complexity
    
    def _calculate_cognitive_complexity_ast(self, tree: ast.AST) -> int:
        """Calculate cognitive complexity using Python AST."""
        complexity = 0
        nesting_level = 0
        
        class CognitiveComplexityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.complexity = 0
                self.nesting_level = 0
            
            def visit_If(self, node):
                self.complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.generic_visit(node)
                self.nesting_level -= 1
            
            def visit_While(self, node):
                self.complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.generic_visit(node)
                self.nesting_level -= 1
            
            def visit_For(self, node):
                self.complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.generic_visit(node)
                self.nesting_level -= 1
            
            def visit_ExceptHandler(self, node):
                self.complexity += 1 + self.nesting_level
                self.nesting_level += 1
                self.generic_visit(node)
                self.nesting_level -= 1
            
            def visit_FunctionDef(self, node):
                # Reset nesting for function definitions
                old_nesting = self.nesting_level
                self.nesting_level = 0
                self.generic_visit(node)
                self.nesting_level = old_nesting
        
        visitor = CognitiveComplexityVisitor()
        visitor.visit(tree)
        
        return visitor.complexity
    
    def _calculate_cyclomatic_complexity_patterns(self, content: str) -> int:
        """Calculate cyclomatic complexity using pattern matching."""
        complexity = 1  # Base complexity
        
        # Decision point patterns
        decision_patterns = [
            r'\bif\b',
            r'\belse\s+if\b',
            r'\belif\b',
            r'\bwhile\b',
            r'\bfor\b',
            r'\bswitch\b',
            r'\bcase\b',
            r'\bcatch\b',
            r'\btry\b',
            r'\band\b',
            r'\bor\b',
            r'&&',
            r'\|\|',
            r'\?.*:',  # Ternary operator
        ]
        
        for pattern in decision_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            complexity += matches
        
        return complexity
    
    def _calculate_cognitive_complexity_patterns(self, content: str) -> int:
        """Calculate cognitive complexity using pattern matching."""
        # Simplified cognitive complexity estimation
        lines = content.split('\n')
        complexity = 0
        nesting_level = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Increase nesting level
            if any(pattern in stripped.lower() for pattern in ['if ', 'for ', 'while ', 'function']):
                complexity += 1 + nesting_level
                if '{' in stripped or ':' in stripped:
                    nesting_level += 1
            
            # Decrease nesting level
            if '}' in stripped or (stripped and stripped[0] not in ' \t' and nesting_level > 0):
                nesting_level = max(0, nesting_level - 1)
        
        return complexity
    
    def _calculate_maintainability_index(
        self,
        cyclomatic: int,
        lines_of_code: int,
        volume: int
    ) -> float:
        """
        Calculate maintainability index.
        
        Simplified version of the maintainability index formula.
        """
        if lines_of_code == 0:
            return 0.0
        
        # Simplified maintainability index
        # Higher values = more maintainable
        volume_factor = max(1, volume / 1000)  # Normalize volume
        complexity_factor = max(1, cyclomatic)
        lines_factor = max(1, lines_of_code / 100)
        
        # Scale from 0-100 (100 = most maintainable)
        index = max(0, 100 - (complexity_factor * 10) - (lines_factor * 5) - (volume_factor * 2))
        
        return min(100.0, index)
    
    def _calculate_halstead_difficulty(self, content: str) -> float:
        """
        Calculate simplified Halstead difficulty metric.
        
        Based on operator and operand counting.
        """
        # Count operators (simplified)
        operators = ['+', '-', '*', '/', '%', '=', '==', '!=', '<', '>', '<=', '>=',
                    '&&', '||', '!', '&', '|', '^', '<<', '>>', '++', '--']
        
        operator_count = sum(content.count(op) for op in operators)
        
        # Count operands (simplified - count identifiers)
        operands = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content)
        unique_operands = len(set(operands))
        total_operands = len(operands)
        
        if unique_operands == 0 or total_operands == 0:
            return 0.0
        
        # Simplified Halstead difficulty
        difficulty = (len(set(operators)) / 2) * (total_operands / unique_operands)
        
        return min(difficulty, 100.0)  # Cap at 100
    
    async def _update_function_complexity(
        self,
        analysis_result: AnalysisResult,
        content: str
    ) -> None:
        """Update complexity metrics for individual functions."""
        if analysis_result.language != LanguageType.PYTHON:
            return  # Only detailed function analysis for Python currently
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Find corresponding function in analysis result
                    func_name_pattern = self._abstract_identifier(node.name)
                    
                    for func in analysis_result.functions:
                        if func.name_pattern == func_name_pattern:
                            # Calculate function-specific complexity
                            func_complexity = self._calculate_function_complexity(node)
                            func.complexity_metrics = func_complexity
                            
                            if func_complexity.cyclomatic_complexity > 20:
                                self._stats['high_complexity_functions'] += 1
                            
                            break
        
        except Exception as e:
            logger.warning(f"Function complexity update failed: {e}")
    
    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> ComplexityMetrics:
        """Calculate complexity metrics for a single function."""
        # Create a temporary tree with just this function
        temp_tree = ast.Module(body=[func_node], type_ignores=[])
        
        cyclomatic = self._calculate_cyclomatic_complexity_ast(temp_tree)
        cognitive = self._calculate_cognitive_complexity_ast(temp_tree)
        
        # Count lines in function
        lines = len([line for line in ast.get_source_segment("", func_node).split('\n') 
                    if line.strip()]) if hasattr(ast, 'get_source_segment') else 0
        
        return ComplexityMetrics(
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            lines_of_code=lines
        )
    
    def _abstract_identifier(self, identifier: str) -> str:
        """Abstract identifier for safety (simplified version)."""
        if len(identifier) <= 3:
            return f"<{identifier.lower()}>"
        
        if identifier.startswith('get_'):
            return "<getter_method>"
        elif identifier.startswith('set_'):
            return "<setter_method>"
        elif identifier.startswith('is_') or identifier.startswith('has_'):
            return "<predicate_method>"
        elif identifier.startswith('_'):
            return "<private_member>"
        else:
            return "<identifier>"
    
    def _update_stats(self, analysis_result: AnalysisResult, processing_time: float) -> None:
        """Update complexity analysis statistics."""
        self._stats['analyses_performed'] += 1
        self._stats['total_functions_analyzed'] += len(analysis_result.functions)
        self._stats['total_processing_time_ms'] += processing_time
        
        if analysis_result.complexity_metrics:
            self._stats['total_complexity_calculated'] += analysis_result.complexity_metrics.cyclomatic_complexity
    
    def assess_quality(self, analysis_result: AnalysisResult) -> QualityMetrics:
        """
        Assess overall code quality based on complexity metrics.
        
        Args:
            analysis_result: Complete analysis result
            
        Returns:
            Quality assessment with issues and recommendations
        """
        issues = []
        quality_scores = []
        
        # Assess overall complexity
        if analysis_result.complexity_metrics:
            complexity_score, complexity_issues = self._assess_complexity_quality(
                analysis_result.complexity_metrics
            )
            quality_scores.append(complexity_score)
            issues.extend(complexity_issues)
        
        # Assess function-level quality
        function_score, function_issues = self._assess_function_quality(analysis_result.functions)
        quality_scores.append(function_score)
        issues.extend(function_issues)
        
        # Assess class-level quality
        class_score, class_issues = self._assess_class_quality(analysis_result.classes)
        quality_scores.append(class_score)
        issues.extend(class_issues)
        
        # Calculate overall score
        overall_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return QualityMetrics(
            overall_score=overall_score,
            maintainability=analysis_result.complexity_metrics.maintainability_index / 100.0 
                          if analysis_result.complexity_metrics else 0.0,
            readability=max(0.0, 1.0 - (len(issues) * 0.1)),  # Simplified readability
            testability=max(0.0, 1.0 - (overall_score * 0.5)),  # Simplified testability
            issues=issues
        )
    
    def _assess_complexity_quality(self, metrics: ComplexityMetrics) -> tuple[float, List[QualityIssue]]:
        """Assess quality based on complexity metrics."""
        issues = []
        score = 1.0
        
        # Check cyclomatic complexity
        if metrics.cyclomatic_complexity > self.cyclomatic_thresholds['poor']:
            issues.append(QualityIssue(
                issue_type="high_cyclomatic_complexity",
                severity=QualityLevel.CRITICAL,
                description=f"Cyclomatic complexity ({metrics.cyclomatic_complexity}) is very high",
                location_pattern="<overall_codebase>",
                suggestion="Consider breaking down complex functions and reducing decision points"
            ))
            score -= 0.4
        elif metrics.cyclomatic_complexity > self.cyclomatic_thresholds['fair']:
            issues.append(QualityIssue(
                issue_type="moderate_cyclomatic_complexity",
                severity=QualityLevel.POOR,
                description=f"Cyclomatic complexity ({metrics.cyclomatic_complexity}) is high",
                location_pattern="<overall_codebase>",
                suggestion="Consider refactoring to reduce complexity"
            ))
            score -= 0.2
        
        # Check cognitive complexity
        if metrics.cognitive_complexity > self.cognitive_thresholds['poor']:
            issues.append(QualityIssue(
                issue_type="high_cognitive_complexity",
                severity=QualityLevel.CRITICAL,
                description=f"Cognitive complexity ({metrics.cognitive_complexity}) is very high",
                location_pattern="<overall_codebase>",
                suggestion="Simplify logic and reduce nesting levels"
            ))
            score -= 0.3
        
        # Check maintainability
        if metrics.maintainability_index < 20:
            issues.append(QualityIssue(
                issue_type="low_maintainability",
                severity=QualityLevel.POOR,
                description=f"Maintainability index ({metrics.maintainability_index:.1f}) is low",
                location_pattern="<overall_codebase>",
                suggestion="Improve code structure and reduce complexity"
            ))
            score -= 0.2
        
        return max(0.0, score), issues
    
    def _assess_function_quality(self, functions: List[FunctionSignature]) -> tuple[float, List[QualityIssue]]:
        """Assess quality at function level."""
        issues = []
        score = 1.0
        
        if not functions:
            return 0.5, issues
        
        high_complexity_functions = sum(
            1 for func in functions
            if func.complexity_metrics and func.complexity_metrics.cyclomatic_complexity > 20
        )
        
        if high_complexity_functions > len(functions) * 0.3:
            issues.append(QualityIssue(
                issue_type="many_complex_functions",
                severity=QualityLevel.POOR,
                description=f"{high_complexity_functions} functions have high complexity",
                location_pattern="<multiple_functions>",
                suggestion="Refactor complex functions into smaller, simpler ones"
            ))
            score -= 0.3
        
        # Check for functions without docstrings
        undocumented_functions = sum(
            1 for func in functions
            if not func.docstring_present
        )
        
        if undocumented_functions > len(functions) * 0.5:
            issues.append(QualityIssue(
                issue_type="insufficient_documentation",
                severity=QualityLevel.FAIR,
                description=f"{undocumented_functions} functions lack documentation",
                location_pattern="<multiple_functions>",
                suggestion="Add docstrings to improve code documentation"
            ))
            score -= 0.1
        
        return max(0.0, score), issues
    
    def _assess_class_quality(self, classes: List[ClassStructure]) -> tuple[float, List[QualityIssue]]:
        """Assess quality at class level."""
        issues = []
        score = 1.0
        
        if not classes:
            return 0.8, issues  # Neutral score for no classes
        
        # Check for classes with too many methods
        large_classes = sum(
            1 for cls in classes
            if cls.method_count > 20
        )
        
        if large_classes > 0:
            issues.append(QualityIssue(
                issue_type="large_classes",
                severity=QualityLevel.FAIR,
                description=f"{large_classes} classes have many methods",
                location_pattern="<multiple_classes>",
                suggestion="Consider breaking large classes into smaller, focused classes"
            ))
            score -= 0.2
        
        return max(0.0, score), issues
    
    def get_stats(self) -> Dict[str, Any]:
        """Get complexity analysis statistics."""
        stats = self._stats.copy()
        
        if stats['analyses_performed'] > 0:
            stats['average_processing_time_ms'] = (
                stats['total_processing_time_ms'] / stats['analyses_performed']
            )
            stats['average_functions_per_analysis'] = (
                stats['total_functions_analyzed'] / stats['analyses_performed']
            )
            stats['average_complexity_per_analysis'] = (
                stats['total_complexity_calculated'] / stats['analyses_performed']
            )
            stats['high_complexity_rate'] = (
                stats['high_complexity_functions'] / max(1, stats['total_functions_analyzed'])
            )
        else:
            stats.update({
                'average_processing_time_ms': 0,
                'average_functions_per_analysis': 0,
                'average_complexity_per_analysis': 0,
                'high_complexity_rate': 0
            })
        
        return stats