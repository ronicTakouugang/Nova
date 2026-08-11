import subprocess
import sys

TIMEOUT_SECONDS = 30
MAX_OUTPUT_CHARS = 3000

RUN_PYTHON_TOOL = {
    "name": "run_python",
    "description": (
        "Exécute du code Python et retourne stdout/stderr. Utilise ceci pour des "
        "calculs, manipuler des fichiers, ou toute tâche qu'un script Python peut "
        "accomplir. Le code tourne avec les mêmes droits que Nova elle-même — "
        "il n'y a pas de sandbox — donc l'utilisateur doit d'abord confirmer "
        "chaque exécution. N'utilise ce que pour des actions que l'utilisateur "
        "a explicitement demandées ou clairement impliquées par sa requête."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Le code Python à exécuter."},
            "purpose": {
                "type": "string",
                "description": (
                    "Explication courte (une phrase) de ce que fait ce code, "
                    "montrée à l'utilisateur avant qu'il confirme."
                ),
            },
        },
        "required": ["code", "purpose"],
    },
}


def run_python(code: str, purpose: str) -> str:
    """Ask the user to confirm, then run `code` in a fresh Python subprocess with
    a timeout. No sandboxing beyond that — the subprocess has the same OS
    permissions as Nova itself, so the confirmation step is the real safeguard."""
    print("\n[Nova veut exécuter du code]")
    print(f"But : {purpose}")
    print("---")
    print(code)
    print("---")
    answer = input("Autoriser ? (o/n) > ").strip().lower()
    if answer not in ("o", "oui", "y", "yes"):
        return "L'utilisateur a refusé l'exécution de ce code."

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return f"Le code a dépassé le délai de {TIMEOUT_SECONDS}s et a été interrompu."

    output = result.stdout.strip()
    if result.stderr.strip():
        output += f"\n[stderr]\n{result.stderr.strip()}"
    if result.returncode != 0:
        output += f"\n[code de retour: {result.returncode}]"
    output = output.strip() or "(aucune sortie)"

    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n[...tronqué...]"
    return output
