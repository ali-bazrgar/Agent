from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from superagent.context.request import Principal


# This adapter deliberately does not trust an arbitrary request-body user_id.
# A production deployment should place authentication in front of the API and
# configure the trusted principal header there. For local-first deployments,
# SUPERAGENT_DEFAULT_PRINCIPAL_ID provides a single explicit local identity.
TRUSTED_PRINCIPAL_HEADER = "X-SuperAgent-Principal"


def get_principal(
    trusted_header: Annotated[str | None, Header(alias=TRUSTED_PRINCIPAL_HEADER)] = None,
) -> Principal:
    configured = os.getenv("SUPERAGENT_DEFAULT_PRINCIPAL_ID", "").strip()
    header_enabled = os.getenv("SUPERAGENT_TRUST_PRINCIPAL_HEADER", "false").strip().lower() in {"1", "true", "yes", "on"}

    if header_enabled:
        if not trusted_header or not trusted_header.strip():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated principal is required")
        return Principal(principal_id=trusted_header.strip(), principal_type="user")

    if configured:
        return Principal(principal_id=configured, principal_type="user")

    return Principal(principal_id="anonymous", principal_type="anonymous")
