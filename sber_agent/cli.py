import argparse
import sys

from .vector_db import VectorDB
from .agent import SupportAgent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="sber_agent/data/docs.jsonl", help="Path to docs.jsonl")
    args = parser.parse_args()

    print("Загружаю векторную базу (может занять время при первом запуске)...")
    vdb = VectorDB.from_jsonl(args.data)
    agent = SupportAgent(vdb)

    print("Sber Инвестиции — 1st-line агент. Введите вопрос на русском (Ctrl-C чтобы выйти).")
    try:
        while True:
            q = input("Вопрос> ")
            if not q.strip():
                continue
            resp = agent.handle_query(q)
            action = resp.get("action")
            if action == "answer":
                print("\n[Agent] Ответ (1-я линия):\n", resp.get("answer"))
                print("[source]", resp.get("source"), "score=", resp.get("score"))
            elif action == "escalate":
                print(f"\n[Agent] Эскалировать на {resp.get('level')}. Причина: {resp.get('reason')}")
                for m in resp.get("top_matches", []):
                    print(f" - id={m['id']} score={m['score']:.3f} text={m['text'][:200]}")
            else:
                print("\n[Agent] Вне темы / нет релевантной информации. Передать на ручную обработку.")
                for m in resp.get("top_matches", []):
                    print(f" - id={m['id']} score={m['score']:.3f} text={m['text'][:200]}")
    except KeyboardInterrupt:
        print("\nВыход.")
        sys.exit(0)


main()
