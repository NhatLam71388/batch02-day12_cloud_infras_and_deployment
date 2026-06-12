from .stock_tool import check_stock
from .discount_tool import get_discount
from .shipping_tool import calc_shipping

ALL_TOOLS = [
    {
        "name": "check_stock",
        "description": "Checks available quantity for an item. Input: item_name (str). Returns: stock count (int).",
        "func": check_stock
    },
    {
        "name": "get_discount",
        "description": "Checks discount percentage for a coupon code. Input: coupon_code (str). Returns: discount percentage (float, e.g., 0.15 for 15%).",
        "func": get_discount
    },
    {
        "name": "calc_shipping",
        "description": "Calculates shipping cost based on weight and destination. Input: weight (float, in kg), destination (str, capitalized city name e.g. 'Hanoi'). Returns: shipping cost (float).",
        "func": calc_shipping
    }
]

__all__ = ["check_stock", "get_discount", "calc_shipping", "ALL_TOOLS"]
