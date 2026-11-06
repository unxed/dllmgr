import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from wine_codepage import decode_stdout, decode_stderr, oem_codec


class CodepageTest(unittest.TestCase):
    def test_locale_precedence(self):
        self.assertEqual(oem_codec({"LC_ALL": "ru_RU.UTF-8", "LC_CTYPE": "fr_FR", "LANG": "en_US"}), "cp866")
        self.assertEqual(oem_codec({"LC_ALL": "", "LC_CTYPE": "fr_FR.UTF-8", "LANG": "ru_RU"}), "cp850")
        self.assertEqual(oem_codec({"LANG": "ru_RU.UTF-8"}), "cp866")

    def test_neutral_and_unknown_locale(self):
        for locale in ("", "C", "C.UTF-8", "POSIX", "unknown"):
            self.assertEqual(oem_codec({"LC_ALL": locale}), "cp437")

    def test_oem_messages(self):
        for locale, codec, message in (("ru_RU.UTF-8", "cp866", "не удалось найти ключ"),
                                       ("fr_FR.UTF-8", "cp850", "opération terminée"),
                                       ("ja_JP.UTF-8", "cp932", "レジストリ"),
                                       ("zh_CN.UTF-8", "gbk", "注册表")):
            self.assertEqual(decode_stdout(message.encode(codec), {"LANG": locale}), message)

    def test_utf8_wine_diagnostics(self):
        message = "wine: /tmp/папка"
        self.assertEqual(decode_stderr(message.encode(), {"LANG": "ru_RU.UTF-8"}), message)

    def test_oem_stderr(self):
        message = "Отказано в доступе"
        self.assertEqual(decode_stderr(message.encode("cp866"), {"LANG": "ru_RU.UTF-8"}), message)


if __name__ == "__main__":
    unittest.main()
