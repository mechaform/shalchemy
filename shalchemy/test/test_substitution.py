from shalchemy import sh, bin
from shalchemy.bin import cat, diff
from shalchemy.test.base import TestCase


class TestSubstitution(TestCase):
    def test_read_sub(self):
        self.assertTrue(diff(
            (cat('./fixtures/shuffled_words.txt') | bin.sort('-r')).read_sub,
            (cat('./fixtures/shuffled_words.txt') | bin.sort | bin.tac).read_sub,
        ) > '/dev/null')
        self.assertFalse(diff(
            (cat('./fixtures/shuffled_words.txt') | bin.sort('-r')).read_sub,
            (cat('./fixtures/shuffled_words.txt') | bin.sort).read_sub,
        ) > '/dev/null')

    def test_write_sub(self):
        sh.run(
            cat('./fixtures/shuffled_words.txt') |
            bin.tee(
                (cat > './fixtures/shuffled_words2.txt').write_sub,
                (cat > './fixtures/shuffled_words3.txt').write_sub,
            ) > '/dev/null'
        )
        self.assertEqual(
            str(cat('./fixtures/shuffled_words.txt')),
            str(cat('./fixtures/shuffled_words2.txt')),
        )
        self.assertEqual(
            str(cat('./fixtures/shuffled_words.txt')),
            str(cat('./fixtures/shuffled_words3.txt')),
        )
        sh.run(bin.rm('./fixtures/shuffled_words2.txt', './fixtures/shuffled_words3.txt'))
