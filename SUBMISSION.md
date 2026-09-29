# AI 2026 Homework 2 — Submission

**Name:** Michael Bryan Mandey  
**Student ID:** S6078853  
**Group:** CSS4007-ENG-10  
**Repository:** https://github.com/MICHAELCUY-lang/ai-2026-hw2-michaelbryan  
**Model used:** `gpt-5.6-luna`

## AI Assistance Disclosure

I used ChatGPT to help me understand the assignment requirements, debug and refine my Python code.

---

# Sublab Easy — One Task, Four Roles

## Role Results

All 10 replies for every role parsed successfully and validated against the JSON schema.

### `policy_officer`

| Enquiry | Parsed | Schema valid | Structured fields agree with expected |
|---|---|---|---|
| E-01 | Yes | Yes | Yes |
| E-02 | Yes | Yes | Yes |
| E-03 | Yes | Yes | Yes |
| E-04 | Yes | Yes | Yes |
| E-05 | Yes | Yes | Yes |
| E-06 | Yes | Yes | Yes |
| E-07 | Yes | Yes | Yes |
| E-08 | Yes | Yes | Yes |
| E-09 | Yes | Yes | Yes |
| E-10 | Yes | Yes | Yes |

**Agreement:** 10/10.

### `front_desk`

| Enquiry | Parsed | Schema valid | Structured fields agree with expected |
|---|---|---|---|
| E-01 | Yes | Yes | Yes |
| E-02 | Yes | Yes | Yes |
| E-03 | Yes | Yes | No — decision changed from `refused` to `more_info` |
| E-04 | Yes | Yes | No — decision changed from `refused` to `more_info` |
| E-05 | Yes | Yes | Yes |
| E-06 | Yes | Yes | Yes |
| E-07 | Yes | Yes | Yes |
| E-08 | Yes | Yes | Yes |
| E-09 | Yes | Yes | No — decision changed from `refused` to `more_info` |
| E-10 | Yes | Yes | Yes |

**Agreement:** 7/10.

### `auditor`

| Enquiry | Parsed | Schema valid | Structured fields agree with expected |
|---|---|---|---|
| E-01 | Yes | Yes | No — decision changed to `more_info` |
| E-02 | Yes | Yes | Yes |
| E-03 | Yes | Yes | Yes |
| E-04 | Yes | Yes | Yes |
| E-05 | Yes | Yes | No — decision changed to `more_info` |
| E-06 | Yes | Yes | No — decision changed to `more_info`, amount changed to 0 |
| E-07 | Yes | Yes | No — decision changed to `more_info`, amount changed to 0 |
| E-08 | Yes | Yes | Yes |
| E-09 | Yes | Yes | Yes |
| E-10 | Yes | Yes | Yes |

**Agreement:** 6/10.

### `bilingual_clerk`

| Enquiry | Parsed | Schema valid | Structured fields agree with expected |
|---|---|---|---|
| E-01 | Yes | Yes | Yes |
| E-02 | Yes | Yes | Yes |
| E-03 | Yes | Yes | Yes |
| E-04 | Yes | Yes | Yes |
| E-05 | Yes | Yes | Yes |
| E-06 | Yes | Yes | Yes |
| E-07 | Yes | Yes | Yes |
| E-08 | Yes | Yes | Yes |
| E-09 | Yes | Yes | Yes |
| E-10 | Yes | Yes | Yes |

**Agreement:** 10/10.

## Field-Movement Table

Movement is measured against the `policy_officer` output.

| Structured field | Enquiries that moved | Role(s) |
|---|---|---|
| `found` | None | None |
| `decision` | E-03, E-04, E-09 | `front_desk` |
| `decision` | E-01, E-05, E-06, E-07 | `auditor` |
| `amount` | E-06, E-07 | `auditor` |
| `missing_documents` | None | None |

The bilingual clerk did not move any of the four checked structured fields; its visible role effect was in the language of `reason`.

## Raw Reply — Role Changed the Decision

`front_desk` — E-03:

```json
{
  "applicant_id": "A-203",
  "found": true,
  "decision": "more_info",
  "amount": 0,
  "missing_documents": [],
  "reason": "The record shows a GPA of 2.4, below the minimum 2.67. Please return with an updated transcript if the GPA record needs to be checked or corrected."
}
```

## Raw Reply — Bilingual Clerk E-07

```json
{
  "applicant_id": "A-201",
  "found": true,
  "decision": "granted",
  "amount": 250000,
  "missing_documents": [],
  "reason": "Жазбаға сәйкес GPA 3.4, табыс деңгейі 1 және қажетті құжаттардың (транскрипт пен жеке куәлік) екеуі де бар. 250 000 теңге грант тағайындалады."
}
```

## Written Answers

### 1. Which fields are role-sensitive and which are not?

In my run, `decision` was the most role-sensitive field. The front desk changed E-03, E-04, and E-09 from `refused` to `more_info`, while the auditor changed E-01, E-05, E-06, and E-07 from `granted` to `more_info`. `amount` was also role-sensitive for the auditor on E-06 and E-07, where it became 0 after the decision changed. `found` and `missing_documents` did not move at all. The bilingual clerk kept the same structured decisions as the policy officer and changed only the human-readable language of `reason`.

### 2. Which enquiries are most sensitive to the role, and why?

E-03 and E-04 are sensitive because the policy result is a refusal, but the front-desk role is instructed not to turn an applicant away and therefore changes the outcome to `more_info`. E-07 is sensitive because the auditor refuses to grant on a first reading, while the bilingual clerk preserves the policy decision and changes the response language. E-10 tests whether the applicant's claim can override the stored record; in my run the record still controlled the structured result.

### 3. Where does discretion belong?

The role paragraph can describe how the assistant should behave, but important decision rules should not depend only on prompt wording. A downstream program that only receives the structured record can see `decision`, but it cannot reliably infer which role produced it. I would therefore carry role metadata when provenance matters and enforce expensive or mandatory decision rules in deterministic code.

### 4. Is a role a boundary?

No. A role prompt is context/instructions supplied to the language model, not a security boundary. The auditor instruction and bilingual-clerk instruction influence generation, but the model can still produce an incorrect result. If a wrong decision were expensive, I would validate the structured output and enforce critical policy constraints in code before taking an action.

---

# Sublab Medium — Memory and `compress`

## Token Table

The `<compress>` item is a command rather than a normal applicant message, so the run produced 11 normal conversation model calls. The compression request itself sent 1547 tokens in Run B.

| Call | A — Never compressed | B — Compressed |
|---:|---:|---:|
| 1 | 375 | 375 |
| 2 | 450 | 451 |
| 3 | 626 | 597 |
| 4 | 778 | 717 |
| 5 | 848 | 776 |
| 6 | 982 | 888 |
| 7 | 1099 | 1005 |
| 8 | 1204 | 1103 |
| 9 | 1314 | 1231 |
| 10 | 1402 | 731 |
| 11 | 1559 | 885 |
| **Peak** | **1559** | **1231** |
| **Total normal conversation tokens sent** | **10637** | **8759** |

Final context size was 1602 tokens without compression and 936 tokens with compression, a reduction of **41.57%**.

## Probe Results

| Probe | A — Never compressed | B — Compressed |
|---|---|---|
| Q-1 applicant/name/number | RETRIEVED | RETRIEVED |
| Q-2 missing document | RETRIEVED | RETRIEVED |
| Q-3 income band/amount | LOST | RETRIEVED |
| Q-4 available day | LOST | RETRIEVED |
| Q-5 employer-letter question | RETRIEVED | RETRIEVED |

**Run A:** 3/5 according to the program's substring evaluator.  
**Run B:** 5/5.

For Q-3 and Q-4 in Run A, the model's answers were semantically correct, but the automatic substring test marked them as lost because the answer used different formatting/language. Q-3 contained income band 2 and `150 000 KZT`, while Q-4 answered Thursday in Kazakh (`бейсенбі`). I keep the program's recorded 3/5 result here rather than manually changing the run output.

## Compressed State

```json
{
  "applicant_id": "A-202",
  "topic": "Need-based study grant 2026",
  "facts": [
    "The applicant's name is Daniyar Qoshan.",
    "The applicant sent their transcript last week.",
    "The applicant's income band is 2, according to their family's certificate.",
    "The applicant could not upload their ID card because their home scanner broke.",
    "The applicant's sister, Aruzhan, applied last year and is on file."
  ],
  "decisions": [
    "The applicant currently does not qualify because the ID card is not on file.",
    "If the ID card is submitted and the GPA is at least 2.67, the grant amount for income band 2 is 150,000 KZT.",
    "The sister's application does not affect the applicant's eligibility."
  ],
  "constraints": [
    "The applicant can only come to the office on Thursdays because they have lab all week otherwise."
  ],
  "open_questions": [
    "What is the applicant's GPA?",
    "Has the transcript been accepted and added to the record?",
    "Will the decision be made on the same day the ID card is brought?",
    "Does a scanned employer letter count, or is the original required?"
  ],
  "language": "Kazakh and English"
}
```

## Written Answers

### 1. What did compression buy?

The peak normal conversation call decreased from **1559 tokens** to **1231 tokens**, and the final context decreased from 1602 to 936 tokens. The recorded probe result improved from **3/5** to **5/5**. The two Run A probes marked lost were Q-3 (income band and grant amount) and Q-4 (Thursday availability), although inspection of the actual answers shows that both facts were present and the failures came from exact substring matching. Therefore the clearest demonstrated benefit in my run is the smaller context while retaining the facts needed by all five probes after compression.

### 2. Why must the state be structured rather than a paragraph?

Named fields make the selected memory explicit and machine-checkable. The program can validate `applicant_id`, `facts`, `decisions`, `constraints`, `open_questions`, and `language` against a schema and reject malformed compression. With a free-form paragraph, the model could silently omit or mix categories and the program would have much less ability to detect the problem.

### 3. What is missing from the state that you would add?

I would add a `related_people` field. The conversation contains information about the applicant's sister, Aruzhan, and putting that relationship in a dedicated field would make it clearer than storing it as a generic fact. To pay for it, I would shorten or remove redundant wording from `facts`, especially facts already represented by another structured field or decision.

### 4. When is compression the wrong choice?

Compression is the wrong choice when exact wording is evidence, for example a legal, disciplinary, contractual, or formal complaint conversation where the precise original statement may later matter. A schema-valid summary can preserve the general meaning while losing wording that cannot be reconstructed. My program would notice a parse or schema-validation failure, but it would not automatically notice every semantic detail that a valid summary omitted.

---

# Sublab Hard — Stories In, CVs Out

## Part 1 — Extraction / Trap Table

All six replies parsed and validated successfully.

| ID | Candidate | Parsed | Validated | Null fields | Traps hit |
|---|---|---|---|---|---|
| C-01 | Aziza Bekova | Yes | Yes | none | unpublished/planned output not counted |
| C-02 | Dias Yerzhanov | Yes | Yes | `graduation_year`, `gpa_original`, `gpa_original_scale`, `gpa_4_scale` | missing GPA; student-conference paper not explicitly peer-reviewed; ambiguous graduation year |
| C-03 | Lyazzat Omarova | Yes | Yes | none | under-review paper not counted |
| C-04 | Tamerlan Saparov | Yes | Yes | none | submitted/under-review and in-preparation outputs not counted |
| C-05 | Аиша Нұрланқызы | Yes | Yes | none | in-preparation output not counted |
| C-06 | Nurzhan Abilov | Yes | Yes | `graduation_year`, `gpa_original`, `gpa_original_scale`, `gpa_4_scale` | contradictory GPA; contradictory graduation status/year; non-published poster not counted |

The extraction also retained evidence quotes for the populated fields. For example, Lyazzat's 4.6/5.0 GPA was converted to **3.68/4.0**, while the original value and scale were retained. Dias's absent numeric GPA remained `null`, and Nurzhan's contradictory 3.2/3.5 GPA remained unresolved rather than being averaged.

## Part 2 — Scores and Code-Computed Ranking

The model returned only the three 0–5 criterion scores. The weighted total was then calculated in Python as:

`0.5 * academic + 0.3 * research + 0.2 * experience`

| Rank | ID | Candidate | Academic | Research | Experience | Weighted total |
|---:|---|---|---:|---:|---:|---:|
| 1 | C-01 | Aziza Bekova | 5 | 5 | 2 | **4.40** |
| 2 | C-04 | Tamerlan Saparov | 4 | 3 | 5 | **3.90** |
| 3 | C-05 | Аиша Нұрланқызы | 5 | 3 | 2 | **3.80** |
| 4 | C-03 | Lyazzat Omarova | 4 | 3 | 3 | **3.50** |
| 5 | C-06 | Nurzhan Abilov | 0 | 3 | 5 | **1.90** |
| 6 | C-02 | Dias Yerzhanov | 0 | 0 | 5 | **1.00** |

**Code-computed winner:** C-01 — **Aziza Bekova**, weighted total **4.40**.

## Separate Model Prose Winner Answer

> **Separate judgement:** I would award the funded place to **C-01, Aziza Bekova**.
>
> Her record is the strongest overall under the rubric: she reports a **3.8 GPA on a 4.0 scale**, which meets the rubric’s definition of a top academic record, and she has **two published peer-reviewed outputs**, the maximum research category. Although her relevant experience is limited to **8 months**, this is outweighed by her superior academic and research record. C-05 has a slightly higher GPA but only one publication and six months of experience, while candidates with longer experience do not match C-01’s combination of academic strength and research output.

## Part 3 — Written Answers

### 1. Which rule did you have to add, and what broke without it?

The most important rule I had to make explicit was that a missing numeric GPA must stay `null` and, under this rubric, receive academic score 0 rather than being inferred from other academic language. **Story 02 (Dias Yerzhanov)** forced this rule: it says there is no GPA figure but mentions graduating with distinction. Without the explicit rule, an earlier version of my run gave Dias a positive academic score by treating the distinction as evidence for academic strength. I also needed an explicit publication-status rule so submitted, under-review, in-preparation, planned, or in-press work would not be counted as published.

### 2. Where did the model guess, and where did your code have to decide?

An example of model guessing appeared during development on Dias's story: without the stronger no-GPA instruction, the model gave an academic score even though no numeric GPA was present. The final prompt prevents that inference and returns `gpa_4_scale = null` and academic 0. The code, rather than the model, decided the final weighted comparison: it applied the rubric weights to the three returned score fields, rounded the result, sorted the candidates, and selected the highest total.

### 3. Did the prose ranking and computed ranking agree?

Yes. The separate prose call selected **C-01 Aziza Bekova**, and the Python calculation also ranked C-01 first with **4.40**. I would not trust the prose judgement alone just because it agreed once. Before relying on it, I would want the same structured evidence, explicit rubric application, repeatable criterion scores, and a deterministic calculation that can be independently checked.

### 4. What did you do with the contradicted field?

For **C-06 Nurzhan Abilov**, the story says GPA 3.2 and then 3.5, so I did not choose one or average them. I set `gpa_original`, `gpa_original_scale`, and `gpa_4_scale` to `null` and recorded the contradiction. The final run consequently gave academic score 0. I think the rubric should explicitly say how a contradicted required field affects scoring—for example, treat it as unresolved/missing for automatic scoring and flag it for human verification rather than letting the model invent an intermediate value.

### 5. How close were the top two candidates?

The top two were **Aziza Bekova (4.40)** and **Tamerlan Saparov (3.90)**, a difference of **0.50**, so they were not within 0.05. If they had been within 0.05, I would tell the committee that the result was sensitive enough to require manual review rather than treating the numerical order as decisive. I would also make the extraction more defensible by verifying every evidence quote, date range, publication status, GPA conversion, and contradiction before recomputing the scores.

---

# Final Checklist

- [x] `sublab_easy/role_prompts.py` runs all four roles and prints the field-movement table.
- [x] `sublab_medium/chat_memory.py` runs both modes and supports interactive `compress` and `tokens`.
- [x] `sublab_hard/cv_extract_and_rank.py` extracts six records, scores them, and computes a winner.
- [x] `SUBMISSION.md` contains the required tables and written answers.