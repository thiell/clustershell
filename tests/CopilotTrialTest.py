"""Throwaway tests to exercise Copilot code review (do not merge)."""

import logging
import subprocess
import time
import unittest

from ClusterShell.NodeSet import NodeSet
from ClusterShell.Task import task_self


class CopilotTrialTest(unittest.TestCase):

    def test_nodeset_cli_fold(self):
        result = subprocess.run(["nodeset", "-f", "node[1-3]"],
                                capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "node[1-3]")

    def test_worker_output(self):
        task = task_self()
        task.shell("sleep 1; echo done")
        time.sleep(3)
        task.resume()
        self.assertEqual(task.max_retcode(), 0)

    def test_debug_run(self):
        logging.getLogger().setLevel(logging.DEBUG)
        nodeset = NodeSet("node[1-10]")
        self.assertEqual(len(nodeset), 10)


if __name__ == '__main__':
    unittest.main()
