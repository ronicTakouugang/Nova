import sys

import anthropic

from .config import MODEL
from .memory import append_memory, load_memory

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

SYSTEM_PROMPT_TEMPLATE = """Tu es Nova, l'assistant personnel de l'utilisateur, dans l'esprit de Jarvis : \
direct, compétent, un peu de personnalité, jamais bavard pour rien.

Réponds en français sauf si on te parle dans une autre langue.

Utilise l'outil `remember` quand l'utilisateur partage une préférence, un fait durable \
ou une décision qui vaut la peine d'être retenue pour les prochaines conversations.

Notes retenues jusqu'ici :
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


def build_system_prompt() -> str:
    memory = load_memory().strip() or "(aucune note pour l'instant)"
    return SYSTEM_PROMPT_TEMPLATE.format(memory=memory)


def run_tool(name: str, tool_input: dict) -> str:
    if name == "remember":
        append_memory(tool_input["content"])
        return "Noté."
    return f"Outil inconnu : {name}"


def chat() -> None:
    client = anthropic.Anthropic()
    messages = []

    print("Nova est en ligne. Tape 'exit' pour quitter.\n")

    while True:
        user_input = input("Toi > ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        messages.append({"role": "user", "content": user_input})

        while True:
            with client.messages.stream(
                model=MODEL,
                max_tokens=2048,
                system=build_system_prompt(),
                tools=[REMEMBER_TOOL],
                output_config={"effort": "medium"},
                messages=messages,
            ) as stream:
                print("Nova > ", end="", flush=True)
                for text in stream.text_stream:
                    print(text, end="", flush=True)
                print()
                response = stream.get_final_message()

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


if __name__ == "__main__":
    chat()
