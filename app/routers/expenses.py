from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
import datetime as dt

from .. import models, schemas
from ..deps import get_current_user, get_db
from ..filters import Period, resolve_date_range

router = APIRouter(prefix="/expenses", tags=["expenses"])


def get_owned_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Expense:
    expense = db.scalar(
        select(models.Expense).where(
            models.Expense.id == expense_id,
            models.Expense.user_id == current_user.id,
        )
    )
    if expense is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    return expense


@router.post("", response_model=schemas.ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    expense = models.Expense(**payload.model_dump(), user_id=current_user.id)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("", response_model=list[schemas.ExpenseOut])
def list_expenses(
    period: Period | None = None,
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    start, end = resolve_date_range(period, start_date, end_date)

    stmt = select(models.Expense).where(models.Expense.user_id == current_user.id)
    if start is not None:
        stmt = stmt.where(models.Expense.date >= start)
    if end is not None:
        stmt = stmt.where(models.Expense.date <= end)

    stmt = stmt.order_by(models.Expense.date.desc(), models.Expense.id.desc())
    return db.scalars(stmt).all()


@router.get("/{expense_id}", response_model=schemas.ExpenseOut)
def get_expense(expense: models.Expense = Depends(get_owned_expense)):
    return expense


@router.patch("/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(
    payload: schemas.ExpenseUpdate,
    expense: models.Expense = Depends(get_owned_expense),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense: models.Expense = Depends(get_owned_expense),
    db: Session = Depends(get_db),
):
    db.delete(expense)
    db.commit()