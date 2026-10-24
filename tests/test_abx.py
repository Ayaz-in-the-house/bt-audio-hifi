"""U18: ABX saf mantığı — deneme üretimi dengeli/tekrarlanabilir, binom p-değeri doğru."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import abx  # noqa: E402


class TestAbx(unittest.TestCase):
    def test_u18_pvalue(self):
        # P(X >= k | n, 0.5) tek yönlü
        self.assertAlmostEqual(abx.p_value(12, 12), 1 / 4096, places=8)
        self.assertAlmostEqual(abx.p_value(6, 12), 0.6128, places=4)
        self.assertAlmostEqual(abx.p_value(10, 12), 0.0193, places=4)
        self.assertEqual(abx.p_value(0, 12), 1.0)

    def test_trials_reproducible_and_balanced(self):
        t1, t2 = abx.make_trials(12, seed=5), abx.make_trials(12, seed=5)
        self.assertEqual(t1, t2)
        self.assertEqual(sorted(set(t1)), ["A", "B"])
        self.assertEqual(t1.count("A"), 6)                      # dengeli: yarı yarıya

    def test_verdict(self):
        self.assertEqual(abx.verdict(11, 12)["distinguishable"], True)
        self.assertEqual(abx.verdict(7, 12)["distinguishable"], False)

    def test_switch_plan_constant_cue(self):
        # her çalmadan önce: önce diğer codec, sonra hedef → her denemede aynı geçiş dizisi
        self.assertEqual(abx.switch_plan("aac", "sbc"), ["sbc", "aac"])
        self.assertEqual(abx.switch_plan("sbc", "aac"), ["aac", "sbc"])


if __name__ == "__main__":
    unittest.main()
