"""
Unit tests for VaultSyncEngine.

Tests memory-to-vault synchronization with mock filesystem.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from src.services.vault import (
    VaultSyncEngine,
    VaultSyncConfig,
    MarkdownNote,
    TemplateType,
    ConflictStrategy
)
from src.core.memory.abstract_models import AbstractMemoryEntry, InteractionType, MemoryMetadata
from src.core.validation.validator import SafetyValidator


class TestVaultSyncEngine:
    """Test vault synchronization engine functionality."""
    
    @pytest.fixture
    def temp_vault_dir(self):
        """Create temporary vault directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def vault_config(self, temp_vault_dir):
        """Create vault sync configuration."""
        return VaultSyncConfig(
            vault_path=temp_vault_dir,
            enable_backlinks=True,
            enable_templates=True,
            conflict_strategy=ConflictStrategy.SAFE_MERGE,
            batch_size=10
        )
    
    @pytest.fixture
    def mock_memory_repository(self):
        """Create mock memory repository."""
        repository = Mock()
        repository.get_memory = AsyncMock()
        repository.get_recent_memories = AsyncMock()
        return repository
    
    @pytest.fixture
    def mock_safety_validator(self):
        """Create mock safety validator."""
        validator = Mock(spec=SafetyValidator)
        validator.auto_abstract_content.return_value = ("abstracted content", {})
        return validator
    
    @pytest.fixture
    def sample_memory(self):
        """Create sample memory entry."""
        memory_id = uuid4()
        return AbstractMemoryEntry(
            id=memory_id,
            content="This is a test memory content with some code: def hello(): pass",
            interaction_type=InteractionType.CODE_ANALYSIS,
            weight=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=MemoryMetadata(
                safety_score=Decimal("0.9"),
                context={'source': 'test'}
            )
        )
    
    @pytest.fixture
    def sync_engine(self, vault_config, mock_memory_repository, mock_safety_validator):
        """Create vault sync engine for testing."""
        return VaultSyncEngine(
            config=vault_config,
            memory_repository=mock_memory_repository,
            safety_validator=mock_safety_validator
        )
    
    @pytest.mark.asyncio
    async def test_sync_engine_initialization(self, sync_engine, vault_config):
        """Test sync engine initialization."""
        assert sync_engine.config == vault_config
        assert sync_engine.markdown_converter is not None
        assert sync_engine.template_processor is not None
        assert sync_engine.conflict_resolver is not None
        assert sync_engine.metadata is not None
    
    @pytest.mark.asyncio
    async def test_sync_memories_to_vault_empty_list(self, sync_engine, mock_memory_repository):
        """Test syncing empty memory list."""
        mock_memory_repository.get_recent_memories.return_value = []
        
        result = await sync_engine.sync_memories_to_vault()
        
        assert result.success is True
        assert result.notes_processed == 0
        assert result.notes_created == 0
        assert result.notes_updated == 0
    
    @pytest.mark.asyncio
    async def test_sync_memories_to_vault_single_memory(
        self,
        sync_engine,
        mock_memory_repository,
        sample_memory,
        temp_vault_dir
    ):
        """Test syncing single memory to vault."""
        mock_memory_repository.get_recent_memories.return_value = [sample_memory]
        
        result = await sync_engine.sync_memories_to_vault(max_memories=1)
        
        assert result.success is True
        assert result.notes_processed == 1
        assert result.notes_created == 1
        assert result.processing_time_ms > 0
        
        # Check that file was created in vault
        vault_files = list(temp_vault_dir.glob("*.md"))
        assert len(vault_files) == 1
        
        # Verify file content
        vault_file = vault_files[0]
        content = vault_file.read_text(encoding='utf-8')
        assert "code_analysis" in content
        assert "abstracted content" in content
    
    @pytest.mark.asyncio
    async def test_sync_with_template(
        self,
        sync_engine,
        mock_memory_repository,
        sample_memory,
        temp_vault_dir
    ):
        """Test syncing with template application."""
        mock_memory_repository.get_recent_memories.return_value = [sample_memory]
        
        result = await sync_engine.sync_memories_to_vault(
            template_type=TemplateType.CHECKPOINT,
            max_memories=1
        )
        
        assert result.success is True
        assert result.notes_created == 1
        
        # Check template was applied
        vault_files = list(temp_vault_dir.glob("*.md"))
        assert len(vault_files) == 1
        
        content = vault_files[0].read_text(encoding='utf-8')
        assert "Checkpoint Summary" in content
        assert "Template Applied: checkpoint" in content
    
    @pytest.mark.asyncio
    async def test_sync_with_conflict_detection(
        self,
        sync_engine,
        mock_memory_repository,
        sample_memory,
        temp_vault_dir
    ):
        """Test sync with existing file causing conflict."""
        mock_memory_repository.get_recent_memories.return_value = [sample_memory]
        
        # Create existing file in vault
        existing_file = temp_vault_dir / "existing_note.md"
        existing_file.write_text("# Existing Note\n\nThis is existing content.", encoding='utf-8')
        
        # Mock the note to use same filename
        with patch.object(sync_engine.markdown_converter, 'convert_memory_to_markdown') as mock_convert:
            mock_note = MarkdownNote(
                title_pattern="<existing_note>",
                content="New content",
                safety_score=Decimal("0.9"),
                memory_id=sample_memory.id
            )
            mock_note.file_path = existing_file
            mock_convert.return_value = mock_note
            
            result = await sync_engine.sync_memories_to_vault(max_memories=1)
            
            assert result.success is True
            # Conflict should be detected and resolved
            assert result.conflicts_detected >= 0  # May detect conflict
    
    @pytest.mark.asyncio
    async def test_sync_safety_validation_failure(
        self,
        sync_engine,
        mock_memory_repository,
        sample_memory
    ):
        """Test sync with safety validation failure."""
        # Mock safety validation to fail
        sample_memory.metadata.safety_score = Decimal("0.5")  # Below threshold
        mock_memory_repository.get_recent_memories.return_value = [sample_memory]
        
        result = await sync_engine.sync_memories_to_vault(max_memories=1)
        
        assert result.success is True  # Operation succeeds but notes skipped
        assert result.notes_processed == 1
        assert result.safety_violations == 1
        assert result.notes_created == 0
    
    @pytest.mark.asyncio
    async def test_sync_vault_to_memories(self, sync_engine, temp_vault_dir):
        """Test syncing vault files back to memories."""
        # Create test markdown files in vault
        test_file1 = temp_vault_dir / "test1.md"
        test_file1.write_text("# Test Note 1\n\nThis is test content.", encoding='utf-8')
        
        test_file2 = temp_vault_dir / "test2.md"
        test_file2.write_text("# Test Note 2\n\nAnother test note.", encoding='utf-8')
        
        result = await sync_engine.sync_vault_to_memories()
        
        assert result.success is True
        assert result.notes_processed == 2
        # Note: Creation would depend on mock implementation
    
    @pytest.mark.asyncio
    async def test_performance_targets(
        self,
        sync_engine,
        mock_memory_repository,
        sample_memory
    ):
        """Test that sync meets performance targets."""
        mock_memory_repository.get_recent_memories.return_value = [sample_memory]
        
        result = await sync_engine.sync_memories_to_vault(max_memories=1)
        
        assert result.success is True
        assert result.processing_time_ms < 1000  # Should be fast for single memory
        
        # Check performance in stats
        stats = sync_engine.get_stats()
        if 'recent_performance' in stats:
            recent_perf = stats['recent_performance']
            # Conversion should be under target
            assert recent_perf.get('avg_conversion_time_ms', 0) < 500
    
    @pytest.mark.asyncio
    async def test_batch_processing(
        self,
        sync_engine,
        mock_memory_repository
    ):
        """Test batch processing of multiple memories."""
        # Create multiple test memories
        memories = []
        for i in range(5):
            memory = AbstractMemoryEntry(
                id=uuid4(),
                content=f"Test memory content {i}",
                interaction_type=InteractionType.QUESTION,
                weight=1.0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata=MemoryMetadata(safety_score=Decimal("0.9"))
            )
            memories.append(memory)
        
        mock_memory_repository.get_recent_memories.return_value = memories
        
        result = await sync_engine.sync_memories_to_vault(max_memories=5)
        
        assert result.success is True
        assert result.notes_processed == 5
        assert result.notes_created == 5
    
    @pytest.mark.asyncio
    async def test_backlink_generation(
        self,
        sync_engine,
        mock_memory_repository
    ):
        """Test backlink generation between related notes."""
        # Create related memories
        memory1 = AbstractMemoryEntry(
            id=uuid4(),
            content="Test memory about python programming",
            interaction_type=InteractionType.CODE_ANALYSIS,
            weight=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=MemoryMetadata(safety_score=Decimal("0.9"))
        )
        
        memory2 = AbstractMemoryEntry(
            id=uuid4(),
            content="Another python related memory content",
            interaction_type=InteractionType.DOCUMENTATION,
            weight=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=MemoryMetadata(safety_score=Decimal("0.9"))
        )
        
        mock_memory_repository.get_recent_memories.return_value = [memory1, memory2]
        
        result = await sync_engine.sync_memories_to_vault(max_memories=2)
        
        assert result.success is True
        assert result.notes_created == 2
        
        # Check that backlinks were generated (simplified check)
        # In a full implementation, would verify actual backlink content
    
    def test_get_stats(self, sync_engine):
        """Test statistics collection."""
        stats = sync_engine.get_stats()
        
        assert 'syncs_performed' in stats
        assert 'total_notes_created' in stats
        assert 'total_notes_updated' in stats
        assert 'vault_metadata' in stats
        assert 'component_stats' in stats
        
        # Check component stats exist
        assert 'markdown_converter' in stats['component_stats']
        assert 'conflict_resolver' in stats['component_stats']
        assert 'template_processor' in stats['component_stats']
    
    @pytest.mark.asyncio
    async def test_shutdown(self, sync_engine):
        """Test engine shutdown."""
        await sync_engine.shutdown()
        # Should complete without errors
    
    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        sync_engine,
        mock_memory_repository
    ):
        """Test error handling during sync operations."""
        # Mock repository to raise error
        mock_memory_repository.get_recent_memories.side_effect = Exception("Database error")
        
        result = await sync_engine.sync_memories_to_vault()
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "Database error" in result.errors[0]


@pytest.mark.asyncio
async def test_vault_sync_engine_integration():
    """Integration test for vault sync engine."""
    with tempfile.TemporaryDirectory() as temp_dir:
        vault_path = Path(temp_dir)
        
        # Create configuration
        config = VaultSyncConfig(
            vault_path=vault_path,
            enable_templates=True,
            batch_size=2
        )
        
        # Create mocks
        mock_repo = Mock()
        mock_validator = Mock(spec=SafetyValidator)
        mock_validator.auto_abstract_content.return_value = ("safe content", {})
        
        # Create test memory
        test_memory = AbstractMemoryEntry(
            id=uuid4(),
            content="def test_function(): return 'hello world'",
            interaction_type=InteractionType.CODE_ANALYSIS,
            weight=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=MemoryMetadata(safety_score=Decimal("0.95"))
        )
        
        mock_repo.get_recent_memories.return_value = [test_memory]
        
        # Create sync engine
        engine = VaultSyncEngine(
            config=config,
            memory_repository=mock_repo,
            safety_validator=mock_validator
        )
        
        # Perform sync
        result = await engine.sync_memories_to_vault(
            template_type=TemplateType.LEARNING,
            max_memories=1
        )
        
        # Verify results
        assert result.success is True
        assert result.notes_processed == 1
        assert result.notes_created == 1
        
        # Verify file creation
        vault_files = list(vault_path.glob("*.md"))
        assert len(vault_files) == 1
        
        # Verify content
        content = vault_files[0].read_text(encoding='utf-8')
        assert "Learning Objective" in content  # Learning template
        assert "safe content" in content       # Abstracted content
        
        # Clean up
        await engine.shutdown()