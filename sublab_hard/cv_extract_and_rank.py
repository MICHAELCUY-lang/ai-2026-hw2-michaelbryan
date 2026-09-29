import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import validate
from openai import OpenAI


# ============================================================
# SETUP
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

MODEL = "gpt-5.6-luna"


# ============================================================
# LOAD RUBRIC
# ============================================================

with open(
    ROOT / "data" / "candidate_rubric.json",
    "r",
    encoding="utf-8",
) as f:
    RUBRIC = json.load(f)


# ============================================================
# STRUCTURED OUTPUT SCHEMA
# ============================================================

CV_SCHEMA = {
    "type": "object",
    "properties": {

        "candidate_id": {
            "type": "string"
        },

        "full_name": {
            "type": ["string", "null"]
        },

        "degree": {
            "type": ["string", "null"]
        },

        "graduation_year": {
            "type": ["integer", "null"]
        },

        "gpa_original": {
            "type": ["number", "null"]
        },

        "gpa_original_scale": {
            "type": ["number", "null"]
        },

        "gpa_4_scale": {
            "type": ["number", "null"]
        },

        "languages": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "published_peer_reviewed_outputs": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "published_peer_reviewed_count": {
            "type": "integer",
            "minimum": 0
        },

        "unpublished_outputs": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "relevant_experience_months": {
            "type": ["integer", "null"]
        },

        "uncountable_experience": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "ambiguities": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "evidence": {
            "type": "object",
            "properties": {

                "full_name": {
                    "type": ["string", "null"]
                },

                "degree": {
                    "type": ["string", "null"]
                },

                "graduation_year": {
                    "type": ["string", "null"]
                },

                "gpa": {
                    "type": ["string", "null"]
                },

                "languages": {
                    "type": ["string", "null"]
                },

                "publications": {
                    "type": ["string", "null"]
                },

                "experience": {
                    "type": ["string", "null"]
                }
            },

            "required": [
                "full_name",
                "degree",
                "graduation_year",
                "gpa",
                "languages",
                "publications",
                "experience"
            ],

            "additionalProperties": False
        },

        "scores": {
            "type": "object",
            "properties": {

                "academic": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5
                },

                "research": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5
                },

                "experience": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5
                }
            },

            "required": [
                "academic",
                "research",
                "experience"
            ],

            "additionalProperties": False
        }
    },

    "required": [
        "candidate_id",
        "full_name",
        "degree",
        "graduation_year",
        "gpa_original",
        "gpa_original_scale",
        "gpa_4_scale",
        "languages",
        "published_peer_reviewed_outputs",
        "published_peer_reviewed_count",
        "unpublished_outputs",
        "relevant_experience_months",
        "uncountable_experience",
        "ambiguities",
        "evidence",
        "scores"
    ],

    "additionalProperties": False
}


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You extract structured scholarship candidate information
from application stories.

You must follow the supplied scholarship rubric exactly.

GENERAL RULES

1. Use ONLY information explicitly stated in the story.

2. Never invent, infer, or estimate missing information.

3. If information is not stated, use null when the schema
   permits null.


GPA RULES

4. Preserve the original numeric GPA and its original scale.

5. Convert GPA to a 4.0 scale when the original GPA and
   scale are explicitly stated.

   Use a linear conversion:

       gpa_4_scale =
       (original GPA / original scale) * 4.0

6. Do not estimate GPA from:
   - degree classification
   - distinction
   - university reputation
   - general academic performance
   - any other indirect description

7. If no numeric GPA is stated:
   - gpa_original = null
   - gpa_original_scale = null
   - gpa_4_scale = null

8. If GPA statements contradict each other:
   - gpa_original = null
   - gpa_original_scale = null
   - gpa_4_scale = null
   - record the contradiction in ambiguities


DEGREE AND GRADUATION RULES

9. Extract degree and graduation year only when explicitly
   supported.

10. If degree status or graduation year contradicts itself,
    do not resolve the contradiction.

    Set the affected field to null and record the
    contradiction in ambiguities.


PUBLICATION RULES

11. Count ONLY peer-reviewed work explicitly described as:
    - published
    - accepted

12. Do NOT count:
    - submitted
    - under review
    - in preparation
    - planned
    - in press

13. Put non-countable research outputs in
    unpublished_outputs.

14. published_peer_reviewed_count must equal the number of
    countable published/accepted peer-reviewed outputs.


EXPERIENCE RULES

15. Count relevant experience in MONTHS, not number of jobs.

16. Overlapping periods count only once.

17. Experience without enough date information to calculate
    months must not be guessed.

18. Put experience that cannot be counted reliably into
    uncountable_experience.


CONTRADICTION RULES

19. Never silently resolve contradictory statements.

20. Never average contradictory values.

21. Set the affected field to null and record the
    contradiction in ambiguities.


EVIDENCE RULES

22. Provide a short verbatim evidence quote from the
    candidate story for every major extracted field.

23. Evidence must come from the story itself.

24. Do not invent evidence.

25. If no supporting quote exists, use null.


SCORING RULES

26. Return ONLY these three model-generated scores:
    - academic
    - research
    - experience

27. Each score must be an integer from 0 to 5.

28. Follow the supplied rubric exactly.

29. IMPORTANT:
    If the story contains NO numeric GPA and the rubric says
    a story with no GPA receives academic score 0, academic
    MUST be 0.

30. Do NOT calculate a weighted total.

31. Do NOT rank candidates.

32. Do NOT select a winner.

The Python program, not you, will calculate weighted totals
and ranking.

Return exactly one JSON object matching the schema.
"""


# ============================================================
# CANDIDATE ID
# ============================================================

def candidate_id_from_filename(filename):

    match = re.search(
        r"(\d+)",
        filename
    )

    if match:
        return f"C-{int(match.group(1)):02d}"

    return filename


# ============================================================
# EXTRACT ONE CANDIDATE
# ============================================================

def extract_candidate(
    candidate_id,
    story,
):

    user_prompt = f"""
CANDIDATE ID:
{candidate_id}

SCHOLARSHIP RUBRIC:
{json.dumps(RUBRIC, ensure_ascii=False, indent=2)}

CANDIDATE STORY:
{story}

Extract the candidate into the required JSON structure.

Important reminders:

- candidate_id must be exactly "{candidate_id}"
- do not invent missing facts
- preserve evidence quotes
- unresolved contradictions must produce null in the
  affected field
- no numeric GPA means academic score 0 when required by
  the rubric
- only published or accepted peer-reviewed outputs count
- submitted, under review, in preparation, planned, and
  in press do not count as published
- calculate countable experience in months
- return only academic, research, and experience scores
- do not calculate weighted total
- do not rank candidates
- do not choose a winner
"""

    response = client.chat.completions.create(
        model=MODEL,

        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "candidate_cv",
                "strict": True,
                "schema": CV_SCHEMA,
            },
        },
    )

    content = response.choices[0].message.content

    result = json.loads(content)

    validate(
        instance=result,
        schema=CV_SCHEMA,
    )

    # Candidate ID is controlled by code.
    if result["candidate_id"] != candidate_id:
        raise ValueError(
            "Model returned incorrect candidate_id: "
            f"{result['candidate_id']} != {candidate_id}"
        )

    # Publication count consistency check.
    expected_count = len(
        result[
            "published_peer_reviewed_outputs"
        ]
    )

    if (
        result["published_peer_reviewed_count"]
        != expected_count
    ):
        raise ValueError(
            "published_peer_reviewed_count does not match "
            "published_peer_reviewed_outputs length"
        )

    return result


# ============================================================
# WEIGHTED TOTAL
# ============================================================

def calculate_total(scores):

    academic_weight = 0.5
    research_weight = 0.3
    experience_weight = 0.2

    total = (
        academic_weight * scores["academic"]
        + research_weight * scores["research"]
        + experience_weight * scores["experience"]
    )

    return round(
        total,
        2
    )


# ============================================================
# NULL FIELD FINDER
# ============================================================

def find_null_fields(cv):

    null_fields = []

    fields = [
        "full_name",
        "degree",
        "graduation_year",
        "gpa_original",
        "gpa_original_scale",
        "gpa_4_scale",
        "relevant_experience_months",
    ]

    for field in fields:

        if cv[field] is None:

            null_fields.append(
                field
            )

    return null_fields


# ============================================================
# TRAP DETECTION
# ============================================================

def detect_traps(cv):

    traps = []

    # Missing GPA
    if (
        cv["gpa_original"] is None
        and cv["gpa_4_scale"] is None
    ):
        traps.append(
            "missing_or_unresolved_GPA"
        )

    # Unpublished research
    if cv["unpublished_outputs"]:
        traps.append(
            "unpublished_output_not_counted"
        )

    # Contradiction / ambiguity
    if cv["ambiguities"]:
        traps.append(
            "contradiction_or_ambiguity"
        )

    # Uncountable experience
    if cv["uncountable_experience"]:
        traps.append(
            "uncountable_experience"
        )

    if not traps:
        traps.append(
            "none"
        )

    return traps


# ============================================================
# LOAD STORIES
# ============================================================

def load_candidates():

    candidate_dir = (
        ROOT
        / "data"
        / "candidates"
    )

    stories = []

    for path in sorted(
        candidate_dir.glob("story-*.md")
    ):

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            story = f.read()

        stories.append(
            {
                "file": path.name,
                "candidate_id":
                    candidate_id_from_filename(
                        path.name
                    ),
                "story": story,
            }
        )

    return stories


# ============================================================
# SEPARATE PROSE WINNER CALL
# ============================================================

def ask_prose_winner(
    candidates,
):

    candidate_text = []

    for item in candidates:

        cv = item["cv"]

        candidate_text.append(
            {
                "candidate_id":
                    cv["candidate_id"],

                "full_name":
                    cv["full_name"],

                "degree":
                    cv["degree"],

                "graduation_year":
                    cv["graduation_year"],

                "gpa_4_scale":
                    cv["gpa_4_scale"],

                "published_peer_reviewed_count":
                    cv[
                        "published_peer_reviewed_count"
                    ],

                "relevant_experience_months":
                    cv[
                        "relevant_experience_months"
                    ],

                "ambiguities":
                    cv["ambiguities"],
            }
        )

    prompt = f"""
The scholarship has one funded place.

Here is the official rubric:

{json.dumps(RUBRIC, ensure_ascii=False, indent=2)}

Here are the structured candidate records:

{json.dumps(candidate_text, ensure_ascii=False, indent=2)}

In prose, say which candidate you think should receive the
funded place and briefly explain why according to the
rubric.

Do this as a separate judgement.

Do not use or refer to the Python weighted totals because
they are intentionally not provided in this prompt.
"""

    response = client.chat.completions.create(
        model=MODEL,

        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return (
        response
        .choices[0]
        .message
        .content
    )


# ============================================================
# MAIN
# ============================================================

def main():

    candidates = load_candidates()

    results = []

    failures = []


    print(
        "=" * 80
    )

    print(
        "SCHOLARSHIP CANDIDATE EXTRACTION"
    )

    print(
        "=" * 80
    )


    # ========================================================
    # EXTRACTION
    # ========================================================

    for candidate in candidates:

        print()

        print(
            f"Processing "
            f"{candidate['file']} "
            f"({candidate['candidate_id']})..."
        )

        try:

            cv = extract_candidate(
                candidate["candidate_id"],
                candidate["story"],
            )

            total = calculate_total(
                cv["scores"]
            )

            null_fields = find_null_fields(
                cv
            )

            traps = detect_traps(
                cv
            )

            result = {
                "file":
                    candidate["file"],

                "cv":
                    cv,

                "weighted_total":
                    total,

                "parsed":
                    True,

                "validated":
                    True,

                "null_fields":
                    null_fields,

                "traps":
                    traps,
            }

            results.append(
                result
            )

            print(
                f"OK | "
                f"{cv['candidate_id']} | "
                f"{cv['full_name']} | "
                f"A={cv['scores']['academic']} | "
                f"R={cv['scores']['research']} | "
                f"E={cv['scores']['experience']} | "
                f"TOTAL={total:.2f}"
            )

        except Exception as exc:

            failures.append(
                {
                    "file":
                        candidate["file"],

                    "candidate_id":
                        candidate[
                            "candidate_id"
                        ],

                    "error":
                        (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                }
            )

            print(
                f"ERROR | "
                f"{type(exc).__name__}: "
                f"{exc}"
            )


    # ========================================================
    # RANK IN PYTHON
    # ========================================================

    ranked = sorted(
        results,

        key=lambda item:
            item["weighted_total"],

        reverse=True,
    )


    # ========================================================
    # PRINT STRUCTURED RECORDS
    # ========================================================

    print()
    print()
    print(
        "=" * 80
    )
    print(
        "STRUCTURED RECORDS FOR SUBMISSION.MD"
    )
    print(
        "=" * 80
    )

    for item in results:

        print()
        print(
            "-" * 80
        )

        print(
            f"{item['cv']['candidate_id']} "
            f"— "
            f"{item['cv']['full_name']}"
        )

        print(
            "-" * 80
        )

        print(
            json.dumps(
                item["cv"],
                ensure_ascii=False,
                indent=2,
            )
        )


    # ========================================================
    # SUBMISSION EXTRACTION TABLE
    # ========================================================

    print()
    print()
    print(
        "=" * 80
    )
    print(
        "SUBMISSION EXTRACTION TABLE"
    )
    print(
        "=" * 80
    )

    print(
        f"{'ID':<8}"
        f"{'Parsed':<10}"
        f"{'Valid':<10}"
        f"{'Null fields':<38}"
        f"{'Traps'}"
    )

    print(
        "-" * 110
    )

    for item in results:

        null_text = (
            ", ".join(
                item["null_fields"]
            )
            if item["null_fields"]
            else "none"
        )

        trap_text = ", ".join(
            item["traps"]
        )

        print(
            f"{item['cv']['candidate_id']:<8}"
            f"{'YES':<10}"
            f"{'YES':<10}"
            f"{null_text:<38}"
            f"{trap_text}"
        )

    for failure in failures:

        print(
            f"{failure['candidate_id']:<8}"
            f"{'NO':<10}"
            f"{'NO':<10}"
            f"{'-':<38}"
            f"{failure['error']}"
        )


    # ========================================================
    # SCORE TABLE
    # ========================================================

    print()
    print()
    print(
        "=" * 80
    )
    print(
        "SCORE TABLE — TOTAL CALCULATED IN PYTHON"
    )
    print(
        "=" * 80
    )

    print(
        f"{'ID':<8}"
        f"{'Candidate':<26}"
        f"{'Academic':<12}"
        f"{'Research':<12}"
        f"{'Experience':<14}"
        f"{'Total':<10}"
    )

    print(
        "-" * 82
    )

    for item in ranked:

        cv = item["cv"]

        print(
            f"{cv['candidate_id']:<8}"
            f"{str(cv['full_name']):<26}"
            f"{cv['scores']['academic']:<12}"
            f"{cv['scores']['research']:<12}"
            f"{cv['scores']['experience']:<14}"
            f"{item['weighted_total']:<10.2f}"
        )


    # ========================================================
    # CODE-COMPUTED WINNER
    # ========================================================

    print()
    print(
        "=" * 80
    )
    print(
        "CODE-COMPUTED WINNER"
    )
    print(
        "=" * 80
    )

    if ranked:

        winner = ranked[0]

        print(
            f"{winner['cv']['candidate_id']} — "
            f"{winner['cv']['full_name']}"
        )

        print(
            f"Weighted total: "
            f"{winner['weighted_total']:.2f}"
        )

    else:

        print(
            "No valid candidates."
        )


    # ========================================================
    # SEPARATE MODEL PROSE CALL
    # ========================================================

    print()
    print(
        "=" * 80
    )
    print(
        "SEPARATE MODEL PROSE WINNER ANSWER"
    )
    print(
        "=" * 80
    )

    if results:

        try:

            prose_answer = ask_prose_winner(
                results
            )

            print(
                prose_answer
            )

        except Exception as exc:

            print(
                f"ERROR: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    else:

        print(
            "No valid candidate records "
            "available for prose call."
        )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print(
        "=" * 80
    )
    print(
        "FINAL SUMMARY FOR SUBMISSION.MD"
    )
    print(
        "=" * 80
    )

    print(
        f"Stories found: {len(candidates)}"
    )

    print(
        f"Parsed + validated: {len(results)}"
    )

    print(
        f"Failed: {len(failures)}"
    )

    if ranked:

        print(
            f"Python winner: "
            f"{ranked[0]['cv']['full_name']} "
            f"({ranked[0]['cv']['candidate_id']})"
        )

        print(
            f"Python winner total: "
            f"{ranked[0]['weighted_total']:.2f}"
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()