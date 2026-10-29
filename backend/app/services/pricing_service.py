"""Centralized pricing service using Python Decimal for monetary precision."""

from decimal import Decimal, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")


def to_decimal(value):
    """Safely convert a number, float, or string to a Decimal."""
    return Decimal(str(value))


def format_currency(decimal_val):
    """Round and format Decimal to float with 2 decimal places."""
    return float(decimal_val.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


class PricingService:
    """Calculates all line totals, basket subtotals, and item counts."""

    @staticmethod
    def calculate_line_total(unit_price, quantity):
        """
        Calculate line total = Unit Price * Quantity.
        Both unit_price and quantity are handled with Decimal precision.
        """
        price_dec = to_decimal(unit_price)
        qty_dec = Decimal(quantity)
        line_total_dec = price_dec * qty_dec
        return format_currency(line_total_dec)

    @classmethod
    def calculate_basket_totals(cls, basket_items, products_map):
        """
        Calculate complete basket review totals using current catalog products.
        Ignores any client-supplied totals or prices.
        """
        reviewed_items = []
        total_items = 0
        subtotal_dec = Decimal("0.00")
        missing_products = []

        for item in basket_items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            product = products_map.get(product_id)

            if not product:
                missing_products.append(product_id)
                continue

            current_unit_price = product["price"]
            line_total = cls.calculate_line_total(current_unit_price, quantity)

            reviewed_items.append({
                "product_id": product_id,
                "name": product["name"],
                "unit_price": current_unit_price,
                "quantity": quantity,
                "line_total": line_total,
            })

            total_items += quantity
            subtotal_dec += to_decimal(line_total)

        return {
            "items": reviewed_items,
            "total_items": total_items,
            "subtotal": format_currency(subtotal_dec),
            "missing_products": missing_products,
        }

