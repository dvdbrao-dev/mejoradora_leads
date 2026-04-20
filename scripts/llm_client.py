# llm_client.py — Router de modelos por tier
# NVIDIA NIM (barato) para volumen, OpenAI para calidad maxima

import os
from openai import OpenAI

NVIDIA_BASE_URL = 'https://integrate.api.nvidia.com/v1'
NVIDIA_MODEL = "z-ai/glm4.7"
OPENAI_MODEL = 'gpt-4o-mini'

def get_client(tier='standard'):
    '''
    tier=premium  -> OpenAI gpt-4o-mini (Manolo Tier A y B)
    tier=standard -> NVIDIA NIM (Paco, Manolo Tier C, Auditor)
    '''
    if tier == 'premium':
        return OpenAI(api_key=os.environ.get('OPENAI_API_KEY', 'tu api aqui perro')), OPENAI_MODEL
    else:
        nvidia_key = os.environ.get('NVIDIA_API_KEY', 'tu api aqui perro')
        if nvidia_key and nvidia_key != 'tu api aqui perro':
            return OpenAI(api_key=nvidia_key, base_url=NVIDIA_BASE_URL), NVIDIA_MODEL
        else:
            # Fallback a OpenAI si no hay key NVIDIA
            return OpenAI(api_key=os.environ.get('OPENAI_API_KEY', 'tu api aqui perro')), OPENAI_MODEL

def call_llm(prompt, tier='standard', system=None, max_tokens=1000):
    '''
    Llamada unificada al LLM segun tier.
    Devuelve el texto de la respuesta.
    '''
    client, model = get_client(tier)
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def get_tier_for_agent(agent_name, lead_tier='B'):
    '''
    Decide que tier de modelo usar segun agente y tier del lead.
    '''
    if agent_name == 'manolo' and lead_tier in ('A', 'B'):
        return 'premium'
    return 'standard'
