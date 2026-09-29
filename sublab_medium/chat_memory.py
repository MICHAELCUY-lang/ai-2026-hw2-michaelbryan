import argparse
import json
import os
from pathlib import Path

import tiktoken
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
# LOAD DATA
# ============================================================

with open(
    ROOT / "data" / "chat_script.json",
    "r",
    encoding="utf-8",
) as f:
    SCRIPT = json.load(f)


with open(
    ROOT / "data" / "memory_state.schema.json",
    "r",
    encoding="utf-8",
) as f:
    MEMORY_SCHEMA = json.load(f)


with open(
    ROOT / "data" / "policy.json",
    "r",
    encoding="utf-8",
) as f:
    POLICY = json.load(f)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = f"""
You are an assistant helping an applicant with the
Need-based study grant 2026.

Use the following official grant policy when answering questions:

{json.dumps(POLICY, ensure_ascii=False, indent=2)}

Remember information that the applicant gives you during
the conversation.

Do not invent information.

Applicant statements establish facts about the applicant,
while the official policy is used to determine eligibility
and grant amounts.

When answering questions, use only:
1. information established in the conversation,
2. compressed memory when available,
3. the official policy above.
"""


# ============================================================
# TOKEN COUNT
# ============================================================

def get_encoding():
    try:
        return tiktoken.encoding_for_model(MODEL)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


ENCODING = get_encoding()


def count_tokens(messages):
    """
    Approximate the number of tokens sent in the messages.
    The same counting method is used for both runs.
    """

    text = json.dumps(
        messages,
        ensure_ascii=False,
    )

    return len(
        ENCODING.encode(text)
    )


# ============================================================
# NORMAL MODEL CALL
# ============================================================

def ask(messages):
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    return response.choices[0].message.content


# ============================================================
# COMPRESS MEMORY
# ============================================================

def compress(messages):
    """
    Ask the model to convert the existing conversation into
    one structured memory object.

    Returns:
        state
        tokens_sent_to_compressor
    """

    compression_prompt = """
Compress the conversation into structured memory.

Follow these rules carefully:

- Do not invent information.
- applicant_id is null if it was never established.
- facts contain only facts stated by the applicant.
- decisions contain decisions already made.
- constraints contain conditions such as days,
  deadlines, availability, or requirements.
- open_questions contain questions that have not
  yet been answered.
- Preserve important details even when they seem
  unrelated to the main grant decision.
- Preserve constraints mentioned only once.
- Preserve unanswered questions.
- Preserve identity information.
- Preserve language information.

Return exactly one JSON object matching the required
memory schema.
"""

    compression_messages = [
        {
            "role": "system",
            "content": compression_prompt,
        },
        {
            "role": "user",
            "content": json.dumps(
                messages,
                ensure_ascii=False,
            ),
        },
    ]

    tokens_sent = count_tokens(
        compression_messages
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=compression_messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "memory_state",
                "strict": True,
                "schema": MEMORY_SCHEMA,
            },
        },
    )

    content = response.choices[0].message.content

    state = json.loads(content)

    validate(
        instance=state,
        schema=MEMORY_SCHEMA,
    )

    return state, tokens_sent


# ============================================================
# NORMALIZE SCRIPT
# ============================================================

def get_conversation_turns():
    """
    chat_script.json contains the scripted conversation and
    a <compress> marker.

    The marker is a command, not an applicant message.

    We return the conversation exactly as stored so both runs
    encounter the same sequence.
    """

    return SCRIPT["conversation"]


# ============================================================
# RUN SCRIPTED CONVERSATION
# ============================================================

def run_conversation(use_compression):
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    memory_state = None

    token_log = []

    call_number = 0

    compression_succeeded = False

    for turn in get_conversation_turns():

        # ----------------------------------------------------
        # COMPRESSION COMMAND
        # ----------------------------------------------------

        if turn in ("<compress>", "compress"):

            if use_compression:

                print(
                    "\nCompression command encountered..."
                )

                # IMPORTANT:
                # Keep a copy. We only throw history away
                # AFTER successful parse + schema validation.
                old_messages = list(messages)

                try:
                    state, compression_tokens = compress(
                        old_messages
                    )

                    memory_state = state

                    compression_succeeded = True

                    print(
                        "Compression: PARSE=OK, VALID=OK"
                    )

                    print(
                        f"Compression request tokens: "
                        f"{compression_tokens}"
                    )

                    # Replace old history only after success.
                    messages = [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT,
                        },
                        {
                            "role": "system",
                            "content": (
                                "The earlier conversation has "
                                "been compressed into the "
                                "following structured memory.\n\n"
                                "COMPRESSED MEMORY:\n"
                                + json.dumps(
                                    memory_state,
                                    ensure_ascii=False,
                                    indent=2,
                                )
                            ),
                        },
                    ]

                except Exception as exc:

                    # Requirement:
                    # malformed compression must NOT destroy
                    # the existing conversation.
                    print(
                        "Compression FAILED:"
                    )

                    print(
                        f"{type(exc).__name__}: {exc}"
                    )

                    print(
                        "Keeping original conversation history."
                    )

                    messages = old_messages

                    memory_state = None

                    compression_succeeded = False

            # Marker itself is NOT a user message.
            continue

        # ----------------------------------------------------
        # NORMAL USER TURN
        # ----------------------------------------------------

        messages.append(
            {
                "role": "user",
                "content": turn,
            }
        )

        tokens_sent = count_tokens(
            messages
        )

        call_number += 1

        reply = ask(
            messages
        )

        token_log.append(
            {
                "call": call_number,
                "tokens": tokens_sent,
                "user_turn": turn,
            }
        )

        messages.append(
            {
                "role": "assistant",
                "content": reply,
            }
        )

    return {
        "messages": messages,
        "memory": memory_state,
        "token_log": token_log,
        "compression_succeeded": compression_succeeded,
    }


# ============================================================
# RUN PROBES
# ============================================================

def run_probes(messages):
    results = []

    for probe in SCRIPT["probes"]:

        probe_messages = messages + [
            {
                "role": "user",
                "content": probe["question"],
            }
        ]

        tokens_sent = count_tokens(
            probe_messages
        )

        reply = ask(
            probe_messages
        )

        reply_lower = reply.lower()

        retrieved = any(
            expected.lower() in reply_lower
            for expected in probe["expect_contains"]
        )

        results.append(
            {
                "id": probe["id"],
                "question": probe["question"],
                "retrieved": retrieved,
                "reply": reply,
                "tokens": tokens_sent,
            }
        )

    return results


# ============================================================
# PRINT ONE RUN
# ============================================================

def print_run(
    title,
    run,
    probes,
):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    token_log = run["token_log"]

    print("\nTOKENS PER CONVERSATION CALL")
    print("-" * 80)

    total = 0

    for entry in token_log:

        print(
            f"Call {entry['call']:>2}: "
            f"{entry['tokens']} tokens"
        )

        total += entry["tokens"]

    if token_log:

        peak = max(
            entry["tokens"]
            for entry in token_log
        )

    else:

        peak = 0

    print("-" * 80)
    print(
        f"Peak conversation call: {peak} tokens"
    )
    print(
        f"Total conversation tokens sent: {total}"
    )

    print(
        f"Final context tokens: "
        f"{count_tokens(run['messages'])}"
    )

    if run["memory"] is not None:

        print()
        print("COMPRESSED MEMORY")
        print("-" * 80)

        print(
            json.dumps(
                run["memory"],
                ensure_ascii=False,
                indent=2,
            )
        )

    print()
    print("PROBES")
    print("-" * 80)

    retrieved_count = 0

    for probe in probes:

        if probe["retrieved"]:
            retrieved_count += 1

        status = (
            "RETRIEVED"
            if probe["retrieved"]
            else "LOST"
        )

        print()
        print(
            f"{probe['id']} | {status}"
        )

        print(
            f"Question: {probe['question']}"
        )

        print(
            f"Answer: {probe['reply']}"
        )

        print(
            f"Probe call tokens: {probe['tokens']}"
        )

    print()
    print(
        f"Probe summary: "
        f"{retrieved_count}/{len(probes)} retrieved"
    )

    return {
        "peak": peak,
        "total": total,
        "retrieved": retrieved_count,
    }


# ============================================================
# PRINT COMPARISON TABLE
# ============================================================

def print_comparison(
    normal_run,
    compressed_run,
    normal_summary,
    compressed_summary,
):

    normal_log = normal_run["token_log"]
    compressed_log = compressed_run["token_log"]

    print()
    print("=" * 80)
    print("SUBMISSION TOKEN TABLE")
    print("=" * 80)

    print(
        f"{'Call':<8}"
        f"{'A — never compressed':<26}"
        f"{'B — compressed':<26}"
    )

    print("-" * 60)

    max_calls = max(
        len(normal_log),
        len(compressed_log),
    )

    for i in range(max_calls):

        if i < len(normal_log):
            a = normal_log[i]["tokens"]
        else:
            a = "-"

        if i < len(compressed_log):
            b = compressed_log[i]["tokens"]
        else:
            b = "-"

        print(
            f"{i + 1:<8}"
            f"{str(a):<26}"
            f"{str(b):<26}"
        )

    print("-" * 60)

    print(
        f"{'PEAK':<8}"
        f"{str(normal_summary['peak']):<26}"
        f"{str(compressed_summary['peak']):<26}"
    )

    print(
        f"{'TOTAL':<8}"
        f"{str(normal_summary['total']):<26}"
        f"{str(compressed_summary['total']):<26}"
    )

    print()
    print("PROBE COMPARISON")

    print(
        f"A — never compressed: "
        f"{normal_summary['retrieved']}/5"
    )

    print(
        f"B — compressed: "
        f"{compressed_summary['retrieved']}/5"
    )

    normal_final = count_tokens(
        normal_run["messages"]
    )

    compressed_final = count_tokens(
        compressed_run["messages"]
    )

    if normal_final > 0:

        reduction = (
            (
                normal_final
                - compressed_final
            )
            / normal_final
            * 100
        )

    else:

        reduction = 0

    print()
    print(
        f"Final context A: {normal_final}"
    )

    print(
        f"Final context B: {compressed_final}"
    )

    print(
        f"Final context reduction: "
        f"{reduction:.2f}%"
    )


# ============================================================
# INTERACTIVE MODE
# ============================================================

def interactive():
    print()
    print("=" * 80)
    print("INTERACTIVE MEMORY CHAT")
    print("=" * 80)

    print(
        "Commands:"
    )
    print(
        "  compress  -> compress conversation into structured memory"
    )
    print(
        "  tokens    -> show token cost of the last model call"
    )
    print(
        "  memory    -> show current compressed memory"
    )
    print(
        "  exit      -> quit"
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    memory_state = None

    last_call_tokens = None

    while True:

        try:
            user_input = input(
                "\nYou: "
            ).strip()

        except (EOFError, KeyboardInterrupt):

            print()
            break

        if not user_input:
            continue

        command = user_input.lower()

        # ----------------------------------------------------
        # EXIT
        # ----------------------------------------------------

        if command in (
            "exit",
            "quit",
        ):

            break

        # ----------------------------------------------------
        # TOKENS
        # ----------------------------------------------------

        if command == "tokens":

            if last_call_tokens is None:

                print(
                    "No model call has been made yet."
                )

            else:

                print(
                    f"Last call sent "
                    f"{last_call_tokens} tokens."
                )

            continue

        # ----------------------------------------------------
        # SHOW MEMORY
        # ----------------------------------------------------

        if command == "memory":

            if memory_state is None:

                print(
                    "No compressed memory exists."
                )

            else:

                print(
                    json.dumps(
                        memory_state,
                        ensure_ascii=False,
                        indent=2,
                    )
                )

            continue

        # ----------------------------------------------------
        # COMPRESS
        # ----------------------------------------------------

        if command in (
            "compress",
            "<compress>",
        ):

            old_messages = list(
                messages
            )

            try:

                state, compression_tokens = compress(
                    old_messages
                )

                memory_state = state

                last_call_tokens = compression_tokens

                messages = [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "system",
                        "content": (
                            "The earlier conversation has "
                            "been compressed into the "
                            "following structured memory.\n\n"
                            "COMPRESSED MEMORY:\n"
                            + json.dumps(
                                memory_state,
                                ensure_ascii=False,
                                indent=2,
                            )
                        ),
                    },
                ]

                print(
                    "Compression successful."
                )

                print(
                    json.dumps(
                        memory_state,
                        ensure_ascii=False,
                        indent=2,
                    )
                )

            except Exception as exc:

                messages = old_messages

                print(
                    f"Compression failed: "
                    f"{type(exc).__name__}: {exc}"
                )

                print(
                    "Original history was kept."
                )

            continue

        # ----------------------------------------------------
        # NORMAL MESSAGE
        # ----------------------------------------------------

        messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        last_call_tokens = count_tokens(
            messages
        )

        try:

            reply = ask(
                messages
            )

        except Exception as exc:

            print(
                f"API error: "
                f"{type(exc).__name__}: {exc}"
            )

            # Remove failed user message.
            messages.pop()

            continue

        messages.append(
            {
                "role": "assistant",
                "content": reply,
            }
        )

        print(
            f"Assistant: {reply}"
        )


# ============================================================
# SCRIPTED MODE
# ============================================================

def scripted():

    print()
    print("#" * 80)
    print("RUN A — NEVER COMPRESSED")
    print("#" * 80)

    normal_run = run_conversation(
        use_compression=False
    )

    normal_probes = run_probes(
        normal_run["messages"]
    )

    normal_summary = print_run(
        "A — NEVER COMPRESSED",
        normal_run,
        normal_probes,
    )


    print()
    print("#" * 80)
    print("RUN B — COMPRESSED")
    print("#" * 80)

    compressed_run = run_conversation(
        use_compression=True
    )

    compressed_probes = run_probes(
        compressed_run["messages"]
    )

    compressed_summary = print_run(
        "B — COMPRESSED",
        compressed_run,
        compressed_probes,
    )


    print_comparison(
        normal_run,
        compressed_run,
        normal_summary,
        compressed_summary,
    )


    print()
    print("=" * 80)
    print("STATE FOR SUBMISSION.MD")
    print("=" * 80)

    if compressed_run["memory"] is None:

        print(
            "No valid compressed state was produced."
        )

    else:

        print(
            json.dumps(
                compressed_run["memory"],
                ensure_ascii=False,
                indent=2,
            )
        )


    print()
    print("=" * 80)
    print("PROBES FOR SUBMISSION.MD")
    print("=" * 80)

    print(
        f"{'Probe':<10}"
        f"{'A':<14}"
        f"{'B':<14}"
    )

    print("-" * 38)

    for normal, compressed in zip(
        normal_probes,
        compressed_probes,
    ):

        a = (
            "RETRIEVED"
            if normal["retrieved"]
            else "LOST"
        )

        b = (
            "RETRIEVED"
            if compressed["retrieved"]
            else "LOST"
        )

        print(
            f"{normal['id']:<10}"
            f"{a:<14}"
            f"{b:<14}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive chat mode",
    )

    args = parser.parse_args()

    if args.interactive:

        interactive()

    else:

        scripted()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()