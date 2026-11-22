"""Run reproducible integration tests and save honest, machine-readable results."""
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.test_system import SystemTests


class Result(unittest.TextTestResult):
    records = []

    def startTest(self, test):
        self.started = time.perf_counter()
        super().startTest(test)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append(dict(test=test.id().split('.')[-1], status='passed',
                                 seconds=round(time.perf_counter() - self.started, 3)))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append(dict(test=test.id().split('.')[-1], status='failed', detail=self._exc_info_to_string(err, test)))

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append(dict(test=test.id().split('.')[-1], status='error', detail=self._exc_info_to_string(err, test)))


if __name__ == '__main__':
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SystemTests))
    report = dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                  duration_seconds=round(time.perf_counter() - started, 3),
                  run_directory=str(getattr(SystemTests, 'run_dir', '')), results=result.records)
    (ROOT / 'docs').mkdir(exist_ok=True)
    (ROOT / 'docs' / 'test-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    sys.exit(0 if result.wasSuccessful() else 1)
