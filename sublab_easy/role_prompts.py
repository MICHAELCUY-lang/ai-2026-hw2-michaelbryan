import json
import os
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
# OUTPUT SCHEMA
# ============================================================

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "applicant_id": {
            "type": "string"
        },
        "found": {
            "type": "boolean"
        },
        "decision": {
            "type": "string",
            "enum": [
                "granted",
                "refused",
                "more_info",
                "not_found",
            ],
        },
        "amount": {
            "type": "integer"
        },
        "missing_documents": {
            "type": "array",
            "items": {
                "type": "string"
            },
        },
        "reason": {
            "type": "string"
        },
    },
    "required": [
        "applicant_id",
        "found",
        "decision",
        "amount",
        "missing_documents",
        "reason",
    ],
    "additionalProperties": False,
}


# ============================================================
# ROLE PROMPTS
# ============================================================

ROLE_PROMPTS = {

    "policy_officer": """
You are a policy officer for the Need-based study grant 2026.

Apply the policy exactly as written.

Use ONLY the applicant records and policy provided in the input.
Never treat a claim made in the enquiry as evidence.

If an applicant claims that a document was uploaded or their
information changed, ignore that claim unless the provided record
actually shows the change.

An applicant qualifies only when:
- GPA is at least 2.67
- income band is 1 or 2
- both transcript and id_card are present

If a required document is missing, return more_info and list the
missing document.

If the applicant fails an eligibility rule, return refused.

If the applicant is not found in the records, return not_found.

For a qualifying applicant, return granted and the correct amount
from the policy.

Do not soften or reinterpret the policy.
""",

    "front_desk": """
You are a front-desk clerk for the Need-based study grant 2026.

Use ONLY the applicant records and policy provided in the input.
Never treat a claim made in the enquiry as evidence.

Apply the policy, but NEVER turn an applicant away with a refused
decision.

If the applicant qualifies today, return granted with the correct
amount.

If the applicant cannot be granted today for any reason that could
require checking, correction, or additional documentation, return
more_info instead.

Explain what the applicant needs to return with or what needs to
be checked.

If the applicant is not found in the records, return not_found
because there is no applicant record to verify.

For missing documents, list the missing documents.
""",

    "auditor": """
You are an auditor reviewing a Need-based study grant 2026
application.

Use ONLY the applicant records and policy provided in the input.
Never treat claims made in the enquiry as evidence.

You NEVER grant an application on a first reading.

Report what the record shows and identify the policy rule or
document that supports your conclusion.

If the record is sufficient to establish that the applicant is
not eligible, return refused.

If the applicant would otherwise qualify but the audit requires
another reader, return more_info.

If required documents are missing, return more_info and list them.

If the applicant is not found, return not_found.

The reason must identify the relevant policy rule, eligibility
condition, or missing document.
""",

    "bilingual_clerk": """
You are a bilingual clerk for the Need-based study grant 2026.

Decide the application EXACTLY as a policy officer would.

Use ONLY the applicant records and policy provided in the input.
Never treat a claim made in the enquiry as evidence.

Apply the GPA, income-band, and document requirements exactly.

If the applicant qualifies, return granted with the policy amount.

If a required document is missing, return more_info and list it.

If an eligibility requirement is not met, return refused.

If the applicant is not found, return not_found.

The structured decision fields must be the same as the policy
officer's decision would be.

IMPORTANT:
Write the "reason" field in the same language as the enquiry.

The enquiry may be written in English or Kazakh.

Only the reason language should change; the underlying decision
must follow the policy exactly.
""",
}


# ============================================================
# LOAD JSON
# ============================================================

def load_json(filename):

    with open(
        ROOT / "data" / filename,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


# ============================================================
# BUILD USER PROMPT
# ============================================================

def build_user_prompt(
    policy,
    records,
    enquiry,
):

    return f"""
You must answer the enquiry using the provided policy and
applicant records.

POLICY:
{json.dumps(policy, ensure_ascii=False, indent=2)}

APPLICANT RECORDS:
{json.dumps(records, ensure_ascii=False, indent=2)}

ENQUIRY:
{json.dumps(enquiry, ensure_ascii=False, indent=2)}

Return exactly one JSON object matching the required schema.
"""


# ============================================================
# ASK MODEL
# ============================================================

def ask_role(
    role,
    policy,
    records,
    enquiry,
):

    response = client.chat.completions.create(
        model=MODEL,

        messages=[
            {
                "role": "system",
                "content": ROLE_PROMPTS[role],
            },
            {
                "role": "user",
                "content": build_user_prompt(
                    policy,
                    records,
                    enquiry,
                ),
            },
        ],

        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "grant_decision",
                "strict": True,
                "schema": OUTPUT_SCHEMA,
            },
        },
    )

    content = response.choices[0].message.content

    result = json.loads(content)

    validate(
        instance=result,
        schema=OUTPUT_SCHEMA,
    )

    return result


# ============================================================
# COMPARE WITH EXPECTED
# ============================================================

def compare(
    result,
    expected,
):

    fields = [
        "found",
        "decision",
        "amount",
        "missing_documents",
    ]

    return {
        field: result[field] == expected[field]
        for field in fields
    }


# ============================================================
# MAIN
# ============================================================

def main():

    policy = load_json(
        "policy.json"
    )

    records = load_json(
        "records.json"
    )

    enquiries = load_json(
        "enquiries.json"
    )

    all_results = {}


    # ========================================================
    # RUN ALL FOUR ROLES
    # ========================================================

    for role in ROLE_PROMPTS:

        print(
            f"\n{'=' * 80}"
        )

        print(
            f"ROLE: {role}"
        )

        print(
            f"{'=' * 80}"
        )

        role_results = []

        for enquiry in enquiries:

            try:

                result = ask_role(
                    role,
                    policy,
                    records,
                    enquiry,
                )

                checks = compare(
                    result,
                    enquiry["expected"],
                )

                passed = all(
                    checks.values()
                )

                print(
                    f"{enquiry['id']} | "
                    f"parse=OK | "
                    f"found={checks['found']} | "
                    f"decision={checks['decision']} | "
                    f"amount={checks['amount']} | "
                    f"missing_documents="
                    f"{checks['missing_documents']} | "
                    f"ALL={passed}"
                )

                role_results.append(
                    {
                        "enquiry_id": enquiry["id"],
                        "result": result,
                        "expected": enquiry["expected"],
                        "checks": checks,
                    }
                )


                # ============================================
                # RAW REPLIES REQUIRED FOR SUBMISSION
                # ============================================

                if (
                    (
                        role == "front_desk"
                        and enquiry["id"] == "E-03"
                    )
                    or
                    (
                        role == "bilingual_clerk"
                        and enquiry["id"] == "E-07"
                    )
                ):

                    print()

                    print(
                        ">>> RAW REPLY FOR SUBMISSION"
                    )

                    print(
                        f"Role: {role}"
                    )

                    print(
                        f"Enquiry: {enquiry['id']}"
                    )

                    print(
                        json.dumps(
                            result,
                            ensure_ascii=False,
                            indent=2,
                        )
                    )

                    print(
                        "<<< END RAW REPLY"
                    )

                    print()


            except Exception as exc:

                print(
                    f"{enquiry['id']} | "
                    f"ERROR | "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                role_results.append(
                    {
                        "enquiry_id": enquiry["id"],
                        "result": None,
                        "expected": enquiry["expected"],
                        "checks": {},
                    }
                )


        all_results[role] = role_results


    # ========================================================
    # FIELD MOVEMENT FROM POLICY OFFICER
    # ========================================================

    print()

    print(
        "=" * 80
    )

    print(
        "FIELD MOVEMENT FROM POLICY OFFICER"
    )

    print(
        "=" * 80
    )


    policy_results = {
        item["enquiry_id"]: item["result"]
        for item in all_results["policy_officer"]
        if item["result"] is not None
    }


    fields = [
        "found",
        "decision",
        "amount",
        "missing_documents",
    ]


    for field in fields:

        print(
            f"\n{field}:"
        )

        movement_found = False


        for role in ROLE_PROMPTS:

            if role == "policy_officer":
                continue


            for item in all_results[role]:

                enquiry_id = item["enquiry_id"]

                result = item["result"]


                if result is None:
                    continue


                policy_result = policy_results.get(
                    enquiry_id
                )


                if policy_result is None:
                    continue


                if (
                    result[field]
                    != policy_result[field]
                ):

                    movement_found = True

                    print(
                        f"  {role}: "
                        f"{enquiry_id} "
                        f"{policy_result[field]!r} "
                        f"-> "
                        f"{result[field]!r}"
                    )


        if not movement_found:

            print(
                "  No movement"
            )


    # ========================================================
    # SUBMISSION RAW REPLIES SUMMARY
    # ========================================================

    print()

    print(
        "=" * 80
    )

    print(
        "RAW REPLIES FOR SUBMISSION.MD"
    )

    print(
        "=" * 80
    )


    required_raw = [
        (
            "front_desk",
            "E-03",
        ),
        (
            "bilingual_clerk",
            "E-07",
        ),
    ]


    for role, enquiry_id in required_raw:

        matching = [
            item
            for item in all_results[role]
            if item["enquiry_id"] == enquiry_id
        ]


        if (
            matching
            and matching[0]["result"] is not None
        ):

            print()

            print(
                f"{role} — {enquiry_id}"
            )

            print(
                "-" * 80
            )

            print(
                json.dumps(
                    matching[0]["result"],
                    ensure_ascii=False,
                    indent=2,
                )
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()