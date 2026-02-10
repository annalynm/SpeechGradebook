# SpeechGradebook – Key Commands

Quick reference for common tasks. Run from your machine (not inside Modal/ISAAC).

---

## 1. Access the repo

```bash
cd "/Users/annamcclure/SpeechGradebook Repo"
```

---

## 2. Push to GitHub

From the repo root:

```bash
./scripts/push_to_github.sh
```

Prompts for a commit message (or press Enter for the default).

Or pass the message on the command line:

```bash
./scripts/push_to_github.sh "Your commit message"
```

---

## 3. Launch Modal (Qwen video evaluation)

**First-time setup:** `modal setup` (authenticate in browser).

**Deploy (permanent URL):**

```bash
cd "/Users/annamcclure/SpeechGradebook Repo"
modal deploy llm_training/qwen_modal.py
```

Copy the URL Modal prints and set `QWEN_API_URL` on Render.

**Dev mode (temporary URL for testing):**

```bash
cd "/Users/annamcclure/SpeechGradebook Repo"
modal serve llm_training/qwen_modal.py
```

Stop with Ctrl+C.

---

## 4. Launch localhost

From the repo root:

```bash
./run_local.sh
```

Opens http://localhost:8000 (or the port in `$PORT`).

Press Ctrl+C to stop.

---

## 5. Kill port 8000 (when localhost is stuck)

If `./run_local.sh` fails because port 8000 is already in use:

```bash
./scripts/kill_port_8000.sh
```

Then run `./run_local.sh` again.

---

## 6. Connect ISAAC + Qwen (campus GPU alternative to Modal)

Use ISAAC campus GPU instead of Modal for Qwen video evaluation. Double‑click **`Connect_ISAAC_Qwen.command`** in the repo root, or from Terminal:

```bash
./scripts/connect_isaac_qwen.sh
```

You’ll be prompted for ISAAC password and Duo. Copy the Cloudflare tunnel URL from the banner and set it as `QWEN_API_URL` on Render.

---

## 7. Run tests

From the repo root:

```bash
pytest
```

Or with venv:

```bash
./venv/bin/python -m pytest
```

---

## 8. Git status / pull

**Check what’s changed before pushing:**

```bash
git status
```

**Get latest from GitHub:**

```bash
git pull origin main
```

(Replace `main` with your branch if different.)

---

## In-app: Undo & recover deleted items

- **Right after a delete:** A toast appears with an **Undo** button for a few seconds. Use it to restore the student, evaluation, or course you just removed (only for “local”/soft deletes).
- **Already deleted:** Open **Settings → General** and click **Recover deleted items** to see students, evaluations, and courses you’ve removed and restore them with **Restore**. This only applies to items removed with Delete/Remove (instructor or admin); it does not restore rows permanently deleted by a super admin.

/Users/annamcclure/Desktop/eTextbook/HAASJ 4377-4 W22_CE (AM Edits) 04.30.24.pdf

python llm_training/ingest_textbook.py "/Users/annamcclure/Desktop/eTextbook/HAASJ 4377-4 W22_CE (AM Edits) 04.30.24.pdf" "Public Speaking in a Global Context"
