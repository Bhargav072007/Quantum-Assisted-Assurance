@echo off
cd /d "C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex"
"C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex\.venv\Scripts\python.exe" -c "from meghyan_portal.app import app; app.run(host='127.0.0.1', debug=False, use_reloader=False, port=5055)" 1>>"C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex\outputs\portal_stdout.log" 2>>"C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex\outputs\portal_stderr.log"
