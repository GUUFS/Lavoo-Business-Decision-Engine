# Voo Developer Pack

Everything needed to run Voo's Summary and Voo's Angle in The Build Room.

## Files

| File | What it is |
|---|---|
| `voo_summary_system_prompt.txt` | Voo's Summary system message |
| `voo_summary_user_prompt.txt` | Voo's Summary user message template |
| `voo_angle_system_prompt.txt` | Voo's Angle system message, including the Lavoo glossary |
| `voo_angle_user_prompt.txt` | Voo's Angle user message template, including Voo's memory |
| `voo_code_spec.md` | Everything that happens in code: triggers, variables, memory, checks, posting and testing |

## Setup order

1. **Remove all previous Voo prompts.** Replace them completely. Do not merge.
2. Load the four prompt files exactly as written.
3. Build the pipeline in `voo_code_spec.md`, sections 3 to 7.
4. Create the `voo_angle_log` table (section 5).
5. Run the checks in section 8 on a test account before going live.

## Placeholders

Variables in the user prompt files appear in curly braces, for example `{author_handle}`. Every variable is defined in `voo_code_spec.md`. If a value is empty, send the word `None`. Never leave a placeholder unfilled.

The system prompt files contain no placeholders. Send them unchanged.
