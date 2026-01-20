"""
Langfuse Prompt Registry integration for TechnoShare Commentator.
Provides prompt versioning, management, and retrieval via Langfuse.
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import hashlib

from ..config import get_settings
from .prompts import load_prompt as load_prompt_from_yaml
from .tracing import _get_langfuse

logger = logging.getLogger(__name__)
settings = get_settings()


class PromptRegistry:
    """Manages prompts via Langfuse Prompt Management."""
    
    def __init__(self):
        self.enabled = settings.LANGFUSE_ENABLED
        self.client = _get_langfuse()
        if self.client:
            logger.info("Langfuse Prompt Registry enabled")
        elif self.enabled:
            logger.warning("Langfuse enabled but client failed to initialize")
            self.enabled = False
    
    def _compute_prompt_hash(self, content: str) -> str:
        """Compute hash of prompt content for version tracking."""
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def register_prompt(
        self,
        name: str,
        content: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Register a prompt in Langfuse.
        
        Note: Langfuse prompts are managed via the UI or API.
        This method creates a trace to track prompt registration.
        
        Args:
            name: Prompt name (e.g., "analyze")
            content: Prompt template content
            description: Human-readable description
            tags: Additional metadata tags
        
        Returns:
            Version hash if successful, None otherwise
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            content_hash = self._compute_prompt_hash(content)
            
            # Create a trace for tracking prompt registration
            metadata = {
                "prompt_name": name,
                "content_hash": content_hash,
                "content_length": len(content),
            }
            if description:
                metadata["description"] = description
            if tags:
                metadata.update(tags)
            
            trace = self.client.trace(
                name=f"prompt_register_{name}",
                metadata=metadata,
                input={"content": content},
                tags=["prompt", "registration"],
            )
            
            logger.info(f"Registered prompt '{name}' with hash {content_hash}")
            self.client.flush()
            
            return content_hash
                
        except Exception as e:
            logger.warning(f"Failed to register prompt '{name}': {e}")
            return None
    
    def sync_prompts_from_yaml(self, force: bool = False) -> Dict[str, str]:
        """
        Sync all YAML prompts - logs registration to Langfuse.
        
        Args:
            force: Force re-registration even if content hasn't changed
        
        Returns:
            Dict mapping prompt names to version hashes
        """
        prompt_names = ["analyze"]  # Single-stage analysis prompt
        results = {}
        
        for name in prompt_names:
            try:
                # Load from YAML
                content = load_prompt_from_yaml(name)
                
                # Register/log in Langfuse
                version = self.register_prompt(
                    name=name,
                    content=content,
                    description=f"Prompt for {name}",
                    tags={"source": "yaml", "stage": "analysis"}
                )
                
                if version:
                    results[name] = version
                    logger.info(f"Synced prompt '{name}' -> version {version}")
                else:
                    logger.warning(f"Failed to sync prompt '{name}'")
                    
            except Exception as e:
                logger.exception(f"Error syncing prompt '{name}'")
        
        return results
    
    def load_prompt(
        self,
        name: str,
        alias: Optional[str] = "prod",
        fallback_to_yaml: bool = True
    ) -> str:
        """
        Load a prompt from Langfuse or fallback to YAML.
        
        Args:
            name: Prompt name
            alias: Alias/label to load (e.g., "production", "latest")
            fallback_to_yaml: If True, fall back to YAML if not found
        
        Returns:
            Prompt content
        """
        if not self.enabled or not self.client:
            return load_prompt_from_yaml(name)
        
        try:
            # Try to fetch from Langfuse prompt management
            prompt = self.client.get_prompt(name, label=alias)
            if prompt:
                return prompt.prompt
        except Exception as e:
            logger.debug(f"Prompt '{name}' not found in Langfuse, using YAML fallback: {e}")
        
        if fallback_to_yaml:
            return load_prompt_from_yaml(name)
        
        raise ValueError(f"Prompt '{name}' not found")
    
    def set_alias(
        self,
        name: str,
        version_hash: str,
        alias: str
    ) -> bool:
        """
        Set an alias for a prompt version.
        
        Note: Langfuse prompt aliases (labels) are managed via the UI.
        
        Args:
            name: Prompt name
            version_hash: Version hash to alias
            alias: Alias name (e.g., "production", "staging")
        
        Returns:
            True if logged successfully
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            # Log alias assignment as a trace
            self.client.trace(
                name=f"prompt_alias_{name}",
                metadata={
                    "prompt_name": name,
                    "version_hash": version_hash,
                    "alias": alias,
                },
                tags=["prompt", "alias"],
            )
            logger.info(f"Logged alias '{alias}' for prompt '{name}' version {version_hash}")
            self.client.flush()
            return True
        except Exception as e:
            logger.warning(f"Failed to log alias: {e}")
            return False


# Global registry instance
prompt_registry = PromptRegistry()
