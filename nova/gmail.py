import base64

from .config import BASE_DIR

# Read-only on purpose — Nova can check/read mail, not send or delete anything.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_PATH = BASE_DIR / "gmail_credentials.json"
TOKEN_PATH = BASE_DIR / ".gmail_token.json"

LIST_EMAILS_TOOL = {
    "name": "list_emails",
    "description": (
        "Recherche des emails dans la boîte Gmail de l'utilisateur et retourne, pour "
        "chacun, un ID, l'expéditeur, le sujet, la date et un court aperçu. Utilise la "
        "syntaxe de recherche Gmail pour `query` — par exemple 'is:important is:unread' "
        "pour les emails importants non lus, 'newer_than:1d' pour les emails du jour, "
        "'from:nom@exemple.com' pour un expéditeur précis. Requête vide = les plus récents."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Requête de recherche Gmail."},
            "max_results": {
                "type": "integer",
                "description": "Nombre maximum d'emails à retourner (défaut 10).",
            },
        },
        "required": ["query"],
    },
}

READ_EMAIL_TOOL = {
    "name": "read_email",
    "description": "Lit le contenu complet d'un email à partir de son ID (obtenu via list_emails).",
    "input_schema": {
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": "L'ID du message, retourné par list_emails.",
            }
        },
        "required": ["message_id"],
    },
}

_service = None


def is_configured() -> bool:
    return CREDENTIALS_PATH.exists()


def _get_service():
    global _service
    if _service is None:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CREDENTIALS_PATH.exists():
                    raise RuntimeError(
                        f"Identifiants Gmail introuvables : {CREDENTIALS_PATH}. "
                        "Voir le README pour la procédure de configuration."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
                creds = flow.run_local_server(port=0)
            TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

        _service = build("gmail", "v1", credentials=creds)
    return _service


def list_emails(query: str = "", max_results: int = 10) -> str:
    service = _get_service()
    resp = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    message_refs = resp.get("messages", [])
    if not message_refs:
        return "Aucun email ne correspond à cette recherche."

    entries = []
    for ref in message_refs:
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=ref["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        entries.append(
            f"- ID: {ref['id']}\n"
            f"  De: {headers.get('From', '?')}\n"
            f"  Sujet: {headers.get('Subject', '(sans sujet)')}\n"
            f"  Date: {headers.get('Date', '?')}\n"
            f"  Aperçu: {msg.get('snippet', '')}"
        )
    return "\n".join(entries)


def read_email(message_id: str) -> str:
    service = _get_service()
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    body = _extract_body(msg["payload"])
    return (
        f"De: {headers.get('From', '?')}\n"
        f"Sujet: {headers.get('Subject', '(sans sujet)')}\n"
        f"Date: {headers.get('Date', '?')}\n\n"
        f"{body}"
    )


def _extract_body(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    return "(contenu non disponible — probablement HTML uniquement)"
