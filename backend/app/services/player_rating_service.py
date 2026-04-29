from __future__ import annotations


def calculate_player_rating(onboarding_score: int | None, games_played: int) -> float:
    base_score = onboarding_score if onboarding_score is not None else 3
    base_component = base_score * 0.7
    games_component = min(games_played, 20) * 0.15
    activity_bonus = 0.0

    if games_played >= 5:
        activity_bonus += 0.4
    if games_played >= 10:
        activity_bonus += 0.5
    if games_played >= 20:
        activity_bonus += 0.7

    rating = base_component + games_component + activity_bonus
    return round(min(max(rating, 1.0), 8.0), 1)
