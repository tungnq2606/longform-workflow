#!/usr/bin/env python3
"""Authorize the YouTube uploader and store a refreshable OAuth token."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
DEFAULT_CLIENT_SECRETS = Path("~/.config/youtube-upload/client_secret.json").expanduser()
DEFAULT_TOKEN = Path("~/.config/youtube-upload/token.json").expanduser()


def authorize(client_secrets: Path, token_path: Path):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise RuntimeError("missing Google API packages; install requirements.txt") from exc

    credentials = None
    if token_path.is_file():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid or not credentials.has_scopes(SCOPES):
        if not client_secrets.is_file():
            raise FileNotFoundError(f"OAuth client secrets not found: {client_secrets}")
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
        credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    os.chmod(token_path, 0o600)
    return credentials


def resolve_paths(client_secrets: str | None, token_path: str | None) -> tuple[Path, Path]:
    client = Path(
        client_secrets or os.environ.get("YOUTUBE_CLIENT_SECRETS", DEFAULT_CLIENT_SECRETS)
    ).expanduser().resolve()
    token = Path(token_path or os.environ.get("YOUTUBE_TOKEN_FILE", DEFAULT_TOKEN)).expanduser().resolve()
    return client, token


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-secrets")
    parser.add_argument("--token-path")
    args = parser.parse_args()
    client, token = resolve_paths(args.client_secrets, args.token_path)
    try:
        authorize(client, token)
    except Exception as exc:
        print(f"Authorization failed: {exc}", file=sys.stderr)
        return 2
    print(f"Authorization complete. Token stored at: {token}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
