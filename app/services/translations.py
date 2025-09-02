translations = {
    "cz": {
        "previous": "Předchozí",
        "next": "Další",
        "save_continue": "Uložit a pokračovat",
        "finish": "Dokončit",
        "original": "Originál",
        "images": "Obrázky",
        "audio_guide": "Audio průvodce",
        "questionnaire": "Dotazník",
        "error": "Chyba",
        "thanks_title": "Děkujeme za návštěvu",
        "thanks_message": "Vaše zpětná vazba je pro nás cenná.",
        "back_to_start": "Zpět na úvod",
    },
    "en": {
        "previous": "Previous",
        "next": "Next",
        "save_continue": "Save and continue",
        "finish": "Finish",
        "original": "Original",
        "images": "Images",
        "audio_guide": "Audio guide",
        "questionnaire": "Questionnaire",
        "error": "Error",
        "thanks_title": "Thank you for visiting",
        "thanks_message": "Your feedback is valuable to us.",
        "back_to_start": "Back to start",
    },
    "ua": {
        "previous": "Попередній",
        "next": "Далі",
        "save_continue": "Зберегти і продовжити",
        "finish": "Завершити",
        "original": "Оригінал",
        "images": "Зображення",
        "audio_guide": "Аудіогід",
        "questionnaire": "Анкета",
        "error": "Помилка",
        "thanks_title": "Дякуємо за візит",
        "thanks_message": "Ваш відгук для нас дуже важливий.",
        "back_to_start": "Повернутись на початок",
    },
}


def get_translations(lang: str) -> dict:
    return translations.get(lang, translations["cz"])
