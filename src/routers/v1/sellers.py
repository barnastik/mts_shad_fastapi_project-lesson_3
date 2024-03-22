from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi import Response
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import icecream as ic
from src.configurations.database import get_async_session

from src.models.sellers import Seller
from src.schemas.sellers import IncomingSeller, ReturnedSeller, ReturnedAllSellers, BaseSeller
from src.schemas import ReturnedAllBooks, ReturnedBook
from src.routers.v1 import books



sellers_router = APIRouter(tags=["sellers"], prefix="/sellers")

# Больше не симулируем хранилище данных. Подключаемся к реальному, через сессию.
DBSession = Annotated[AsyncSession, Depends(get_async_session)]


# Ручка для создания записи о книге в БД. Возвращает созданную книгу.
@sellers_router.post("/", response_model=ReturnedSeller,
                     status_code=status.HTTP_201_CREATED)  # Прописываем модель ответа
async def create_seller(
        seller: IncomingSeller, session: DBSession
):
    hashed_password = bcrypt.hashpw(seller.password.encode('utf-8'), bcrypt.gensalt())
    print(hashed_password.decode('utf-8'))
    new_seller = Seller(
        first_name=seller.first_name,
        last_name=seller.last_name,
        email=seller.email,
        password=hashed_password.decode('utf-8')
    )
    session.add(new_seller)
    await session.commit()  # Фиксируем изменения в базе данных
    await session.refresh(new_seller)

    return_books = ReturnedAllBooks()
    # Добавляем книги продавца
    for incoming_book in seller.books:
        incoming_book.seller_id = new_seller.id
        return_books.books.append(await books.create_book(incoming_book, session))

    return_seller = ReturnedSeller(
        id=new_seller.id,
        first_name=new_seller.first_name,
        last_name=new_seller.last_name,
        email=new_seller.email,
        books=return_books
    )

    return return_seller


@sellers_router.get("/", response_model=ReturnedAllSellers)
async def get_all_sellers(session: DBSession):
    query = select(Seller).options(selectinload(Seller.books))
    res = await session.execute(query)
    sellers = res.scalars().all()
    returned_sellers = list(map(lambda seller: ReturnedSeller(
        id=seller.id,
        first_name=seller.first_name,
        last_name=seller.last_name,
        email=seller.email,
        books=ReturnedAllBooks(
            books=list(map(lambda book: ReturnedBook(
                id=book.id,
                count_pages=book.count_pages,
                title=book.title,
                author=book.author,
                year=book.year
            ), seller.books))
        )
    ), sellers))
    return {"sellers": returned_sellers}


@sellers_router.get("/{seller_id}", response_model=ReturnedSeller)
async def get_seller(seller_id: int, session: DBSession):
    seller = await session.execute(select(Seller)
                                   .where(Seller.id == seller_id)
                                   .options(selectinload(Seller.books)))
    seller = seller.scalar()
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")
    returned_books = ReturnedAllBooks()
    for book in seller.books:
        returned_books.books.append(book)
    returned_seller = ReturnedSeller(
        id=seller.id,
        first_name=seller.first_name,
        last_name=seller.last_name,
        email=seller.email,
        books=returned_books
    )
    return returned_seller




@sellers_router.put("/{seller_id}", response_model=ReturnedSeller)
async def update_seller(seller_id: int, update_seller: BaseSeller, session: DBSession):
    seller = await session.get(Seller, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")
    seller.first_name = update_seller.first_name
    seller.last_name = update_seller.last_name
    seller.email = update_seller.email
    await session.commit()
    return await get_seller(seller_id, session)


@sellers_router.delete("/{seller_id}")
async def delete_seller(seller_id: int, session: DBSession):
    seller = await session.execute(
        select(Seller)
        .where(Seller.id == seller_id)
        .options(selectinload(Seller.books))
    )
    seller = seller.scalar()

    # Если продавец не найден, возбуждаем исключение HTTP 404
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    # Удаляем все книги продавца
    for book in seller.books:
        await session.delete(book)

    # Удаляем продавца
    await session.delete(seller)

    # Сохраняем изменения в базе данных
    await session.commit()

    # Возвращаем ответ с кодом состояния HTTP 204 No Content
    return Response(status_code=204)
