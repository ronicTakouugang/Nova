# Nova

Assistant personnel façon Jarvis. Nova vise, à terme, la voix (réveil + écoute + synthèse),
la mémoire long terme, le contrôle d'outils réels (domotique, code, web) et une interface
HUD — construits couche par couche, chaque phase validée avant la suivante.

## État actuel : Phase 2 — voix sortante

Un agent conversationnel en ligne de commande, propulsé par Claude, avec une mémoire
sémantique persistante (ChromaDB) et une voix : chaque réponse finale est synthétisée
localement avec XTTS-v2 (Coqui) et jouée automatiquement.

- Mémoire : `remember`/`recall` sémantiques dans une base vectorielle locale ; journal
  lisible en parallèle dans `memory/notes.md`.
- Voix : synthèse 100% locale et gratuite via XTTS-v2, lecture via `winsound` (Windows).
  Coupe-la avec `NOVA_VOICE=off` si tu veux du texte seul.
- ElevenLabs reste une option envisagée pour une meilleure qualité de voix, pas encore
  branchée (nécessite une clé API payante) — voir la feuille de route.

### Lancer Nova

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # puis renseigner ANTHROPIC_API_KEY
python main.py
```

Au premier lancement :
- ChromaDB télécharge un petit modèle d'embeddings (~80 Mo, une fois, hors-ligne ensuite).
- XTTS-v2 télécharge le modèle de synthèse vocale (~1,8 Go, une fois — accepte la licence
  CPML de Coqui automatiquement via la variable `COQUI_TOS_AGREED`).

Le premier tour de parole peut donc être lent le temps de ces téléchargements ; les
suivants sont rapides (modèles mis en cache localement).

### Notes techniques

- `coqui-tts` ne fixe pas de plafond sur `transformers` ; la 5.x casse une API interne
  encore utilisée par XTTS-v2. `requirements.txt` épingle `transformers==4.57.6`.
- PyTorch récent (2.9+) nécessite `torchcodec` pour l'I/O audio — inclus via l'extra
  `coqui-tts[codec]`.
- La lecture audio utilise `winsound` (natif Python sur Windows) plutôt qu'une lib tierce
  — évite d'avoir besoin d'un compilateur C. À revoir si Nova tourne un jour hors Windows.

## Feuille de route

- [x] **Phase 0** — Cerveau texte : chat CLI + Claude + mémoire markdown
- [x] **Phase 1** — Mémoire vectorielle (ChromaDB)
- [x] **Phase 2** — Voix sortante (XTTS-v2 local ; ElevenLabs en option future)
- [ ] **Phase 3** — Voix entrante (STT + wake word)
- [ ] **Phase 4** — Les mains (MCP, domotique, exécution de code)
- [ ] **Phase 5** — Interface HUD (Electron/Tauri)
- [ ] **Phase 6** — Orchestration temps réel avec interruption (LiveKit/Pipecat)
