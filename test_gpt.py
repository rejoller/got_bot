
from config import gpt_token

import os
import asyncio
from openai import AsyncOpenAI

async def query_gpt4(prompt, user_id, context_history, client):
    thread_id = context_history.get('thread_id')
    full_prompt = "\n".join(context_history['messages'] + [prompt])

    try:
        chat_completion = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": full_prompt}],
            thread_id=thread_id
        )
        answer = chat_completion.choices[0].message.content
        tokens_used = chat_completion.usage.total_tokens
        return answer, tokens_used
    except Exception as e:
        return str(e), 0
