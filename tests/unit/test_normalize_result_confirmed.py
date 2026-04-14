from __future__ import annotations

from WorkAI.normalize.runner import _is_result_confirmed
from WorkAI.normalize.time_parse import TimeInfo


def test_result_confirmed_true_when_duration_present() -> None:
    value = _is_result_confirmed(
        text="Любой текст без статуса",
        time_info=TimeInfo(start=None, end=None, duration_minutes=45),
        is_zhdun=False,
    )
    assert value is True


def test_result_confirmed_false_for_blank_text_without_duration() -> None:
    value = _is_result_confirmed(text="   ", time_info=None, is_zhdun=False)
    assert value is False


def test_result_confirmed_false_for_wait_markers() -> None:
    value = _is_result_confirmed(
        text="Вернуться к вопросу после согласования",
        time_info=None,
        is_zhdun=False,
    )
    assert value is False


def test_result_confirmed_false_for_zhdun() -> None:
    value = _is_result_confirmed(
        text="Ожидание ответа от клиента",
        time_info=None,
        is_zhdun=True,
    )
    assert value is False


def test_result_confirmed_true_for_regular_task_text() -> None:
    value = _is_result_confirmed(
        text="Магнит уточнить про подпись в ЭДО",
        time_info=None,
        is_zhdun=False,
    )
    assert value is True
