# sber_assistance

Assistance for hackaton (case 6)

для запуска понадобятся 3 ебучих терминала

в первом:
`bash
cd sber_agent
. .venv/scripts/activate
python bot.py
`

во втором:
`bash
cd RAG
. .venv/scripts/activate
uvicorn app:app --reload
`

в третьем:
во втором:
`bash
ollama run llama3.2
`