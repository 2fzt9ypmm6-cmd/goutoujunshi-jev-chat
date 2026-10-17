"""Exercise Windows process/UI orchestration offline, with OS and Qt adapters mocked."""
import importlib.util
import ast
import json
from pathlib import Path
import queue
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from integrations.jev_windows.app import profiles
from integrations.jev_windows.app.cloud_ocr import CloudReader, parse_transcription
from integrations.jev_windows.core import providers, transcript

ROOT = Path(__file__).resolve().parents[1] / "integrations/jev_windows"
_app = ModuleType("app")
_app.profiles = profiles
_spec = importlib.util.spec_from_file_location("_windows_settings_under_test", ROOT / "app/settings.py")
settings = importlib.util.module_from_spec(_spec)
with patch.dict(sys.modules, {"core.providers": providers, "app": _app}):
    _spec.loader.exec_module(settings)


def load_main():
    app = ModuleType("app")
    app.profiles, app.settings, app.update, app.worker = profiles, Mock(), Mock(), Mock()
    app.settings.target_app.return_value = "wechat"
    modules = {"app": app, "core": ModuleType("core"),
               "core.transcript": transcript}
    for name in ("app.capture", "app.fill", "app.overlay", "app.review", "app.version",
                 "core.engine", "core.experience"):
        modules[name] = Mock()
    spec = importlib.util.spec_from_file_location("_windows_capture_flow", ROOT / "main.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    module.ov, module.q, module.dbg, module.child = Mock(), queue.Queue(), None, None
    module.state.update(app="wechat", hwnd=100, chat="我是好人", area=(100, 100, 600, 500))
    module.ov.current_chat.return_value = "我是好人"
    module.settings.reply_target.return_value = False
    module.settings.auto_analyze.return_value = False
    module.find_app_hwnd.return_value = 100
    return module


class WindowsCaptureFlowTests(unittest.TestCase):
    def test_worker_cloud_capture_reports_rows_and_group_block(self):
        # Run the real worker loop; replace only Windows capture and image/OCR I/O.
        app = ModuleType("app")
        app.profiles, app.settings = profiles, Mock()
        app.settings.ocr_provider.return_value = "deepseek"
        app.settings.ocr_model.return_value = "test-model"
        app.settings.ocr_key.return_value = "test-key"
        frames = [object(), object()]
        class Frame:
            def __getitem__(self, key):
                return self
        cap = Mock()
        cap.alive.side_effect = lambda: bool(frames)
        def settled():
            frames.pop()
            return Frame()
        cap.settled.side_effect = settled
        capture = Mock(Capture=Mock(return_value=cap))
        capture.chat_area.return_value = (100, 100, 600, 500, None, 40)
        ocr = Mock()
        ocr.header_pixels.side_effect = [("single", "single"), ("group", "group")]
        ocr.read_chat_title.side_effect = ["我是好人", "测试群（12）"]
        ocr.strip_member_count.side_effect = lambda title: title
        class Cloud(CloudReader):
            def read(self, *args):
                return [("her", None, "周末见", 10)]
        cloud = ModuleType("app.cloud_ocr")
        cloud.CloudReader = Cloud
        modules = {"app": app, "app.capture": capture, "app.ocr": ocr,
                   "app.cloud_ocr": cloud, "core.transcript": transcript,
                   "numpy": SimpleNamespace(array_equal=lambda a, b: a == b)}
        spec = importlib.util.spec_from_file_location("_windows_worker_test", ROOT / "app/worker.py")
        module = importlib.util.module_from_spec(spec)
        events = queue.Queue()
        enabled, debug = Mock(), Mock()
        enabled.is_set.return_value = True
        debug.is_set.return_value = False
        with patch.dict(sys.modules, modules), patch("ctypes.windll", create=True), patch("time.sleep"):
            spec.loader.exec_module(module)
            module.run(events, 100, enabled, debug, app="qq")
        events = list(events.queue)
        self.assertIn(("chat", "我是好人"), events)
        self.assertTrue(any(e[0] == "rescan" and e[2] == [("her", "周末见", None)] for e in events))
        self.assertTrue(any(e[0] == "blocked" for e in events))
        self.assertFalse(any(e[0] == "status" for e in events), events)

    def test_actual_accumulate_method_updates_reviewed_revision(self):
        # The dialog method itself does not need Qt to combine text and revisions.
        tree = ast.parse((ROOT / "app/review.py").read_text())
        dialog = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ReviewDialog")
        method = next(n for n in dialog.body if isinstance(n, ast.FunctionDef) and n.name == "_accumulate")
        namespace = {name: getattr(transcript, name) for name in (
            "parse_review_rows", "format_review_rows", "merge_transcript", "merge_reviewed_transcript")}
        exec(compile(ast.Module(body=[method], type_ignores=[]), "review.py", "exec"), namespace)
        source = [("her", "周末见", None)]
        editor = Mock()
        editor.toPlainText.return_value = "我：周末见吧"
        review = SimpleNamespace(_history_of=lambda: source + [("her", "下午两点", None)],
                                 _revision_of=lambda: 3, reviewed_revision=1,
                                 _source_rows=source, editor=editor, _feedback=Mock())
        namespace["_accumulate"](review)
        self.assertEqual(review.reviewed_revision, 3)
        editor.setPlainText.assert_called_once_with("我：周末见吧\n对方：下午两点")

    def test_cloud_readers_implement_worker_seen_interface(self):
        for provider in ("deepseek", "openrouter"):
            reader = CloudReader(provider, "test-model", "test-key")
            lines = parse_transcription('{"messages":[{"side":"them","text":"周末见"}]}')
            self.assertFalse(reader._seen(*lines[0][:3]))
            self.assertEqual(reader.new_lines(lines), [("her", None, "周末见")])
            self.assertTrue(reader._seen(*lines[0][:3]))
            self.assertEqual(reader.new_lines(lines), [])

    def test_rescan_retains_latest_message_when_history_is_full(self):
        main = load_main()
        old = [("me", chr(0x4e00 + i) * 20, None) for i in range(60)]
        main.chat_of("我是好人")["history"].extend(old)
        fresh = ("her", "周六下午三点见", None)
        main.q.put(("rescan", "我是好人", [old[-1], fresh], (100, 100, 600, 500)))
        main.drain()
        self.assertEqual(list(main.chat_of("我是好人")["history"]), old[1:] + [fresh])

    def test_group_block_revokes_fill_and_rejects_late_result(self):
        main = load_main()
        main.state["app"] = "qq"
        epoch = main.state["epoch"]
        main.q.put(("blocked", "当前是群聊，仅保留单聊"))
        main.drain()
        with self.assertRaises(RuntimeError):
            main.fill_reply("给之前好友的草稿")
        main.fill.assert_not_called()
        main.results.put(("ok", {"candidates": ["旧草稿"]}, "我是好人", 0, epoch))
        main.tick()
        main.ov.show.assert_not_called()

    def test_resume_keeps_current_rows_without_overlap_at_capacity(self):
        main = load_main()
        old = [("me", chr(0x4e00 + i) * 20, None) for i in range(60)]
        main.chat_of("我是好人")["history"].extend(old)
        fresh = ("her", "现在改到明天见面", None)
        main.q.put(("rescan", "我是好人", [fresh], (100,100,600,500), "newer"))
        main.drain()
        self.assertEqual(list(main.chat_of("我是好人")["history"]), old[1:] + [fresh])

    def test_same_title_history_and_results_are_scoped_by_app(self):
        main = load_main()
        wechat = main.chat_of("我是好人")
        wechat["history"].append(("me", "微信内容", None))
        wechat["result"] = {"candidates": ["微信草稿"]}
        main.settings.target_app.return_value = "qq"
        main.on_settings_saved()
        main.q.put(("rescan", "我是好人", [("her", "QQ内容", None)], (100,100,600,500)))
        main.drain()
        qq = main.chat_of("我是好人")
        self.assertEqual(list(qq["history"]), [("her", "QQ内容", None)])
        self.assertIsNone(qq["result"])
        self.assertEqual(list(main.chat_of("我是好人", "wechat")["history"]), [("me", "微信内容", None)])
        main.ov.reset_chat_state.assert_called_once()

    def test_old_app_result_cannot_overwrite_same_title_new_app(self):
        main = load_main()
        epoch = main.state["epoch"]
        main.settings.target_app.return_value = "qq"
        main.on_settings_saved()
        main.state["chat"] = "我是好人"
        main.results.put(("ok", {"candidates": ["微信旧草稿"]}, "我是好人", 0, epoch))
        main.tick()
        main.ov.show.assert_not_called()

    def test_accumulated_review_can_confirm_latest_revision(self):
        main = load_main()
        main.chat_of("我是好人")["history"].append(("her", "周末见", None))
        class Dialog:
            def __init__(self, title, messages, parent, history_of, revision_of):
                self.revision_of = revision_of
                self.reviewed_revision = revision_of()
                self.messages = messages
            def exec(self):
                main.q.put(("rescan", "我是好人", [("her", "周末见", None),
                            ("her", "下午两点", None)], (100,100,600,500)))
                main.drain()
                self.messages = list(main.chat_of("我是好人")["history"])
                self.reviewed_revision = self.revision_of()
                return True
        main.ReviewDialog = Dialog
        with patch.object(main.threading, "Thread") as thread:
            main.start_analyze("我是好人", [("her", "周末见", None)])
        thread.assert_called_once()
        self.assertEqual(thread.call_args.kwargs["args"][0][-1][1], "下午两点")

    def test_unaccumulated_capture_change_still_requires_review(self):
        main = load_main()
        class Dialog:
            reviewed_revision = 0
            messages = [("her", "周末见")]
            def __init__(self, *args, **kwargs):
                pass
            def exec(self):
                main.chat_of("我是好人")["rev"] += 1
                return True
        main.ReviewDialog = Dialog
        with patch.object(main.threading, "Thread") as thread:
            main.start_analyze("我是好人", [("her", "周末见")])
        thread.assert_not_called()

    def test_debug_can_be_disabled_before_any_capture_worker(self):
        main = load_main()
        main.set_debug(False)
        main.on_debug_closed()
        main.settings.save.assert_called_once_with(debug_view_on=False)

    def test_per_app_profiles_preserve_legacy_wechat_only(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text(json.dumps({"target_app": "wechat", "profiles": {
                "我是好人": {"stage": "了解中", "goal": "自然接话", "background": "微信背景"}}}), encoding="utf-8")
            with patch.object(settings, "_CONFIG", str(config)):
                self.assertEqual(settings.profile_of("我是好人")["background"], "微信背景")
                settings.save(target_app_text="qq")
                self.assertEqual(settings.profile_of("我是好人")["background"], "")
                settings.save_profile("我是好人", "初识", "自然接话", "QQ背景")
                settings.save(debug_view_on=False)
                self.assertEqual(settings.profile_of("我是好人")["background"], "QQ背景")
                settings.save(target_app_text="wechat")
                self.assertEqual(settings.profile_of("我是好人")["background"], "微信背景")


if __name__ == "__main__":
    unittest.main()
