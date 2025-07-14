"""
Memory management API endpoints.

This module provides REST endpoints for creating, reading, updating,
and searching memories with automatic safety validation and abstraction.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse

from ..dependencies import (
    CurrentUser,
    PaginationParams,
    get_memory_repository,
    get_intent_engine,
)
from ..models.common import PaginatedResponse, SuccessResponse
from ..models.memory import (
    MemoryCreate,
    MemoryUpdate,
    MemoryResponse,
    MemorySearch,
    MemorySearchResult,
    MemoryCluster,
    MemoryReinforce,
)
from ...core.memory.repository import SafeMemoryRepository
from ...core.intent.engine import IntentEngine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new memory",
    description="Create a new memory with automatic safety validation and abstraction"
)
async def create_memory(
    memory_data: MemoryCreate,
    current_user: CurrentUser,
    memory_repo: SafeMemoryRepository = Depends(get_memory_repository),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> MemoryResponse:
    """Create a new memory with automatic abstraction."""
    try:
        # Create memory through repository (handles abstraction and validation)
        memory = await memory_repo.create_memory(
            memory_type=memory_data.memory_type,
            prompt=memory_data.prompt,
            content=memory_data.content,
            metadata=memory_data.metadata or {},
        )
        
        # Schedule background tasks
        background_tasks.add_task(_update_memory_clusters, memory_repo, memory.memory_id)
        
        logger.info(f"Created memory {memory.memory_id} for user {current_user['user_id']}")
        
        return MemoryResponse.model_validate(memory)
        
    except ValueError as e:
        logger.warning(f"Validation error creating memory: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating memory: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create memory"
        )


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get memory by ID",
    description="Retrieve a specific memory by its ID"
)
async def get_memory(
    memory_id: UUID,
    current_user: CurrentUser,
    memory_repo: SafeMemoryRepository = Depends(get_memory_repository),
) -> MemoryResponse:
    """Get a specific memory by ID."""
    try:
        memory = await memory_repo.get_memory(memory_id)
        
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found"
            )
        
        # Update access tracking
        await memory_repo.update_access_time(memory_id)
        
        logger.info(f"Retrieved memory {memory_id} for user {current_user['user_id']}")
        
        return MemoryResponse.model_validate(memory)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving memory {memory_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory"
        )


@router.put(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Update memory",
    description="Update an existing memory with new content"
)
async def update_memory(
    memory_id: UUID,
    memory_data: MemoryUpdate,
    current_user: CurrentUser,
    memory_repo: SafeMemoryRepository = Depends(get_memory_repository),
) -> MemoryResponse:
    """Update an existing memory."""
    try:
        # Check if memory exists
        existing_memory = await memory_repo.get_memory(memory_id)
        if not existing_memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found"
            )
        
        # Update memory
        updated_memory = await memory_repo.update_memory(
            memory_id=memory_id,
            prompt=memory_data.prompt,
            content=memory_data.content,
            metadata=memory_data.metadata,
        )
        
        logger.info(f"Updated memory {memory_id} for user {current_user['user_id']}")
        
        return MemoryResponse.model_validate(updated_memory)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error updating memory {memory_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating memory {memory_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update memory"
        )


@router.delete(
    "/{memory_id}",
    response_model=SuccessResponse,
    summary="Delete memory",
    description="Delete a memory permanently"
)
async def delete_memory(
    memory_id: UUID,
    current_user: CurrentUser,
    memory_repo: SafeMemoryRepository = Depends(get_memory_repository),
) -> SuccessResponse:
    """Delete a memory permanently."""
    try:
        # Check if memory exists
        existing_memory = await memory_repo.get_memory(memory_id)
        if not existing_memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found"
            )
        
        # Delete memory
        await memory_repo.delete_memory(memory_id)
        
        logger.info(f"Deleted memory {memory_id} for user {current_user['user_id']}")
        
        return SuccessResponse(
            message=f"Memory {memory_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memory"
        )


@router.post(
    "/search",
    response_model=List[MemorySearchResult],
    summary="Search memories",
    description="Search memories with intent analysis and relevance scoring"
)
async def search_memories(
    search_request: MemorySearch,
    current_user: CurrentUser,
    memory_repo: SafeMemoryRepository = Depends(get_memory_repository),
    intent_engine: IntentEngine = Depends(get_intent_engine),
) -> List[MemorySearchResult]:
    """Search memories with intent analysis."""
    try:
        if search_request.enable_intent_analysis:
            # Use intent engine for smart search
            search_results = await intent_engine.find_relevant_memories(
                query=search_request.query,
                memory_types=search_request.memory_types,
                limit=search_request.limit,
                include_peripheral=search_request.include_peripheral,
            )
            
            # Convert to API format
            results = []
            for connection in search_results.connections:
                memory = await memory_repo.get_memory(connection.memory_id)
                if memory:
                    # Apply filters
                    if search_request.min_safety_score and memory.safety_score < search_request.min_safety_score:
                        continue
                    if search_request.min_temporal_weight and memory.temporal_weight < search_request.min_temporal_weight:
                        continue
                    
                    results.append(MemorySearchResult(
                        memory=MemoryResponse.model_validate(memory),
                        relevance_score=connection.confidence,
                        match_reason=connection.reason,
                    ))
            
            logger.info(f"Intent-based search for '{search_request.query}' returned {len(results)} results")
            
        else:
            # Basic text search
            memories = await memory_repo.search_memories(
                query=search_request.query,
                memory_types=search_request.memory_types,
                limit=search_request.limit,
            )
            
            results = []
            for memory in memories:
                # Apply filters
                if search_request.min_safety_score and memory.safety_score < search_request.min_safety_score:
                    continue
                if search_request.min_temporal_weight and memory.temporal_weight < search_request.min_temporal_weight:
                    continue
                
                results.append(MemorySearchResult(
                    memory=MemoryResponse.model_validate(memory),
                    relevance_score=0.8,  # Default relevance for basic search
                    match_reason="text_match",
                ))
            
            logger.info(f"Basic search for '{search_request.query}' returned {len(results)} results")
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching memories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search memories"
        )


@router.get(
    "/",
    response_model=PaginatedResponse[MemoryResponse],
    summary="List memories",
    description="Get paginated list of memories"
)
async def list_memories(
    current_user: CurrentUser,
    pagination: PaginationParams,
    memory_repo: SafeMemoryRepository = Depends(get_memory_repository),
) -> PaginatedResponse[MemoryResponse]:
    """Get paginated list of memories."""
    try:
        # Get memories with pagination
        memories, total_count = await memory_repo.list_memories(
            offset=pagination["offset"],
            limit=pagination["limit"],
        )
        
        # Convert to response models
        memory_responses = [
            MemoryResponse.model_validate(memory)
            for memory in memories
        ]
        
        # Calculate pagination metadata
        total_pages = (total_count + pagination["page_size"] - 1) // pagination["page_size"]
        
        logger.info(f"Listed {len(memories)} memories (page {pagination['page']}) for user {current_user['user_id']}")
        
        return PaginatedResponse[MemoryResponse](
            items=memory_responses,
            meta={
                "page": pagination["page"],
                "page_size": pagination["page_size"],
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": pagination["page"] < total_pages,
                "has_previous": pagination["page"] > 1,
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing memories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list memories"
        )


@router.put(
    "/{memory_id}/reinforce",
    response_model=MemoryResponse,
    summary="Reinforce memory",
    description="Reinforce a memory to increase its temporal weight"
)
async def reinforce_memory(
    memory_id: UUID,
    reinforce_data: MemoryReinforce,
    current_user: CurrentUser,
    memory_repo: SafeMemoryRepository = Depends(get_memory_repository),
) -> MemoryResponse:
    """Reinforce a memory to increase its importance."""
    try:
        # Check if memory exists
        existing_memory = await memory_repo.get_memory(memory_id)
        if not existing_memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory {memory_id} not found"
            )
        
        # Reinforce the memory
        reinforced_memory = await memory_repo.reinforce_memory(
            memory_id=memory_id,
            reinforcement_value=reinforce_data.reinforcement_value,
        )
        
        logger.info(
            f"Reinforced memory {memory_id} by {reinforce_data.reinforcement_value} "
            f"for user {current_user['user_id']}"
        )
        
        return MemoryResponse.model_validate(reinforced_memory)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reinforcing memory {memory_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reinforce memory"
        )


@router.get(
    "/clusters",
    response_model=List[MemoryCluster],
    summary="Get memory clusters",
    description="Get current memory clusters with their themes and members"
)
async def get_memory_clusters(
    current_user: CurrentUser,
    memory_repo: SafeMemoryRepository = Depends(get_memory_repository),
) -> List[MemoryCluster]:
    """Get current memory clusters."""
    try:
        clusters = await memory_repo.get_memory_clusters()
        
        cluster_responses = []
        for cluster in clusters:
            cluster_responses.append(MemoryCluster(
                cluster_id=cluster["cluster_id"],
                centroid_memory_id=cluster["centroid_memory_id"],
                member_ids=cluster["member_ids"],
                cluster_theme=cluster["theme"],
                average_safety_score=cluster["average_safety_score"],
                size=len(cluster["member_ids"]),
            ))
        
        logger.info(f"Retrieved {len(clusters)} memory clusters for user {current_user['user_id']}")
        
        return cluster_responses
        
    except Exception as e:
        logger.error(f"Error retrieving memory clusters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory clusters"
        )


async def _update_memory_clusters(memory_repo: SafeMemoryRepository, memory_id: UUID):
    """Background task to update memory clusters after creating a new memory."""
    try:
        await memory_repo.update_clustering()
        logger.info(f"Updated memory clusters after creating memory {memory_id}")
    except Exception as e:
        logger.error(f"Failed to update clusters after creating memory {memory_id}: {str(e)}")