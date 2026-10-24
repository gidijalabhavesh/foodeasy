"""
main.py - FastAPI application orchestrating conversational order flows.
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from model import AddCartItemRequest, Cart, ChatRequest, ChatResponse, UpdateCartItemRequest
from tools import AVAILABLE_TOOLS, MENU_CATALOG, add_to_cart, clear_cart, search_menu, view_cart

load_dotenv()

logger = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
CARTS: Dict[str, Cart] = {}
PROJECT_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Smart Food Delivery AI API",
    description="Conversational food ordering backend driven by OpenAI function calling.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=PROJECT_DIR / "frontend" / "assets"), name="assets")

SYSTEM_PROMPT = """
You are a warm, knowledgeable culinary assistant and ordering concierge for a premium restaurant.
Your primary goals:
1. Help users discover dishes that match their tastes, budget, allergens, and nutritional goals.
2. Proactively call tools to look up the menu, check the cart, and execute add-to-cart operations when the user asks to buy or order something.
3. Always confirm specific dish details (name, price) when suggesting or adding them.
4. Keep answers concise, appetizing, and focused on making the ordering experience smooth.
5. The menu does not contain complete allergen or cross-contamination data; never guarantee allergy safety.
   Tell users with allergies to verify directly with the restaurant before ordering.
"""


@app.get("/")
def health_check():
    return FileResponse(PROJECT_DIR / "frontend" / "index.html")


@app.get("/health")
@app.get("/api/health")
def service_health():
    return {"status": "online", "service": "Smart Food Delivery AI"}


def get_cart(cart_id: str) -> Cart:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", cart_id):
        raise HTTPException(status_code=422, detail="Invalid cart ID.")
    return CARTS.setdefault(cart_id, Cart())


@app.get("/menu")
@app.get("/api/menu")
def get_full_menu():
    return {"menu": [item.model_dump() for item in MENU_CATALOG]}


@app.get("/api/cart/{cart_id}")
def get_cart_endpoint(cart_id: str):
    cart = get_cart(cart_id)
    cart.recalculate()
    return cart


@app.post("/api/cart/{cart_id}/items")
def add_cart_item(cart_id: str, payload: AddCartItemRequest):
    cart = get_cart(cart_id)
    result = json.loads(add_to_cart(payload.dish_id, payload.quantity, cart))
    if result["status"] == "error":
        status_code = 404 if "not found" in result["message"].lower() else 400
        raise HTTPException(status_code=status_code, detail=result["message"])
    return cart


@app.delete("/api/cart/{cart_id}/items/{dish_id}")
def remove_cart_item(cart_id: str, dish_id: str):
    cart = get_cart(cart_id)
    original_count = len(cart.items)
    cart.items = [item for item in cart.items if item.item_id != dish_id]
    if len(cart.items) == original_count:
        raise HTTPException(status_code=404, detail="That dish is not in your cart.")
    cart.recalculate()
    return cart


@app.patch("/api/cart/{cart_id}/items/{dish_id}")
def update_cart_item(cart_id: str, dish_id: str, payload: UpdateCartItemRequest):
    cart = get_cart(cart_id)
    item = next((entry for entry in cart.items if entry.item_id == dish_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="That dish is not in your cart.")
    item.quantity = payload.quantity
    cart.recalculate()
    return cart


@app.delete("/api/cart/{cart_id}")
def clear_cart_endpoint(cart_id: str):
    cart = get_cart(cart_id)
    clear_cart(cart)
    return cart


@app.post("/chat", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    cart = get_cart(payload.cart_id)
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="Message must not be empty.")

    if client is None:
        lowered_message = payload.message.lower()
        if any(phrase in lowered_message for phrase in ("show my cart", "view cart", "my order")):
            reply = f"Your cart total is ${cart.total_price:.2f}."
            if cart.items:
                reply += " " + ", ".join(f"{item.quantity}x {item.name}" for item in cart.items) + "."
            else:
                reply += " Your cart is empty right now."
        elif "clear cart" in lowered_message or "empty cart" in lowered_message:
            clear_cart(cart)
            reply = "Your cart is clear. Whenever you're ready, I can help you pick something delicious."
        else:
            results = json.loads(search_menu(query=payload.message))
            if results:
                reply = "Here are a few dishes that might fit: " + "; ".join(
                    f"{item['name']} (${item['price']:.2f})" for item in results[:3]
                ) + ". You can add any of them from the menu."
            else:
                reply = "I couldn't find an exact menu match. Try a dish name, ingredient, or dietary preference."
        cart.recalculate()
        return ChatResponse(reply=reply, cart=cart, suggested_dishes=[])

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Inject existing conversation history
        if payload.conversation_history:
            messages.extend(payload.conversation_history)

        # Append new user message
        messages.append({"role": "user", "content": payload.message})

        # First model call with tool definitions
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=AVAILABLE_TOOLS,
            tool_choice="auto",
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # Handle tool execution loop if requested by OpenAI
        if tool_calls:
            messages.append(response_message)

            for tool_call in tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                if func_name == "add_to_cart":
                    tool_output = add_to_cart(**func_args, cart=cart)
                elif func_name == "view_cart":
                    tool_output = view_cart(cart=cart)
                elif func_name == "clear_cart":
                    tool_output = clear_cart(cart=cart)
                elif func_name == "search_menu":
                    tool_output = search_menu(**func_args)
                else:
                    tool_output = json.dumps({"error": f"Function {func_name} not found"})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output,
                })

            # Get final conversational answer after tool execution
            second_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            final_reply = second_response.choices[0].message.content
        else:
            final_reply = response_message.content

        cart.recalculate()

        return ChatResponse(
            reply=final_reply or "",
            cart=cart,
            suggested_dishes=[],
        )

    except Exception as e:
        logger.exception("Food assistant request failed")
        raise HTTPException(status_code=502, detail="The food assistant is temporarily unavailable.") from e


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))