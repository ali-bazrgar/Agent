from __future__ import annotations

import ipaddress
import logging
import re
import socket
import urllib.parse
import urllib.request
from typing import Any

from superagent.tools.models import (
    RiskLevel,
    ToolCall,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolResult,
)
from superagent.tools.ports import ToolProvider

logger = logging.getLogger(__name__)


class WebFetchProvider:
    """Safely fetches and extracts text content from web URLs with SSRF protection."""

    MAX_BYTES = 1_000_000  # 1 MB

    @classmethod
    def validate_url_ssrf(cls, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Disallowed URL scheme '{parsed.scheme}'. Only http and https are allowed.")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("URL must contain a valid hostname.")

        if hostname.lower() in ("localhost", "localhost.localdomain", "127.0.0.1", "::1"):
            raise ValueError("Access to localhost is restricted for security (SSRF protection).")

        # Resolve IP addresses
        try:
            addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        except socket.gaierror as exc:
            raise ValueError(f"Could not resolve hostname '{hostname}': {exc}")

        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)

            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_multicast
                or ip_obj.is_reserved
                or ip_str == "0.0.0.0"
            ):
                raise ValueError(f"Access to private or internal IP address '{ip_str}' is restricted (SSRF protection).")

        return url

    def fetch(self, url: str, timeout_seconds: float = 10.0) -> dict[str, Any]:
        safe_url = self.validate_url_ssrf(url)

        req = urllib.request.Request(
            safe_url,
            headers={"User-Agent": "SuperAgent/1.0 (WebFetch)"},
        )

        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            content_type = resp.headers.get("Content-Type", "").lower()
            if not any(ct in content_type for ct in ("text/", "application/json", "application/xml")):
                raise ValueError(f"Unsupported content type '{content_type}'. Only text, JSON, or XML pages are supported.")

            raw_body = resp.read(self.MAX_BYTES + 1)
            if len(raw_body) > self.MAX_BYTES:
                raw_body = raw_body[: self.MAX_BYTES]

            encoding = resp.headers.get_param("charset") or "utf-8"
            try:
                body_text = raw_body.decode(encoding, errors="replace")
            except Exception:
                body_text = raw_body.decode("utf-8", errors="replace")

            # Basic HTML title and body extraction
            title = "Untitled Page"
            title_match = re.search(r"<title>(.*?)</title>", body_text, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()

            # Clean HTML tags for readable text extraction
            clean_text = re.sub(r"<script.*?>.*?</script>", " ", body_text, flags=re.IGNORECASE | re.DOTALL)
            clean_text = re.sub(r"<style.*?>.*?</style>", " ", clean_text, flags=re.IGNORECASE | re.DOTALL)
            clean_text = re.sub(r"<[^>]+>", " ", clean_text)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()

            return {
                "url": safe_url,
                "title": title,
                "text": clean_text[:20000],  # Truncate text for context safety
                "content_type": content_type,
                "content_length": len(clean_text),
            }


class WebFetchTool(ToolProvider):
    """Tool enabling agent to fetch and parse external webpage content safely."""

    def __init__(self, provider: WebFetchProvider | None = None) -> None:
        self.provider = provider or WebFetchProvider()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_fetch",
            description="Fetches and extracts text content from a specified web URL.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full HTTP or HTTPS web URL to fetch.",
                    }
                },
                "required": ["url"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "title": {"type": "string"},
                    "text": {"type": "string"},
                    "content_length": {"type": "integer"},
                },
            },
            requires_network=True,
            risk_level=RiskLevel.MEDIUM,
            timeout_seconds=10.0,
            enabled=True,
        )

    def execute(
        self,
        call: ToolCall,
        context: ToolExecutionContext | None = None,
    ) -> ToolResult:
        url = call.arguments.get("url")
        if not url or not isinstance(url, str) or not url.strip():
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="web_fetch",
                status=ToolExecutionStatus.INVALID_ARGUMENTS,
                error="Argument 'url' must be a non-empty string.",
            )

        timeout = (context.timeout_seconds if context else None) or self.definition.timeout_seconds

        try:
            res = self.provider.fetch(url.strip(), timeout_seconds=timeout)
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="web_fetch",
                status=ToolExecutionStatus.SUCCESS,
                output=res,
            )
        except ValueError as val_err:
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="web_fetch",
                status=ToolExecutionStatus.SECURITY_REJECTED
                if "SSRF" in str(val_err) or "restricted" in str(val_err)
                else ToolExecutionStatus.ERROR,
                error=str(val_err),
            )
        except Exception as exc:
            logger.warning(f"WebFetchTool failed for URL '{url}': {exc}")
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="web_fetch",
                status=ToolExecutionStatus.ERROR,
                error=f"Failed to fetch URL: {exc}",
            )
