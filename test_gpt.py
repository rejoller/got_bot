
from config import gpt_token
import logging
import os
import asyncio
from openai import AsyncOpenAI

from icecream import ic


async def query_gpt4(prompt, user_id, context_data, client):
    thread_id = context_data.get('thread_id')
    print(f'thread_id: {thread_id}')
    ic()
    try:
        # Используем thread.completions.create для отправки в контексте потока
        chat_completion = await client.threads.completions.create(
            thread_id=thread_id.id,
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = chat_completion.choices[0].message.content
        tokens_used = chat_completion.usage.total_tokens
        return answer, tokens_used
    except Exception as e:
        logging.error(f"Error querying GPT-4: {str(e)}")
        return "Sorry, I encountered an error.", 0






