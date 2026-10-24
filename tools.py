"""
tools.py - Business logic tools and OpenAI Function schemas.
"""

import json
from typing import List, Optional
from model import Cart, CartItem, MenuItem

# In-memory mock database of restaurant menu items
MENU_CATALOG: List[MenuItem] = [
    MenuItem(
        id="dish-001",
        name="Mediterranean Quinoa Bowl",
        description="Fluffy organic quinoa topped with kalamata olives, crisp cucumbers, heirloom tomatoes, and lemon-tahini dressing.",
        category="Main",
        price=14.50,
        calories=520,
        protein_g=18,
        dietary_tags=["vegan", "gluten-free", "healthy"],
    ),
    MenuItem(
        id="dish-002",
        name="Smoked Angus Burger",
        description="Char-grilled prime Angus beef patty with aged cheddar, caramelized onions, and house aioli on a brioche bun.",
        category="Main",
        price=16.00,
        calories=850,
        protein_g=42,
        dietary_tags=["high-protein"],
    ),
    MenuItem(
        id="dish-003",
        name="Citrus Glazed Wild Salmon",
        description="Pan-seared Atlantic salmon with blood orange glaze, steamed broccolini, and jasmine rice.",
        category="Main",
        price=21.00,
        calories=610,
        protein_g=45,
        dietary_tags=["gluten-free", "pescatarian", "high-protein"],
    ),
    MenuItem(
        id="dish-004",
        name="Truffle Wild Mushroom Risotto",
        description="Arborio rice slowly simmered with chanterelle and portobello mushrooms, finished with white truffle oil and parmigiano.",
        category="Main",
        price=18.50,
        calories=680,
        protein_g=14,
        dietary_tags=["vegetarian"],
    ),
    MenuItem(
        id="dish-005",
        name="Crispy Cauliflower Wings",
        description="Beer-battered florets glazed in spicy gochujang chili sauce, served with vegan ranch dip.",
        category="Appetizer",
        price=10.50,
        calories=380,
        protein_g=8,
        dietary_tags=["vegan", "spicy"],
    ),
    MenuItem(
        id="dish-006",
        name="Sparkling Hibiscus Berry Cooler",
        description="Cold-steeped organic hibiscus tea infused with fresh raspberries, mint, and sparkling mineral water.",
        category="Drink",
        price=5.50,
        calories=60,
        protein_g=0,
        dietary_tags=["vegan", "gluten-free"],
    ),
]

# Shared session cart instance (in production, use session/token-scoped carts)
CURRENT_CART = Cart()


def search_menu(
    query: Optional[str] = None,
    max_price: Optional[float] = None,
    dietary_preference: Optional[str] = None,
    min_protein: Optional[int] = None,
) -> str:
    """Searches the menu database based on criteria."""
    results = MENU_CATALOG.copy()

    if query:
        q = query.lower()
        results = [
            m for m in results if q in m.name.lower() or q in m.description.lower() or q in m.category.lower()
        ]

    if max_price is not None:
        results = [m for m in results if m.price <= max_price]

    if dietary_preference:
        pref = dietary_preference.lower()
        results = [m for m in results if any(pref in tag.lower() for tag in m.dietary_tags)]

    if min_protein is not None:
        results = [m for m in results if m.protein_g is not None and m.protein_g >= min_protein]

    return json.dumps([item.model_dump() for item in results])


def add_to_cart(dish_id: str, quantity: int = 1, cart: Optional[Cart] = None) -> str:
    """Adds a dish to the customer's shopping cart."""
    target_cart = cart if cart is not None else CURRENT_CART
    if quantity < 1 or quantity > 20:
        return json.dumps({"status": "error", "message": "Quantity must be between 1 and 20."})

    dish = next((m for m in MENU_CATALOG if m.id == dish_id), None)
    if not dish:
        return json.dumps({"status": "error", "message": f"Dish ID '{dish_id}' not found."})

    for item in target_cart.items:
        if item.item_id == dish_id:
            if item.quantity + quantity > 20:
                return json.dumps({"status": "error", "message": "A maximum of 20 servings per dish is allowed."})
            item.quantity += quantity
            target_cart.recalculate()
            return json.dumps({
                "status": "success",
                "message": f"Updated {dish.name} quantity to {item.quantity}.",
                "cart": target_cart.model_dump(),
            })

    target_cart.items.append(
        CartItem(
            item_id=dish.id,
            name=dish.name,
            quantity=quantity,
            unit_price=dish.price,
            subtotal=round(dish.price * quantity, 2),
        )
    )
    target_cart.recalculate()
    return json.dumps({
        "status": "success",
        "message": f"Added {quantity}x {dish.name} to cart.",
        "cart": target_cart.model_dump(),
    })


def view_cart(cart: Optional[Cart] = None) -> str:
    """Returns the current state and totals of the customer's cart."""
    target_cart = cart if cart is not None else CURRENT_CART
    target_cart.recalculate()
    return json.dumps(target_cart.model_dump())


def clear_cart(cart: Optional[Cart] = None) -> str:
    """Removes all items from the cart."""
    target_cart = cart if cart is not None else CURRENT_CART
    target_cart.items.clear()
    target_cart.recalculate()
    return json.dumps({"status": "success", "message": "Cart has been cleared."})


# OpenAI Tool Definitions
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_menu",
            "description": "Search dishes in the restaurant database matching dietary restrictions, keyword queries, protein targets, or price limits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Free text search e.g., 'burger', 'pasta', 'quinoa'"},
                    "max_price": {"type": "number", "description": "Max budget per dish in USD"},
                    "dietary_preference": {
                        "type": "string",
                        "description": "E.g., 'vegan', 'gluten-free', 'vegetarian', 'high-protein'",
                    },
                    "min_protein": {"type": "integer", "description": "Minimum grams of protein required"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add an item from the menu into the customer's ordering cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dish_id": {"type": "string", "description": "The exact dish ID (e.g. 'dish-001')"},
                    "quantity": {"type": "integer", "default": 1, "description": "Number of servings"},
                },
                "required": ["dish_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_cart",
            "description": "Inspect the customer's active cart and total balance.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_cart",
            "description": "Empty the cart.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_MAP = {
    "search_menu": search_menu,
    "add_to_cart": add_to_cart,
    "view_cart": view_cart,
    "clear_cart": clear_cart,
}