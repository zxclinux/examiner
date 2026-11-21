---
title: НМТ-екзаменатор
emoji: 🎓
colorFrom: blue
colorTo: yellow
sdk: gradio
sdk_version: 6.31.0
app_file: app.py
pinned: false
---

# 🎓 НМТ-екзаменатор

LLM-агент на [Gradio](https://www.gradio.app/) + OpenAI tool calling, який проводить тренувальний усний іспит для підготовки до НМТ з одного з 4 предметів і виставляє бал за шкалою 100–200.

Повний опис системи, інструментів агента і рішень — у [SUBMISSION.md](SUBMISSION.md).

## Запуск локально

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python app.py
```

Відкрити http://127.0.0.1:7860, ввести OpenAI API-ключ і почати діалог.

## Деплой

- **HuggingFace Spaces:** New Space → SDK Gradio → завантажити файли репозиторію (заголовок цього README налаштовує Space).
- **Render:** New → Blueprint → вибрати репозиторій (`render.yaml`).
