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

LLM-агент на [Gradio](https://www.gradio.app/) + tool calling (Groq або OpenAI), який проводить тренувальний усний іспит для підготовки до НМТ з одного з 4 предметів і виставляє бал за шкалою 100–200.

## Як це працює

Агент (`agent.py`) спілкується зі студентом і керує іспитом через інструменти з `exam_tools.py`:

| Інструмент | Що робить |
|---|---|
| `list_subjects` | список доступних предметів |
| `start_exam` | починає іспит для студента з обраного предмета |
| `get_next_topic` | наступна тема іспиту (за замовчуванням 3 теми) |
| `get_question` | питання з банку (`data/subjects.json`) для теми |
| `get_weak_topics` | слабкі теми з попередніх спроб цього студента |
| `end_exam` | завершує іспит, рахує бал НМТ |
| `quit_exam` | дострокове завершення на прохання студента |

Предмети: українська мова, математика, історія України, англійська мова. Бал НМТ — лінійне перетворення середньої оцінки за теми (0–10) у шкалу 100–200. Результати зберігаються як JSON у `results/` (не комітяться, бо містять історію чату).

Налаштування через змінні середовища (`config.py`): `EXAMINER_TEMPERATURE`, `EXAMINER_REQUEST_TIMEOUT`, `EXAMINER_TOPICS_PER_EXAM`, `EXAMINER_RESPONSE_LANGUAGE`, `EXAMINER_RESULTS_DIR`.

## Запуск локально

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python app.py
```

Відкрити http://127.0.0.1:7860, обрати провайдера (Groq — безкоштовний ключ на [console.groq.com](https://console.groq.com/keys), або OpenAI), ввести ключ і почати діалог.

## Деплой

- **Render:** New → Blueprint → вибрати репозиторій (`render.yaml`). На безкоштовному плані диск тимчасовий, тож `results/` (і `get_weak_topics`) губляться після перезапуску.
