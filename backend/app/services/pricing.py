import math

PLATFORM_FEE = 90


def calculate_pricing_breakdown(
    hourly_rate: int,
    duration_hours: int,
    required_players: int,
    registered_players: int | None = None,
) -> dict[str, int | bool]:
    rent_total = hourly_rate * duration_hours
    rent_share_per_player = math.ceil(rent_total / required_players)
    final_price_per_player = rent_share_per_player + PLATFORM_FEE
    actual_players = registered_players if registered_players is not None else required_players
    pricing_applied = actual_players >= required_players
    recognized_rent_total = rent_share_per_player * actual_players if pricing_applied else 0
    recognized_platform_fee_total = PLATFORM_FEE * actual_players if pricing_applied else 0

    return {
        "hourly_rate": hourly_rate,
        "duration_hours": duration_hours,
        "required_players": required_players,
        "registered_players": actual_players,
        "rent_total": rent_total,
        "rent_share_per_player": rent_share_per_player,
        "platform_fee_per_player": PLATFORM_FEE,
        "final_price_per_player": final_price_per_player,
        "admin_rent_total": recognized_rent_total,
        "admin_platform_fee_total": recognized_platform_fee_total,
        "partner_rent_revenue": recognized_rent_total,
        "pricing_applied": pricing_applied,
        "refund_required": not pricing_applied,
    }


def calculate_cost_per_player(hourly_rate: int, duration_hours: int, required_players: int) -> int:
    breakdown = calculate_pricing_breakdown(hourly_rate, duration_hours, required_players)
    return int(breakdown["final_price_per_player"])
