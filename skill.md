# Skill Specification: Smart Food Delivery AI Agent

## 1. Overview
The **Smart Food Delivery AI Agent** serves as an interactive culinary assistant and order management agent. It translates natural language user intents into structured restaurant database operations, dish recommendations, and real-time shopping cart transactions.

---

## 2. Core Capabilities
* **Nutritional & Dietary Filtering:** Filters dishes matching macro targets (calories, minimum protein) and dietary flags (`vegan`, `vegetarian`, `gluten-free`, `halal`, `nut-free`).
* **Semantic Dish Matching:** Interprets unstructured queries (e.g., *"I want something fresh and tangy under $15"*) into catalog search queries.
* **Autonomous Cart Management:** Direct execution of `add_to_cart`, `view_cart`, and `clear_cart` actions via native OpenAI Tool Calling.
* **Cross-Selling & Pairing:** Suggests relevant appetizers and beverages matching the primary selected dish.

---

## 3. Operational Rules & Constraints
1. **Never Hallucinate Item IDs:** Dish IDs must strictly come from the output of `search_menu`. Never guess an ID like `dish-999`.
2. **Explicit Confirmation on Actions:** Whenever an item is added to the cart, the agent must confirm the item title, quantity, and new cart subtotal.
3. **Allergen Warnings:** If the user specifies a severe allergy (e.g., peanut, dairy, gluten), the agent must query dietary tags and explicitly verify compliance prior to recommending an item.
4. **Tool Fallback:** If `search_menu` returns an empty array, the agent must apologize gracefully and suggest widening the criteria rather than fabricating dishes.

---

## 4. Function / Tool Call Signatures

| Tool Name | Parameters | Purpose |
| :--- | :--- | :--- |
| `search_menu` | `query`, `max_price`, `dietary_preference`, `min_protein` | Filters the menu database for matching dishes |
| `add_to_cart` | `dish_id` (str), `quantity` (int) | Adds selected dish and quantity to current cart |
| `view_cart` | *None* | Retrieves current line items, quantities, and totals |
| `clear_cart` | *None* | Resets the shopping cart |

---

## 5. Quickstart & Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: enables AI-powered recommendations
$env:OPENAI_API_KEY = "your-api-key-here"

# Start the server
python main.py
```

Open http://localhost:8000 to use the menu, dietary filters, shopping bag, and food assistant.
Without `OPENAI_API_KEY`, the assistant uses a basic menu-search fallback.