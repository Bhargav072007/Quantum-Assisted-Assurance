Set-Location 'C:\Users\msrib\OneDrive\Documents - OneDrive\Playground\qaa_codex'
 = 'openai_compatible'
 = 'https://api.openai.com/v1'
 = 'YOUR_OPENAI_API_KEY'
 = 'gpt-5.4-mini'
@'
import os
from meghyan_portal.llm_service import llm_config, llm_status
print(os.getenv('MEGHYAN_LLM_MODE'))
print(llm_config())
print(llm_status())
'@ | .\.venv\Scripts\python.exe -
