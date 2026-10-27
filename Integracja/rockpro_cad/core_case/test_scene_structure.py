import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.scene_structure import group_for_part, required_t1_machining, validate_t1_machining, rebase_scene_expression


class SceneStructureTests(unittest.TestCase):
    def test_shared_stages_keep_sockets_with_wheels_and_braces_with_corners(self):
        self.assertEqual(group_for_part('socket/left/front')['id'], 'wheels')
        self.assertEqual(group_for_part('support/left')['id'], 'wheels')
        self.assertEqual(group_for_part('profile/base/brace-front-left')['id'], 'corners')
        self.assertEqual(group_for_part('hinge/1/base')['label'], '04. Zamki i zawiasy')

    def test_profile_cut_does_not_replace_plywood_cut(self):
        parts=['hinge/1/base', 'plywood/base/rear', 'profile/EG-0500_1/rear']
        profile=dict(key='hinge-profile/1/base', owner=parts[0], target=parts[2])
        with self.assertRaisesRegex(ValueError, 'BRAK_WYMAGANYCH_WYCIEC'):
            validate_t1_machining(parts, [profile])
        panel=dict(key='hinge-panel/1/base', owner=parts[0], target=parts[1])
        self.assertTrue(validate_t1_machining(parts, [profile, panel]))
        with self.assertRaisesRegex(ValueError, 'Powtórzone'):
            validate_t1_machining(parts, [profile, panel, panel])

    def test_wrong_target_and_orphan_are_rejected(self):
        parts=['hinge/1/base', 'plywood/base/rear', 'profile/EG-0500_1/rear']
        with self.assertRaisesRegex(ValueError, 'katalogowego'):
            validate_t1_machining(parts, [dict(key='bad', owner=parts[0], target=parts[0])])
        with self.assertRaisesRegex(ValueError, 'istniejącego'):
            validate_t1_machining(parts, [dict(key='bad', owner='hinge/9/base', target=parts[1])])

    def test_grouping_rebases_scene_paths_without_touching_local_expressions(self):
        self.assertEqual(rebase_scene_expression(r'Parent\Params\RP_Dlugosc/4', ['RP_Dlugosc']), r'Parent\Parent\Params\RP_Dlugosc/4')
        self.assertEqual(rebase_scene_expression(r'Parent\Parent\Params\RP_Dlugosc', ['RP_Dlugosc']), r'Parent\Parent\Parent\Params\RP_Dlugosc')
        self.assertEqual(rebase_scene_expression('RP_PolozenieX', ['RP_Dlugosc']), 'RP_PolozenieX')
