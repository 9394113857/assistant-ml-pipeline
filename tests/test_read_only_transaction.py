import unittest


from train import enforce_read_only_transaction


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeConnection:
    def __init__(self, read_only_mode="on"):
        self.read_only_mode = read_only_mode
        self.statements = []

    def exec_driver_sql(self, statement):
        self.statements.append(statement)
        if statement == "SHOW transaction_read_only":
            return FakeResult(self.read_only_mode)
        return FakeResult(None)


class ReadOnlyTransactionTests(unittest.TestCase):
    def test_sets_read_only_before_verifying(self):
        connection = FakeConnection()

        enforce_read_only_transaction(connection)

        self.assertEqual(
            connection.statements,
            [
                "SET TRANSACTION READ ONLY",
                "SHOW transaction_read_only",
            ],
        )

    def test_rejects_transaction_when_postgres_reports_read_write(self):
        connection = FakeConnection(read_only_mode="off")

        with self.assertRaisesRegex(
            RuntimeError, "did not confirm a read-only transaction"
        ):
            enforce_read_only_transaction(connection)

    def test_verifies_each_invocation(self):
        connection = FakeConnection()

        enforce_read_only_transaction(connection)
        enforce_read_only_transaction(connection)

        self.assertEqual(connection.statements.count("SET TRANSACTION READ ONLY"), 2)


if __name__ == "__main__":
    unittest.main()
