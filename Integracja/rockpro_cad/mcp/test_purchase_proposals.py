import copy
from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch
from purchase_proposals import calculate_purchases


def inputs(late=False):
    requirements=dict(scope='synthetic_test',bindings=[dict(bom_sha256='a'*64)],lines=[dict(
        id='locks-1',item_id='lock-test',unit='piece',quantity=120,required_date='2026-11-05')])
    inventory=dict(lots=[dict(id='lot',item_id='lock-test',unit='piece',scope='synthetic_test',
        condition='usable',on_hand=30,reserved=10,free=20)],deliveries=[dict(
        id='delivery',item_id='lock-test',unit='piece',scope='synthetic_test',outstanding=30,
        due_date='2026-11-06' if late else '2026-11-01')])
    offers=[dict(id='offer',item_id='lock-test',unit='piece',supplier='test-supplier',currency='PLN',
        quote_date='2026-10-20',valid_until='2026-11-10',pack_size=25,moq=25,lead_days=3,
        available_quantity=1000,price_breaks=[dict(min_quantity=1,unit_net='10')],shipping_net='20',tax_percent='23')]
    policy=dict(as_of_date='2026-10-25',currency='PLN',max_surplus_units=50,max_cash_gross='10000',approved_substitutes={})
    return requirements,inventory,offers,policy


class PurchaseTests(unittest.TestCase):
    def test_required_120_with_20_free_30_on_time_and_pack_25_buys_75(self):
        r=calculate_purchases(*inputs());line=r['lines'][0];o=line['preferred_option']
        self.assertEqual(line['shortage'],70);self.assertEqual(o['quantity'],75);self.assertEqual(o['surplus'],5)
        self.assertEqual(o['total_net'],'770.00');self.assertEqual(o['total_gross'],'947.10')
        self.assertFalse(r['orders_placed'])

    def test_late_delivery_does_not_cover_requirement(self):
        r=calculate_purchases(*inputs(late=True))
        self.assertEqual(r['lines'][0]['preferred_option']['quantity'],100)

    def test_same_supply_not_allocated_twice_and_reserved_not_subtracted_again(self):
        req,stock,offers,policy=inputs();req['lines'].append(req['lines'][0]|dict(id='locks-2',quantity=10))
        r=calculate_purchases(req,stock,offers,policy)
        self.assertEqual([line['shortage'] for line in r['lines']],[70,10])
        self.assertEqual(sum(a['quantity'] for l in r['lines'] for a in l['allocations']),50)

    def test_price_break_moq_shipping_and_limits_are_visible(self):
        req,stock,offers,policy=inputs();offers[0]['price_breaks'].append(dict(min_quantity=100,unit_net='6'))
        r=calculate_purchases(req,stock,offers,policy)
        self.assertEqual(r['lines'][0]['preferred_option']['quantity'],100)
        self.assertEqual(r['lines'][0]['preferred_option']['total_gross'],'762.60')
        policy['max_surplus_units']=10
        r=calculate_purchases(req,stock,offers,policy);self.assertEqual(r['lines'][0]['preferred_option']['quantity'],75)
        policy['max_cash_gross']='500'
        r=calculate_purchases(req,stock,offers,policy);self.assertIsNone(r['lines'][0]['preferred_option'])
        self.assertTrue(all('cash_limit' in o['restrictions'] for o in r['lines'][0]['options']))

    def test_incomplete_expired_quotes_and_unapproved_substitutes_are_not_selected(self):
        req,stock,offers,policy=inputs();offers[0]['shipping_net']=None
        r=calculate_purchases(req,stock,offers,policy);self.assertEqual(r['lines'][0]['rejected_offers'][0]['reason'],'incomplete_offer')
        req,stock,offers,policy=inputs();offers[0]['valid_until']='2026-10-24'
        self.assertIsNone(calculate_purchases(req,stock,offers,policy)['lines'][0]['preferred_option'])
        req,stock,offers,policy=inputs();offers[0]['item_id']='other'
        self.assertFalse(calculate_purchases(req,stock,offers,policy)['lines'][0]['options'])
        policy['approved_substitutes']={'lock-test':['other']}
        self.assertTrue(calculate_purchases(req,stock,offers,policy)['lines'][0]['preferred_option']['substitute'])

    def test_lead_time_and_confirmed_availability_block_infeasible_offer(self):
        req,stock,offers,policy=inputs();offers[0].update(lead_days=20,available_quantity=50)
        line=calculate_purchases(req,stock,offers,policy)['lines'][0]
        self.assertIsNone(line['preferred_option'])
        self.assertEqual(set(line['options'][0]['restrictions']),{'late_arrival','insufficient_confirmed_availability'})

    def test_missing_identity_supplier_or_unit_is_reported_without_inventing_an_offer(self):
        for field in ('id','supplier','item_id','unit'):
            with self.subTest(field=field):
                requirements,stock,offers,policy=inputs();offers[0][field]=None
                result=calculate_purchases(requirements,stock,offers,policy)
                self.assertIsNone(result['lines'][0]['preferred_option'])
                self.assertEqual(result['offer_issues'][0]['offer_index'],0)
                self.assertIn(field,result['offer_issues'][0]['missing_fields'])
                self.assertFalse(result['orders_placed']);self.assertFalse(result['production_approved'])

    def test_incomplete_unrelated_offer_stays_visible_without_blocking_a_valid_quote(self):
        requirements,stock,offers,policy=inputs()
        offers.append(offers[0]|dict(id='unrelated-incomplete',item_id=None,supplier=None))
        result=calculate_purchases(requirements,stock,offers,policy)
        self.assertEqual(result['lines'][0]['preferred_option']['quantity'],75)
        self.assertEqual(result['offer_issues'],[dict(offer_index=1,offer_id='unrelated-incomplete',
            reason='incomplete_offer',missing_fields=['item_id','supplier'])])

    def test_operator_preview_reads_current_shared_inventory_without_writing(self):
        import inventory_service as inv
        import project_store as store
        import worker
        with tempfile.TemporaryDirectory() as temp,patch.object(store,'DB_PATH',Path(temp)/'qa.sqlite3'):
            stock=dict(id='stock-test',item_id='lock-test',unit='piece',location='rack-test',on_hand=30,
                       dimensions_mm=None,condition='usable',scope='synthetic_test')
            inv.inventory_command(dict(action='register',lot=stock),'qa-register',0)
            hold=dict(action='reserve',lot_id='stock-test',reservation_id='qa-held',plan_id='qa-plan',quantity=10)
            inv.inventory_command(hold,'qa-hold',1)
            inv.inventory_command(dict(action='delivery',delivery=dict(id='supply-test',item_id='lock-test',unit='piece',
                quantity=30,due_date='2026-11-01',confirmation_reference='QA-PO',scope='synthetic_test')),'qa-delivery',0)
            req,_,offers,policy=inputs();before=hashlib.sha256(store.DB_PATH.read_bytes()).hexdigest()
            result=worker.dispatch('preview_purchases',dict(requirements=req,offers=offers,policy=policy))
            self.assertEqual(result['lines'][0]['preferred_option']['quantity'],75)
            self.assertEqual(hashlib.sha256(store.DB_PATH.read_bytes()).hexdigest(),before)
            inv.inventory_command(hold|dict(reservation_id='qa-other'),'qa-other-hold',2)
            changed=worker.dispatch('preview_purchases',dict(requirements=req,offers=offers,policy=policy))
            self.assertEqual(changed['lines'][0]['preferred_option']['quantity'],100)
            self.assertNotEqual(result['input_sha256'],changed['input_sha256'])
            self.assertFalse(changed['orders_placed'])


if __name__=='__main__':unittest.main()
