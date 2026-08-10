from dataclasses import dataclass
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True)
class PaginationParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination_params(
    page: int = Query(default=1, ge=1, le=1_000),
    page_size: int = Query(default=25, ge=1, le=100),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


def paginated_response(items, total: int, pagination: PaginationParams) -> dict:
    return {
        "items": items,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total": total,
    }
