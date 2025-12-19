# transformers_rag.py
# import os
# import pandas as pd
# import torch
# from transformers import AutoTokenizer, AutoModel
# from rich import print as rprint
# import numpy as np
# from typing import Optional
import requests

# class RAGModel:
#     # === Загрузка CSV ===
#     if not os.path.exists("data/data.csv"):
#         rprint("[red] Файл data.csv не найден![/red]")
#         exit(1)

#     # === Загрузка модели и токенизатора ===
#     rprint("[yellow]🔁 Загрузка модели paraphrase-multilingual-MiniLM-L12-v2...[/yellow]")
#     tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
#     model = AutoModel.from_pretrained("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
#     model.eval()  # режим инференса
#     rprint("[green]✅ Модель загружена![/green]")

#     # === Функция усреднения эмбеддингов (mean pooling) ===
#     def mean_pooling(self, model_output, attention_mask):
#         token_embeddings = model_output.last_hidden_state
#         input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
#         return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

#     # === Генерация эмбеддингов вопросов ===
#     def encode(self, texts):
#         if isinstance(texts, str):
#             texts = [texts]
#         encoded = self.tokenizer(
#             texts, padding=True, truncation=True, return_tensors="pt", max_length=128
#         )
#         with torch.no_grad():
#             output = self.model(**encoded)
#         embeddings = self.mean_pooling(output, encoded["attention_mask"])
#         # L2-нормализация (как в sentence-transformers)
#         embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
#         return embeddings.numpy()

#     rprint("[yellow]🔁 Генерация эмбеддингов вопросов...[/yellow]")
#     rprint("[green]✅ Готово![/green]")

#     # === Поиск ===
#     def get_answer(self, query: str) -> Optional[str]:
#         df = pd.read_csv("data/data.csv")
#         question_embs = self.encode(df["question"].tolist())
#         query_emb = self.encode(query)
#         sims = (question_embs @ query_emb.T).flatten()
#         best_idx = int(np.argmax(sims))
#         score = float(sims[best_idx])

#         row = df.iloc[best_idx]

#         match row['priority_class']:
#             case 'well_known_question':
#                 row['priority_class'] = 'low'
#             case 'send_to_helpdesk':
#                 row['priority_class'] = 'medium'
#             case 'high_priority':
#                 row['priority_class'] = 'high'

#         row['simularity'] = f'{score:.2f}'
#         return row

class RAGModel:
    def get_answer(self, query, host='http://127.0.0.1:8000'):
        response = requests.post(f'{host}/ask', json={'question': query})
        return response.json()
