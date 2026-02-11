# Mac Shortcuts for SpeechGradebook

Two scripts you can run from the repo and turn into Mac shortcuts (e.g. double‑click or a keyboard shortcut).

---

## 1. Connect to ISAAC and launch Qwen

**Easiest (recommended):** Double‑click **`Connect_ISAAC_Qwen.command`** in the repo root. It opens a real Terminal window and runs the connect script there, so SSH can prompt for password and Duo without errors.

If you see **"could not be executed because you do not have appropriate access privileges"**, make the file executable once (in Terminal, from the repo root):  
`chmod +x Connect_ISAAC_Qwen.command`

**Script (used by the .command file):** `scripts/connect_isaac_qwen.sh`

- SSHes to ISAAC, requests a GPU job, and runs Qwen + the Cloudflare quick tunnel on the compute node.
- You’ll be prompted for your password and Duo.
- When the tunnel is up, a **banner** in the terminal will say **COPY THIS URL** and show the `https://….trycloudflare.com` URL. Copy it and set **QWEN_API_URL** on Render (Environment) and Save.

**First-time setup:** Run this once in Terminal and type `yes` when asked to accept the host key:

```bash
ssh amcclu12@login.isaac.utk.edu
```

After that, the `.command` file (and any shortcut that opens it) will work. If you skip this, you may see **"Host key verification failed."**

**From Terminal (repo root):**

```bash
chmod +x scripts/connect_isaac_qwen.sh
./scripts/connect_isaac_qwen.sh
```

**Optional:** Set `ISAAC_USER` or `ISAAC_HOST` if different:

```bash
export ISAAC_USER=amcclu12
export ISAAC_HOST=login.isaac.utk.edu
./scripts/connect_isaac_qwen.sh
```

**Note:** ISAAC must already have `~/llm_training` with the Qwen script and conda env (e.g. `qwen` with Python 3.10 and `requirements-qwen.txt` installed). If you’ve changed the repo, copy updates first:  
`scp -r llm_training amcclu12@login.isaac.utk.edu:~/`

---

## 2. Push updates to GitHub

**Script:** `scripts/push_to_github.sh`

- Stages all changes, commits (with a message you provide or a default), and pushes to the current branch on `origin`.

**From Terminal (repo root):**

```bash
chmod +x scripts/push_to_github.sh
./scripts/push_to_github.sh
# You’ll be prompted for a commit message, or press Enter for "Updates to SpeechGradebook"

# Or pass the message on the command line:
./scripts/push_to_github.sh "Add Qwen named tunnel docs"
```

---

## Creating Mac shortcuts

### ISAAC + Qwen: use the .command file (not Run Shell Script)

Running `connect_isaac_qwen.sh` from an Automator **Run Shell Script** action fails because:

- **"Pseudo-terminal will not be allocated because stdin is not a terminal"** — Automator doesn't give the script a real terminal, so SSH can't prompt for password or Duo.
- **"Host key verification failed"** — Fix this once by running `ssh amcclu12@login.isaac.utk.edu` in Terminal and typing `yes` to accept the host key.

**Recommended:** Use **`Connect_ISAAC_Qwen.command`** in the repo root. Double‑click it (or open it from a shortcut) to get a real Terminal window.

- **Desktop/Applications shortcut:** In Finder, Right‑click `Connect_ISAAC_Qwen.command` → **Make Alias**, then move the alias to Desktop or Applications.
- **Keyboard shortcut:** Use a Quick Action that runs `open "/Users/annamcclure/SpeechGradebook/Connect_ISAAC_Qwen.command"` (see Option B).

### Option A: Double‑click to run (Automator app)

1. Open **Automator** (Applications → Automator).
2. **File → New** → choose **Application**.
3. Add a **Run Shell Script** action.
4. Set **Shell** to `/bin/zsh` (or `/bin/bash`).
5. In the script box (for **Push to GitHub** only; for ISAAC use the `.command` file above):

   **Push to GitHub:**
   ```bash
   cd "/Users/annamcclure/SpeechGradebook"
   ./scripts/push_to_github.sh
   ```

6. **File → Save** (e.g. “Push SpeechGradebook to GitHub.app”).
7. Put the app in Applications or on the Desktop. Double‑click to run.

To keep the window open so you can see the result, add at the end:

```bash
echo "Press Enter to close."
read
```

### Option B: Keyboard shortcut (Automator + System Settings)

1. Create an Automator **Quick Action** (not Application):
   - **File → New** → **Quick Action**.
   - **Workflow receives:** no input.
   - Add **Run Shell Script**; put one of these in the script box:
     - **Connect ISAAC + Qwen:** `open "/Users/annamcclure/SpeechGradebook/Connect_ISAAC_Qwen.command"`
     - **Push to GitHub:** `cd "/Users/annamcclure/SpeechGradebook"` then `./scripts/push_to_github.sh`
   - Save (e.g. “Connect ISAAC Qwen”, “Push SpeechGradebook to GitHub”).
2. Open **System Settings → Keyboard → Keyboard Shortcuts → Services**.
3. Find your Quick Action and assign a shortcut (e.g. **⌃⌘I** for ISAAC, **⌃⌘G** for GitHub).

### Option C: Terminal alias (for use inside Terminal)

Add to `~/.zshrc` (or `~/.bashrc`):

```bash
alias isaac-qwen='cd "/Users/annamcclure/SpeechGradebook" && ./scripts/connect_isaac_qwen.sh'
alias push-speechgradebook='cd "/Users/annamcclure/SpeechGradebook" && ./scripts/push_to_github.sh'
```

Then run `isaac-qwen` or `push-speechgradebook` from any directory (after `source ~/.zshrc` or opening a new terminal).

---

## Paths to use in shortcuts

Replace with your actual repo path if different:

- **Repo root:** `/Users/annamcclure/SpeechGradebook`
- **Connect ISAAC + Qwen (recommended):** `Connect_ISAAC_Qwen.command` in repo root (double‑click or `open "…/Connect_ISAAC_Qwen.command"`).
- **Connect ISAAC + Qwen (from Terminal):** `./scripts/connect_isaac_qwen.sh`
- **Push to GitHub:** `./scripts/push_to_github.sh`
