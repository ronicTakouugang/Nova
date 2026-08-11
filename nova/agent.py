import sys

import anthropic

from .audio import record_until_silence
from .code_exec import RUN_PYTHON_TOOL, run_python
from .config import CODE_EXEC_ENABLED, GMAIL_ENABLED, MODEL, WEB_SEARCH_ENABLED
from .gmail import LIST_EMAILS_TOOL, READ_EMAIL_TOOL
from .gmail import is_configured as gmail_configured
from .gmail import list_emails, read_email
from .memory import recall, remember
from .stt import transcribe
from .tts import speak
from .wakeword import wait_for_wake_word
from .web_search import WEB_SEARCH_TOOL

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

SYSTEM_PROMPT_TEMPLATE = """Tu es Nova, l'assistant personnel de l'utilisateur, dans l'esprit de Jarvis : \
direct, compétent, un peu de personnalité, jamais bavard pour rien.

Réponds en français sauf si on te parle dans une autre langue.

{tool_notes}

Souvenirs pertinents pour cette conversation :
{memory}
"""

REMEMBER_TOOL = {
    "name": "remember",
    "description": (
        "Enregistre une information importante en mémoire long terme, relue au début "
        "de chaque conversation future. À utiliser pour les préférences, faits durables "
        "ou décisions de l'utilisateur — pas pour des détails ponctuels sans intérêt futur."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "L'information à retenir, formulée clairement et de façon autonome.",
            }
        },
        "required": ["content"],
    },
}


_GMAIL_ACTIVE = GMAIL_ENABLED and gmail_configured()


def build_tools() -> list[dict]:
    tools = [REMEMBER_TOOL]
    if CODE_EXEC_ENABLED:
        tools.append(RUN_PYTHON_TOOL)
    if WEB_SEARCH_ENABLED:
        tools.append(WEB_SEARCH_TOOL)
    if _GMAIL_ACTIVE:
        tools.extend([LIST_EMAILS_TOOL, READ_EMAIL_TOOL])
    return tools


def build_tool_notes() -> str:
    notes = [
        "Utilise l'outil `remember` quand l'utilisateur partage une préférence, un fait "
        "durable ou une décision qui vaut la peine d'être retenue pour les prochaines "
        "conversations."
    ]
    if CODE_EXEC_ENABLED:
        notes.append(
            "Utilise l'outil `run_python` pour les calculs, manipulations de fichiers ou "
            "toute tâche qu'un script Python peut accomplir. L'utilisateur doit confirmer "
            "chaque exécution — c'est normal, ne le présente pas comme une erreur."
        )
    if WEB_SEARCH_ENABLED:
        notes.append(
            "Utilise `web_search` quand la réponse dépend d'informations récentes ou que tu "
            "n'es pas sûr (actualités, météo, prix, événements récents) plutôt que de "
            "répondre depuis tes connaissances — ne demande pas la permission, cherche "
            "directement."
        )
    if _GMAIL_ACTIVE:
        notes.append(
            "Utilise `list_emails` puis `read_email` pour consulter la boîte mail de "
            "l'utilisateur — par exemple avec la requête Gmail 'is:important is:unread' "
            "pour les emails importants non lus, ou 'newer_than:1d' pour ceux du jour."
        )
    return "\n\n".join(notes)


def build_system_prompt(relevant_memories: list[str]) -> str:
    if relevant_memories:
        memory = "\n".join(f"- {m}" for m in relevant_memories)
    else:
        memory = "(aucun souvenir pertinent pour cette conversation)"
    return SYSTEM_PROMPT_TEMPLATE.format(tool_notes=build_tool_notes(), memory=memory)


def run_tool(name: str, tool_input: dict) -> str:
    if name == "remember":
        remember(tool_input["content"])
        return "Noté."
    if name == "run_python":
        return run_python(tool_input["code"], tool_input["purpose"])
    if name == "list_emails":
        return list_emails(tool_input.get("query", ""), tool_input.get("max_results", 10))
    if name == "read_email":
        return read_email(tool_input["message_id"])
    return f"Outil inconnu : {name}"


def handle_turn(client: anthropic.Anthropic, messages: list, user_text: str) -> None:
    """Send one user message through the full tool loop, print the streamed reply,
    and speak the final answer. Shared by both the text and voice input modes."""
    messages.append({"role": "user", "content": user_text})
    relevant_memories = recall(user_text)

    final_text = ""
    while True:
        with client.messages.stream(
            model=MODEL,
            max_tokens=2048,
            system=build_system_prompt(relevant_memories),
            tools=build_tools(),
            output_config={"effort": "medium"},
            messages=messages,
        ) as stream:
            print("Nova > ", end="", flush=True)
            chunks = []
            for text in stream.text_stream:
                print(text, end="", flush=True)
                chunks.append(text)
            print()
            response = stream.get_final_message()
        final_text = "".join(chunks)

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    speak(final_text)


def chat_text() -> None:
    client = anthropic.Anthropic()
    messages = []

    print("Nova est en ligne. Tape 'exit' pour quitter.\n")

    while True:
        user_input = input("Toi > ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break
        handle_turn(client, messages, user_input)


def chat_voice() -> None:
    client = anthropic.Anthropic()
    messages = []

    print('Nova écoute. Dis "Hey Jarvis" pour lui parler (Ctrl+C pour quitter).\n')

    while True:
        wait_for_wake_word()
        print("(réveillée, je t'écoute...)")
        audio = record_until_silence()
        user_text = transcribe(audio)
        if not user_text:
            print("(rien entendu)\n")
            continue
        print(f"Toi > {user_text}")
        handle_turn(client, messages, user_text)


if __name__ == "__main__":
    chat_text()
