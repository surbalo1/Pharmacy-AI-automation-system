"""
integrations/openai_client.py - openai wrapper
handles api calls with retry logic
"""

from openai import AsyncOpenAI
from typing import List, Dict
import asyncio

from config import settings


# init client
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def get_completion(messages: List[Dict[str, str]], 
                         model: str = "gpt-4o-mini",
                         temperature: float = 0.7,
                         max_tokens: int = 500) -> str:
    """
    get a completion from openai
    
    args:
        messages: list of message dicts with role and content
        model: which model to use
        temperature: creativity level
        max_tokens: response limit
    
    returns:
        the ai response text
    """
    # mock mode for testing
    if settings.MOCK_MODE:
        user_msg = messages[-1].get("content", "") if messages else ""
        return f"[MOCK] Received: {user_msg[:50]}... I understand your question and would help with that."
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        # log error and retry once
        print(f"openai error: {e}")
        await asyncio.sleep(1)
        
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e2:
            return f"Error: could not get AI response - {str(e2)}"


async def get_embedding(text: str) -> List[float]:
    """get embedding vector for text"""
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def sync_completion(messages: List[Dict[str, str]], **kwargs) -> str:
    """sync version for non-async contexts"""
    import asyncio
    return asyncio.run(get_completion(messages, **kwargs))
