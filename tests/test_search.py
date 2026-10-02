"""Backend integration tests; run with python3 -B -m unittest discover -s tests."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'python/search.py'


class SearchTest(unittest.TestCase):
    def test_external_docs_cache_and_exclusions(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            database = temp / 'cache' / 'index.sqlite3'
            for name, heading in [('docs one', 'Alpha'), ('docs two', 'Beta')]:
                root = temp / name
                for folder in ['topics', 'ref', 'releases', 'internals', 'intro']:
                    (root / folder).mkdir(parents=True)
                (root / 'topics/example.md').write_text(
                    f'# {heading}\n\n## Simple view\n```python\n# code comment\nvalue = 1\n```\n')
                (root / 'ref/api.md').write_text('# API\n\n## Marker\n')
                for path in ['releases/old.md', 'internals/contributing.md', 'intro/contributing.md']:
                    (root / path).write_text('# Excluded\n\nSimple view\n')
                output = subprocess.check_output([
                    sys.executable, str(SCRIPT), '--docs', str(root),
                    '--database', str(database), '--json', 'simple view'], text=True)
                result = json.loads(output)[0]
                self.assertEqual(result['path'], str(root / 'topics/example.md'))
                self.assertEqual(result['line'], 3)
                self.assertEqual(result['title'], f'{heading} › Simple view')
                with sqlite3.connect(database) as conn:
                    paths = {row[0] for row in conn.execute('SELECT DISTINCT path FROM sections')}
                    self.assertEqual(paths, {'topics/example.md', 'ref/api.md'})
                    body = conn.execute("SELECT body FROM sections WHERE heading = 'Simple view'").fetchone()[0]
                    self.assertIn('# code comment\nvalue = 1\n```', body)


if __name__ == '__main__':
    unittest.main()
