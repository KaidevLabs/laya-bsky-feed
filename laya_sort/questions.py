# QUESTION_SET_V1 — wording is a design artifact; A/B it later via scripts/replay.py.
# Two-option choice with neutral keys A/B on purpose: the vendor README ("Honest limits")
# warns that yes/no-style labels can hijack the answer.
QUESTION_SET = {
    "quality": {
        "type": "choice",
        "instructions": "Does this social media post contain something worth showing to others (information, art, humor, help), or is it noise?",
        "criteria": {
            "A": "substantive: informs, teaches, shows work, makes a real point, or is genuinely funny",
            "B": "noise: empty chatter, spam, bait, a repost of nothing, or unintelligible",
        },
    },
}
QUESTION_SET_VERSION = "v1"
