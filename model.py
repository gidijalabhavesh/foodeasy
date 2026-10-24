"""
model.py - Data schemas for the Smart Food Delivery AI application.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class MenuItem(BaseModel):
    id: str = Field(..., description="Unique dish identifier")
    name: str = Field(..., description="Dish title")
    description: str = Field(..., description="Sensory and culinary description")
    category: str = Field(..., description="E.g., Appetizer, Main, Dessert, Drink")
    price: float = Field(..., ge=0.0, description="Price in USD")
    calories: Optional[int] = Field(None, description="Caloric content")
    protein_g: Optional[int] = Field(None, description="Protein in grams")
    dietary_tags: List[str] = Field(
        default_factory=list,
        description="Tags like vegan, vegetarian, gluten-free, halal, nut-free",
    )
    is_available: bool = True


class CartItem(BaseModel):
    item_id: str
    name: str
    quantity: int = Field(default=1, ge=1)
    unit_price: float
    subtotal: float


class Cart(BaseModel):
    items: List[CartItem] = Field(default_factory=list)
    total_price: float = 0.0

    def recalculate(self) -> None:
        for item in self.items:
            item.subtotal = round(item.quantity * item.unit_price, 2)
        self.total_price = round(sum(i.subtotal for i in self.items), 2)


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's input message")
    cart_id: str = Field(..., min_length=1, max_length=64)
    conversation_history: Optional[List[dict]] = Field(
        default_factory=list,
        description="Prior conversation history in OpenAI message format",
    )


class AddCartItemRequest(BaseModel):
    dish_id: str = Field(..., min_length=1)
    quantity: int = Field(default=1, ge=1, le=20)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=1, le=20)


class ChatResponse(BaseModel):
    reply: str
    cart: Cart
    suggested_dishes: List[MenuItem] = Field(default_factory=list)