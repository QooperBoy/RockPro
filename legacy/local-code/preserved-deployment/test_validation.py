import copy
import json
import unittest
from pathlib import Path
from run_mvp import validate

class InputValidation(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(Path(__file__).with_name('mvp_config.json').read_text(encoding='utf-8'))

    def test_default_variants(self):
        validate(self.config)

    def test_invalid_dimensions(self):
        for value in (-1, 0, 799, 1101, float('nan'), float('inf'), True, '900'):
            with self.subTest(value=value):
                config = copy.deepcopy(self.config)
                config['variants'][0]['value_mm'] = value
                with self.assertRaises(ValueError):
                    validate(config)

    def test_path_escape(self):
        self.config['variants'][0]['name'] = '../source'
        with self.assertRaises(ValueError):
            validate(self.config)

    def test_duplicate_names(self):
        self.config['variants'][1]['name'] = self.config['variants'][0]['name']
        with self.assertRaises(ValueError):
            validate(self.config)

if __name__ == '__main__':
    unittest.main()
