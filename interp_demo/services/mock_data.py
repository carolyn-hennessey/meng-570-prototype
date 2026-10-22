"""Deterministic demo phrases used by mock STT and mock translation.

These let the end-to-end flow run offline. Every mock output is labeled in the UI.
"""

from __future__ import annotations

# Each entry is one utterance in several languages. Staff and patient lines alternate.
STAFF_PHRASES: list[dict[str, str]] = [
    {
        "en": "Hello, I am your nurse today. What brings you in?",
        "es": "Hola, hoy soy su enfermera. ¿Qué le trae por aquí?",
        "zh": "您好，我是您今天的护士。您今天为什么来就诊？",
        "vi": "Xin chào, tôi là y tá của bạn hôm nay. Bạn đến khám vì lý do gì?",
        "ar": "مرحبًا، أنا ممرضتك اليوم. ما سبب زيارتك؟",
        "fr": "Bonjour, je suis votre infirmière aujourd'hui. Qu'est-ce qui vous amène ?",
        "pt": "Olá, hoje sou sua enfermeira. O que o traz aqui?",
        "ko": "안녕하세요, 오늘 담당 간호사입니다. 어떤 일로 오셨나요?",
        "ru": "Здравствуйте, сегодня я ваша медсестра. Что вас беспокоит?",
    },
    {
        "en": "Can you show me where it hurts?",
        "es": "¿Puede mostrarme dónde le duele?",
        "zh": "您能指给我看哪里疼吗？",
        "vi": "Bạn có thể chỉ cho tôi chỗ nào đau không?",
        "ar": "هل يمكنك أن تريني أين يؤلمك؟",
        "fr": "Pouvez-vous me montrer où vous avez mal ?",
        "pt": "Pode me mostrar onde dói?",
        "ko": "어디가 아픈지 보여 주시겠어요?",
        "ru": "Покажите, пожалуйста, где болит?",
    },
    {
        "en": "Thank you. The doctor will see you soon.",
        "es": "Gracias. El médico le atenderá pronto.",
        "zh": "谢谢。医生很快就会来看您。",
        "vi": "Cảm ơn bạn. Bác sĩ sẽ khám cho bạn sớm.",
        "ar": "شكرًا لك. سيراك الطبيب قريبًا.",
        "fr": "Merci. Le médecin va vous voir bientôt.",
        "pt": "Obrigada. O médico vai atendê-lo em breve.",
        "ko": "감사합니다. 곧 의사 선생님이 진료하실 거예요.",
        "ru": "Спасибо. Врач скоро вас примет.",
    },
]

PATIENT_PHRASES: list[dict[str, str]] = [
    {
        "en": "My stomach has hurt since yesterday.",
        "es": "Me duele el estómago desde ayer.",
        "zh": "我从昨天开始肚子疼。",
        "vi": "Tôi bị đau bụng từ hôm qua.",
        "ar": "معدتي تؤلمني منذ الأمس.",
        "fr": "J'ai mal au ventre depuis hier.",
        "pt": "Estou com dor de estômago desde ontem.",
        "ko": "어제부터 배가 아파요.",
        "ru": "У меня болит живот со вчерашнего дня.",
    },
    {
        "en": "Here, on the right side.",
        "es": "Aquí, en el lado derecho.",
        "zh": "这里，右边。",
        "vi": "Ở đây, bên phải.",
        "ar": "هنا، على الجانب الأيمن.",
        "fr": "Ici, du côté droit.",
        "pt": "Aqui, do lado direito.",
        "ko": "여기, 오른쪽이요.",
        "ru": "Вот здесь, справа.",
    },
    {
        "en": "Thank you. Can my daughter stay with me?",
        "es": "Gracias. ¿Puede quedarse mi hija conmigo?",
        "zh": "谢谢。我女儿可以陪着我吗？",
        "vi": "Cảm ơn. Con gái tôi có thể ở lại với tôi không?",
        "ar": "شكرًا. هل يمكن لابنتي أن تبقى معي؟",
        "fr": "Merci. Ma fille peut-elle rester avec moi ?",
        "pt": "Obrigado. Minha filha pode ficar comigo?",
        "ko": "감사합니다. 딸이 같이 있어도 되나요?",
        "ru": "Спасибо. Можно моей дочери остаться со мной?",
    },
]


def sample_utterance(speaker: str, language: str, index: int) -> str | None:
    phrases = STAFF_PHRASES if speaker == "staff" else PATIENT_PHRASES
    return phrases[index % len(phrases)].get(language)


def lookup_translation(text: str, source_language: str, target_language: str) -> str | None:
    needle = text.strip()
    for entry in STAFF_PHRASES + PATIENT_PHRASES:
        if entry.get(source_language) == needle:
            return entry.get(target_language)
    return None
