# Upload coding example videos to Supabase (behavior-examples folder)

Coding example videos/images are stored in the **existing** `evaluation-media` bucket, in a folder named **`behavior-examples`**. The Qwen behavior references file (`qwen_behavior_references.json`) is already configured to use these URLs once you upload files and set your project ref.

---

## 1. Create the folder in Supabase

1. Open your Supabase project → **Storage**.
2. Open the **`evaluation-media`** bucket.
3. Click **New folder** and name it **`behavior-examples`**.

---

## 2. Upload your files

Upload your coding example clips into **`evaluation-media/behavior-examples/`** using these **exact filenames** (so they match the URLs in `qwen_behavior_references.json`):

| Behavior              | Filename                    | Type  |
|-----------------------|-----------------------------|------|
| Hands in pockets      | `hands-in-pockets.mp4`      | video |
| Hands clasped (front) | `hands-clasped-front.mp4`   | video |
| Hands clasped behind  | `hands-clasped-behind.mp4`  | video |
| Swaying               | `swaying.mp4`               | video |
| Tapping hands         | `tapping-hands.mp4`         | video |
| Vocalized pause       | `vocalized-pause.mp4`       | video |
| Purpose statement     | `purpose-statement.mp4`     | video |

- You can use **.png** or **.jpg** for still images instead of .mp4; if you do, rename the file in the table above and update the same filename and `"media_type": "image"` for that entry in `qwen_behavior_references.json`.
- If you don’t have a clip for a behavior, you can leave that file out; the model still uses the text `description` and `scoring_guidance` for that behavior. To avoid broken URLs, remove or comment out the `media_url` (and `media_type`) for that entry in `qwen_behavior_references.json`.

---

## 3. Set the bucket to public (if needed)

For the Qwen service to load these URLs, the files must be publicly readable:

1. In Storage, click the **⋮** (or settings) for the **`evaluation-media`** bucket.
2. If the bucket is **private**, either:
   - Make the bucket **public**, or  
   - Create a bucket policy that allows public read for the `behavior-examples/` prefix.

If you use a different policy (e.g. signed URLs), the Qwen service must be updated to use that method instead of the public URL.

---

## 4. Replace YOUR_PROJECT_REF in the JSON

1. Get your **Supabase project reference**: from the Supabase URL  
   `https://XXXXXXXX.supabase.co`  
   the project ref is **XXXXXXXX**.
2. Open **`llm_training/qwen_behavior_references.json`**.
3. Replace every **`YOUR_PROJECT_REF`** with your actual project ref (e.g. **XXXXXXXX**).

After this, the `media_url` values will be valid (e.g.  
`https://XXXXXXXX.supabase.co/storage/v1/object/public/evaluation-media/behavior-examples/hands-in-pockets.mp4`).

---

## 5. Restart the Qwen service

If the Qwen (video) model service caches the behavior references file, restart it so it reloads `qwen_behavior_references.json` with the new URLs.

---

## Summary

| Step | Action |
|------|--------|
| 1 | In Storage → `evaluation-media`, create folder **`behavior-examples`**. |
| 2 | Upload each coding example with the filenames in the table above. |
| 3 | Ensure the bucket (or `behavior-examples/`) is publicly readable. |
| 4 | In `qwen_behavior_references.json`, replace **YOUR_PROJECT_REF** with your Supabase project ref. |
| 5 | Restart the Qwen service if needed. |
