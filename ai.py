import os
import json
from typing import Dict, Any
from openai import OpenAI



def ask_model(
    task: str,
    model_answer: str,
    student_answer: str) -> Dict[str, Any]:

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    prompt = """
     Ты — автоматический ассессор. Ты получаешь три текста: `task` (один или несколько пронумерованных вопросов; у каждого вопроса может быть указано количество баллов), `model_answer` (эталонные ответы, пронумерованные) и `student_answer`.

     Инструкция (простая и универсальная):
     1) Разбери `task` на отдельные пронумерованные вопросы и извлеки баллы для каждого вопроса.
     2) Для каждой пронумерованной позиции i:
         a) Найди в `model_answer` соответствующую пронумерованную часть и выдели 1–4 ключевых пунктов, которые составляют правильный ответ для этого вопроса.
         b) Проверь `student_answer` на наличие эквивалентных идей для каждого ключевого пункта. Будь лоялен к перефразированию и синонимам; если идея явно есть — считай пункт найденным.
         c) Вычисли долю найденных пунктов и умножь на максимальные баллы вопроса → полученные баллы для этого вопроса. Округли до 2 знаков.
         c) Вычисли долю найденных пунктов и умножь на максимальные баллы вопроса → полученные баллы для этого вопроса. Округли до 2 знаков.
     3) Суммируй полученные баллы по всем вопросам — это итоговая оценка.

     Выходной формат (строго JSON):
     - Обязательное поле: `grade` — итоговая сумма баллов как строка, например "1" или "2.5".
     - Необязательное поле: `comment` — если какие-то вопросы не получили полный балл, кратко (1–2 предложения) перечисли ключевые отсутствующие идеи для самых важных вопросов.

     Дополнительно:
     - Оцени каждый вопрос независимо: отсутствие/наличие деталей в одном вопросе не влияет на другие.
     - Не добавляй новых фактов; используй только `model_answer` и `student_answer`.
     - Отвечай только JSON и ничего более.

     Примеры:
     {"grade": "3"}
     {"grade": "2.5", "comment": "В вопросе 2 не хватает упоминания механизма r; в вопросе 4 отсутствует восстановление из истории"}
     """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "system", "content": f"Вопросы для студентов и баллы за правильный ответ: {task}"},
            {"role": "system", "content": f"Пример ответа на полный балл: {model_answer}"},
            {"role": "user", "content": student_answer},
        ],
        response_format={
            'type': 'json_object'
        },
        max_tokens=8192,
        temperature=1.3,
        stream=False,
    )

    if response.usage:
        usage = response.usage
        pt = usage.prompt_tokens
        ct = usage.completion_tokens
        tt = usage.total_tokens
        print(f"API usage: prompt_tokens={pt}, completion_tokens={ct}, total_tokens={tt}")
        if usage.prompt_tokens_details and usage.prompt_tokens_details.cached_tokens:
            ch = usage.prompt_tokens_details.cached_tokens
            print(f"Cache ratio: {ch * 100 / pt:.2f}")

    # Parse the model response (SDK might return dict or JSON string).
    content = response.choices[0].message.content
    if content is None:
        raise Exception("Model returned nothing")

    data = json.loads(content)

    # Minimal validation and conversion; allow exceptions to propagate if keys are missing or types are wrong
    grade = float(data["grade"])  # may raise KeyError/ValueError
    comment = str(data.get("comment", ""))

    return {"grade": grade, "comment": comment}


if __name__ == "__main__":
    # quick example when run as a script
    example_task = "1) Приведите пример не из статьи, где был бы полезен протокол из статьи AMOEBA. (1 балл)"
    example_model_answer = "1) Протокол полезен в распределенных базах данных с репликацией. Там важен порядок UPDATE/INSERT. AMOEBA как раз гарантирует эти свойства, т.к. он позволяет одной ноде выдавать уникальные номера транзакциям/записям изменений и рассылать их строго по очереди всем узлам. Похожая идея используется в СУБД гугла Spanner, только там в роли sequencer используется атомные часы и технология TrueTime, а порядок гарантируется с помощью 2-phase commit протокола PAXOS."
    example_student_answer = """1. Единая точка изменений конфигураций/фича-флагов в большой микросервисной системе. Каждое изменение (включить фичу X, поменять лимиты, ротация ключей) должно применяться у всех сервисов в одном и том же порядке, иначе часть трафика пойдёт по старым правилам, часть - по новым. Amoeba дал бы:

    Тотальный порядок всех апдейтов.
    Атомарность при сбоях узлов/сетевых потерь - через подтверждения и accept с параметром r.
"""

    print(ask_model(example_task, example_model_answer, example_student_answer))
