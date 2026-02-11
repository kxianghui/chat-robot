# Dify API client with streaming support
import httpx
from typing import Generator
import json


class DifyClient:
    """Client for Dify API with streaming response support."""

    def __init__(self, api_key: str, base_url: str, user_id: str = "desktop-client-user", endpoint_path: str = "chat-messages"):
        """Initialize Dify client.

        Args:
            api_key: Dify API key
            base_url: Dify API base URL (e.g., https://api.dify.ai/v1)
            user_id: Optional user identifier for tracking
            endpoint_path: Custom endpoint path (e.g., "chat-messages")
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.endpoint_path = endpoint_path.lstrip("/")
        self.timeout = 60.0

    def stream_chat(
        self, message: str, conversation_id: str = ""
    ) -> Generator[str, None, None]:
        """Stream chat response from Dify API.

        Args:
            message: User's message to send
            conversation_id: Optional conversation ID for multi-turn chat

        Yields:
            Text chunks from the streaming response

        Raises:
            httpx.HTTPError: For HTTP request errors
            ValueError: For invalid responses
        """
        # Build request payload - use the correct format from Dify API
        payload = {
            "inputs": {},
            "query": message,
            "response_mode": "streaming",
            "user": self.user_id,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Debug logging
        import sys
        print(f"DEBUG: Request payload: {json.dumps(payload, ensure_ascii=False)}", file=sys.stderr)
        print(f"DEBUG: Request headers: {headers}", file=sys.stderr)

        # Try common endpoint variations - start with custom endpoint if provided
        endpoints = [f"{self.base_url}/{self.endpoint_path}"]

        # Base URL without version suffix
        base_no_version = self.base_url.rstrip('/')
        if base_no_version.endswith('/v1'):
            base_no_version = base_no_version[:-3]

        # Add common fallbacks (without version prefix since base_url may already have it)
        common_endpoints = [
            "chat-messages",
            "chat",
            "api/chat-messages",
            "api/chat",
            "completion-messages",
            "api/completion-messages",
        ]
        for path in common_endpoints:
            if path != self.endpoint_path:
                endpoints.append(f"{self.base_url}/{path}")

        # Also try with v1 prefix if base doesn't have it
        if not self.base_url.endswith('/v1'):
            for path in ["v1/chat-messages", "v1/chat"]:
                endpoints.append(f"{self.base_url}/{path}")
        # If base has v1, try without it
        else:
            for path in ["chat-messages", "chat"]:
                endpoints.append(f"{base_no_version}/{path}")

        last_error = None

        for endpoint in endpoints:
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    with client.stream("POST", endpoint, json=payload, headers=headers) as response:
                        # Log status code
                        import sys
                        print(f"DEBUG: Response status: {response.status_code} for {endpoint}", file=sys.stderr)

                        if response.status_code == 405:
                            # Try next endpoint
                            last_error = f"405 METHOD NOT ALLOWED at {endpoint}"
                            continue

                        if response.status_code == 400:
                            # Try to read error response before it's consumed
                            try:
                                error_content = response.read()
                                error_text = error_content.decode("utf-8", errors="ignore")
                                print(f"DEBUG: 400 Error response: {error_text}", file=sys.stderr)
                                raise httpx.HTTPStatusError(
                                    f"HTTP 400 Error: {error_text}",
                                    request=None,
                                    response=None
                                )
                            except Exception as ex:
                                raise httpx.HTTPStatusError(
                                    f"HTTP 400 Error (Could not read response: {ex})",
                                    request=None,
                                    response=None
                                )

                        response.raise_for_status()

                        # Parse SSE (Server-Sent Events) stream
                        for line in response.iter_lines():
                            if not line:
                                continue

                            # line = line.decode("utf-8")

                            # SSE format: "data: {...}"
                            if line.startswith("data: "):
                                data_str = line[6:]  # Remove "data: " prefix

                                # Skip end of stream marker
                                if data_str == "[DONE]":
                                    continue

                                # Parse JSON response
                                try:
                                    data = json.loads(data_str)

                                    # Extract text from response
                                    if "answer" in data:
                                        yield data["answer"]
                                except json.JSONDecodeError:
                                    # Skip malformed JSON
                                    continue
                            # Skip keep-alive and other SSE control messages
                            elif not line.startswith(":"):
                                # Log unknown line format for debugging
                                continue
                # Success - return from function
                return

            except Exception as e:
                # Handle all exceptions
                if isinstance(e, httpx.HTTPStatusError):
                    if e.response.status_code == 405:
                        last_error = f"405 at {endpoint}"
                        continue
                    elif e.response.status_code == 400:
                        # 400 error - try to get details before re-raising
                        error_msg = f"HTTP 400 Error at {endpoint}"
                        try:
                            if e.response and hasattr(e.response, '_content') and e.response._content:
                                content = e.response._content
                                if isinstance(content, bytes):
                                    error_body = content.decode("utf-8", errors="ignore")
                                else:
                                    error_body = str(content)
                                error_msg = f"{error_msg}: {error_body}"
                                import sys
                                print(f"DEBUG: 400 Error response: {error_body}", file=sys.stderr)
                        except Exception:
                            pass
                        raise Exception(error_msg)
                # Re-raise other exceptions
                raise

        # All endpoints failed with 405
        if last_error:
            raise httpx.HTTPStatusError(
                f"405 METHOD NOT ALLOWED. Tried endpoints: {', '.join(endpoints[:5])}... "
                f"Please check your Dify API documentation for the correct endpoint.",
                request=None,
                response=None
            )