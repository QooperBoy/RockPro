import copy
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rockpro_cad.core_case.t2_parametric import REFERENCE, NOTES, validate_parameters, combine_local, zero, point, expression, evaluate
from rockpro_cad.core_case.profile_rules import value


class T2ParametricTests(unittest.TestCase):
    def test_source_dimensions_and_presentation_limits(self):
        self.assertEqual(validate_parameters(REFERENCE),REFERENCE)
        for name,bad in [('RP_GlebokoscObudowy',626),('RP_WysokoscObudowy',900),('RP_UniesienieRacka',-1),('RP_OdsuniecieKlapy',math.nan),('RP_UniesienieCzapki',True),('RP_PrzesuniecieUchwytow',11)]:
            with self.subTest(name=name),self.assertRaises(ValueError):validate_parameters(dict(REFERENCE,**{name:bad}))
        with self.assertRaises(ValueError):validate_parameters(dict(REFERENCE,RP_Szerokosc=600))

    def test_rack_cancels_hood_lift_through_reflected_parent_axes(self):
        parent=zero();child=zero();parent['RP_UniesienieCzapki'][2]=1;child['RP_UniesienieRacka'][2]=1
        mirror=[[-1,0,0,0],[0,0,1,0],[0,1,0,0],[100,200,300,1]]
        local=combine_local(child,parent,mirror)
        for values in [dict(REFERENCE,RP_UniesienieCzapki=120),dict(REFERENCE,RP_UniesienieCzapki=120,RP_UniesienieRacka=80)]:
            pdelta=[sum(parent[n][j]*(values[n]-REFERENCE[n]) for n in REFERENCE) for j in range(3)]
            ldelta=[sum(local[n][j]*(values[n]-REFERENCE[n]) for n in REFERENCE) for j in range(3)]
            world=[pdelta[j]+sum(ldelta[k]*mirror[k][j] for k in range(3)) for j in range(3)]
            self.assertEqual(world,[0,0,values['RP_UniesienieRacka']])

    def test_linear_mm_expressions_match_numeric_motion(self):
        c={'RP_GlebokoscObudowy':.5,'RP_OdsuniecieKlapy':-1}
        target=dict(REFERENCE,RP_GlebokoscObudowy=667,RP_OdsuniecieKlapy=50)
        self.assertEqual(value(expression(100,c),target),70)
        self.assertEqual(evaluate(100,c,target),70)

    def test_all_user_parameters_have_polish_descriptions(self):
        self.assertEqual(set(NOTES),set(REFERENCE))
        self.assertTrue(all(len(note)>90 for note in NOTES.values()))
        self.assertIn('Rack nie podnosi',NOTES['RP_UniesienieCzapki'])
