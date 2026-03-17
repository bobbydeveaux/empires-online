from typing import Dict, Any
from app.models.models import SpawnedCountry


class GameLogic:
    """Core game logic for Empires Online development algorithm."""

    @staticmethod
    def calculate_development(spawned_country: SpawnedCountry) -> Dict[str, Any]:
        """
        Implements the core development algorithm exactly as specified in the design document.

        Algorithm:
        1. Calculate luxury production: luxuries = MIN(people, goods)
        2. Calculate industries: industries = MIN(territories, people - luxuries)
        3. Check unemployment: if unemployed > 1, add 1 revolter
        4. Banking operations: pay bank costs, add banking stability
        5. Update supporters and resources
        6. Calculate goods for next round
        """

        # Current state
        gold = spawned_country.gold
        bonds = spawned_country.bonds
        territories = spawned_country.territories
        goods = spawned_country.goods
        people = spawned_country.people
        banks = spawned_country.banks
        supporters = spawned_country.supporters
        revolters = spawned_country.revolters

        # Track changes for history
        changes = {
            "before": {
                "gold": gold,
                "supporters": supporters,
                "revolters": revolters,
                "goods": goods,
            }
        }

        # Phase 1: Calculate luxury production
        luxuries = min(people, goods)
        available_workers = people - luxuries

        # Phase 2: Calculate industrial production
        industries = min(territories, available_workers)
        gold_from_industries = industries

        # Phase 3: Check for unemployment
        unemployed = people - luxuries - industries
        unemployment_revolt = 1 if unemployed > 1 else 0

        # Phase 4: Banking operations
        bank_maintenance_cost = banks
        banking_stability = bonds - banks  # Positive means more revolt

        # Apply changes
        new_gold = gold - bank_maintenance_cost + gold_from_industries
        new_supporters = supporters + luxuries
        new_revolters = revolters + unemployment_revolt + banking_stability
        new_goods = min(territories, people)  # For next round

        # Ensure no negative values
        new_gold = max(0, new_gold)
        new_supporters = max(0, new_supporters)
        new_revolters = max(0, new_revolters)
        new_goods = max(0, new_goods)

        changes["after"] = {
            "gold": new_gold,
            "supporters": new_supporters,
            "revolters": new_revolters,
            "goods": new_goods,
        }

        changes["calculations"] = {
            "luxuries": luxuries,
            "industries": industries,
            "unemployed": unemployed,
            "unemployment_revolt": unemployment_revolt,
            "bank_maintenance_cost": bank_maintenance_cost,
            "banking_stability": banking_stability,
            "gold_from_industries": gold_from_industries,
        }

        return {
            "new_state": {
                "gold": new_gold,
                "supporters": new_supporters,
                "revolters": new_revolters,
                "goods": new_goods,
            },
            "changes": changes,
        }

    @staticmethod
    def calculate_victory_points(spawned_country: SpawnedCountry) -> Dict[str, Any]:
        """
        Calculate victory points based on the design specification:
        - Base Score = gold * 1
        - Territory Bonus = territories * 2
        - Stability Bonus = MAX(0, supporters - revolters) * 1
        - Economic Bonus = bonds * 1
        - Instability Penalty = If revolters > supporters, multiply total by 0.5
        """

        base_score = spawned_country.gold
        territory_bonus = spawned_country.territories * 2
        stability_bonus = max(0, spawned_country.supporters - spawned_country.revolters)
        economic_bonus = spawned_country.bonds

        total_before_penalty = (
            base_score + territory_bonus + stability_bonus + economic_bonus
        )

        # Apply instability penalty
        instability_penalty = spawned_country.revolters > spawned_country.supporters
        final_score = (
            total_before_penalty * 0.5 if instability_penalty else total_before_penalty
        )

        return {
            "total_score": final_score,
            "breakdown": {
                "base_score": base_score,
                "territory_bonus": territory_bonus,
                "stability_bonus": stability_bonus,
                "economic_bonus": economic_bonus,
                "instability_penalty": instability_penalty,
                "total_before_penalty": total_before_penalty,
            },
        }

    # Action cost definitions
    ACTION_COSTS = {
        "buy_bond": 2,
        "build_bank": 3,
        "recruit_people": 2,
        "acquire_territory": 3,
    }

    @staticmethod
    def can_perform_action(
        spawned_country: SpawnedCountry, action: str, quantity: int = 1
    ) -> bool:
        """Check if a player can perform a specific action."""
        cost_per_unit = GameLogic.ACTION_COSTS.get(action)
        if cost_per_unit is None:
            return False
        return spawned_country.gold >= (cost_per_unit * quantity)

    @staticmethod
    def perform_action(
        spawned_country: SpawnedCountry, action: str, quantity: int = 1
    ) -> Dict[str, Any]:
        """Perform an action and return the updated state."""

        if not GameLogic.can_perform_action(spawned_country, action, quantity):
            return {
                "success": False,
                "error": "Cannot perform action - insufficient resources",
            }

        cost_per_unit = GameLogic.ACTION_COSTS[action]
        cost = cost_per_unit * quantity
        changes = {"action": action, "quantity": quantity, "cost": cost}

        spawned_country.gold -= cost

        if action == "buy_bond":
            spawned_country.bonds += quantity
        elif action == "build_bank":
            spawned_country.banks += quantity
        elif action == "recruit_people":
            spawned_country.people += quantity
        elif action == "acquire_territory":
            spawned_country.territories += quantity

        return {
            "success": True,
            "changes": changes,
            "new_state": {
                "gold": spawned_country.gold,
                "bonds": spawned_country.bonds,
                "banks": spawned_country.banks,
                "people": spawned_country.people,
                "territories": spawned_country.territories,
            },
        }

    @staticmethod
    def run_stability_check(spawned_country: SpawnedCountry) -> Dict[str, Any]:
        """Run stability check at end of round.

        If revolters > supporters, deduct gold equal to (revolters - supporters),
        with gold floored at 0.
        """
        revolters = spawned_country.revolters
        supporters = spawned_country.supporters

        if revolters <= supporters:
            return {
                "stable": True,
                "gold_lost": 0,
                "revolters": revolters,
                "supporters": supporters,
            }

        excess = revolters - supporters
        gold_before = spawned_country.gold
        gold_lost = min(gold_before, excess)
        spawned_country.gold = max(0, gold_before - excess)

        return {
            "stable": False,
            "gold_lost": gold_lost,
            "revolters": revolters,
            "supporters": supporters,
            "gold_before": gold_before,
            "gold_after": spawned_country.gold,
        }
