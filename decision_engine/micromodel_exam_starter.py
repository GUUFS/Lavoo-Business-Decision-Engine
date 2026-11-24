"""
A starter set of 30 exam questions for the micromodel's weekly exam
(decision_engine/micromodel_exam.py), added from the admin Micromodel page
with "Add starter questions".

The right answers follow the same rule the LLM uses to decide whether to ask
(AgenticAnalyzer.generate_clarifying_questions):

  - ASK unless the prompt says BOTH what the business sells or does AND at
    least one concrete number, constraint or thing already tried. A request
    to choose between options that aren't named always needs asking.
  - DON'T ASK when both are there, even if more detail would be nice.

15 are "ask" and 15 "don't ask", so the exam tests both mistakes (asking
when it shouldn't and not asking when it should). Some prompts are the ones
the team tested by hand. An admin can remove any question they disagree
with, and add their own.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.pg_models import MicromodelExamQuestion

# (prompt, should ask, the questions it should ask, why)
STARTER_QUESTIONS: list[tuple[str, bool, list[str], str]] = [
    # ── It SHOULD ask: something load-bearing is missing ──
    ("My sales are low", True,
     ["What do you sell, and through which channel (shop, online, marketplace)?",
      "How much were you selling before and how much now, and since when?"],
     "No business, no numbers."),
    ("How do I get more customers?", True,
     ["What does your business sell, and who buys it?",
      "How do customers find you today, and how many do you get a month?"],
     "No business, no numbers."),
    ("I'm a coach. I want more clients", True,
     ["What kind of coaching do you offer, and at what price?",
      "How many clients do you have now, and where did they come from?"],
     "Business named, but no number or anything tried."),
    ("Everything is going wrong with my business. Marketing, cash, staff, product. Where do I start?", True,
     ["What does your business sell?",
      "How much cash do you have against your monthly costs?",
      "Which of these problems is costing you the most money right now?"],
     "No business and no numbers; four problems with no way to rank them."),
    ("I want to start a laundry pickup service for students in Abuja. Should I hire a sales person or run ads?", True,
     ["How much can you spend a month on sales or ads?",
      "How many pickups a week do you need to break even?"],
     "The business is clear, but there's no budget or target to choose between the two."),
    ("I have too many ideas and don't know which one to focus on first", True,
     ["What are the ideas you're choosing between?",
      "How much time or money can you put into one right now?"],
     "A choice between options it hasn't been told."),
    ("Sales dropped and I don't know why", True,
     ["What do you sell, and through which channel?",
      "When did sales start dropping, and did anything change then (price, ads, season, competitors)?"],
     "A symptom with no business, timeframe or numbers."),
    ("Should I raise my prices?", True,
     ["What do you sell, and what do you charge now?",
      "What is your profit margin at the current price?"],
     "No product, no price, no margin."),
    ("My team is not performing", True,
     ["What does your business do, and how many people are on the team?",
      "What should they be achieving that they aren't (targets, deadlines, quality)?"],
     "No business and no measure of performance."),
    ("I want to grow my Instagram page", True,
     ["What do you sell or offer through the page?",
      "How many followers do you have, and does the page bring you sales today?"],
     "No business goal behind the page, no numbers."),
    ("Should I quit my job to go full time on my business?", True,
     ["What does your business do, and how much does it make a month?",
      "How many months of living costs do you have saved?"],
     "A decision that turns on revenue and savings it wasn't given."),
    ("I need funding for my business", True,
     ["What does your business do, and how much does it make a month?",
      "How much do you need, and what exactly will you spend it on?"],
     "No business, amount or use of funds."),
    ("My website gets no sales", True,
     ["What do you sell on the website?",
      "About how many visitors does it get a month, and where do they come from?"],
     "No product and no traffic numbers."),
    ("Help me choose between opening a second branch or selling online", True,
     ["What does your business sell, and how much does your first branch make a month?",
      "How much money do you have for the expansion?"],
     "A choice with no business, revenue or budget."),
    ("My customers don't come back", True,
     ["What do you sell, and how often should a customer need it?",
      "Roughly what share of customers buy a second time?"],
     "No business and no repeat-rate number."),

    # ── It should NOT ask: the business and a concrete number/constraint/attempt are there ──
    ("My restaurant is busy on weekends but empty Monday to Thursday.", False, [],
     "Business named and a concrete pattern (which days are empty): enough to diagnose."),
    ("My Shopify store sells handmade candles, gets about 2,000 visits a month, converts at 0.8%, "
     "and I've already tried dropping prices 20% with no change in conversion.", False, [],
     "Product, channel, traffic, conversion and an attempt."),
    ("I run a bakery in Lagos. Sales dropped 30% in the last two months after a new bakery opened on my street.",
     False, [], "Business, the size and timing of the drop, and a likely cause."),
    ("I run a 6-person digital marketing agency making N4m a month, but two clients make up 70% of revenue "
     "and one just gave notice.", False, [], "Business, revenue, concentration and the trigger."),
    ("I sell skincare on Instagram with 15,000 followers but only get 3-4 orders a week. I've tried giveaways "
     "and they bring followers, not buyers.", False, [], "Product, channel, numbers and an attempt."),
    ("My SaaS for dentists has 40 paying clinics at $99 a month. Churn is 8% a month and most leave in the "
     "first 60 days.", False, [], "Product, customers, price, churn and when it happens."),
    ("I own a car wash in Accra doing 25 cars a day on weekdays and I want 50. I have GHS 5,000 a month "
     "for marketing.", False, [], "Business, current and target volume, and a budget."),
    ("I'm a freelance designer earning $3,000 a month from 5 clients, but I work 70-hour weeks and can't take "
     "on more work.", False, [], "Business, income, client count and the constraint."),
    ("My pharmacy in Kano spends 40% of revenue on stock, and I keep running out of fast-moving drugs while "
     "slow ones expire.", False, [], "Business, a number and a clear operational problem."),
    ("We run a delivery startup with 12 bikes. Deliveries take 3 hours on average and customers complain. "
     "Riders are paid per day, not per delivery.", False, [], "Business, capacity, delivery time and pay model."),
    ("My online course sold 120 copies at launch but only 5 a month since. I've posted on Twitter every day "
     "for 3 months.", False, [], "Product, sales numbers and what's been tried."),
    ("I run a 20-room hotel in Nairobi at 35% occupancy. 80% of bookings come through Booking.com, which "
     "takes 18% commission.", False, [], "Business, occupancy and channel economics."),
    ("My boutique made N2.5m last December but averages N600k in other months, and rent is N400k a month.",
     False, [], "Business, seasonal revenue and fixed costs."),
    ("I'm a real estate agent closing 1 deal a quarter. I get leads from Facebook ads at N5,000 per lead, "
     "but most never answer my calls.", False, [], "Business, deal rate, lead cost and where it breaks."),
    ("Our school has 180 students and room for 300. Fees are N150k a term and parents say we're too expensive "
     "compared with the school nearby.", False, [], "Business, capacity, price and the objection."),
]


def add_starter_questions(db: Session, created_by: int | None = None) -> dict:
    """Add the starter questions that aren't in the exam yet (same prompt,
    ignoring case and spaces, counts as already there, even if removed).
    Returns {"added": n, "skipped": n}."""
    # 1. The prompts already in the exam (active or removed: a removed one
    #    was removed on purpose and isn't added back).
    have = {" ".join(p.lower().split()) for (p,) in db.query(func.coalesce(MicromodelExamQuestion.prompt, "")).all()}
    added = skipped = 0
    # 2. Each starter question not already there.
    for prompt, should_ask, expected, note in STARTER_QUESTIONS:
        if " ".join(prompt.lower().split()) in have:
            skipped += 1
            continue
        db.add(MicromodelExamQuestion(prompt=prompt, should_ask=should_ask, expected_questions=expected if should_ask else [],
                                      note=f"Starter question. {note}", created_by=created_by, active=True))
        added += 1
    # 3. Saved together.
    db.commit()
    return {"added": added, "skipped": skipped}
