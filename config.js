// SpeechGradebook config
// When run through Python server (python app.py or uvicorn), this file is overridden
// by the dynamic /config.js endpoint which injects SUPABASE_URL and SUPABASE_ANON_KEY
// from environment variables.
//
// When opening index.html directly (file://) or using a simple file server, these
// empty values are used. To use Supabase, you must run via: ./run_local.sh
// (or: python -m uvicorn app:app --host 0.0.0.0 --port 8000)
// and set SUPABASE_URL and SUPABASE_ANON_KEY as environment variables.
//
// For local dev with env vars, create a .env file and run:
//   export $(cat .env | xargs) && ./run_local.sh
window.SUPABASE_URL = window.SUPABASE_URL || '';
window.SUPABASE_ANON_KEY = window.SUPABASE_ANON_KEY || '';
window.QWEN_API_URL = window.QWEN_API_URL || '';
