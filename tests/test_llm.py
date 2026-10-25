import unittest
from unittest import mock

import httpx
from openai import APIConnectionError

import llm


def chunk(text, page=1):
    return {"source": "lec.pdf", "page": page, "text": text}


class TestFormatContext(unittest.TestCase):
    def test_marks_source_and_page(self):
        result = llm._format_context([chunk("Привет", 3), chunk("Мир", 4)])
        self.assertEqual(result, "[lec.pdf, стр. 3]\nПривет\n\n[lec.pdf, стр. 4]\nМир")


class TestSplitBySize(unittest.TestCase):
    def test_groups_fit_limit(self):
        chunks = [chunk("a" * 40) for _ in range(5)]
        groups = llm._split_by_size(chunks, 100)
        self.assertEqual([len(g) for g in groups], [2, 2, 1])

    def test_big_chunk_goes_alone(self):
        groups = llm._split_by_size([chunk("a" * 500)], 100)
        self.assertEqual(len(groups), 1)


def fake_response(text):
    message = mock.Mock(content=text)
    return mock.Mock(choices=[mock.Mock(message=message)])


CONN_ERROR = APIConnectionError(request=httpx.Request("POST", "https://test"))


@mock.patch("llm.time.sleep")  # не ждём реальные 2/5/10 с
@mock.patch("llm._get_client")  # вместо OpenRouter фальшивый клиент
class TestCallModel(unittest.TestCase):
    def test_retry_then_success(self, get_client, sleep):
        create = get_client.return_value.chat.completions.create
        create.side_effect = [CONN_ERROR, fake_response("ответ")]
        self.assertEqual(llm._call_model("вопрос"), "ответ")
        sleep.assert_called_once_with(2)

    def test_busy_after_all_retries(self, get_client, sleep):
        create = get_client.return_value.chat.completions.create
        create.side_effect = CONN_ERROR
        with self.assertRaises(llm.LLMBusyError):
            llm._call_model("вопрос")
        self.assertEqual(create.call_count, 4)  # 1 попытка + 3 повтора
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 5, 10])
