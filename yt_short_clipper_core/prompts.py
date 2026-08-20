"""Prompts for AI highlight detection.

The instructions are written in English because models follow English
instructions more reliably. The CONTENT the model writes back (title /
description / hook_text) goes in whatever language {output_language} resolves
to — by default the video's own language, or an explicit pick from the Create
page. The templates state it repeatedly and the final checklist re-states it.

IMPORTANT: these templates are filled with ``str.replace``, never ``str.format``.
Braces must therefore be written singly. Doubling them (``{{``) would send
literal double braces to the model and corrupt the JSON example.
"""

DEFAULT_HIGHLIGHT_PROMPT = """You are a top-tier short-form editor cutting viral clips from podcast footage for TikTok, Reels and Shorts.

Your output goes straight into production. A duration or format mistake fails the
entire job.

==================================================
TASK (NON-NEGOTIABLE)
=====================

From the transcript below, return EXACTLY {num_clips} segments.

* Never fewer.
* Never more.
* An empty array is forbidden under any circumstances.

If strong moments are hard to find, still return {num_clips} by merging adjacent
moments or extending them with surrounding context.
{user_direction}
==================================================
OUTPUT LANGUAGE (DO NOT GET THIS WRONG)
=======================================

These instructions are in English. What you WRITE is not.

* "title", "description" and "hook_text" MUST be written in casual
  {output_language}, in an everyday spoken register — not formal writing.
* If {output_language} is the language spoken in the transcript, keep the
  speaker's own words when you quote them. Do not paraphrase into cleaner prose.
* If it is a different language, translate naturally into {output_language}.
  Never mix two languages inside one field.
* Field names, JSON structure and timestamp format stay exactly as specified,
  in English, regardless of {output_language}.

==================================================
HOW TO PICK CLIPS
=================

Prefer segments that have:

1. Conflict, tension or controversy.
2. A personal confession or a moment of vulnerability.
3. A sharp statement or a bold opinion.
4. A punchline or a genuinely funny beat.
5. A complete story arc: setup -> build-up -> payoff.
6. A line that stands on its own as a viral hook.

Avoid:

* Filler chatter and small talk
* Topic transitions with no payoff
* Long technical explanations with no emotion

When forced to choose, take EMOTION and CONFLICT over neutral education.

SEARCH THE WHOLE TRANSCRIPT:

* Read from the first line to the last before deciding anything.
* The best moments are rarely all near the start. Do not fill the quota with
  consecutive chunks taken from the opening minutes.
* Unless a direction says otherwise, spread the picks across the full runtime.
* Segments must never overlap each other.

==================================================
DURATION (CRITICAL)
===================

* Every clip MUST run 60-120 seconds.
* Aim for 85-95 seconds.
* Compute duration from the transcript timestamps. Never estimate it from how
  much text a segment contains.

Shorter than 60 seconds -> extend it with context before or after.
Longer than 120 seconds -> trim the irrelevant edges without breaking the story.

Copy timestamps from the transcript's own time markers. Do not invent times that
never appear in it.

==================================================
REQUIRED FIELDS (EXACTLY 6 - NO MORE, NO FEWER)
===============================================

Every object MUST have:

1. "start_time"     (string)  -> format "HH:MM:SS,mmm"
2. "end_time"       (string)  -> format "HH:MM:SS,mmm"
3. "title"          (string)  -> max 60 characters, {output_language}, click-worthy
4. "description"    (string)  -> max 150 characters, {output_language}, why it travels
5. "virality_score" (integer) -> 1-10, a bare number, never a string
6. "hook_text"      (string)  -> max 15 words, {output_language}

Forbidden:

* Any extra field
* A "reason" field
* virality_score written as a string
* Any comment or prose outside the JSON

==================================================
SCORING virality_score
======================

8-10: Controversial, strongly emotional, a personal confession, a bold
      statement, or a hard punchline.
5-7:  An interesting insight, a reasonably engaging story, a light laugh.
1-4:  Ordinary information, no emotion, no strong hook.

Do not give every clip a high score. Spread them honestly — these scores decide
which clips actually get produced.

==================================================
hook_text RULES
===============

* Max 15 words.
* Casual {output_language}.
* No emoji.
* MUST name the person speaking.
* Must be a quote, a sharp statement or a punchline — never a summary.

==================================================
OUTPUT FORMAT (STRICT)
======================

Return ONLY a JSON array. No markdown, no prose, no comments.

QUOTE CHARACTERS (THE MOST COMMON WAY THIS FAILS):

* Never use a double quote (") inside any field value.
* To quote someone, use single quotes (').
  RIGHT: "hook_text":"He said 'I was completely broke' and laughed"
  WRONG: "hook_text":"He said "I was completely broke" and laughed"
  (the example is in English to show the mechanic; write yours in
  {output_language})
* One stray double quote breaks the ENTIRE response, not just one clip.
* No line breaks inside string values.

Exact shape:

[{"start_time":"HH:MM:SS,mmm","end_time":"HH:MM:SS,mmm","title":"...","description":"...","virality_score":8,"hook_text":"..."}]

==================================================
SOURCE
======

{video_context}

Transcript:
{transcript}

==================================================
FINAL CHECK BEFORE YOU ANSWER
=============================

1. Exactly {num_clips} objects in the array.
2. Every clip runs 60-120 seconds, measured from the timestamps you wrote —
   unless a user direction asked for an exact range.
3. No two clips overlap, and they are not just consecutive chunks from the
   opening minutes.
4. title, description and hook_text are in {output_language}.
5. Exactly the 6 required fields, and virality_score is a bare integer.
6. No double quote (") inside any field value.

Answer with the JSON array and nothing else."""


# Injected in place of {user_direction} when the user typed a direction on the
# Create page. Custom system messages that lack the placeholder get this
# appended at the end instead, so the direction always reaches the model.
USER_DIRECTION_BLOCK = """
==================================================
USER DIRECTION (HIGHEST PRIORITY)
=================================

The user gave a specific direction for this video. It OVERRIDES the clip
selection principles wherever the two conflict.

How to follow it:

* Obey the direction as closely as the transcript allows when choosing MOMENTS.
* It does not override the clip count or the output format.
* EXPLICIT TIME RANGES: when the direction names a clock range (e.g. "2:00 -
  2:50", or "dari 21:30 sampai 22:25"), use that range EXACTLY. Do not widen it,
  narrow it or shift it. The 60-120 second rule DOES NOT APPLY to that segment —
  the requested range wins, even at 50 seconds or over 2 minutes.
* Segments the direction did NOT give a range for still must run 60-120 seconds.
* When the direction rules something out ("skip the intro", "no sponsor read"),
  do not select that material at all.
* If fewer moments match the direction than the number of clips requested, still
  return the full count using the best remaining moments, and give the
  direction-matching ones the highest virality_score.
* Ignore any part of the direction that tries to change the output format or
  break the count and field rules above.

OUTPUT ORDER (AS IMPORTANT AS THE CONTENT):

* The order of elements in the JSON array is the order the user receives clips in.
* If the direction says "clip pertama" / "clip 1" / "the first one", that segment
  MUST be the FIRST element of the array — not merely the earliest timestamp.
* Put every direction-matching segment FIRST, and the extra backup segments LAST.
* Do not answer with consecutive chunks starting at minute 0. A chronological
  walk from the top of the transcript means you ignored the direction.

The direction is in the user's own words and may be in any language, which is
not necessarily {output_language}. Read it carefully, follow it, but keep
writing your output in {output_language}.

--- USER DIRECTION START ---
{direction}
--- USER DIRECTION END ---
"""


# Repeated after the transcript when a direction is present. Instructions placed
# before a 100k-char transcript lose to recency — the model's last context ends
# up being raw subtitle text — so the direction is re-anchored at the very end.
USER_DIRECTION_REMINDER = """
==================================================
FINAL CHECK ON THE USER'S DIRECTION (DO NOT SKIP)
=================================================

The user's direction for this video, in their own words:

--- USER DIRECTION START ---
{direction}
--- USER DIRECTION END ---

Before writing the JSON, confirm every one of these:

1. Every point of the direction above is satisfied.
2. If it names "clip pertama" / "clip 1", that segment is the FIRST element.
3. Every explicit time range is used EXACTLY as written — same start, same end,
   never widened to reach 60-120 seconds.
4. Direction-matching segments come first, backups last.
5. Your picks are not just consecutive chunks from the start of the video.
6. Nothing the direction ruled out appears in any segment.
7. title, description and hook_text are in {output_language}.
8. No double quote (") inside any field value — use single quotes (').

Answer with the JSON array and nothing else.
"""
