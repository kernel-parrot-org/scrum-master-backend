from typing import Any
from pydantic_core import core_schema

def apply_monkeypatch():
    """
    Monkeypatches mcp.client.session.ClientSession, PIL.Image.Image, and the Pydantic schema generator
    to be compatible with Pydantic v2.
    """
    # 1. Fix for mcp.client.session.ClientSession
    try:
        from mcp.client.session import ClientSession
        
        def validate_client_session(v: Any, _info: Any) -> ClientSession:
            if isinstance(v, ClientSession):
                return v
            raise ValueError(f"Expected ClientSession, got {type(v)}")

        ClientSession.__get_pydantic_core_schema__ = classmethod(
            lambda cls, source_type, handler: core_schema.with_info_plain_validator_function(
                validate_client_session
            )
        )
    except ImportError:
        pass

    # 2. Fix for PIL.Image.Image
    try:
        from PIL import Image
        
        def validate_pil_image(v: Any, _info: Any) -> Image.Image:
            if isinstance(v, Image.Image):
                return v
            raise ValueError(f"Expected PIL.Image.Image, got {type(v)}")

        Image.Image.__get_pydantic_core_schema__ = classmethod(
            lambda cls, source_type, handler: core_schema.with_info_plain_validator_function(
                validate_pil_image
            )
        )
    except ImportError:
        pass

    # 3. Catch-all fix for other types (like types.GenericAlias) that Pydantic v2 fails on
    try:
        from pydantic._internal import _generate_schema
        from pydantic.errors import PydanticSchemaGenerationError
        
        original_match_type = _generate_schema.GenerateSchema.match_type
        
        def patched_match_type(self, obj: Any) -> core_schema.CoreSchema:
            try:
                return original_match_type(self, obj)
            except PydanticSchemaGenerationError:
                # Fallback to Any schema for types that Pydantic can't handle
                return core_schema.any_schema()
        
        _generate_schema.GenerateSchema.match_type = patched_match_type
    except ImportError:
        pass
