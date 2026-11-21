import gradio as gr
import openai

from agent import GREETING, ExamAgent
from config import Settings
from exam_tools import ExamSession
from question_bank import QuestionBank
from storage import ResultStore

API_ERROR_MESSAGES: dict[type[openai.OpenAIError], str] = {
    openai.AuthenticationError: "Невірний API-ключ.",
    openai.RateLimitError: "Перевищено ліміт запитів або закінчився баланс. Спробуй пізніше.",
    openai.APIConnectionError: "Не вдалося під'єднатися до OpenAI. Перевір інтернет.",
}


def build_demo(settings: Settings, bank: QuestionBank, store: ResultStore) -> gr.Blocks:
    def new_agent() -> ExamAgent:
        return ExamAgent(settings, ExamSession(bank, store, settings))

    def chat(user_text: str, api_key: str, agent: ExamAgent | None):
        user_text, api_key = user_text.strip(), api_key.strip()
        if not api_key:
            raise gr.Error("Введи свій OpenAI API-ключ.")
        if not user_text:
            raise gr.Error("Напиши відповідь.")
        agent = agent or new_agent()
        try:
            agent.reply(user_text, api_key)
        except openai.OpenAIError as e:
            message = next(
                (msg for exc_type, msg in API_ERROR_MESSAGES.items() if isinstance(e, exc_type)),
                "Помилка OpenAI API. Спробуй ще раз.",
            )
            raise gr.Error(message) from e
        return agent.transcript, "", agent

    def reset():
        return [{"role": "assistant", "content": GREETING}], "", None

    with gr.Blocks(title="НМТ-екзаменатор") as demo:
        gr.Markdown(
            "# 🎓 НМТ-екзаменатор\n\n"
            "LLM-агент, який проводить тренувальний усний іспит для підготовки до НМТ. "
            "Назви своє ім'я і предмет — агент обере теми, ставитиме питання з банку, "
            "оцінюватиме відповіді й наприкінці дасть бал за шкалою НМТ (100–200) і поради, що повторити.\n\n"
            f"- **Предмети:** {', '.join(bank.subject_names)}.\n"
            f"- **Модель:** `{settings.model}` (OpenAI) з викликом інструментів.\n"
            "- **API-ключ** використовується лише для запитів поточної сесії і **ніде не зберігається**."
        )
        api_key = gr.Textbox(label="OpenAI API key", type="password", placeholder="sk-...")
        chatbot = gr.Chatbot(
            value=[{"role": "assistant", "content": GREETING}],
            label="Іспит",
            height=480,
            buttons=["copy"],
        )
        with gr.Row():
            message = gr.Textbox(
                placeholder="Твоя відповідь...",
                show_label=False,
                scale=5,
                autofocus=True,
            )
            send = gr.Button("Надіслати", variant="primary", scale=1)
        new_exam = gr.Button("Почати заново")
        agent_state = gr.State(None)

        inputs = [message, api_key, agent_state]
        outputs = [chatbot, message, agent_state]
        send.click(chat, inputs=inputs, outputs=outputs)
        message.submit(chat, inputs=inputs, outputs=outputs)
        new_exam.click(reset, outputs=outputs)
        chatbot.clear(reset, outputs=outputs)

    return demo


settings = Settings.from_env()
demo = build_demo(settings, QuestionBank.from_file(settings.data_path), ResultStore(settings.results_dir))

if __name__ == "__main__":
    demo.launch()
