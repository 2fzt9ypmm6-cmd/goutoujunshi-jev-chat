import unittest

from integrations.jev_windows.core.transcript import merge_transcript, similar


class TranscriptMergeTest(unittest.TestCase):
    def _texts(self, rows):
        return [t for _, t, _ in rows]

    def test_scrollback_overlapping_head_prepends_in_order(self):
        old = [("me", "行，周六见", None), ("her", "好呀", None), ("me", "那到时候联系", None)]
        scan = [("her", "在吗", None), ("me", "在的", None), ("her", "周六见吗", None), ("me", "行，周六见", None)]
        merged = merge_transcript(old, scan)
        self.assertEqual(self._texts(merged),
                         ["在吗", "在的", "周六见吗", "行，周六见", "好呀", "那到时候联系"])

    def test_no_overlap_treats_scan_as_older(self):
        old = [("her", "好呀", None)]
        scan = [("her", "更早的一句话", None)]
        self.assertEqual(self._texts(merge_transcript(old, scan)), ["更早的一句话", "好呀"])

    def test_latest_view_matches_tail_without_duplicates(self):
        old = [("me", "一", None), ("her", "二", None), ("me", "三", None)]
        scan = [("her", "二", None), ("me", "三", None)]
        self.assertEqual(self._texts(merge_transcript(old, scan)), ["一", "二", "三"])

    def test_scan_covering_editor_inserts_older_part_in_place(self):
        old = [("me", "你好", None), ("her", "在的", None)]
        scan = [("her", "更早的一条", None), ("me", "你好", None), ("her", "在的", None)]
        self.assertEqual(self._texts(merge_transcript(old, scan)),
                         ["更早的一条", "你好", "在的"])

    def test_empty_sides_pass_through(self):
        self.assertEqual(merge_transcript([], [("me", "x", None)]), [("me", "x", None)])
        self.assertEqual(merge_transcript([("me", "x", None)], []), [("me", "x", None)])

    def test_newer_lines_missing_from_history_are_appended(self):
        old = [("me", "一", None), ("her", "二", None)]
        scan = [("her", "二", None), ("her", "二点五", None)]
        self.assertEqual(self._texts(merge_transcript(old, scan)), ["一", "二", "二点五"])


class SimilarTest(unittest.TestCase):
    def test_ocr_jitter_is_similar(self):
        self.assertTrue(similar("不好意思", "不好竟思"))
        self.assertTrue(similar("傻逼了", "傻逼"))

    def test_different_messages_are_not_similar(self):
        self.assertFalse(similar("晚上好", "今天去哪吃"))


if __name__ == "__main__":
    unittest.main()
