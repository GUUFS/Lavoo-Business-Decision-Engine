import os
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('C:/Users/Owner/dev/projects/Lavoo-Business-Decision-Engine/.env.local')

from api.routes.community.community import _generate_voo_answer_message, _generate_grok_takeaways

print('Testing _generate_voo_answer_message with NVIDIA...')
answer = _generate_voo_answer_message(
    author_handle='Kingsley',
    question_title='How do I validate my B2B SaaS before building features?',
    question_content='I want to talk to 15 business owners before writing code.',
    contributors=[],
    replies_text=''
)
print('--- VOO ANSWER OUTPUT ---')
print(answer)

print('\nTesting _generate_grok_takeaways with NVIDIA...')
takeaways = _generate_grok_takeaways(
    title='Why we switched from freemium to a 14-day free trial',
    content='We noticed that 90% of freemium users never engaged with paid features. Switching to a free trial increased conversion by 35%.'
)
print('--- TAKEAWAYS OUTPUT ---')
print(takeaways)
