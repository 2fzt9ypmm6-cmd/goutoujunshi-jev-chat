import unittest

from integrations.jev_windows.app import profiles


class PickWindowTest(unittest.TestCase):
    def _candidate(self, hwnd, exe, cls, title="", area=0):
        return {"hwnd": hwnd, "exe": exe, "cls": cls, "title": title, "area": area}

    def test_qq_picks_largest_visible_electron_window(self):
        candidates = [
            self._candidate(1, "qq.exe", "Chrome_WidgetWin_0"),
            self._candidate(2, "qq.exe", "Chrome_WidgetWin_1", "QQ", 800_000),
            self._candidate(3, "qq.exe", "Chrome_WidgetWin_1", "QQ", 462_000),
        ]
        self.assertEqual(profiles.pick_window("qq", candidates), 2)

    def test_qq_returns_none_when_only_other_apps(self):
        candidates = [self._candidate(9, "weixin.exe", "Qt51514QWindowIcon", "微信", 999_999)]
        self.assertIsNone(profiles.pick_window("qq", candidates))

    def test_wechat_prefers_main_window_title(self):
        candidates = [
            self._candidate(1, "weixin.exe", "Qt51514QWindowIcon", "Weixin", 999_999),
            self._candidate(2, "weixin.exe", "Qt51514QWindowIcon", "微信", 100),
        ]
        self.assertEqual(profiles.pick_window("wechat", candidates), 2)

    def test_wechat_falls_back_to_first_visible_window(self):
        candidates = [self._candidate(5, "wechat.exe", "WeChatMainWndForPC", "微信 3.9", 100)]
        self.assertEqual(profiles.pick_window("wechat", candidates), 5)


class ClassifyBubbleTest(unittest.TestCase):
    def test_wechat_green_bubble_is_me(self):
        self.assertEqual(profiles.classify_bubble("wechat", (149, 236, 105), 150), "me")

    def test_wechat_light_bubble_with_strong_ink_is_her(self):
        self.assertEqual(profiles.classify_bubble("wechat", (255, 255, 255), 178), "her")

    def test_wechat_low_contrast_note_is_gray(self):
        self.assertEqual(profiles.classify_bubble("wechat", (240, 240, 240), 90), "gray")

    def test_qq_gold_theme_bubble_is_me(self):
        self.assertEqual(profiles.classify_bubble("qq", (246, 216, 96), 160), "me")

    def test_qq_default_blue_bubble_is_me(self):
        self.assertEqual(profiles.classify_bubble("qq", (18, 150, 255), 180), "me")

    def test_qq_light_bubble_with_strong_ink_is_her(self):
        self.assertEqual(profiles.classify_bubble("qq", (247, 245, 250), 190), "her")

    def test_qq_low_contrast_stamp_is_gray(self):
        self.assertEqual(profiles.classify_bubble("qq", (242, 243, 245), 90), "gray")


class FillPointTest(unittest.TestCase):
    def test_wechat_fill_point_unchanged(self):
        self.assertEqual(profiles.fill_point((100, 200, 900, 600), "wechat"), (160, 640))

    def test_qq_fill_point_sits_below_message_area(self):
        x, y = profiles.fill_point((100, 200, 900, 600), "qq")
        self.assertEqual(x, 160)
        self.assertGreater(y, 600)


class TextRegionTest(unittest.TestCase):
    def test_wechat_requires_flat_background(self):
        self.assertTrue(profiles.looks_like_text_region("wechat", (255, 255, 255), 0.5))
        self.assertFalse(profiles.looks_like_text_region("wechat", (255, 255, 255), 0.3))

    def test_qq_accepts_dense_saturated_bubble(self):
        # 金黄色主题气泡实测众数占比 0.23~0.32（短句密排），比微信低得多；高饱和底色放宽到 15%
        self.assertTrue(profiles.looks_like_text_region("qq", (185, 136, 56), 0.23))
        self.assertTrue(profiles.looks_like_text_region("qq", (245, 250, 255), 0.66))

    def test_qq_rejects_low_coverage_and_neutral_regions(self):
        self.assertFalse(profiles.looks_like_text_region("qq", (185, 136, 56), 0.10))  # 覆盖太少 = 画里的字
        self.assertFalse(profiles.looks_like_text_region("qq", (223, 242, 252), 0.30))  # 中性底色 30% 不够


class NamesTest(unittest.TestCase):
    def test_app_display_names(self):
        self.assertEqual(profiles.app_name("wechat"), "微信")
        self.assertEqual(profiles.app_name("qq"), "QQ")

    def test_wechat_window_error_stays_verbatim(self):
        self.assertIn("Weixin.exe", profiles.window_error("wechat"))

    def test_qq_window_error_mentions_qq(self):
        self.assertIn("QQ", profiles.window_error("qq"))


class PaneToleranceTest(unittest.TestCase):
    def test_wechat_tolerance_stays_tight(self):
        self.assertTrue(profiles.on_pane("wechat", (240, 240, 240), (240, 240, 242)))
        self.assertFalse(profiles.on_pane("wechat", (240, 240, 240), (245, 242, 238)))

    def test_qq_tolerance_covers_the_gradient(self):
        # QQ 皮肤整窗渐变：名字底下（左）和滚动条内侧（右）的底色差 ~14；微信的 6 会把群里发言人名字全滤掉
        self.assertTrue(profiles.on_pane("qq", (227, 241, 252), (236, 246, 252)))

    def test_qq_still_rejects_bubble_color(self):
        self.assertFalse(profiles.on_pane("qq", (245, 250, 255), (227, 241, 252)))

if __name__ == "__main__":
    unittest.main()
