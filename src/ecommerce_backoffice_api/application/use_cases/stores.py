"""Store catalog use cases."""

from __future__ import annotations

from ecommerce_backoffice_api.application.ports.repositories import StoreRepository
from ecommerce_backoffice_api.domain import authorization
from ecommerce_backoffice_api.domain.entities import Store, User
from ecommerce_backoffice_api.domain.exceptions import AuthorizationError, NotFoundError


class ListStores:
    """List stores visible to the actor."""

    def __init__(self, store_repository: StoreRepository) -> None:
        self._store_repository = store_repository

    def execute(self, *, actor: User) -> list[Store]:
        stores = self._store_repository.list_all()
        if authorization.can_list_all_stores(actor):
            return stores
        visible: list[Store] = []
        for store in stores:
            if store.id is not None and authorization.can_read_store(actor, store.id):
                visible.append(store)
        return visible


class GetStore:
    """Fetch a single store if the actor may read it."""

    def __init__(self, store_repository: StoreRepository) -> None:
        self._store_repository = store_repository

    def execute(self, *, actor: User, store_id: int) -> Store:
        if not authorization.can_read_store(actor, store_id):
            raise AuthorizationError("Not permitted to read this store.")
        store = self._store_repository.get_by_id(store_id)
        if store is None:
            raise NotFoundError(f"Store {store_id} was not found.")
        return store


class CreateStore:
    """Create a store (admin only)."""

    def __init__(self, store_repository: StoreRepository) -> None:
        self._store_repository = store_repository

    def execute(self, *, actor: User, name: str, owner_user_id: int | None) -> Store:
        if not authorization.can_create_store(actor):
            raise AuthorizationError("Not permitted to create stores.")
        return self._store_repository.add(Store(name=name.strip(), owner_user_id=owner_user_id))
