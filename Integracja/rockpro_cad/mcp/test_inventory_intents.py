from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import inventory_service as inventory
import inventory_intents as intents
import project_store as store
import worker
from test_inventory_service import lot


class InventoryIntentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.p=patch.object(store,'DB_PATH',Path(self.temp.name)/'qa.sqlite3');self.p.start()
        inventory.inventory_command(dict(action='register',lot=lot()),'seed-test',0)
        self.command=dict(action='reserve',lot_id='offcut-1',reservation_id='hold-test',plan_id='plan-test',quantity=1)

    def tearDown(self):self.p.stop();self.temp.cleanup()

    def prepare(self,ident='request-test',command=None,revision=1):
        return worker.dispatch('prepare_inventory_command',dict(command=self.command if command is None else command,
            operation_id=ident,expected_revision=revision,decision_reference='Synthetic operator instruction',actor='test-operator'))

    def test_preparation_is_durable_idempotent_and_does_not_change_stock(self):
        before=inventory.get_inventory();request=self.prepare()
        self.assertEqual(request['state'],'prepared');self.assertFalse(request['production_approved'])
        self.assertEqual(inventory.get_inventory(),before)
        self.assertEqual(self.prepare(),request)
        # A separate database connection finds the same request after the caller loses its memory.
        read=worker.dispatch('list_inventory_intents',{})['intents'][0]
        self.assertEqual(read['operation_id'],request['operation_id']);self.assertEqual(read['command'],self.command)
        with self.assertRaisesRegex(ValueError,'OPERATION_ID_REUSED'):
            self.prepare(command=self.command|dict(quantity=2))

    def test_concurrent_execution_commits_stock_and_receipt_once(self):
        self.prepare()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:intents.execute_inventory_intent('request-test'),range(2)))
        self.assertEqual([r['state'] for r in results],['committed','committed'])
        stock=inventory.get_inventory()['lots'][0];self.assertEqual((stock['on_hand'],stock['reserved'],stock['free']),(1,1,0))
        self.assertEqual(len(inventory.get_inventory_history()['events']),2)
        self.assertEqual(results[0]['receipt'],results[1]['receipt'])

    def test_lost_reply_after_commit_is_recovered_without_execution(self):
        self.prepare();execute=inventory.inventory_command
        def lost(*args):execute(*args);raise TimeoutError('simulated lost reply after commit')
        with patch.object(inventory,'inventory_command',side_effect=lost):
            with self.assertRaises(TimeoutError):intents.execute_inventory_intent('request-test')
        with patch.object(inventory,'inventory_command') as writer:
            read=intents.get_inventory_intent('request-test')
            self.assertEqual(read['state'],'committed');self.assertIsNotNone(read['receipt'])
            writer.assert_not_called()
        self.assertEqual(inventory.get_inventory()['lots'][0]['reserved'],1)

    def test_unknown_failure_before_commit_stays_discoverable_and_retains_exact_id(self):
        request=self.prepare()
        with patch.object(inventory,'inventory_command',side_effect=TimeoutError('unknown result')):
            with self.assertRaises(TimeoutError):intents.execute_inventory_intent('request-test')
        pending=intents.list_inventory_intents()['intents']
        self.assertEqual(pending,[request]);self.assertEqual(inventory.get_inventory()['lots'][0]['reserved'],0)
        self.assertEqual(intents.execute_inventory_intent('request-test')['state'],'committed')

    def test_changed_stock_revision_rejects_without_refreshing_request_or_affecting_stock(self):
        request=self.prepare()
        inventory.inventory_command(self.command|dict(reservation_id='other'),'other-operation',1)
        before=inventory.get_inventory()
        with self.assertRaisesRegex(ValueError,'REVISION_CONFLICT'):intents.execute_inventory_intent('request-test')
        rejected=intents.get_inventory_intent('request-test')
        self.assertEqual(rejected['state'],'rejected');self.assertEqual(rejected['expected_revision'],request['expected_revision'])
        self.assertEqual(rejected['command'],self.command);self.assertIsNone(rejected['receipt'])
        with self.assertRaisesRegex(ValueError,'TERMINAL'):intents.execute_inventory_intent('request-test')
        self.assertEqual(inventory.get_inventory(),before)

    def test_cancellation_prevents_execution_through_both_entry_points(self):
        request=self.prepare();before=inventory.get_inventory()
        result=worker.dispatch('cancel_inventory_intent',dict(operation_id='request-test',command_sha256=request['command_sha256']))
        self.assertEqual(result['state'],'cancelled')
        with self.assertRaisesRegex(ValueError,'TERMINAL'):intents.execute_inventory_intent('request-test')
        with self.assertRaisesRegex(ValueError,'TERMINAL'):inventory.inventory_command(self.command,'request-test',1)
        self.assertEqual(inventory.get_inventory(),before)

    def test_committed_request_cannot_be_cancelled_and_receipt_corruption_blocks_replay(self):
        request=self.prepare();intents.execute_inventory_intent('request-test')
        with self.assertRaisesRegex(ValueError,'TERMINAL'):intents.cancel_inventory_intent('request-test',request['command_sha256'])
        with store.db() as conn:conn.execute("UPDATE inventory_journal SET result_json='{}' WHERE operation_id='request-test'")
        with self.assertRaisesRegex(ValueError,'RECEIPT_INTEGRITY'):intents.get_inventory_intent('request-test')
        with self.assertRaisesRegex(ValueError,'RECEIPT_INTEGRITY'):intents.execute_inventory_intent('request-test')

    def test_corrupt_request_and_old_direct_operation_cannot_be_rebound(self):
        self.prepare()
        with store.db() as conn:conn.execute("UPDATE inventory_intents SET command_json='{}' WHERE operation_id='request-test'")
        with self.assertRaisesRegex(ValueError,'INTENT_INTEGRITY'):intents.execute_inventory_intent('request-test')
        with self.assertRaisesRegex(ValueError,'ALREADY_COMMITTED'):
            self.prepare('seed-test',dict(action='register',lot=lot()),0)
        self.assertEqual(inventory.get_inventory()['lots'][0]['reserved'],0)

    def test_cancel_execution_race_has_one_terminal_outcome(self):
        request=self.prepare()
        def action(cancel):
            try:
                result=(intents.cancel_inventory_intent('request-test',request['command_sha256']) if cancel
                        else intents.execute_inventory_intent('request-test'))
                return result['state']
            except ValueError:return 'refused'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(action,[True,False]))
        state=intents.get_inventory_intent('request-test')['state']
        self.assertIn(state,('committed','cancelled'))
        self.assertEqual(sorted(results),sorted([state,'refused']))
        self.assertEqual(inventory.get_inventory()['lots'][0]['reserved'],1 if state=='committed' else 0)

    def test_failed_journal_insert_rolls_back_stock_and_never_claims_committed(self):
        self.prepare();before=inventory.get_inventory()
        with store.db() as conn:
            conn.execute("""CREATE TRIGGER reject_receipt BEFORE INSERT ON inventory_journal
                WHEN NEW.operation_id='request-test' BEGIN SELECT RAISE(ABORT,'synthetic journal failure'); END""")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'synthetic journal failure'):intents.execute_inventory_intent('request-test')
        rejected=intents.get_inventory_intent('request-test')
        self.assertEqual(rejected['state'],'rejected');self.assertIsNone(rejected['receipt'])
        self.assertEqual(inventory.get_inventory(),before)

    def test_prepared_receipt_is_bound_to_delivery_revision_and_cannot_overreceive(self):
        supply=dict(id='supply-test',item_id='locks-test',unit='piece',quantity=20,due_date='2030-01-01',
                    confirmation_reference='SYNTHETIC-PO',scope='synthetic_test')
        inventory.inventory_command(dict(action='delivery',delivery=supply),'supply-create',0)
        receipt=lot('receipt-test',10,'piece')|dict(item_id='locks-test')
        command=dict(action='receive',delivery_id='supply-test',lot=receipt)
        self.prepare('receive-request',command,1)
        inventory.inventory_command(dict(action='receive',delivery_id='supply-test',lot=receipt|dict(id='other-receipt',on_hand=5)),'other-receive',1)
        before=inventory.get_inventory()
        with self.assertRaisesRegex(ValueError,'DELIVERY_REVISION_CONFLICT'):intents.execute_inventory_intent('receive-request')
        rejected=intents.get_inventory_intent('receive-request')
        self.assertEqual(rejected['state'],'rejected');self.assertEqual(rejected['expected_revision'],1)
        self.assertEqual(inventory.get_inventory(),before)


if __name__=='__main__':unittest.main()
