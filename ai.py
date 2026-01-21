import os
import json
from typing import Dict, Any
from openai import OpenAI



def ask_model(
    prompt: str,
    task: str,
    student_answer: str) -> Dict[str, Any]:

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "system", "content": f"Task: {task}"},
            {"role": "user", "content": student_answer},
        ],
        response_format={
            'type': 'json_object'
        },
        max_tokens=8192,
        temperature=1.3,
        stream=False,
    )

    log_token_usage(response)

    return parse_response(response)

def log_token_usage(response):
    if response.usage:
        usage = response.usage
        pt = usage.prompt_tokens
        ct = usage.completion_tokens
        tt = usage.total_tokens
        print(f"API usage: prompt_tokens={pt}, completion_tokens={ct}, total_tokens={tt}")
        if usage.prompt_tokens_details and usage.prompt_tokens_details.cached_tokens:
            ch = usage.prompt_tokens_details.cached_tokens
            print(f"Cache ratio: {ch * 100 / pt:.2f}")

def parse_response(response):
    content = response.choices[0].message.content
    if content is None:
        raise Exception("Model returned nothing")

    data = json.loads(content)

    # Minimal validation and conversion; allow exceptions to propagate if keys are missing or types are wrong
    grade = float(data["grade"])  # may raise KeyError/ValueError
    comment = str(data.get("comment", ""))
    return {"grade": grade, "comment": comment}


if __name__ == "__main__":
    example_prompt = "Grade student answer using provided criteria. Return json only. Example outout: {grade: 0.7, comment: 'Unclrea explanation'}"
    example_task = "1) Explan how to vibe code (1 point): Student mentions coursor (0.5 points), Stunent mentions copilot (0.5 points)"
    example_student_answer = "1) You install cursor and then prompt it to get code"

    print(ask_model(example_prompt, example_task, example_student_answer))
