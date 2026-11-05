# Voo: Developer Spec

This covers everything that happens in code around Voo's two prompts. The prompts only work as well as the pipeline around them.

**Replace any earlier Voo prompts completely.** Do not merge these with older versions. Old instructions such as "Socratic Provocateur", "before writing a line of code" or "Beat 1 / Beat 2 / Beat 3" must not appear anywhere.

---

## 1. Files

| File | Used for |
|---|---|
| `voo_summary_system_prompt.txt` | Voo's Summary, system message. Static. |
| `voo_summary_user_prompt.txt` | Voo's Summary, user message. Filled per post. |
| `voo_angle_system_prompt.txt` | Voo's Angle, system message. Static. Contains the Lavoo glossary. |
| `voo_angle_user_prompt.txt` | Voo's Angle, user message. Filled per post. Contains Voo's memory. |

**Rules:**

- Send the system prompt files exactly as written. Do not edit, shorten or add to them in code.
- Everything that changes per post goes in the user prompt only.
- Turn on **prompt caching** for both system prompts. They are identical on every call, so caching makes the long glossary and examples cheap.
- When the glossary needs updating, edit `voo_angle_system_prompt.txt` and redeploy. Nothing else needs to change.

---

## 2. Model settings

| Setting | Voo's Summary | Voo's Angle |
|---|---|---|
| Model | A fast, low-cost model is fine | The strongest model available |
| Temperature | 0.2 | 0.7 |
| Max output tokens | 300 | 1,000 |
| Output | JSON mode / structured output | JSON mode / structured output |
| Extended thinking | Off | On, if the model supports it |

---

## 3. Voo's Summary

### When to run

- On every new Build Room post, as soon as it is published.
- **Skip the call** if title plus content is under 25 words. Show no summary box.
- Regenerate only if the author edits the post.

### Variables

| Variable | Value |
|---|---|
| `{author_name}` | The author's current display name |
| `{post_title}` | Post title |
| `{post_content}` | Post content, trimmed to about 1,500 words |

### Checking the response

1. Parse the JSON. If it fails, retry once. If it fails again, show no summary and log it.
2. If `skip` is true or `takeaways` is empty, show no summary box.
3. `takeaways` must have 1 to 3 items, each under 30 words. If not, retry once. If it still fails, show no summary and log it.
4. Clean dashes (see section 6).
5. Render each item as a bullet in the Voo's Summary box.

A missing summary is acceptable. A wrong summary is not.

---

## 4. Voo's Angle

### When to run

**Every post that asks a question gets Voo's Angle.** Business or not, long or short, whatever topic it was filed under.

**Decide this from the text, never from the topic or post type.** Members put questions under "Shared Wins", "Business Strategy" and other topics.

Treat a post as a question if **any** of these are true:

1. The title or content contains a question mark.
2. The title or content starts with a question word: how, what, why, when, where, who, which, should, can, could, would, will, is, are, do, does, did, any, anyone, has, have, abeg.
3. The classifier below returns YES.

Always run Voo's Angle on Platform Polls.

**Question classifier** (use the Summary model, temperature 0):

System message:
```
You decide whether a community post is asking a question. Answer YES if the post asks for an answer, opinion, advice, recommendation or help, even without a question mark. Otherwise answer NO. Reply with YES or NO only.
```
User message:
```
Title: {post_title}
Content: {post_content}
```

Other rules:

- **No minimum length.** "how does this work?" gets a reply.
- **No delay.** Run as soon as the post is published.
- **One Angle per question.** Regenerate only if the author substantially edits the post or explicitly asks.
- **Run a moderation check first.** Skip only spam, scams, abuse and harmful requests.

### Variables

| Variable | Value |
|---|---|
| `{author_handle}` | The author's **current** handle, read live from their profile, e.g. `@TimelessWealth`. Never a stored or old handle. |
| `{author_role}` | `member` or `lavoo_team`. All Lavoo staff accounts must be flagged `lavoo_team`. |
| `{author_context}` | Only details the member wrote in their public profile: business type, industry, country. **Never** infer or add a stage such as "pre-revenue" or "startup". Never include private Check-up or Mission data. Send `None` if empty. |
| `{post_type}` | `Question`, `Platform Poll` or `Post` |
| `{post_topic}` | The topic tag, e.g. `Shared Wins`. Context only. |
| `{post_title}` | Post title |
| `{post_content}` | Post content, trimmed to about 1,500 words |
| `{thread_replies}` | Up to the last 10 human replies, oldest first, one per line as `@handle: reply text`, each trimmed to about 80 words. Exclude Voo's own replies. Send `None` if there are none. |
| `{community_context}` | Optional. Titles of up to 3 similar Resolved questions. Send `None` if nothing is genuinely relevant. |
| `{recent_openings}` | See section 5 |
| `{recent_tests}` | See section 5 |
| `{recent_angle_types}` | See section 5 |

---

## 5. Voo's memory

Voo has no memory between calls. Without this, it repeats the same openings and test patterns until members notice it is a template.

### Table: `voo_angle_log`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | |
| `post_id` | uuid | The question Voo answered |
| `created_at` | timestamp | |
| `opening` | text | First sentence of `angle`, cut to the first 12 words |
| `test` | text | The full `test` field |
| `angle_type` | text | The lens Voo chose |
| `reasoning` | text | For debugging only. Never shown to members. |
| `obvious_answer` | text | For debugging only |
| `model` | text | Model name and version |
| `attempts` | int | How many calls it took |
| `warnings` | text | Any check that failed but was posted anyway |

Save one row **after** each Angle is posted. **Do not save `care` replies.**

### Before each call

Pull from the **whole Build Room**, not just this member's posts:

```sql
SELECT opening, test, angle_type
FROM voo_angle_log
ORDER BY created_at DESC
LIMIT 10;
```

### Formatting

One item per line in quotes for openings and tests. Comma-separated for lenses. Newest first.

```
{recent_openings}
"Once Chops can buy a Check-up, you have published a price for"
"Referral programmes multiply whatever already exists."

{recent_tests}
"Pick the Chops price first, then ask whether you would be comfortable"
"If ten people will not use it weekly when you onboard them yourself"

{recent_angle_types}
incentives, assumption, reframe
```

If there is no history yet, send `None` for all three.

---

## 6. Checking Voo's Angle before posting

**Never fail silently.** A missing reply looks broken to members. Every check has a fallback that still posts.

1. **Parse the JSON.** It must contain `respond`, `reasoning`, `obvious_answer`, `angle_type`, `angle` and `test`. If it fails, retry up to 2 more times. If all 3 attempts fail, post nothing, log a high-priority error and alert the team. This should be rare.

2. **`respond` is false.** Read `reasoning`. If it names spam, a scam, abuse or a harmful request, post nothing and log it. For any other reason, retry once with this line added to the end of the user message:
   `This post is a genuine question. You must respond.`

3. **Care replies.** If `angle_type` is `care`, skip checks 4 to 6. Post the angle with no Voo Test.

4. **Length.** `angle` between 40 and 120 words. `test` under 30 words. Retry once if outside. If the retry also fails, post it and record a warning.

5. **Repetition.** Compare the first 4 words of `angle` with the stored openings. Retry once on a match. If the retry still matches, post it and record a warning.

6. **Banned phrases.** Case-insensitive search of `angle` and `test` for the list below. Keep the list in a config file so it can grow. Retry once on a match. If the retry still matches, post it and record a warning.

```
be honest with yourself
the real question is
the uncomfortable truth
great question
it's important to
it is important to
at the end of the day
game changer
game-changer
unlock
leverage
dive into
in today's world
this highlights
a testament to
before writing a line of code
```

7. **Clean dashes.** Replace every em dash (—) and en dash (–), with any spaces around it, with a comma followed by one space. Then tidy any double commas or double spaces. **Leave normal hyphens alone** so "Check-up" survives.

8. **Strip extras.** Remove any leading greeting, wrapping quotes or markdown the model added.

Each retry uses a fresh call with the same inputs.

---

## 7. Posting Voo's Angle

Build the visible reply in code:

```
Hey {author_handle}.

{angle}

THE VOO TEST
{test}
```

- `{author_handle}` is read live from the profile at posting time.
- `angle` may contain `\n\n`. Render it as a paragraph break.
- Render the Voo Test as the highlighted block with the Lavoo orange accent.
- **If `test` is empty, do not render the Voo Test block at all.**
- Then write the row to `voo_angle_log` (section 5).

---

## 8. Confirming the new prompts are live

Before announcing the update, run these four posts on a test account and check every item.

| Test post | It must |
|---|---|
| Title: "What does it take to be a great business owner?" Content: "How to be good at running a business" | Not mention pre-revenue, startups, paying customers or building a product. No "is not X, it is Y" sentence. |
| Title: "how does this work?" Content: "how does this work?" | Reply, and say how it read the question. |
| Title: "Nigerian jollof or Ghanaian jollof?" Content: "Settle this." | Reply, without forcing a business lesson. |
| Any question posted under the Shared Wins topic | Reply. |

Also confirm:

- [ ] The greeting uses the **current** handle (e.g. `@TimelessWealth`), not an old one.
- [ ] Logged raw responses contain `obvious_answer` and `reasoning`. If these fields are missing, the old prompt is still running.
- [ ] The system prompt sent to the model contains the line "Write the obvious answer". Check this by logging the exact request once.
- [ ] `voo_angle_log` is filling up and the memory fields appear in the next request.
- [ ] Prompt caching is on for both system prompts.

---

## 9. Ongoing quality

- **Test set.** Keep 20 real Build Room questions, including the four above. Run every prompt change against all 20 and read the results side by side before shipping.
- **Weekly review.** Read 10 random Angles. Look for repeated openings, one lens dominating, invented facts, assumptions about the member's stage, and anything salesy about Lavoo.
- **Warnings.** Review rows where `warnings` is not empty. If one check fails often, the prompt needs adjusting.
- **Resolved signal.** Angles marked Resolved earn Chops. If accepted Angles start drifting towards flattering the person asking, flag it.
- **Best of file.** Save genuinely brilliant real Angles. Every few months, swap the best ones into the system prompt examples in place of the invented ones.
