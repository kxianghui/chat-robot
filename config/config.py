# Configuration management for Dify Chat application
import configparser
import os
from typing import Optional, Tuple


class Config:
    """Manages application configuration using config.ini file."""

    CONFIG_FILE = "config.ini"

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.api_key: Optional[str] = None
        self.base_url: Optional[str] = None
        self.user_id: Optional[str] = None
        self.endpoint_path: Optional[str] = None

    def load(self) -> bool:
        """Load configuration from config.ini file.

        Returns:
            True if file exists and was loaded, False otherwise.
        """
        if not os.path.exists(self.CONFIG_FILE):
            return False

        try:
            self.config.read(self.CONFIG_FILE)
            if self.config.has_section("dify"):
                self.api_key = self.config.get("dify", "api_key", fallback=None)
                self.base_url = self.config.get("dify", "base_url", fallback=None)
                self.user_id = self.config.get("dify", "user_id", fallback=None)
                self.endpoint_path = self.config.get("dify", "endpoint_path", fallback=None)
            return True
        except Exception:
            return False

    def save(self, api_key: str, base_url: str, user_id: str = "desktop-client-user", endpoint_path: str = None) -> None:
        """Save configuration to config.ini file.

        Args:
            api_key: Dify API key
            base_url: Dify API base URL
            user_id: Optional user identifier
            endpoint_path: Optional custom endpoint path (e.g., "/chat")
        """
        if not self.config.has_section("dify"):
            self.config.add_section("dify")

        self.config.set("dify", "api_key", api_key)
        self.config.set("dify", "base_url", base_url)
        self.config.set("dify", "user_id", user_id)
        if endpoint_path:
            self.config.set("dify", "endpoint_path", endpoint_path)

        with open(self.CONFIG_FILE, "w") as f:
            self.config.write(f)

        # Update instance attributes
        self.api_key = api_key
        self.base_url = base_url
        self.user_id = user_id
        self.endpoint_path = endpoint_path

    def validate(self) -> Tuple[bool, str]:
        """Validate configuration values.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.api_key:
            return False, "API Key is required"
        if not self.base_url:
            return False, "Base URL is required"
        if not self.base_url.startswith(("http://", "https://")):
            return False, "Base URL must start with http:// or https://"
        return True, ""

    def is_configured(self) -> bool:
        """Check if configuration is complete and valid.

        Returns:
            True if configured, False otherwise.
        """
        is_valid, _ = self.validate()
        return is_valid