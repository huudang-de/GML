import unittest

from app.agents.orchestrator import OrchestratorAgent
from app.agents.sql_agent import SQLAgent


class FakeDatabase:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def _execute(self, query, fetch):
        if self.error:
            raise self.error
        return self.result


class NoHallucinationGuardTests(unittest.TestCase):
    def _agent_with_db(self, db):
        agent = SQLAgent.__new__(SQLAgent)
        agent.db = db
        return agent

    def test_empty_sql_result_is_explicit_no_data(self):
        result = self._agent_with_db(FakeDatabase([])).execute_sql({"sql_query": "SELECT 1"})

        self.assertEqual(result["sql_status"], "no_data")
        self.assertEqual(result["row_count"], 0)
        self.assertEqual(result["data"], [])
        self.assertEqual(OrchestratorAgent._after_sql(None, result), "no_data")

        response = OrchestratorAgent._no_data_response(result)
        self.assertEqual(response["answer_type"], "no_data")
        self.assertNotIn("850", response["answer"])
        self.assertNotIn("620", response["answer"])

    def test_sql_error_never_reaches_synthesizer_route(self):
        result = self._agent_with_db(FakeDatabase(error=RuntimeError("database unavailable"))).execute_sql(
            {"sql_query": "SELECT 1", "retries": 0}
        )

        self.assertEqual(result["sql_status"], "execution_error")
        self.assertEqual(OrchestratorAgent._after_sql(None, result), "sql_error")
        self.assertEqual(OrchestratorAgent._sql_error_response(result)["answer_type"], "execution_error")

    def test_rows_are_preserved_for_a_grounded_answer(self):
        rows = [{"Doanh thu": 74991248312}]
        result = self._agent_with_db(FakeDatabase(rows)).execute_sql({"sql_query": "SELECT 1"})

        self.assertEqual(result["sql_status"], "ok")
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(result["data"], rows)
        self.assertEqual(OrchestratorAgent._after_sql(None, result), "synthesize")


if __name__ == "__main__":
    unittest.main()
