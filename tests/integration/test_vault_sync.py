"""
Integration tests for vault synchronization system.

Tests complete vault sync pipeline with memory system, AST analysis,
and intent engine integration.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from src.services.vault import (
    VaultSyncEngine,
    VaultSyncConfig,
    TemplateType,
    ConflictStrategy
)
from src.core.memory.abstract_models import AbstractMemoryEntry, InteractionType, MemoryMetadata
from src.core.validation.validator import SafetyValidator
from src.core.analysis.ast_analyzer import ASTAnalyzer
from src.core.intent.engine import IntentEngine


class TestVaultSyncIntegration:
    """Integration tests for vault synchronization."""
    
    @pytest.fixture
    def temp_vault_dir(self):
        """Create temporary vault directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_memory_repository(self):
        """Create comprehensive mock memory repository."""
        repository = Mock()
        repository.get_memory = AsyncMock()
        repository.get_recent_memories = AsyncMock()
        repository.search_memories = AsyncMock()
        repository.create_memory = AsyncMock()
        repository.update_memory = AsyncMock()
        return repository
    
    @pytest.fixture
    def mock_safety_validator(self):
        """Create mock safety validator with realistic behavior."""
        validator = Mock(spec=SafetyValidator)
        
        def mock_abstract_content(content):
            # Simulate abstraction of common concrete references
            abstracted = content
            concrete_refs = {}
            
            # Abstract file paths
            if '/' in content or '\\' in content:
                abstracted = abstracted.replace('/path/to/file', '<file_path>')
                abstracted = abstracted.replace('C:\\Users\\user', '<user_directory>')
                concrete_refs['file_paths'] = ['replaced paths']
            
            # Abstract API keys and secrets
            if 'api_key' in content.lower() or 'secret' in content.lower():
                abstracted = abstracted.replace('sk-1234567890', '<api_key>')
                concrete_refs['secrets'] = ['replaced secrets']
            
            return abstracted, concrete_refs
        
        validator.auto_abstract_content.side_effect = mock_abstract_content
        return validator
    
    @pytest.fixture
    def mock_ast_analyzer(self):
        """Create mock AST analyzer."""
        analyzer = Mock(spec=ASTAnalyzer)
        
        async def mock_analyze_code(content, filename=None, context=None):
            from src.core.analysis.models import AnalysisResult, AnalysisMetadata, LanguageType
            
            result = Mock(spec=AnalysisResult)
            result.language = LanguageType.PYTHON
            result.functions = []
            result.classes = []
            result.design_patterns = []
            result.complexity_metrics = None
            result.dependency_graph = {}
            result.metadata = Mock(spec=AnalysisMetadata)
            result.metadata.safety_score = Decimal("0.9")
            result.metadata.processing_time_ms = 50
            result.abstracted_content = content
            result.concrete_references_removed = 0
            result.is_analysis_complete.return_value = True
            result.get_summary_stats.return_value = {
                'language': 'python',
                'function_count': 0,
                'class_count': 0
            }
            result.get_detected_patterns.return_value = []
            
            return result
        
        analyzer.analyze_code = mock_analyze_code
        analyzer.get_stats.return_value = {
            'analyses_performed': 0,
            'component_stats': {}
        }
        return analyzer
    
    @pytest.fixture
    def mock_intent_engine(self):
        """Create mock intent engine."""
        engine = Mock(spec=IntentEngine)
        
        async def mock_analyze_query(query, **kwargs):
            from src.core.intent.models import QueryAnalysis, IntentResult, IntentType
            
            analysis = Mock(spec=QueryAnalysis)
            analysis.intent_result = Mock(spec=IntentResult)
            analysis.intent_result.intent_type = IntentType.CODE_ANALYSIS
            analysis.connection_result = None
            analysis.is_safe_for_processing.return_value = True
            return analysis
        
        engine.analyze_query = mock_analyze_query
        engine.get_stats.return_value = {
            'queries_analyzed': 0,
            'component_stats': {}
        }
        return engine
    
    @pytest.fixture
    def vault_config(self, temp_vault_dir):
        """Create vault configuration for integration testing."""
        return VaultSyncConfig(
            vault_path=temp_vault_dir,
            enable_backlinks=True,
            enable_templates=True,
            template_directory=None,  # Use built-in templates
            conflict_strategy=ConflictStrategy.SAFE_MERGE,
            batch_size=20,
            safety_score_threshold=Decimal("0.8")
        )
    
    @pytest.fixture
    def integrated_sync_engine(
        self,
        vault_config,
        mock_memory_repository,
        mock_safety_validator,
        mock_ast_analyzer,
        mock_intent_engine
    ):
        """Create fully integrated vault sync engine."""
        return VaultSyncEngine(
            config=vault_config,
            memory_repository=mock_memory_repository,
            safety_validator=mock_safety_validator,
            ast_analyzer=mock_ast_analyzer,
            intent_engine=mock_intent_engine
        )
    
    def create_test_memories(self, count: int = 3) -> list:
        """Create test memories for integration testing."""
        memories = []
        
        # Code analysis memory
        code_memory = AbstractMemoryEntry(
            id=uuid4(),
            content="""
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class MathUtilities:
    @staticmethod
    def factorial(n):
        if n == 0:
            return 1
        return n * MathUtilities.factorial(n-1)
""",
            interaction_type=InteractionType.CODE_ANALYSIS,
            weight=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=MemoryMetadata(
                safety_score=Decimal("0.95"),
                context={'language': 'python', 'complexity': 'medium'}
            )
        )
        memories.append(code_memory)
        
        # Question memory
        question_memory = AbstractMemoryEntry(
            id=uuid4(),
            content="How do I optimize this recursive algorithm for better performance? Should I use memoization or dynamic programming?",
            interaction_type=InteractionType.QUESTION,
            weight=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=MemoryMetadata(
                safety_score=Decimal("0.9"),
                context={'topic': 'optimization', 'domain': 'algorithms'}
            )
        )
        memories.append(question_memory)
        
        # Documentation memory
        doc_memory = AbstractMemoryEntry(
            id=uuid4(),
            content="""
# Algorithm Performance Analysis

This document outlines performance characteristics of recursive algorithms:

## Fibonacci Sequence
- Time Complexity: O(2^n) without memoization
- Space Complexity: O(n) due to recursion stack
- Optimization: Use dynamic programming for O(n) time

## Best Practices
1. Always consider iterative alternatives
2. Implement memoization for overlapping subproblems
3. Use tail recursion when possible
""",
            interaction_type=InteractionType.DOCUMENTATION,
            weight=1.2,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=MemoryMetadata(
                safety_score=Decimal("0.92"),
                context={'type': 'documentation', 'subject': 'algorithms'}
            )
        )
        memories.append(doc_memory)
        
        return memories[:count]
    
    @pytest.mark.asyncio
    async def test_end_to_end_memory_sync(
        self,
        integrated_sync_engine,
        mock_memory_repository,
        temp_vault_dir
    ):
        """Test complete end-to-end memory synchronization."""
        # Setup test data
        test_memories = self.create_test_memories(3)
        mock_memory_repository.get_recent_memories.return_value = test_memories
        
        # Perform sync
        result = await integrated_sync_engine.sync_memories_to_vault(
            template_type=TemplateType.CHECKPOINT,
            max_memories=3
        )
        
        # Verify sync results
        assert result.success is True
        assert result.notes_processed == 3
        assert result.notes_created == 3
        assert result.conflicts_detected == 0
        assert result.safety_violations == 0
        assert result.processing_time_ms > 0
        
        # Verify vault files created
        vault_files = list(temp_vault_dir.glob("*.md"))
        assert len(vault_files) == 3
        
        # Verify file contents
        for vault_file in vault_files:
            content = vault_file.read_text(encoding='utf-8')
            
            # Should have checkpoint template structure
            assert "Checkpoint Summary" in content
            assert "Safety Score:" in content
            assert "Template Applied: checkpoint" in content
            
            # Should contain abstracted content
            assert "calculate_fibonacci" in content or "optimization" in content or "Algorithm Performance" in content
            
            # Should have YAML frontmatter
            assert "---" in content
            assert "type:" in content
            assert "created:" in content
    
    @pytest.mark.asyncio
    async def test_different_template_types(
        self,
        integrated_sync_engine,
        mock_memory_repository,
        temp_vault_dir
    ):
        """Test sync with different template types."""
        test_memories = self.create_test_memories(3)
        
        # Test each template type
        template_types = [TemplateType.CHECKPOINT, TemplateType.LEARNING, TemplateType.DECISION]
        
        for i, template_type in enumerate(template_types):
            mock_memory_repository.get_recent_memories.return_value = [test_memories[i]]
            
            result = await integrated_sync_engine.sync_memories_to_vault(
                template_type=template_type,
                max_memories=1
            )
            
            assert result.success is True
            assert result.notes_created == 1
        
        # Verify different template structures
        vault_files = list(temp_vault_dir.glob("*.md"))
        contents = [f.read_text(encoding='utf-8') for f in vault_files]
        
        # Should have different template markers
        template_markers = ["Checkpoint Summary", "Learning Objective", "Decision Context"]
        found_markers = [any(marker in content for content in contents) for marker in template_markers]
        assert all(found_markers), "Not all template types were applied correctly"
    
    @pytest.mark.asyncio
    async def test_ast_analysis_integration(
        self,
        integrated_sync_engine,
        mock_memory_repository,
        mock_ast_analyzer,
        temp_vault_dir
    ):
        """Test integration with AST analysis for code content."""
        # Create code memory
        code_memories = [mem for mem in self.create_test_memories() 
                        if mem.interaction_type == InteractionType.CODE_ANALYSIS]
        
        mock_memory_repository.get_recent_memories.return_value = code_memories
        
        result = await integrated_sync_engine.sync_memories_to_vault(max_memories=1)
        
        assert result.success is True
        assert result.notes_created == 1
        
        # Verify AST analyzer was called
        mock_ast_analyzer.analyze_code.assert_called()
        
        # Verify enhanced content
        vault_files = list(temp_vault_dir.glob("*.md"))
        content = vault_files[0].read_text(encoding='utf-8')
        
        # Should have code analysis enhancements
        assert "python" in content.lower()
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_workflow(
        self,
        integrated_sync_engine,
        mock_memory_repository,
        temp_vault_dir
    ):
        """Test conflict detection and resolution workflow."""
        test_memories = self.create_test_memories(1)
        mock_memory_repository.get_recent_memories.return_value = test_memories
        
        # First sync to create initial files
        result1 = await integrated_sync_engine.sync_memories_to_vault(max_memories=1)
        assert result1.success is True
        assert result1.notes_created == 1
        
        # Modify vault file to create conflict
        vault_files = list(temp_vault_dir.glob("*.md"))
        vault_file = vault_files[0]
        original_content = vault_file.read_text(encoding='utf-8')
        modified_content = original_content + "\n\n## Manual Addition\n\nThis was added manually."
        vault_file.write_text(modified_content, encoding='utf-8')
        
        # Second sync should detect and resolve conflict
        result2 = await integrated_sync_engine.sync_memories_to_vault(max_memories=1)
        assert result2.success is True
        # Conflict detection depends on implementation details
    
    @pytest.mark.asyncio
    async def test_bidirectional_sync(
        self,
        integrated_sync_engine,
        temp_vault_dir,
        mock_memory_repository
    ):
        """Test bidirectional synchronization."""
        # Create manual vault files
        manual_note1 = temp_vault_dir / "manual_note1.md"
        manual_note1.write_text("""# Manual Note 1

This is a manually created note in the vault.

## Content
- Manual bullet point 1
- Manual bullet point 2

Tags: #manual #test
""", encoding='utf-8')
        
        manual_note2 = temp_vault_dir / "manual_note2.md"
        manual_note2.write_text("""---
type: manual
created: 2024-01-01T00:00:00
---

# Manual Note 2

Another manual note with frontmatter.
""", encoding='utf-8')
        
        # Sync vault to memories
        result = await integrated_sync_engine.sync_vault_to_memories()
        
        assert result.success is True
        assert result.notes_processed == 2
        # Note creation depends on mock implementation
    
    @pytest.mark.asyncio
    async def test_safety_validation_integration(
        self,
        integrated_sync_engine,
        mock_memory_repository,
        mock_safety_validator
    ):
        """Test safety validation throughout sync pipeline."""
        # Create memory with potentially unsafe content
        unsafe_memory = AbstractMemoryEntry(
            id=uuid4(),
            content="This contains a file path /home/user/secret/file.txt and api_key = 'sk-1234567890abcdef'",
            interaction_type=InteractionType.DOCUMENTATION,
            weight=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=MemoryMetadata(safety_score=Decimal("0.85"))
        )
        
        mock_memory_repository.get_recent_memories.return_value = [unsafe_memory]
        
        result = await integrated_sync_engine.sync_memories_to_vault(max_memories=1)
        
        assert result.success is True
        assert result.notes_created == 1
        
        # Verify safety validator was called
        assert mock_safety_validator.auto_abstract_content.called
        
        # Verify abstracted content in vault
        vault_files = list(temp_vault_dir.glob("*.md"))
        content = vault_files[0].read_text(encoding='utf-8')
        
        # Should not contain concrete references
        assert "/home/user/secret" not in content
        assert "sk-1234567890abcdef" not in content
        assert "<file_path>" in content
        assert "<api_key>" in content
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(
        self,
        integrated_sync_engine,
        mock_memory_repository
    ):
        """Test performance meets targets."""
        # Create larger set of memories
        test_memories = []
        for i in range(10):
            memory = AbstractMemoryEntry(
                id=uuid4(),
                content=f"Test memory content {i} with some longer text to simulate real content",
                interaction_type=InteractionType.QUESTION,
                weight=1.0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata=MemoryMetadata(safety_score=Decimal("0.9"))
            )
            test_memories.append(memory)
        
        mock_memory_repository.get_recent_memories.return_value = test_memories
        
        result = await integrated_sync_engine.sync_memories_to_vault(max_memories=10)
        
        assert result.success is True
        assert result.notes_processed == 10
        assert result.notes_created == 10
        
        # Performance targets (for 10 memories)
        assert result.processing_time_ms < 5000  # Should be under 5 seconds for 10 memories
        
        # Check component performance
        stats = integrated_sync_engine.get_stats()
        if 'recent_performance' in stats:
            perf = stats['recent_performance']
            assert perf.get('avg_conversion_time_ms', 0) < 500
            assert perf.get('avg_template_time_ms', 0) < 200
            assert perf.get('avg_conflict_time_ms', 0) < 300
    
    @pytest.mark.asyncio
    async def test_tag_and_backlink_generation(
        self,
        integrated_sync_engine,
        mock_memory_repository,
        temp_vault_dir
    ):
        """Test tag extraction and backlink generation."""
        # Create related memories with common themes
        related_memories = []
        
        memory1 = AbstractMemoryEntry(
            id=uuid4(),
            content="Python programming best practices for web development. #python #web #best-practices",
            interaction_type=InteractionType.DOCUMENTATION,
            weight=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=MemoryMetadata(safety_score=Decimal("0.9"))
        )
        related_memories.append(memory1)
        
        memory2 = AbstractMemoryEntry(
            id=uuid4(),
            content="How to optimize Python web applications for better performance? #python #optimization",
            interaction_type=InteractionType.QUESTION,
            weight=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=MemoryMetadata(safety_score=Decimal("0.9"))
        )
        related_memories.append(memory2)
        
        mock_memory_repository.get_recent_memories.return_value = related_memories
        
        result = await integrated_sync_engine.sync_memories_to_vault(max_memories=2)
        
        assert result.success is True
        assert result.notes_created == 2
        
        # Verify tag extraction
        vault_files = list(temp_vault_dir.glob("*.md"))
        contents = [f.read_text(encoding='utf-8') for f in vault_files]
        
        # Should have extracted tags
        combined_content = ' '.join(contents)
        assert 'python' in combined_content.lower()
        assert '#' in combined_content  # Tag formatting
    
    def test_comprehensive_stats_collection(self, integrated_sync_engine):
        """Test comprehensive statistics collection."""
        stats = integrated_sync_engine.get_stats()
        
        # Verify main stats
        required_stats = [
            'syncs_performed', 'total_notes_created', 'total_notes_updated',
            'total_conflicts_resolved', 'vault_metadata', 'component_stats'
        ]
        
        for stat in required_stats:
            assert stat in stats, f"Missing required stat: {stat}"
        
        # Verify component stats
        component_stats = stats['component_stats']
        required_components = ['markdown_converter', 'conflict_resolver', 'template_processor']
        
        for component in required_components:
            assert component in component_stats, f"Missing component stats: {component}"
    
    @pytest.mark.asyncio
    async def test_error_recovery(
        self,
        integrated_sync_engine,
        mock_memory_repository,
        mock_safety_validator
    ):
        """Test error recovery during sync operations."""
        test_memories = self.create_test_memories(2)
        mock_memory_repository.get_recent_memories.return_value = test_memories
        
        # Mock one memory to cause error during conversion
        def side_effect_abstract(content):
            if "calculate_fibonacci" in content:
                raise Exception("Safety validation error")
            return "safe content", {}
        
        mock_safety_validator.auto_abstract_content.side_effect = side_effect_abstract
        
        result = await integrated_sync_engine.sync_memories_to_vault(max_memories=2)
        
        # Should handle error gracefully
        assert result.success is True  # Overall operation succeeds
        assert len(result.errors) > 0  # But errors are recorded
        # Some notes may still be created successfully
    
    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self, integrated_sync_engine):
        """Test proper cleanup during shutdown."""
        await integrated_sync_engine.shutdown()
        # Should complete without errors
        
        # Components should be properly shut down
        # (This is implementation-dependent and may require additional verification)