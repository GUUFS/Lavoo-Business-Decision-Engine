import os
import json
import re
from dotenv import load_dotenv

load_dotenv('C:/Users/Owner/dev/projects/Lavoo-Business-Decision-Engine/.env.local')
from openai import OpenAI

title = 'How we reduced churn by 20% in 30 days'
content = 'We started sending personal video check-ins to all new signups. We also simplified our onboarding from 7 steps to 3 steps.'

api_key = os.getenv('NVIDIA_API_KEY')
client = OpenAI(api_key=api_key, base_url='https://integrate.api.nvidia.com/v1', timeout=20.0)

prompt = (
    f"Analyze this founder post from the Lavoo Build Room:\n\n"
    f"Headline: {title}\n"
    f"Content: {content}\n\n"
    f"Extract EXACTLY 3 concise, highly actionable Decision Takeaways for solo founders.\n"
    f"Format your response as a strict JSON object: {{\"takeaways\": [\"Takeaway 1\", \"Takeaway 2\", \"Takeaway 3\"]}}"
)

resp = client.chat.completions.create(
    model='meta/llama-3.2-11b-vision-instruct',
    messages=[
        {'role': 'system', 'content': 'You are the Lavoo Business Decision Engine AI. Extract 3 actionable decision takeaways for solo founders in strict JSON format.'},
        {'role': 'user', 'content': prompt}
    ],
    temperature=0.3,
    max_tokens=250,
)

raw = resp.choices[0].message.content.strip()
if '```' in raw:
    raw = re.sub(r'^```(?:json)?|```$', '', raw, flags=re.MULTILINE).strip()

print('Takeaways parsed:', json.loads(raw))
