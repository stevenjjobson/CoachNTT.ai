"""
Tests for safety abstraction enforcement across all layers.

Ensures that concrete references are properly abstracted and
safety validation is enforced at every level.
"""

import pytest
from typing import Dict, Any
import time

from tests.fixtures.safety import SafetyFixtures
from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
from src.core.validation.validator import SafetyValidator


@pytest.mark.safety
class TestAbstractionEnforcement:
    """Test abstraction enforcement at all levels."""
    
    @pytest.fixture
    def safety_fixtures(self):
        """Provide safety test fixtures."""
        return SafetyFixtures()
    
    @pytest.mark.parametrize("pattern_type,patterns", [
        (k, v) for k, v in SafetyFixtures.get_unsafe_patterns().items()
    ])
    async def test_unsafe_pattern_detection(
        self,
        abstraction_engine: ConcreteAbstractionEngine,
        pattern_type: str,
        patterns: list
    ):
        """Test detection of all unsafe pattern types."""
        for pattern in patterns:
            result = abstraction_engine.process_content(pattern)
            
            # Should detect as unsafe
            assert result.safety_score < 0.8, f"Failed to detect {pattern_type}: {pattern}"
            
            # Should be abstracted
            assert result.has_changes, f"No abstraction for {pattern_type}: {pattern}"
            assert pattern not in result.content, f"Unsafe pattern remains: {pattern}"
    
    async def test_safe_abstraction_mapping(
        self,
        abstraction_engine: ConcreteAbstractionEngine,
        safety_fixtures: SafetyFixtures
    ):
        """Test that abstractions are appropriate and consistent."""
        mappings = safety_fixtures.get_safe_abstractions()
        
        for category, cases in mappings.items():
            for unsafe, expected in cases:
                result = abstraction_engine.process_content(unsafe)
                
                # Check abstraction occurred
                assert result.has_changes
                assert unsafe not in result.content
                
                # Verify abstraction quality
                if '<' in expected and '>' in expected:
                    # Check that abstraction placeholders are present
                    assert '<' in result.content and '>' in result.content
    
    async def test_edge_case_handling(
        self,
        abstraction_engine: ConcreteAbstractionEngine,
        safety_validator: SafetyValidator,
        safety_fixtures: SafetyFixtures
    ):
        """Test edge cases in safety validation."""
        edge_cases = safety_fixtures.get_edge_cases()
        
        for case in edge_cases:
            input_content = case.get("input", "")
            
            # Handle None input
            if input_content is None:
                input_content = ""
            
            # Process with abstraction
            abstraction_result = abstraction_engine.process_content(input_content)
            
            # Validate safety
            validation_result = await safety_validator.validate(abstraction_result.content)
            
            # Check safety score
            min_score = case.get("safety_score_min", 0.8)
            assert abstraction_result.safety_score >= min_score, (
                f"Edge case failed: {case.get('note', 'Unknown')} - "
                f"Score {abstraction_result.safety_score} < {min_score}"
            )
            
            # Check expected content
            if "expected_contains" in case:
                for expected in case["expected_contains"]:
                    assert expected in abstraction_result.content, (
                        f"Missing expected pattern: {expected}"
                    )
    
    async def test_safety_score_accuracy(
        self,
        abstraction_engine: ConcreteAbstractionEngine,
        safety_fixtures: SafetyFixtures
    ):
        """Test accuracy of safety scoring."""
        scoring_cases = safety_fixtures.get_safety_scoring_cases()
        
        for case in scoring_cases:
            content = case["content"]
            expected_min, expected_max = case["expected_score_range"]
            
            result = abstraction_engine.process_content(content)
            
            assert expected_min <= result.safety_score <= expected_max, (
                f"Score {result.safety_score} outside expected range "
                f"[{expected_min}, {expected_max}] for: {content[:50]}..."
            )
    
    async def test_validation_pipeline(
        self,
        safety_validator: SafetyValidator,
        safety_fixtures: SafetyFixtures
    ):
        """Test complete validation pipeline with all test cases."""
        test_cases = safety_fixtures.get_validation_test_cases()
        
        for case in test_cases:
            data = case["data"]
            expected_valid = case["expected_valid"]
            stage = case["stage"]
            
            # Skip structure/type validation tests for this validator
            if stage == "structure":
                continue
            
            # Validate content if present
            if isinstance(data, dict) and "content" in data:
                validation_result = await safety_validator.validate(data["content"])
                
                if expected_valid:
                    assert validation_result.is_valid, (
                        f"Test '{case['test_name']}' should be valid"
                    )
                else:
                    assert not validation_result.is_valid, (
                        f"Test '{case['test_name']}' should be invalid"
                    )
    
    @pytest.mark.performance
    async def test_abstraction_performance(
        self,
        abstraction_engine: ConcreteAbstractionEngine,
        safety_fixtures: SafetyFixtures
    ):
        """Test performance of abstraction engine."""
        perf_data = safety_fixtures.get_performance_test_data()
        targets = perf_data["performance_targets"]
        
        results = {}
        
        for content_type in ["small_content", "medium_content", "large_content", 
                           "many_patterns", "complex_patterns"]:
            content = perf_data[content_type]
            target_ms = targets[f"{content_type}_ms"]
            
            # Warm up
            abstraction_engine.process_content(content)
            
            # Measure
            start = time.time()
            iterations = 10
            for _ in range(iterations):
                result = abstraction_engine.process_content(content)
            
            avg_time_ms = (time.time() - start) * 1000 / iterations
            results[content_type] = avg_time_ms
            
            # Check performance target
            assert avg_time_ms < target_ms, (
                f"{content_type} took {avg_time_ms:.2f}ms "
                f"(target: {target_ms}ms)"
            )
        
        # Log results
        print("\nAbstraction Performance Results:")
        for content_type, time_ms in results.items():
            print(f"  {content_type}: {time_ms:.2f}ms")
    
    async def test_consistency_across_calls(
        self,
        abstraction_engine: ConcreteAbstractionEngine
    ):
        """Test that abstraction is consistent across multiple calls."""
        test_content = "Contact admin@example.com about /etc/config issues"
        
        # Process same content multiple times
        results = []
        for _ in range(5):
            result = abstraction_engine.process_content(test_content)
            results.append(result)
        
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.content == first_result.content
            assert abs(result.safety_score - first_result.safety_score) < 0.01
            assert result.has_changes == first_result.has_changes
    
    async def test_incremental_abstraction(
        self,
        abstraction_engine: ConcreteAbstractionEngine
    ):
        """Test handling of partially abstracted content."""
        # Start with unsafe content
        unsafe = "File at /home/user/data.csv"
        
        # First pass
        result1 = abstraction_engine.process_content(unsafe)
        assert result1.has_changes
        
        # Second pass on already abstracted content
        result2 = abstraction_engine.process_content(result1.content)
        
        # Should recognize it's already safe
        assert not result2.has_changes or result2.content == result1.content
        assert result2.safety_score >= result1.safety_score
    
    async def test_no_over_abstraction(
        self,
        abstraction_engine: ConcreteAbstractionEngine
    ):
        """Test that safe content is not unnecessarily abstracted."""
        safe_contents = [
            "This is completely safe content",
            "Using design patterns like Singleton and Factory",
            "The regex /[a-z]+/ matches lowercase",
            "Mathematical formula: E = mc^2",
            "Code comment: // TODO: implement feature",
        ]
        
        for content in safe_contents:
            result = abstraction_engine.process_content(content)
            
            # Should have high safety score
            assert result.safety_score > 0.9
            
            # Should not change safe content significantly
            if result.has_changes:
                # Ensure essential content is preserved
                assert len(result.content) >= len(content) * 0.8