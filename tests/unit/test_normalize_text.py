from WorkAI.normalize.text_norm import normalize_task_text


def test_normalize_task_text_nfkc_and_whitespace() -> None:
    text = "  Fullwidth\uff1a\uff21\uff22\uff23   task\tname  "
    assert normalize_task_text(text) == "Fullwidth:ABC task name"


def test_normalize_task_text_unifies_dashes() -> None:
    text = "Plan \u2014 implement \u2013 verify \u2212 done"
    assert normalize_task_text(text) == "Plan - implement - verify - done"
