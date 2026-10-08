import tempfile, unittest
from pathlib import Path
from dupe_radar import scan
class ScanTests(unittest.TestCase):
 def test_equal_size_different_content_and_empty(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d)
   for name,data in [('a',b'abc'),('b',b'abc'),('c',b'xyz'),('empty1',b''),('empty2',b'')]: (r/name).write_bytes(data)
   out=scan(r);self.assertEqual(out['reclaimable_bytes'],3);self.assertEqual(len(out['groups']),2);self.assertEqual(out['errors'],[])
 def test_exclude_report(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'a').write_text('x');(r/'report').write_text('x')
   self.assertEqual(scan(r,r/'report')['groups'],[])
