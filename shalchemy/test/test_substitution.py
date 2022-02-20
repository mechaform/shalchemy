from shalchemy import sh, bin
from shalchemy.bin import cat, diff, echo
from shalchemy.test.base import TestCase, random_filename


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

    def test_write_sub_kwarg(self):
        fname1 = random_filename()
        fname2 = random_filename()

        sh.run(
            cat('./fixtures/shuffled_words.txt') |
            bin.shalchemyprobe.kwtee(
                apple=(cat > fname1).write_sub,
                banana=(cat > fname2).write_sub,
            )
        )
        self.assertEqual(str(cat(fname1)), str(cat('./fixtures/shuffled_words.txt')))
        self.assertEqual(str(cat(fname2)), str(cat('./fixtures/shuffled_words.txt')))
        sh.run(bin.rm(fname1))
        sh.run(bin.rm(fname2))

    def test_read_sub_kwarg(self):
        result = str(
            bin.shalchemyprobe.kwcat(
                apple=(echo('Apple')).read_sub,
                banana=(echo('Banana')).read_sub,
                carrot=(echo('Carrot')).read_sub,
            )
        )
        self.assertEqual(result, 'Apple\nBanana\nCarrot\n')
