from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import icecream as ic
from src.configurations.database import get_async_session
from src.models.books import Book
from src.models.sellers import Seller
from src.schemas import IncomingBook, ReturnedAllBooks, ReturnedBook

# todo: Make connect with sellers __PS

books_router = APIRouter(tags=["books"], prefix="/books")

# Больше не симулируем хранилище данных. Подключаемся к реальному, через сессию.
DBSession = Annotated[AsyncSession, Depends(get_async_session)]


# Ручка для создания записи о книге в БД. Возвращает созданную книгу.
@books_router.post("/", response_model=ReturnedBook, status_code=status.HTTP_201_CREATED)  # Прописываем модель ответа
async def create_book(
        book: IncomingBook, session: DBSession
):  # прописываем модель валидирующую входные данные и сессию как зависимость.
    # это - бизнес логика. Обрабатываем данные, сохраняем, преобразуем и т.д.
    new_book = Book(
        title=book.title,
        author=book.author,
        year=book.year,
        count_pages=book.count_pages,
        seller_id=book.seller_id
    )
    session.add(new_book)
    await session.flush()
    await session.refresh(new_book)
    return_book = ReturnedBook(
        title=book.title,
        author=book.author,
        year=book.year,
        count_pages=book.count_pages,
        id=new_book.id
    )
    return new_book


# Ручка, возвращающая все книги
@books_router.get("/", response_model=ReturnedAllBooks)
async def get_all_books(session: DBSession):
    # Хотим видеть формат:
    # books: [{"id": 1, "title": "Blabla", ...}, {"id": 2, ...}]
    query = select(Book)
    res = await session.execute(query)
    books = res.scalars().all()
    return {"books": books}


# Ручка для получения книги по ее ИД
@books_router.get("/{book_id}", response_model=ReturnedBook)
async def get_book(book_id: int, session: DBSession):
    res = await session.get(Book, book_id)
    return res


# Ручка для удаления книги
@books_router.delete("/{book_id}")
async def delete_book(book_id: int, session: DBSession):
    # deleted_book = await session.get(Book, book_id)
    # ic(deleted_book)  # Красивая и информативная замена для print. Полезна при отладке.
    # if deleted_book:
    #     await session.delete(deleted_book)
    #
    # return Response(status_code=status.HTTP_204_NO_CONTENT)  # Response может вернуть текст и метаданные.
    book = await session.execute(select(Book).filter(Book.id == book_id))
    if not book.scalar():
        return Response(status_code=status.HTTP_404_NOT_FOUND)

        # Удаляем книгу из базы данных
    await session.execute(delete(Book).where(Book.id == book_id))

    # Удаляем связь книги с продавцом
    await session.execute(
        delete(Seller).where(Seller.books.any(id=book_id))
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Ручка для обновления данных о книге
@books_router.put("/{book_id}")
async def update_book(book_id: int, new_data: ReturnedBook, session: DBSession):
    # Оператор "морж", позволяющий одновременно и присвоить значение и проверить его.
    if updated_book := await session.get(Book, book_id):
        updated_book.author = new_data.author
        updated_book.title = new_data.title
        updated_book.year = new_data.year
        updated_book.count_pages = new_data.count_pages

        await session.flush()

        return updated_book

    return Response(status_code=status.HTTP_404_NOT_FOUND)
