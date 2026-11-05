import sys
sys.path.insert(0, '.')
from api.routes.community.community import _validate_angle_data

data = {
  "respond": True,
  "reasoning": "Real decision: how to allocate limited founder time to reach 25 paying B2B clients before runway ends.",
  "obvious_answer": "Split your time between both or lean on outbound since you need revenue fast.",
  "angle_type": "reframe",
  "angle": "The question treats the two as alternatives, yet both still require you to know exactly which 25 businesses have the problem your software solves. Outbound forces those conversations now. Content waits for strangers to self-identify later.\n\nWith four months left, the daily choice is simple: spend the next two weeks on direct outreach until you have either five signed clients or clear proof the offer does not land. That data decides whether content is even worth writing.",
  "test": "How many of those 25 businesses have you already spoken with this month?"
}

valid, err, cleaned = _validate_angle_data(
    data=data,
    recent_raw_openings=[],
    thread_replies_str="",
    post_type="questions",
    post_title="How do you choose between direct outbound sales vs inbound content when bootstrapping?",
    post_content="We have roughly 4 months of runway left and need our first 25 paying business clients."
)

print(f"Valid: {valid}")
print(f"Error: {err}")
