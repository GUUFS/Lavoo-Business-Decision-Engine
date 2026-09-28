import os
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('C:/Users/Owner/dev/projects/Lavoo-Business-Decision-Engine/.env.local')

from api.routes.support.ai_support import _generate_humanized_support_reply

print('Testing _generate_humanized_support_reply with NVIDIA NIM...')
reply = _generate_humanized_support_reply(
    user_name='Alex',
    user_email='alex@example.com',
    category='billing',
    issue_text='How do I upgrade to Pro plan to get unlimited deep idea evaluations?',
    ticket_id=101,
    conversation_history=None
)

print('--- CUSTOMER SERVICE AI REPLY ---')
print(reply)
