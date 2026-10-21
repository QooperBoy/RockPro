"""GREEN: existing layout API, exact synthetic dimensions and placements."""
import unittest
from contract import FIXTURES
from oracle import near
import layout


class ExistingLayoutRegression(unittest.TestCase):
    def test_frozen_abc_dimensions_and_legacy_placements(self):
        for case in FIXTURES['cases']:
            with self.subTest(case=case['id']):
                actual = layout.calculate_layout(case['spec']['layout'])
                e = case['expected']
                near(actual['internal'], e['internal'], 'usable space')
                near(actual['external'], e['plywood_external'], 'bare plywood')
                near(actual['parameters']['RP_BaseHeight'], e['base_height'])
                near(actual['parameters']['RP_LidHeight'], e['lid_height'])
                near(actual['parameters']['RP_Thickness'], 9)
                self.assertEqual(actual['checks'], {'collisions': False, 'contained': True})
                for kind, expected in [('device', case['legacy_boxes']['devices']),
                                       ('accessory', [case['legacy_boxes']['accessory']]),
                                       ('divider', case['legacy_boxes']['dividers'])]:
                    parts = [p for p in actual['boxes'] if p['kind'] == kind]
                    self.assertEqual(len(parts), len(expected))
                    for p, ep in zip(parts, expected):
                        near(p['pos'], ep['pos'], kind + ' position')
                        near(p['size'], ep['size'], kind + ' dimensions')
                self.assertEqual(len([p for p in actual['boxes'] if p['kind'] == 'divider']), 2)


if __name__ == '__main__':
    unittest.main()
