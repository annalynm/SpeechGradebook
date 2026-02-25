# SpeechGradebook – Key Commands

Quick reference for common tasks.

---

## 1. Access the repo

```bash
cd /Users/annamcclure/SpeechGradebook
```

---

## 2. Development Workflow

### Push to Development Branch

Work on the `develop` branch and push changes:

```bash
git checkout develop
git add .
git commit -m "Your commit message"
git push origin develop
```

This automatically deploys to the development site on Render.

### Merge to Main (Production)

When ready to deploy to production:

```bash
git checkout main
git pull origin main
git merge develop
git push origin main
```

This automatically deploys to the production site on Render.

**Note:** Always test on the development site before merging to main.

---

## 3. Push to GitHub (Alternative Method)

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

## 4. Launch Modal (Qwen video evaluation)

**First-time setup:** `modal setup` (authenticate in browser).

**Deploy (permanent URL):**

```bash
cd /Users/annamcclure/SpeechGradebook
modal deploy llm_training/qwen_modal.py
```

Copy the URL Modal prints and set `QWEN_API_URL` on Render.

**Dev mode (temporary URL for testing):**

```bash
cd /Users/annamcclure/SpeechGradebook
modal serve llm_training/qwen_modal.py
```

Stop with Ctrl+C.

---

## 5. Launch localhost (Development)

From the repo root:

```bash
./run_local_dev.sh
```

Opens http://localhost:8000 (or the port in `$PORT`).

Uses development Supabase project (configured in `.env` file).

Press Ctrl+C to stop.

**Note:** Make sure `.env` file exists with your development Supabase credentials. See `docs/DEVELOPMENT_SETUP.md` for setup.

---

## 6. Kill port 8000 (when localhost is stuck)

If `./run_local_dev.sh` fails because port 8000 is already in use:

```bash
./scripts/kill_port_8000.sh
```

Then run `./run_local_dev.sh` again.

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
