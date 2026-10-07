import logging
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .metrics import EXPENSE_AMOUNT, EXPENSES_CREATED
from .models import Expense
from .schemas import CATEGORIES, CategoryTotal, ExpenseCreate, ExpenseOut, ExpenseUpdate, SummaryOut

logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("spendwise")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # The schema is owned by Alembic (`alembic upgrade head` runs before uvicorn starts).
    log.info("starting %s %s env=%s", settings.app_name, settings.app_version, settings.app_env)
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
Instrumentator(excluded_handlers=["/metrics", "/health", "/ready"]).instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)


def _get_or_404(db: Session, expense_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@app.get("/")
def root():
    return {"service": settings.app_name, "version": settings.app_version, "env": settings.app_env, "docs": "/docs"}


@app.get("/health")
def health():
    """Liveness: the process is up. Deliberately does not touch the database."""
    return {"status": "UP"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness: can we serve traffic, i.e. is the database reachable?"""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any DB error means not ready
        log.warning("readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "READY"}


@app.get("/api/categories")
def categories():
    return list(CATEGORIES)


@app.get("/api/expenses", response_model=list[ExpenseOut])
def list_expenses(
    category: str | None = Query(default=None),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    stmt = select(Expense).order_by(Expense.spent_on.desc(), Expense.id.desc())
    if category:
        stmt = stmt.where(Expense.category == category.upper())
    if month:
        year, mon = (int(p) for p in month.split("-"))
        start = date(year, mon, 1)
        end = date(year + (mon == 12), mon % 12 + 1, 1)
        stmt = stmt.where(Expense.spent_on >= start, Expense.spent_on < end)
    return list(db.scalars(stmt))


@app.get("/api/expenses/summary", response_model=SummaryOut)
def summary(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Expense.category, func.coalesce(func.sum(Expense.amount), 0), func.count(Expense.id))
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
    ).all()
    by_category = [CategoryTotal(category=c, total=Decimal(t), count=n) for c, t, n in rows]
    today = date.today()
    month_start = today.replace(day=1)
    this_month = db.scalar(select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.spent_on >= month_start))
    return SummaryOut(
        currency=settings.currency,
        count=sum(c.count for c in by_category),
        total=sum((c.total for c in by_category), Decimal(0)),
        this_month=Decimal(this_month or 0),
        top_category=by_category[0].category if by_category else None,
        by_category=by_category,
    )


@app.get("/api/expenses/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, expense_id)


@app.post("/api/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db)):
    expense = Expense(**payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    EXPENSES_CREATED.labels(category=expense.category).inc()
    EXPENSE_AMOUNT.observe(float(expense.amount))
    log.info("expense created id=%s category=%s amount=%s", expense.id, expense.category, expense.amount)
    return expense


@app.put("/api/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, payload: ExpenseUpdate, db: Session = Depends(get_db)):
    expense = _get_or_404(db, expense_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(expense, key, value)
    db.commit()
    db.refresh(expense)
    return expense


@app.delete("/api/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    db.delete(_get_or_404(db, expense_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
