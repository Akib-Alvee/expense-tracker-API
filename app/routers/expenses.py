from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db

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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stmt = (
        select(models.Expense)
        .where(models.Expense.user_id == current_user.id)
        .order_by(models.Expense.date.desc(), models.Expense.id.desc())
    )
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