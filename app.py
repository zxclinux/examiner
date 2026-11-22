import gradio as gr
import openai

from agent import GREETING, ExamAgent
from config import DEFAULT_PROVIDER, PROVIDERS, Settings
from exam_tools import ExamSession
from question_bank import QuestionBank
from storage import ResultStore

API_ERROR_MESSAGES: dict[type[openai.OpenAIError], str] = {
    openai.AuthenticationError: "Невірний API-ключ для обраного провайдера.",
    openai.RateLimitError: "Перевищено ліміт запитів або закінчився баланс. Спробуй пізніше або іншу модель.",
    openai.APIConnectionError: "Не вдалося під'єднатися до API. Перевір інтернет.",
    openai.NotFoundError: "Модель недоступна для цього ключа. Обери іншу модель.",
    openai.BadRequestError: "Модель не змогла коректно викликати інструмент. Надішли повідомлення ще раз або обери іншу модель.",
}

DESCRIPTION = """# 🎓 НМТ-екзаменатор
LLM-агент, який проводить тренувальний усний іспит для підготовки до НМТ. Назви своє ім'я і предмет —
агент обере теми, ставитиме питання з банку, пояснить помилки й наприкінці дасть бал за шкалою НМТ (100–200).

Безкоштовний ключ можна отримати на [console.groq.com](https://console.groq.com/keys)
або використати ключ [OpenAI](https://platform.openai.com/api-keys). Ключ ніде не зберігається.
"""

EXAMPLES = [
    "Привіт, я Оля. Хочу потренуватися з математики.",
    "Мене звати Тарас, давай історію України.",
    "Я Марія, українська мова.",
    "Я Андрій, хочу англійську.",
]


def build_demo(settings: Settings, bank: QuestionBank, store: ResultStore) -> gr.Blocks:
    def new_agent() -> ExamAgent:
        return ExamAgent(settings, ExamSession(bank, store, settings))

    def chat(user_text: str, api_key: str, provider_name: str, model: str, agent: ExamAgent | None):
        user_text, api_key = user_text.strip(), api_key.strip()
        if not api_key:
            raise gr.Error("Введи ключ API.")
        if not user_text:
            raise gr.Error("Напиши відповідь.")
        agent = agent or new_agent()
        try:
            agent.reply(user_text, api_key, PROVIDERS[provider_name], model)
        except openai.OpenAIError as e:
            message = next(
                (msg for exc_type, msg in API_ERROR_MESSAGES.items() if isinstance(e, exc_type)),
                "Помилка запиту до LLM. Спробуй ще раз.",
            )
            raise gr.Error(message) from e
        return agent.transcript, "", agent

    def switch_provider(provider_name: str):
        provider = PROVIDERS[provider_name]
        return (
            gr.Dropdown(choices=list(provider.models), value=provider.models[0]),
            gr.Textbox(value="", placeholder=provider.key_placeholder),
        )

    def reset():
        return [{"role": "assistant", "content": GREETING}], "", None

    with gr.Blocks(title="НМТ-екзаменатор") as demo:
        gr.Markdown(DESCRIPTION)
        with gr.Row():
            provider = gr.Dropdown(list(PROVIDERS), value=DEFAULT_PROVIDER.name, label="Провайдер")
            api_key = gr.Textbox(label="Ключ API", type="password", placeholder=DEFAULT_PROVIDER.key_placeholder)
            model = gr.Dropdown(list(DEFAULT_PROVIDER.models), value=DEFAULT_PROVIDER.models[0], label="Модель")
        chatbot = gr.Chatbot(
            value=[{"role": "assistant", "content": GREETING}],
            label="Іспит",
            height=480,
            buttons=["copy"],
        )
        with gr.Row():
            message = gr.Textbox(
                placeholder="Твоя відповідь…",
                show_label=False,
                scale=5,
                autofocus=True,
            )
            send = gr.Button("Надіслати", variant="primary", scale=1)
        gr.Examples(EXAMPLES, inputs=message, label="Почати з прикладу")
        new_exam = gr.Button("Почати заново")
        agent_state = gr.State(None)

        inputs = [message, api_key, provider, model, agent_state]
        outputs = [chatbot, message, agent_state]
        send.click(chat, inputs=inputs, outputs=outputs)
        message.submit(chat, inputs=inputs, outputs=outputs)
        provider.change(switch_provider, inputs=provider, outputs=[model, api_key])
        new_exam.click(reset, outputs=outputs)
        chatbot.clear(reset, outputs=outputs)

    return demo


settings = Settings.from_env()
demo = build_demo(settings, QuestionBank.from_file(settings.data_path), ResultStore(settings.results_dir))

if __name__ == "__main__":
    demo.launch()
