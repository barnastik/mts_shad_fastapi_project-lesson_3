from typing import List

from pydantic import BaseModel, field_validator, EmailStr
from pydantic_core import PydanticCustomError
from .books import IncomingBook, ReturnedAllBooks

__all__ = ["IncomingSeller", "ReturnedAllSellers", "ReturnedSeller"]


# Базовый класс "Книги", содержащий поля, которые есть во всех классах-наследниках.
class BaseSeller(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr


# Класс для валидации входящих данных. Не содержит id так как его присваивает БД.
class IncomingSeller(BaseSeller):
    books: List[IncomingBook]
    password: str

    @field_validator("first_name")
    @staticmethod
    def first_name_validator(first_name: str) -> str:
        if first_name is None or len(first_name) == 0:
            raise PydanticCustomError("Validation error", f"First name can't be empty.")
        return first_name

    @field_validator("last_name")
    @staticmethod
    def second_name_validator(last_name: str) -> str:
        if last_name is None or len(last_name) == 0:
            raise PydanticCustomError("Validation error", f"last name can't be empty.")
        return last_name

    @field_validator("password")
    @staticmethod
    def password_validator(passw: str) -> str:
        if passw is None or len(passw) == 0:
            raise PydanticCustomError("Validation error", f"password can't be empty.")
        return passw


# Класс, валидирующий исходящие данные. Он уже содержит id
class ReturnedSeller(BaseSeller):
    id: int
    books: ReturnedAllBooks


# Класс для возврата массива объектов "Книга"
class ReturnedAllSellers(BaseModel):
    sellers: list[ReturnedSeller] = []
