"""
Safety validation middleware.

This middleware ensures all request and response content meets safety requirements
by validating and abstracting concrete references automatically.
"""

import json
import logging
from typing import Any, Dict, List, Union

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ...core.abstraction.concrete_engine import ConcreteAbstractionEngine
from ...core.validation.validator import SafetyValidator
from ..config import get_settings

logger = logging.getLogger(__name__)


class SafetyMiddleware(BaseHTTPMiddleware):
    """Middleware for safety validation and automatic abstraction."""
    
    def __init__(self, app, abstraction_engine: ConcreteAbstractionEngine, safety_validator: SafetyValidator):
        super().__init__(app)
        self.abstraction_engine = abstraction_engine
        self.safety_validator = safety_validator
        self.settings = get_settings()
        self.auto_abstract = self.settings.safety_auto_abstract
        self.min_score = float(self.settings.safety_min_score)
        
        # Paths to exclude from safety validation
        self.excluded_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request through safety validation."""
        # Skip safety validation for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Skip validation for OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Validate request body if present
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await self._get_request_body(request)
                if body:
                    validated_body = await self._validate_and_abstract(body)
                    if validated_body is None:
                        return JSONResponse(
                            status_code=400,
                            content={
                                "detail": "Request content failed safety validation",
                                "error_code": "SAFETY_VALIDATION_FAILED"
                            }
                        )
                    
                    # Replace request body with abstracted version
                    request._body = json.dumps(validated_body).encode()
            
            # Process request
            response = await call_next(request)
            
            # Validate response body for safety
            if response.status_code < 400:  # Only validate successful responses
                response_body = await self._get_response_body(response)
                if response_body:
                    validated_response = await self._validate_and_abstract(response_body)
                    if validated_response is None:
                        logger.error("Response failed safety validation")
                        return JSONResponse(
                            status_code=500,
                            content={
                                "detail": "Response content failed safety validation",
                                "error_code": "SAFETY_VALIDATION_FAILED"
                            }
                        )
                    
                    # Create new response with abstracted content
                    return JSONResponse(
                        content=validated_response,
                        status_code=response.status_code,
                        headers=dict(response.headers)
                    )
            
            return response
            
        except Exception as e:
            logger.error(f"Safety middleware error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal safety validation error",
                    "error_code": "SAFETY_ERROR"
                }
            )
    
    async def _get_request_body(self, request: Request) -> Union[Dict[str, Any], List[Any], None]:
        """Extract and parse request body."""
        try:
            if not hasattr(request, "_body"):
                request._body = await request.body()
            
            if request._body:
                return json.loads(request._body)
            return None
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse request body as JSON")
            return None
        except Exception as e:
            logger.error(f"Error reading request body: {str(e)}")
            return None
    
    async def _get_response_body(self, response: Response) -> Union[Dict[str, Any], List[Any], None]:
        """Extract and parse response body."""
        try:
            # Read response body
            body_bytes = b""
            async for chunk in response.body_iterator:
                body_bytes += chunk
            
            if body_bytes:
                return json.loads(body_bytes.decode())
            return None
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse response body as JSON")
            return None
        except Exception as e:
            logger.error(f"Error reading response body: {str(e)}")
            return None
    
    async def _validate_and_abstract(self, data: Union[Dict, List]) -> Union[Dict, List, None]:
        """Validate content and apply abstraction if needed."""
        try:
            # Convert to string for validation
            content_str = json.dumps(data)
            
            # Check if abstraction is needed
            if self.auto_abstract:
                # Abstract the content first
                abstracted_data = await self._abstract_data(data)
                
                # Validate abstracted content
                validation_result = self.safety_validator.validate_content(
                    json.dumps(abstracted_data)
                )
                
                if validation_result.is_safe and validation_result.safety_score >= self.min_score:
                    return abstracted_data
                else:
                    logger.warning(
                        f"Content failed safety validation: "
                        f"score={validation_result.safety_score}, "
                        f"issues={validation_result.issues}"
                    )
                    return None
            else:
                # Just validate without abstraction
                validation_result = self.safety_validator.validate_content(content_str)
                
                if validation_result.is_safe and validation_result.safety_score >= self.min_score:
                    return data
                else:
                    logger.warning(
                        f"Content failed safety validation: "
                        f"score={validation_result.safety_score}, "
                        f"issues={validation_result.issues}"
                    )
                    return None
                    
        except Exception as e:
            logger.error(f"Error during validation/abstraction: {str(e)}")
            return None
    
    async def _abstract_data(self, data: Union[Dict, List]) -> Union[Dict, List]:
        """Recursively abstract data structures."""
        if isinstance(data, dict):
            abstracted = {}
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    abstracted[key] = await self._abstract_data(value)
                elif isinstance(value, str):
                    # Abstract string values
                    abstraction = self.abstraction_engine.abstract(value)
                    abstracted[key] = abstraction.abstracted_content
                else:
                    # Keep non-string values as-is
                    abstracted[key] = value
            return abstracted
            
        elif isinstance(data, list):
            abstracted = []
            for item in data:
                if isinstance(item, (dict, list)):
                    abstracted.append(await self._abstract_data(item))
                elif isinstance(item, str):
                    # Abstract string values
                    abstraction = self.abstraction_engine.abstract(item)
                    abstracted.append(abstraction.abstracted_content)
                else:
                    # Keep non-string values as-is
                    abstracted.append(item)
            return abstracted
            
        else:
            # Return non-container types as-is
            return data