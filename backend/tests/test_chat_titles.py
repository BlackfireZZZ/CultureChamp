from app.application.chat_titles import first_turn_title


def test_image_template_title_uses_filled_subject() -> None:
    prompt = (
        "Составь готовый промпт для генерации изображения русского костюма "
        "по теме традиционная одежда. Опиши композицию."
    )
    assert first_turn_title(prompt, "UC-03") == (
        "Изображение: русского костюма · традиционная одежда"
    )


def test_unfilled_image_template_gets_useful_title() -> None:
    prompt = (
        "Составь готовый промпт для генерации изображения [предмета или сцены] "
        "по материалам о [теме]."
    )
    assert first_turn_title(prompt, "UC-03") == "Промпт для изображения"


def test_partly_filled_image_template_uses_the_changed_topic() -> None:
    prompt = (
        "Составь готовый промпт для генерации изображения [предмета или сцены] "
        "по теме костюм центральной России."
    )
    assert first_turn_title(prompt, "UC-03") == "Изображение: костюм центральной России"


def test_regular_task_still_uses_first_line() -> None:
    assert first_turn_title("Расскажи о вышивке\nПодробнее", None) == "Расскажи о вышивке"
