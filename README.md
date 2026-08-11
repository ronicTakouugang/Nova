# Nova

Assistant personnel façon Jarvis. Nova vise, à terme, la voix (réveil + écoute + synthèse),
la mémoire long terme, le contrôle d'outils réels (domotique, code, web) et une interface
HUD — construits couche par couche, chaque phase validée avant la suivante.

## État actuel : Phase 3 — voix entrante

Un agent conversationnel propulsé par Claude, avec mémoire sémantique (ChromaDB), voix
sortante locale (XTTS-v2) et maintenant voix entrante : mot de réveil + reconnaissance
vocale.

- **Mémoire** : `remember`/`recall` sémantiques ; journal lisible dans `memory/notes.md`.
- **Voix sortante** : XTTS-v2 local et gratuit. `NOVA_VOICE=off` pour du texte seul.
- **Voix entrante** : dis **"Hey Jarvis"** pour réveiller Nova (openWakeWord), puis parle
  — elle enregistre jusqu'à ce que tu t'arrêtes (silence détecté) et transcrit avec
  faster-whisper (modèle `small`, local, français).
- ElevenLabs reste une option future non branchée (nécessite une clé API payante).

### Lancer Nova

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # puis renseigner ANTHROPIC_API_KEY
python main.py                # mode texte (clavier)
python main.py --voice        # mode voix (micro + "Hey Jarvis")
```

Au premier lancement, plusieurs modèles se téléchargent une fois (puis tout tourne
hors-ligne) :
- ChromaDB : ~80 Mo (embeddings mémoire)
- XTTS-v2 : ~1,8 Go (voix sortante ; licence CPML acceptée automatiquement)
- openWakeWord : ~7 Mo (mot de réveil "Hey Jarvis")
- faster-whisper : ~500 Mo (modèle `small`, reconnaissance vocale)

### Notes techniques

- `coqui-tts` ne fixe pas de plafond sur `transformers` ; la 5.x casse une API interne
  encore utilisée par XTTS-v2 → `requirements.txt` épingle `transformers==4.57.6`.
- PyTorch récent (2.9+) nécessite `torchcodec` pour l'I/O audio → extra `coqui-tts[codec]`.
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
- [x] **Phase 2** — Voix sortante (XTTS-v2 local ; ElevenLabs en option future)
- [x] **Phase 3** — Voix entrante (wake word "Hey Jarvis" + faster-whisper)
- [ ] **Phase 4** — Les mains (MCP, domotique, exécution de code)
- [ ] **Phase 5** — Interface HUD (Electron/Tauri)
- [ ] **Phase 6** — Orchestration temps réel avec interruption (LiveKit/Pipecat)
