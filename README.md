# Nova

Assistant personnel façon Jarvis. Nova vise, à terme, la voix (réveil + écoute + synthèse),
la mémoire long terme, le contrôle d'outils réels (domotique, code, web) et une interface
HUD — construits couche par couche, chaque phase validée avant la suivante.

## État actuel : Phase 4 — les mains (code, web, Gmail)

Un agent conversationnel propulsé par Claude, avec mémoire sémantique (ChromaDB), voix
sortante locale (Piper), voix entrante (mot de réveil + reconnaissance vocale), et la
capacité d'agir réellement : exécuter du code, chercher sur le web, lire ses emails.

- **Mémoire** : `remember`/`recall` sémantiques ; journal lisible dans `memory/notes.md`.
- **Voix sortante** : Piper (local, rapide — ~6s pour une réponse courte, pas de GPU
  requis). `NOVA_VOICE=off` pour du texte seul. XTTS-v2 reste dispo en option qualité
  (`NOVA_TTS_BACKEND=xtts`) mais est ~11x plus lent sur CPU — voir Notes techniques.
- **Voix entrante** : dis **"Hey Jarvis"** pour réveiller Nova (openWakeWord), puis parle
  — elle enregistre jusqu'à ce que tu t'arrêtes (silence détecté) et transcrit avec
  faster-whisper (modèle `small`, local, français).
- **Exécution de code** : Nova peut écrire et exécuter du Python (`run_python`) pour des
  calculs, manipulations de fichiers, etc. **Aucune sandbox** — le code tourne avec les
  mêmes droits qu'elle-même — donc chaque exécution demande une confirmation explicite
  dans le terminal avant de tourner. `NOVA_CODE_EXEC=off` pour désactiver entièrement.
- **Recherche web** : outil serveur natif de Claude (`web_search`), aucune config requise.
  `NOVA_WEB_SEARCH=off` pour désactiver.
- **Gmail** : `list_emails`/`read_email`, en lecture seule (scope `gmail.readonly` — Nova
  ne peut ni envoyer ni supprimer). Nécessite `gmail_credentials.json` à la racine (voir
  Configuration Gmail ci-dessous) ; sans ce fichier, les outils sont simplement absents.
- ElevenLabs, Home Assistant et les autres serveurs MCP restent des options futures non
  branchées.

### Lancer Nova

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # puis renseigner ANTHROPIC_API_KEY
python main.py                # mode texte (clavier)
python main.py --voice        # mode voix (micro + "Hey Jarvis")
```

Au premier lancement, plusieurs modèles se téléchargent une fois (puis les composants
voix/mémoire tournent hors-ligne) :
- ChromaDB : ~80 Mo (embeddings mémoire)
- Piper : ~60 Mo (voix française `fr_FR-siwis-medium`)
- openWakeWord : ~7 Mo (mot de réveil "Hey Jarvis")
- faster-whisper : ~500 Mo (modèle `small`, reconnaissance vocale)

**Ce qui n'est jamais hors-ligne** : chaque tour de conversation part vers l'API Claude
(`client.messages.stream`, dans `nova/agent.py`) — ça demande une connexion réseau et
`ANTHROPIC_API_KEY` à chaque fois. Web search tourne aussi côté serveur Anthropic. Seuls
la mémoire, la synthèse vocale, le mot de réveil et la transcription tournent localement.

### Configuration Gmail

1. Sur [console.cloud.google.com](https://console.cloud.google.com) : active l'API Gmail
   (APIs & Services → Library), configure l'écran de consentement OAuth en type
   **Externe** (pas Interne — "Interne" ne marche que pour un compte Google Workspace
   d'entreprise, il bloquera même le propriétaire sur un compte Gmail perso) avec ton
   email en test user, puis crée un identifiant OAuth de type **Desktop app**.
2. Télécharge le JSON, renomme-le `gmail_credentials.json`, dépose-le à la racine du
   projet (déjà dans `.gitignore` — jamais commité).
3. Au premier appel d'un outil Gmail, une fenêtre de navigateur s'ouvre pour
   l'autorisation ; le token est ensuite mis en cache dans `.gmail_token.json`
   (auto-renouvelé, aussi gitignored) et réutilisé sans re-demander.

### Voix — Piper vs XTTS-v2

Mesuré sur cette machine (CPU, pas de GPU exploitable — carte AMD intégrée, pas de
CUDA), pour une réponse de 41 mots :

| | Chargement (1x/session) | Synthèse | Total premier tour |
|---|---|---|---|
| **Piper** (défaut) | ~6s | ~6s | ~13s |
| XTTS-v2 | ~72s | ~65s (≈1,5s/mot) | ~137s |

XTTS-v2 sonne mieux et peut cloner une voix (`NOVA_VOICE_SAMPLE=chemin.wav`), mais à
cette vitesse une réponse de 100+ mots prend plusieurs minutes — inutilisable pour une
conversation. Piper est le défaut pour que la voix reste réactive ; XTTS-v2 reste une
option pour qui a un GPU ou n'est pas pressé.

### Problèmes connus (voix, non résolus)

- **Le mot de réveil entend encore mal une vraie voix**, même après avoir corrigé deux
  causes réelles confirmées (voir Notes techniques ci-dessous : MME au lieu de WASAPI,
  puis un plantage `PortAudioError` une fois passé sur WASAPI). Reste possible : le
  modèle pré-entraîné `hey_jarvis` d'openWakeWord n'est peut-être simplement pas robuste
  à un accent non natif, indépendamment de la qualité audio.
- **La latence perçue reste notable** même après le passage à Piper (~11x plus rapide
  que XTTS-v2) : ~12-14s par tour en régime établi. Une bonne partie est le temps réel
  de prononcer la réponse à voix haute plus la latence normale de l'API Claude — pas
  clairement un bug à ce stade.

Les deux ont été mis de côté volontairement pour avancer sur la Phase 4 — à reprendre.

### Notes techniques

- **Sécurité de `run_python`** : aucune sandbox, aucune restriction de dossier — le seul
  garde-fou est la confirmation manuelle avant chaque exécution (`nova/code_exec.py`).
  Ne pas confirmer un code dont l'effet n'est pas clair. Timeout de 30s, sortie tronquée
  à 3000 caractères.
- **Gmail est en lecture seule par choix** (`SCOPES` dans `nova/gmail.py` — juste
  `gmail.readonly`), pas parce que l'API ne permet pas plus. Étendre les scopes (envoi,
  suppression) demanderait de repasser par l'écran de consentement OAuth.
- **Le micro par défaut de Windows n'est pas forcément le bon** : sur cette machine,
  `sounddevice`/PortAudio résolvait le périphérique par défaut vers la variante **MME**
  du micro (l'API audio la plus ancienne de Windows), qui contourne le traitement DSP
  au niveau pilote (formation de faisceau du réseau de micros, gain automatique) que
  les apps modernes (navigateurs, etc.) obtiennent via **WASAPI**. `nova/audio.py`
  (`get_input_device`) sélectionne maintenant explicitement la variante WASAPI. Ça a
  révélé un second bug : WASAPI en mode partagé refuse un taux d'échantillonnage qui ne
  correspond pas à celui du périphérique (48kHz natif vs nos 16kHz demandés) — corrigé
  avec `WasapiSettings(auto_convert=True)`.
- Un gain logiciel (`apply_gain`) avait été tenté avant de trouver la cause ci-dessus —
  supprimé : sur un signal propre atténué à 12%, le score de détection ne changeait pas
  (0.999 → 0.999), donc l'amplitude seule n'expliquait pas le problème.
- Seuil de déclenchement du mot de réveil (`nova/wakeword.py`) laissé à 0.2 (au lieu du
  0.5 par défaut) — à remonter si ça déclenche sur autre chose que "Hey Jarvis".
- `coqui-tts` (XTTS-v2, optionnel) ne fixe pas de plafond sur `transformers` ; la 5.x
  casse une API interne encore utilisée → épingler `transformers==4.57.6` si tu actives
  ce backend. PyTorch récent (2.9+) nécessite aussi `torchcodec` (`coqui-tts[codec]`).
- Lecture audio via `winsound` (natif Windows) plutôt qu'une lib tierce — évite un
  compilateur C. À revoir si Nova tourne un jour hors Windows.
- Le mot de réveil est **"Hey Jarvis"** (modèle pré-entraîné anglais d'openWakeWord,
  clin d'œil assumé) — pas encore de mot de réveil français personnalisé, ça demanderait
  d'entraîner un modèle dédié. La commande vocale qui suit, elle, est bien transcrite
  en français.
- `huggingface_hub` essaie de créer des liens symboliques dans son cache, ce qui
  nécessite le Mode Développeur Windows ou des droits admin. `nova/stt.py` contourne
  ça au niveau applicatif (pas de modification système) — voir `_disable_hf_symlinks`.
- Détection de silence maison dans `nova/audio.py` (seuil RMS) pour savoir quand couper
  l'enregistrement — pas de VAD sophistiqué pour l'instant.

## Feuille de route

- [x] **Phase 0** — Cerveau texte : chat CLI + Claude + mémoire markdown
- [x] **Phase 1** — Mémoire vectorielle (ChromaDB)
- [x] **Phase 2** — Voix sortante (Piper local ; XTTS-v2 et ElevenLabs en options)
- [x] **Phase 3** — Voix entrante (wake word "Hey Jarvis" + faster-whisper)
- [x] **Phase 4** — Les mains : exécution de code, recherche web, Gmail (lecture seule)
- [ ] **Phase 5** — Interface HUD (Electron/Tauri)
- [ ] **Phase 6** — Orchestration temps réel avec interruption (LiveKit/Pipecat)
