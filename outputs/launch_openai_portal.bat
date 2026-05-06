@echo off
cd /d "C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex"
set "MEGHYAN_LLM_MODE=openai_compatible"
set "MEGHYAN_LLM_ENDPOINT=https://api.openai.com/v1"
set "MEGHYAN_LLM_API_KEY=YOUR_OPENAI_API_KEY"
set "MEGHYAN_LLM_MODEL=gpt-5.4-mini"
"C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex\.venv\Scripts\python.exe" -c "from meghyan_portal.app import app; app.run(host='127.0.0.1', debug=False, use_reloader=False, port=5055)" 1>>"C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex\outputs\openai_portal_stdout.log" 2>>"C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex\outputs\openai_portal_stderr.log"
