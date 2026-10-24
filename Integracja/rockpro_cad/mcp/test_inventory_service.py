from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import inventory_service as inv
import project_store as store
import worker


def lot(ident='offcut-1',count=1,unit='offcut'):
    return dict(id=ident,item_id='plywood-test',unit=unit,location='rack-A',on_hand=count,
                dimensions_mm=[1000,600,9] if unit!='piece' else None,condition='usable',scope='synthetic_test')


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.p=patch.object(store,'DB_PATH',Path(self.temp.name)/'db.sqlite3');self.p.start();self.index=0
        self.cmd(dict(action='register',lot=lot()),0)

    def tearDown(self):self.p.stop();self.temp.cleanup()

    def cmd(self,c,revision,op=None):
        self.index+=1
        return worker.dispatch('inventory_command',dict(command=c,operation_id=op or 'op-'+str(self.index),expected_revision=revision))

    def reserve(self,r='hold-1',plan='plan-1',revision=1,ident='offcut-1',n=1,op=None):
        return self.cmd(dict(action='reserve',lot_id=ident,reservation_id=r,plan_id=plan,quantity=n),revision,op)

    def test_same_offcut_cannot_be_held_twice_and_concurrent_cas_has_one_winner(self):
        def reserve(index):
            try:return inv.inventory_command(dict(action='reserve',lot_id='offcut-1',reservation_id='h-'+str(index),plan_id='p-'+str(index),quantity=1),'race-'+str(index),1)
            except ValueError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(reserve,[1,2]))
        self.assertEqual(sum(r is not None for r in results),1)
        balance=inv.get_inventory()['lots'][0]
        self.assertEqual((balance['on_hand'],balance['reserved'],balance['free']),(1,1,0))
        with self.assertRaisesRegex(ValueError,'FREE_STOCK'):self.reserve('another','another',2)

    def test_issue_is_subtracted_once_and_consumption_cannot_be_cancelled_or_returned(self):
        self.reserve();self.cmd(dict(action='issue',reservation_id='hold-1'),2)
        b=inv.get_inventory()['lots'][0];self.assertEqual((b['on_hand'],b['reserved'],b['free']),(0,0,0))
        self.cmd(dict(action='consume',reservation_id='hold-1'),3)
        for action in ('cancel','return'):
            c=dict(action=action,reservation_id='hold-1')
            if action=='return':c['quantity']=1
            with self.assertRaises(ValueError):self.cmd(c,4)
        self.assertEqual(inv.get_inventory()['lots'][0]['on_hand'],0)

    def test_cancelling_only_held_material_frees_it(self):
        self.reserve();r=self.cmd(dict(action='cancel',reservation_id='hold-1'),2)
        self.assertEqual(r['lot']['free'],1);self.assertEqual(r['lot']['on_hand'],1)

    def test_partial_return_does_not_overcredit_and_replay_is_idempotent(self):
        self.cmd(dict(action='register',lot=lot('handles',10,'piece')),0)
        self.reserve('handles-hold','plan',1,'handles',4)
        self.cmd(dict(action='issue',reservation_id='handles-hold'),2)
        c=dict(action='return',reservation_id='handles-hold',quantity=2)
        self.cmd(c,3,'return-op');self.assertTrue(self.cmd(c,3,'return-op')['replayed'])
        self.assertEqual([b for b in inv.get_inventory()['lots'] if b['id']=='handles'][0]['on_hand'],8)
        with self.assertRaisesRegex(ValueError,'OPERATION_ID_REUSED'):self.cmd(c|dict(quantity=3),3,'return-op')
        with self.assertRaises(ValueError):self.cmd(c|dict(quantity=3),4)
        self.assertEqual(len(inv.get_inventory_history()['events']),5)

    def test_confirmed_delivery_is_separate_until_received(self):
        delivery=dict(id='delivery-1',item_id='locks',unit='piece',quantity=30,due_date='2026-11-01',confirmation_reference='PO-TEST',scope='synthetic_test')
        self.cmd(dict(action='delivery',delivery=delivery),0)
        snapshot=inv.get_inventory();self.assertEqual(len(snapshot['lots']),1);self.assertEqual(snapshot['deliveries'][0]['outstanding'],30)
        receipt=lot('received',20,'piece');receipt['item_id']='locks'
        self.cmd(dict(action='receive',delivery_id='delivery-1',lot=receipt),1)
        self.assertEqual(inv.get_inventory()['deliveries'][0]['outstanding'],10)
        with self.assertRaises(ValueError):self.cmd(dict(action='receive',delivery_id='delivery-1',lot=receipt|dict(id='over')),2)

    def test_quarantine_is_not_free_and_offcuts_are_physical_units(self):
        self.cmd(dict(action='register',lot=lot('quarantine')|dict(condition='quarantine')),0)
        with self.assertRaisesRegex(ValueError,'FREE_STOCK'):self.reserve('q','plan',1,'quarantine')
        with self.assertRaisesRegex(ValueError,'unique'):self.cmd(dict(action='register',lot=lot('duplicate',2)),0)


if __name__=='__main__':unittest.main()
