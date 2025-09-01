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
    },
}


def get_translations(lang: str) -> dict:
    return translations.get(lang, translations["cz"])
