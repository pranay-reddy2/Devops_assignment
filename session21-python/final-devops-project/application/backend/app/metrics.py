"""Business metrics on top of the HTTP metrics from the instrumentator."""
from prometheus_client import Counter, Histogram

EXPENSES_CREATED = Counter(
    "spendwise_expenses_created_total", "Expenses created through the API", ["category"]
)
EXPENSE_AMOUNT = Histogram(
    "spendwise_expense_amount",
    "Amount of created expenses",
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000),
)
