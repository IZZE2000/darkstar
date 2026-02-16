import unittest

from ml.corrector import _clamp_correction


class TestCorrectorClamp(unittest.TestCase):
    def test_clamp_correction_rev_f67(self):
        print("\n--- Testing Corrector Clamp (REV F67) ---")

        base = 0.1

        # 1. Test 50% correction (was valid, still valid)
        corr_50 = 0.05
        result = _clamp_correction(base, corr_50)
        self.assertEqual(result, 0.05)

        # 2. Test 150% correction (was capped at 0.05, now valid 0.15)
        corr_150 = 0.15
        result = _clamp_correction(base, corr_150)
        self.assertEqual(result, 0.15)

        # 3. Test 200% correction (allowed limit)
        corr_200 = 0.20
        result = _clamp_correction(base, corr_200)
        self.assertEqual(result, 0.20)

        # 4. Test 250% correction (capped at 200% = 0.20)
        corr_250 = 0.25
        result = _clamp_correction(base, corr_250)
        self.assertEqual(result, 0.20)

        # 5. Test negative 200%
        corr_neg_200 = -0.20
        result = _clamp_correction(base, corr_neg_200)
        self.assertEqual(result, -0.20)

        # 6. Test negative 300% (capped at -0.20)
        corr_neg_300 = -0.30
        result = _clamp_correction(base, corr_neg_300)
        self.assertEqual(result, -0.20)

        print("✅ Corrector clamp verified with ±200% limits!")


if __name__ == "__main__":
    unittest.main()
