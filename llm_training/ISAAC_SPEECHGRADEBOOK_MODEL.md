# Running the SpeechGradebook Text Model (Mistral) on ISAAC (GPU)

You can run the **SpeechGradebook Text Model (Mistral)** (fine-tuned Mistral 7B evaluation server) on an ISAAC GPU node instead of locally. Evaluations then use ISAAC’s GPU for inference; you connect from your laptop via an SSH tunnel.

---

## Prerequisites

- You’ve already **trained** the model on ISAAC (or copied `mistral7b-speech-lora` to `~/llm_training/` on ISAAC).
- Same one-time setup as training: conda env `speechgradebook`, `pip install -r requirements-train.txt`, and (for file upload) `pip install openai-whisper`. See `ISAAC_SETUP.md`.

---

## Option A: Interactive GPU session (recommended first)

1. **Request an interactive GPU job on ISAAC**

   ```bash
   ssh amcclu12@login.isaac.utk.edu
   cd ~/llm_training
   srun --pty -p campus-gpu --account=ACF-UTK0011 --gres=gpu:1 -t 4:00:00 -c 8 --mem=24G bash
   ```

 You’ll get a shell on a compute node (e.g. `clrv0701`).

2. **Start the SpeechGradebook model server on that node**

   In that same shell:

   ```bash
   module load anaconda3
   conda activate speechgradebook
   cd ~/llm_training
   python serve_model.py --model_path ./mistral7b-speech-lora --port 8000 --load_in_8bit
   ```

   Leave this running. Note the **hostname** (e.g. `clrv0701`) shown in your prompt.

3. **Create an SSH tunnel from your laptop**

   In a **new terminal on your laptop**:

   ```bash
   ssh -L 8000:localhost:8000 -J amcclu12@login.isaac.utk.edu amcclu12@NODE_NAME
   ```

   Example:

   ```bash
   ssh -L 8000:localhost:8000 -J amcclu12@login.isaac.utk.edu amcclu12@clrv0701
   ```

   Keep this tunnel running.

4. **Use SpeechGradebook**

   - In SpeechGradebook, go to **Settings → General**.
   - Set **Evaluation server URL** (SpeechGradebook Text Model (Mistral)) to: `http://localhost:8000`
   - Run evaluations as usual; they will use the model on ISAAC.

---

## Option B: Batch job (SLURM script)

You can submit a job that runs the server for a fixed time (e.g. 4 hours):

1. Edit `run_serve_model_isaac.slurm`: set `PARTITION_PLACEHOLDER` and `ACCOUNT_PLACEHOLDER` (e.g. `campus-gpu`, `ACF-UTK0011`).
2. From your laptop (with `run_config.env` set), run:

   ```bash
   cd llm_training
   ./run_serve_model_isaac.sh
   ```

   Or on ISAAC: `cd ~/llm_training && sbatch run_serve_model_isaac.slurm`

3. When the job starts, check the log for the node name:

   ```bash
   ssh amcclu12@login.isaac.utk.edu 'tail -20 ~/llm_training/logs/serve_model_*.out'
   ```

4. From your laptop, create the tunnel (replace `NODE_NAME` with the node from the log):

   ```bash
   ssh -L 8000:localhost:8000 -J amcclu12@login.isaac.utk.edu amcclu12@NODE_NAME
   ```

5. In SpeechGradebook, set Evaluation server URL to `http://localhost:8000`.

---

## Ports

| Service              | Port | Tunnel / URL |
|----------------------|------|-----------------------------|
| SpeechGradebook Text Model (Mistral) | 8000 | `ssh -L 8000:localhost:8000 ...` → `http://localhost:8000` |
| SpeechGradebook Text + Video Model (Qwen) | 8001 | `ssh -L 8001:localhost:8001 ...` → `QWEN_API_URL=http://localhost:8001` |

You can run both on the same ISAAC session: start `serve_model.py --port 8000` and `qwen_serve.py --port 8001`, then create both tunnels.

---

## Troubleshooting

- **"Could not connect to the SpeechGradebook Text Model (Mistral) server"**  
  Ensure the SSH tunnel is running and the Evaluation server URL is `http://localhost:8000` (no trailing slash).

- **503 or "no model is loaded"**  
  On ISAAC, confirm `mistral7b-speech-lora` exists under `~/llm_training/` and that you started `serve_model.py` with `--model_path ./mistral7b-speech-lora`.

- **File upload / transcription errors**  
  On the ISAAC env, install Whisper: `pip install openai-whisper`.
