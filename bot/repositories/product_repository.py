"""Репозиторий для работы с товарами в базе данных."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.product import Product
from bot.core.config import config


class ProductRepository:
    """Репозиторий для управления товарами в базе данных."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    
    async def add_product(self, name: str, description: str, price: int) -> Product:
        """Добавить новый товар в базу данных."""
        new_product = Product(name=name, description=description, price=price)
        self.session.add(new_product)
        await self.session.commit()
        await self.session.refresh(new_product)
        return new_product
        
        
    async def get_product_by_id(self, product_id: int) -> Product | None:
        """Получить товар по его ID."""
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        return result.scalars().first()
    
    
    async def get_all_products(self) -> list[list[Product]]:
        """Получить список всех товаров."""
        result = await self.session.execute(select(Product).where(Product.is_active.is_(True)).order_by(Product.id))
        products = result.scalars().all()
        page_size = config.SHOP_LIST_PAGINATION_SIZE

        return [products[index:index + page_size] for index in range(0, len(products), page_size)]
    
    
    async def update_product(self, product_id: int, name: str | None = None, description: str | None = None, price: int | None = None) -> Product | None:
        """Обновить информацию о товаре."""
        product = await self.get_product_by_id(product_id)
        if not product:
            return None
        
        if name is not None:
            product.name = name
        if description is not None:
            product.description = description
        if price is not None:
            product.price = price
            
        await self.session.commit()
        await self.session.refresh(product)
        return product
    
    
    async def delete_product(self, product_id: int) -> bool:
        """Удалить товар из базы данных."""
        product = await self.get_product_by_id(product_id)
        if not product:
            return False
        
        await self.session.delete(product)
        await self.session.commit()
        return True
