import pytest
from unittest.mock import Mock
from app.services.game_logic import GameLogic
from app.models.models import SpawnedCountry


class TestGameLogic:
    """Test the core game development algorithm."""

    def create_mock_spawned_country(self, **kwargs):
        """Create a mock spawned country with default values."""
        defaults = {
            "gold": 5,
            "bonds": 1,
            "territories": 4,
            "goods": 2,
            "people": 3,
            "banks": 1,
            "supporters": 0,
            "revolters": 0,
        }
        defaults.update(kwargs)

        mock_country = Mock(spec=SpawnedCountry)
        for key, value in defaults.items():
            setattr(mock_country, key, value)

        return mock_country

    def test_development_algorithm_france_example(self):
        """Test the development algorithm with the France example from the design document."""
        # Starting state from design document
        country = self.create_mock_spawned_country(
            gold=4,
            bonds=1,
            territories=4,
            goods=2,
            people=3,
            banks=1,
            supporters=0,
            revolters=0,
        )

        result = GameLogic.calculate_development(country)

        # Expected calculations:
        # luxuries = MIN(3, 2) = 2
        # available_workers = 3 - 2 = 1
        # industries = MIN(4, 1) = 1
        # unemployed = 3 - 2 - 1 = 0 (no unemployment revolt)
        # gold = 4 - 1 + 1 = 4 (pay bank maintenance, add industrial income)
        # supporters = 0 + 2 = 2
        # revolters = 0 + 0 + (1 - 1) = 0 (no unemployment, no banking issues)
        # goods = MIN(4, 3) = 3 (for next round)

        expected_state = {"gold": 4, "supporters": 2, "revolters": 0, "goods": 3}

        assert result["new_state"] == expected_state
        assert result["changes"]["calculations"]["luxuries"] == 2
        assert result["changes"]["calculations"]["industries"] == 1
        assert result["changes"]["calculations"]["unemployed"] == 0
        assert result["changes"]["calculations"]["unemployment_revolt"] == 0
        assert result["changes"]["calculations"]["bank_maintenance_cost"] == 1
        assert result["changes"]["calculations"]["banking_stability"] == 0

    def test_unemployment_revolt(self):
        """Test unemployment causing revolt."""
        country = self.create_mock_spawned_country(
            people=5,  # 5 people
            goods=1,  # Only 1 goods (so 1 luxury)
            territories=2,  # Only 2 territories (so 2 industries max)
            bonds=0,  # No bonds to avoid banking stability issues
            banks=0,
            revolters=0,
        )

        result = GameLogic.calculate_development(country)

        # luxuries = MIN(5, 1) = 1
        # available_workers = 5 - 1 = 4
        # industries = MIN(2, 4) = 2
        # unemployed = 5 - 1 - 2 = 2 (> 1, so +1 revolt)
        # banking_stability = 0 - 0 = 0 (no additional revolt)

        assert result["changes"]["calculations"]["luxuries"] == 1
        assert result["changes"]["calculations"]["industries"] == 2
        assert result["changes"]["calculations"]["unemployed"] == 2
        assert result["changes"]["calculations"]["unemployment_revolt"] == 1
        assert result["changes"]["calculations"]["banking_stability"] == 0
        assert result["new_state"]["revolters"] == 1

    def test_banking_stability(self):
        """Test banking stability effects."""
        country = self.create_mock_spawned_country(
            bonds=3, banks=1, revolters=0  # bonds > banks causes revolt
        )

        result = GameLogic.calculate_development(country)

        # banking_stability = 3 - 1 = 2 (adds 2 revolters)
        assert result["changes"]["calculations"]["banking_stability"] == 2
        assert result["new_state"]["revolters"] == 2

    def test_no_negative_values(self):
        """Test that values don't go negative."""
        country = self.create_mock_spawned_country(
            gold=1,  # Very low gold
            banks=3,  # High bank maintenance cost
        )

        result = GameLogic.calculate_development(country)

        # Should not go negative
        assert result["new_state"]["gold"] >= 0

    def test_victory_points_calculation(self):
        """Test victory points calculation."""
        country = self.create_mock_spawned_country(
            gold=10, territories=5, supporters=8, revolters=2, bonds=3
        )

        result = GameLogic.calculate_victory_points(country)

        # base_score = 10
        # territory_bonus = 5 * 2 = 10
        # stability_bonus = MAX(0, 8 - 2) = 6
        # economic_bonus = 3
        # total = 10 + 10 + 6 + 3 = 29
        # no instability penalty (supporters > revolters)

        assert result["breakdown"]["base_score"] == 10
        assert result["breakdown"]["territory_bonus"] == 10
        assert result["breakdown"]["stability_bonus"] == 6
        assert result["breakdown"]["economic_bonus"] == 3
        assert result["breakdown"]["instability_penalty"] == False
        assert result["total_score"] == 29

    def test_instability_penalty(self):
        """Test instability penalty when revolters > supporters."""
        country = self.create_mock_spawned_country(
            gold=10,
            territories=5,
            supporters=2,
            revolters=8,  # More revolters than supporters
            bonds=3,
        )

        result = GameLogic.calculate_victory_points(country)

        # total_before_penalty = 10 + 10 + 0 + 3 = 23
        # instability penalty applies (revolters > supporters)
        # final_score = 23 * 0.5 = 11.5

        assert result["breakdown"]["instability_penalty"] == True
        assert result["breakdown"]["total_before_penalty"] == 23
        assert result["total_score"] == 11.5

    def test_can_perform_action_buy_bond(self):
        """Test checking if player can buy bonds."""
        country = self.create_mock_spawned_country(gold=5)

        # Can afford 2 bonds (2 gold each)
        assert GameLogic.can_perform_action(country, "buy_bond", 2) == True

        # Cannot afford 3 bonds (6 gold needed)
        assert GameLogic.can_perform_action(country, "buy_bond", 3) == False

    def test_can_perform_action_build_bank(self):
        """Test checking if player can build banks."""
        country = self.create_mock_spawned_country(gold=6)

        # Can afford 2 banks (3 gold each)
        assert GameLogic.can_perform_action(country, "build_bank", 2) == True

        # Cannot afford 3 banks (9 gold needed)
        assert GameLogic.can_perform_action(country, "build_bank", 3) == False

    def test_perform_action_buy_bond(self):
        """Test performing buy bond action."""
        country = self.create_mock_spawned_country(gold=6, bonds=1)

        result = GameLogic.perform_action(country, "buy_bond", 2)

        assert result["success"] == True
        assert country.gold == 2  # 6 - (2 * 2)
        assert country.bonds == 3  # 1 + 2
        assert result["changes"]["cost"] == 4

    def test_perform_action_build_bank(self):
        """Test performing build bank action."""
        country = self.create_mock_spawned_country(gold=9, banks=1)

        result = GameLogic.perform_action(country, "build_bank", 2)

        assert result["success"] == True
        assert country.gold == 3  # 9 - (2 * 3)
        assert country.banks == 3  # 1 + 2
        assert result["changes"]["cost"] == 6

    def test_perform_action_insufficient_funds(self):
        """Test performing action with insufficient funds."""
        country = self.create_mock_spawned_country(gold=1)

        result = GameLogic.perform_action(country, "buy_bond", 1)

        assert result["success"] == False
        assert "insufficient resources" in result["error"]

    # --- Stability check tests ---

    def test_stability_check_stable(self):
        """Stable country (supporters >= revolters) loses no gold."""
        country = self.create_mock_spawned_country(
            gold=10, supporters=5, revolters=3
        )
        result = GameLogic.run_stability_check(country)

        assert result["stable"] is True
        assert result["gold_lost"] == 0
        assert country.gold == 10  # Unchanged

    def test_stability_check_unstable(self):
        """Unstable country loses gold equal to excess revolters."""
        country = self.create_mock_spawned_country(
            gold=10, supporters=2, revolters=5
        )
        result = GameLogic.run_stability_check(country)

        # excess = 5 - 2 = 3, so lose 3 gold
        assert result["stable"] is False
        assert result["gold_lost"] == 3
        assert result["excess_revolters"] == 3
        assert country.gold == 7

    def test_stability_check_gold_floor_at_zero(self):
        """Gold cannot go below zero from stability check."""
        country = self.create_mock_spawned_country(
            gold=2, supporters=0, revolters=5
        )
        result = GameLogic.run_stability_check(country)

        assert result["stable"] is False
        assert country.gold == 0
        assert result["gold_lost"] == 2  # Only lost what they had

    def test_stability_check_equal_supporters_revolters(self):
        """Equal supporters and revolters means stable."""
        country = self.create_mock_spawned_country(
            gold=10, supporters=4, revolters=4
        )
        result = GameLogic.run_stability_check(country)
        assert result["stable"] is True

    # --- New action tests ---

    def test_can_perform_action_recruit_people(self):
        """Recruit people costs 2 gold each."""
        country = self.create_mock_spawned_country(gold=4)
        assert GameLogic.can_perform_action(country, "recruit_people", 2) is True
        assert GameLogic.can_perform_action(country, "recruit_people", 3) is False

    def test_can_perform_action_acquire_territory(self):
        """Acquire territory costs 3 gold each."""
        country = self.create_mock_spawned_country(gold=6)
        assert GameLogic.can_perform_action(country, "acquire_territory", 2) is True
        assert GameLogic.can_perform_action(country, "acquire_territory", 3) is False

    def test_perform_action_recruit_people(self):
        """Test recruiting people."""
        country = self.create_mock_spawned_country(gold=6, people=3)
        result = GameLogic.perform_action(country, "recruit_people", 2)

        assert result["success"] is True
        assert country.gold == 2  # 6 - (2 * 2)
        assert country.people == 5  # 3 + 2
        assert result["changes"]["cost"] == 4

    def test_perform_action_recruit_people_insufficient_funds(self):
        """Test recruiting people with insufficient gold."""
        country = self.create_mock_spawned_country(gold=1, people=3)

        result = GameLogic.perform_action(country, "recruit_people", 1)

        assert result["success"] == False
        assert country.people == 3  # unchanged

    def test_perform_action_acquire_territory(self):
        """Test acquiring territory."""
        country = self.create_mock_spawned_country(gold=9, territories=4)
        result = GameLogic.perform_action(country, "acquire_territory", 2)

        assert result["success"] is True
        assert country.gold == 3  # 9 - (2 * 3)
        assert country.territories == 6  # 4 + 2
        assert result["changes"]["cost"] == 6

    def test_perform_action_acquire_territory_insufficient_funds(self):
        """Test acquiring territory with insufficient gold."""
        country = self.create_mock_spawned_country(gold=2, territories=4)

        result = GameLogic.perform_action(country, "acquire_territory", 1)

        assert result["success"] == False
        assert country.territories == 4  # unchanged

    # ---- unknown action tests ----

    def test_can_perform_unknown_action(self):
        """Test that unknown action types return False."""
        country = self.create_mock_spawned_country(gold=100)
        assert GameLogic.can_perform_action(country, "unknown_action", 1) == False

    def test_perform_unknown_action(self):
        """Test that unknown action types fail."""
        country = self.create_mock_spawned_country(gold=100)
        result = GameLogic.perform_action(country, "unknown_action", 1)
        assert result["success"] == False
