import random
from random import choice
from typing import Literal

import i18n

from scripts.cat.cats import Cat
from scripts.cat.enums import CatCompatibility
from scripts.cat_relations.relationship import Relationship, create_one_relationship
from scripts.clan_package.settings import get_clan_setting
from scripts.events_module.event_information import EventInformation
from scripts.game_structure import game
from scripts.game_structure.localization import load_lang_resource
from scripts.events_module.text_adjust import (
    event_text_adjust,
    relationship_text_adjust,
)
from scripts.events_module.consequences import change_relationship_values
from scripts.events_module.event_filters import (
    get_highest_like_relation,
    get_personality_compatibility,
)
from scripts.config import get_config


# ---------------------------------------------------------------------------- #
#                                LOAD RESOURCES                                #
# ---------------------------------------------------------------------------- #

current_loaded_lang = None

PARTNER_DICTS = {}
BREAKUP_STRINGS = {}
POLY_PARTNER_DICTS = {}


def handle_partner_and_breakup(cat: Cat):
    """
    Checks if the given cat should move on from prior partners, breakup current ones, or take on a new one.
    :param cat: Cat to check
    """
    _rebuild_dicts()

    # check setting first
    if cat.no_partners:
        return

    # just ensure relationships exist
    for p in cat.partner:
        partner = Cat.fetch_cat(p)
        if partner.ID not in cat.relationships:
            cat.create_one_relationship(partner)
        if cat.ID not in partner.relationships:
            partner.create_one_relationship(cat)

    _handle_moving_on(cat)
    _handle_breakup_events(cat)
    _handle_new_partner_events(cat)


def _handle_moving_on(cat: Cat, disable_random: bool = False):
    """Handles moving on from dead or outside partners
    :param cat: cat who may try to move on
    :param disable_random: used for testing
    """
    for partner_id in cat.partner:
        # check valid partner
        if partner_id not in Cat.all_cats:
            print(f"WARNING: Cat #{cat} has a invalid partner. It will be removed.")
            cat.partner.remove(partner_id)
            continue

        partner: Cat = Cat.fetch_cat(partner_id)
        # check the partner's setting
        if partner.no_partners:
            continue

        # check if the partner has been gone for at least 4 moons
        dead_or_gone = (
            not partner.status.group_ID == cat.status.group_ID and partner.status.moons_as >= 4
        )

        # if cat is not grief stricken, then we try to move on
        if "grief stricken" not in cat.illnesses and dead_or_gone:
            chance = get_config("mates.moving_on.chance")
            for threshold_reached in [
                cat.personality.stability > 8,
                cat.personality.sociability < 8,
                cat.personality.aggression < 8,
            ]:
                if threshold_reached:
                    chance += get_config("mates.moving_on.facet_influence")

            if random.random() <= chance or disable_random:
                text = i18n.t("hardcoded.move_on_dead_mate", partner=str(partner.name))
                game.cur_events_list.append(
                    EventInformation(text, "relation", cat_dict={"m_c": cat, "r_c": partner}, clan=cat.status.group_ID)
                )
                cat.unset_partner(partner)


def _handle_breakup_events(cat: Cat):
    """Triggers and handles any events that results in a breakup"""

    for x in cat.partner:
        partner = Cat.fetch_cat(x)

        # check the partner's setting
        if partner.no_partners:
            continue

        _attempt_breakup(cat, partner)


def _attempt_breakup(cat_from: Cat, cat_to: Cat, disable_random: bool = False):
    """Checks if the cats wish to breakup and handles the ensuing result."""

    if not _check_if_breakup(cat_from, cat_to, disable_random):
        return

    # gather relationships
    relationship_from: Relationship = cat_from.relationships[cat_to.ID]
    relationship_to: Relationship = cat_to.relationships[cat_from.ID]

    # Determine the type of breakup
    possible_breakups = get_config("mates.breakup_partners.default_weights")

    become_mates = False

    # most of these are determined solely by the cat_from's feelings, except for deciding to be mates
    # CHILL
    if relationship_from.like < 40:
        possible_breakups["chill_breakup"] += 2
    # GREW APART
    if relationship_from.like < 20:
        possible_breakups["grew_apart"] += 5
    # FIGHT/BAD
    if relationship_from.total_relationship_value < 80:
        possible_breakups["had_fight"] += 3
        possible_breakups["bad_breakup"] += 2
    # FRIENDLY
    if relationship_from.like > 40 and relationship_to.like > 40:
        possible_breakups["decided_to_be_friends"] += 5
    # ROMANCE
    if relationship_from.romance > 35 and relationship_to.romance > 35:
        possible_breakups["decided_to_be_mates"] += 5

    breakup_type = random.choices(
        list(possible_breakups.keys()), weights=list(possible_breakups.values())
    )[0]
    if breakup_type == "decided_to_be_mates":
        become_mates = True

    # GET TEXT
    text = choice(BREAKUP_STRINGS[breakup_type])
    text = event_text_adjust(Cat, text, main_cat=cat_from, random_cat=cat_to)

    breakup_changes = get_config(f"mates.breakup.reactions.{breakup_type}")
    variability = get_config("mates.breakup.reactions.variability")

    # CAT_FROM REACTION
    cat_from_change = breakup_changes.copy()
    for change in cat_from_change:
        cat_from_change[change] += random.randint(variability[0], variability[1])
    cat_from_change["cats_from"] = [cat_from]
    cat_from_change["cats_to"] = [cat_to]
    cat_from_change["log"] = text

    # CAT_TO REACTION
    cat_to_change = breakup_changes.copy()
    for change in cat_to_change:
        cat_to_change[change] += random.randint(variability[0], variability[1])

    cat_to_change["cats_from"] = [cat_to]
    cat_to_change["cats_to"] = [cat_from]
    cat_to_change["log"] = text

    # CHANGE VALUES
    change_relationship_values(
        **cat_from_change,
    )
    change_relationship_values(
        **cat_to_change,
    )

    if become_mates == True:
        cat_from.set_mate(cat_to)
    else:
        cat_from.unset_partner(cat_to, user_initiated_breakup=False)

    game.cur_events_list.append(
        EventInformation(
            text,
            ["relation", "misc"],
            [cat_from.ID, cat_to.ID],
            cat_dict={"m_c": cat_from, "r_c": cat_to},
            clan=cat_from.status.group_ID,
        )
    )


def _check_if_breakup(cat_from: Cat, cat_to: Cat, disable_random: bool = False) -> bool:
    """
    Returns True if the cats should break up
    """
    # Moving on, not breakups, occur when one partner is dead or outside.
    if not cat_to.status.group_ID == cat_from.status.group_ID:
        return False

    chance_number = _get_breakup_chance(cat_from, cat_to)

    if chance_number == 0 and not disable_random:
        return False

    return not int(random.random() * chance_number) or disable_random


def _get_breakup_chance(cat_from: Cat, cat_to: Cat) -> int:
    """
    Looks into the current values and calculates the chance of breaking up. The lower, the more likely they will break up.
    :return: chance of breaking up
    """
    # Gather relationships
    relationship: Relationship = cat_from.relationships[cat_to.ID]

    # No breakup chance if the cat is above the breakup threshold.
    threshold = get_config("mates.breakup_partners.initial_chance.threshold")
    if relationship.total_relationship_value > threshold:
        return 0

    chance_number = get_config("mates.breakup_partners.initial_chance.default_chance")
    for value in [
        relationship.like,
        relationship.respect,
        relationship.trust,
        relationship.comfort,
    ]:
        chance_number += int(value / 10)

    # change the change based on the personality
    compatibility = get_personality_compatibility(cat_from, cat_to)
    if compatibility == CatCompatibility.POSITIVE:
        chance_number += get_config(
            "mates.breakup_partners.initial_chance.positive_compatibility"
        )
    if compatibility == CatCompatibility.NEGATIVE:
        chance_number += get_config(
            "mates.breakup_partners.initial_chance.negative_compatibility"
        )

    # Then, at least a 1/5 chance
    chance_number = max(chance_number, 5)

    return chance_number


def _handle_new_partner_events(cat: Cat):
    """Triggers and handles any events that result in a new partner"""

    # no trying to take a new partner if you're sad
    if "grief stricken" in cat.illnesses:
        return

    # First, check high love confession
    if _attempt_confession(cat):
        return

    # Then, handle the mutual interest events
    # Choose some subset of cats that they have relationships with
    if not cat.relationships:
        return
    subset = [
        Cat.fetch_cat(x)
        for x in cat.relationships
        if x not in cat.partner
        and x not in cat.mate if get_clan_setting("mutually exclusive mates partnerrs")
        and Cat.fetch_cat(x).status.group_ID == cat.status.group_ID
        and cat.is_potential_partner(Cat.fetch_cat(x))
    ]
    if not subset:
        return

    subset = random.sample(subset, max(int(len(subset) / 3), 1))

    # see if any of them want to pair up
    for other_cat in subset:
        _attempt_mutual_interest_partners(cat, other_cat)


def _attempt_confession(cat_from: Cat) -> bool:
    """
    Check if the cat has a high love for another and attempt to become partners. Handles resulting rejection or acceptance.
    return: bool if event is triggered or not
    """

    # get the highest platonic love relationship
    chosen_relationship = get_highest_like_relation(
        cat_from.relationships.values(), exclude_partner=True, potential_partner=True
    )

    if not chosen_relationship:
        return False

    # Config check
    if not get_config("mates.allow_partners"):
        return False

    # check if it meets confession threshold
    condition = get_config("mates.confession.make_confession_partners")
    if not chosen_relationship.relationship_qualifies(condition):
        return False

    cat_to: Cat = chosen_relationship.cat_to

    if get_clan_setting("mutually exclusive mates partners"):
        if cat_to in cat_from.mate:
            return False

    # need to be in the same "place"
    if cat_to.status.group != cat_from.status.group:
        return False

    # need to be okay to try and approach this cat
    if not _check_against_grief(cat_from, cat_to):
        return False

    # CONFESS
    become_partners, cat_from_change, cat_to_change, partner_string = _try_confession(
        cat_from, cat_to
    )

    if not become_partners:
        return False

    # do the final prep of the rel change dicts
    cat_from_change["cats_from"] = [cat_from]
    cat_from_change["cats_to"] = [cat_to]
    cat_from_change["log"] = partner_string

    cat_to_change["cats_from"] = [cat_to]
    cat_to_change["cats_to"] = [cat_from]
    cat_to_change["log"] = partner_string

    # CHANGE VALUES
    change_relationship_values(
        **cat_from_change,
    )
    change_relationship_values(
        **cat_to_change,
    )

    game.cur_events_list.append(
        EventInformation(
            partner_string,
            ["relation", "misc"],
            cat_dict={"m_c": cat_from, "r_c": cat_to},
            clan=cat_from.status.group_ID,
        )
    )

    if become_partners:
        cat_from.set_partner(cat_to)

    return True


def _try_confession(cat_from, cat_to) -> tuple[bool, dict, dict, str]:
    # CHECK POLY
    existing_from_cat_partners, existing_to_cat_partners = _get_existing_partners(
        cat_from, cat_to
    )
    poly = any([existing_from_cat_partners, existing_to_cat_partners])

    if poly and not _current_partners_allow_new_partner(
        cat_from, cat_to, existing_from_cat_partners, existing_to_cat_partners
    ):
        return False, {}, {}, ""

    become_partners = False
    # accept confession
    condition = get_config("mates.confession.accept_confession_partners")
    variability = get_config("mates.confession.reactions.variability")
    if cat_to.relationships[cat_from.ID].relationship_qualifies(condition):
        become_partners = True
        if cat_from.ID in cat_to.previous_partners:
            partner_string = _get_partner_string(
                "high_like_makeup",
                poly,
                existing_from_cat_partners,
                existing_to_cat_partners,
            )
            confession_changes = get_config("mates.confession.reactions_partners.makeup")
            cat_from_change, cat_to_change = _get_relationship_change_dict(
                confession_changes, variability
            )
        else:
            partner_string = _get_partner_string(
                "high_like",
                poly,
                existing_from_cat_partners,
                existing_to_cat_partners,
            )
            confession_changes = get_config("mates.confession.reactions_partners.accepted")
            cat_from_change, cat_to_change = _get_relationship_change_dict(
                confession_changes, variability
            )
    else:
        if cat_from.ID in cat_to.previous_partners:
            partner_string = _get_partner_string(
                "makeup_fail",
                poly,
                existing_from_cat_partners,
                existing_to_cat_partners,
            )
            confession_changes = get_config("mates.confession.reactions_partners.makeup_fail")
            cat_from_change, cat_to_change = _get_relationship_change_dict(
                confession_changes, variability
            )
        else:
            partner_string = _get_partner_string(
                "rejected",
                poly,
                existing_from_cat_partners,
                existing_to_cat_partners,
            )
            confession_changes = get_config("mates.confession.reactions_partners.rejected")
            cat_from_change, cat_to_change = _get_relationship_change_dict(
                confession_changes, variability
            )

    partner_string = relationship_text_adjust(partner_string, cat_from, cat_to)

    return become_partners, cat_from_change, cat_to_change, partner_string


def _attempt_mutual_interest_partners(
    cat_from: Cat, cat_to: Cat, disable_random: bool = False
):
    """Checks if the two cats have a high enough mutual interest to become partners. Handles the ensuing event if so."""

    become_partners = False

    if not _check_against_grief(cat_from, cat_to):
        return

    # Gather relationships
    if cat_to.ID in cat_from.relationships:
        relationship_from = cat_from.relationships[cat_to.ID]
    else:
        relationship_from = cat_from.create_one_relationship(cat_to)

    if cat_from.ID in cat_to.relationships:
        relationship_to = cat_to.relationships[cat_from.ID]
    else:
        relationship_to = cat_to.create_one_relationship(cat_from)

    partner_string = None
    partner_chance = get_config("mates.chance_fulfilled_condition_partners")
    becoming_partners = not int(random.random() * partner_chance) or disable_random

    # has to be high because every moon this will be checked for each relationship in the game
    romance_to_like = get_config("mates.chance_romance_to_like")
    becoming_romance_to_like = (
        not int(random.random() * romance_to_like) or disable_random
    )

    # already return if there is 'no' hit (everything above 0), other checks are not necessary
    if not becoming_partners and not becoming_romance_to_like:
        return

    # CHECK POLY
    existing_from_cat_partners, existing_to_cat_partners = _get_existing_partners(
        cat_from, cat_to
    )
    poly = any([existing_from_cat_partners, existing_to_cat_partners])

    if poly and not _current_partners_allow_new_partner(
        cat_from, cat_to, existing_from_cat_partners, existing_to_cat_partners
    ):
        return

    # GET TOGETHER
    if (
        becoming_partners
        and relationship_from.relationship_qualifies(get_config("mates.partner_condition"))
        and relationship_to.relationship_qualifies(get_config("mates.partner_condition"))
    ):
        become_partners = True
        if cat_from.ID in cat_to.previous_partners:
            partner_string = _get_partner_string(
                "low_like_makeup",
                poly,
                existing_from_cat_partners,
                existing_to_cat_partners,
            )
        else:
            partner_string = _get_partner_string(
                "low_like",
                poly,
                existing_from_cat_partners,
                existing_to_cat_partners,
            )
    elif (
        becoming_romance_to_like
        and relationship_from.relationship_qualifies(
            get_config("mates.romance_to_like")
        )
        and relationship_to.relationship_qualifies(get_config("mates.romance_to_like"))
    ):
        become_partners = True
        if cat_from.ID in cat_to.previous_partners:
            partner_string = _get_partner_string(
                "low_like_makeup",
                poly,
                existing_from_cat_partners,
                existing_to_cat_partners,
            )
        else:
            partner_string = _get_partner_string(
                "romance_to_like",
                poly,
                existing_from_cat_partners,
                existing_to_cat_partners,
            )

    if not become_partners:
        return

    if poly:
        print("----- POLY-POLY-POLY", cat_from.name, cat_to.name)
        print(cat_from.partner)
        print(cat_to.partner)

    partner_string = relationship_text_adjust(partner_string, cat_from, cat_to)

    cat_from_change = {
        "cats_from": [cat_from],
        "cats_to": [cat_to],
        "like": 10,
        "log": partner_string,
    }
    cat_to_change = {
        "cats_from": [cat_to],
        "cats_to": [cat_from],
        "like": 10,
        "log": partner_string,
    }
    # CHANGE VALUES
    change_relationship_values(
        **cat_from_change,
    )
    change_relationship_values(
        **cat_to_change,
    )

    cat_from.set_partner(cat_to)
    game.cur_events_list.append(
        EventInformation(
            partner_string,
            ["relation", "misc"],
            cat_dict={"m_c": cat_from, "r_c": cat_to},
            clan=cat_from.status.group_ID,
        )
    )


def _current_partners_allow_new_partner(
    cat_from: Cat, cat_to: Cat, cat_from_partners: list[str], cat_to_partners: list[str]
) -> bool:
    """
    Check if all current partners fulfill the required conditions to allow a new partner.
    :return: True if conditions are fulfilled, False if not
    """
    current_partner_condition = get_config("mates.poly.current_partner_condition")
    current_to_new_condition = get_config("mates.poly.partners_to_each_other")

    # check relationship from current partners from cat_from
    for partner_id in cat_from_partners:
        partner: Cat = Cat.fetch_cat(partner_id)
        if partner_id in cat_from.relationships and cat_from.ID in partner.relationships:
            if not cat_from.relationships[partner_id].relationship_qualifies(
                current_partner_condition
            ) or not partner.relationships[cat_from.ID].relationship_qualifies(
                current_partner_condition
            ):
                return False

        if partner_id in cat_to.relationships and cat_to.ID in partner.relationships:
            if not cat_to.relationships[partner_id].relationship_qualifies(
                current_to_new_condition
            ) or not partner.relationships[cat_to.ID].relationship_qualifies(
                current_to_new_condition
            ):
                return False

    # check relationship from current partners from cat_to
    for partner_id in cat_to_partners:
        partner = Cat.fetch_cat(partner_id)
        if partner_id in cat_to.relationships and cat_to.ID in partner.relationships:
            if not cat_to.relationships[partner_id].relationship_qualifies(
                current_partner_condition
            ) or not partner.relationships[cat_to.ID].relationship_qualifies(
                current_partner_condition
            ):
                return False

        if partner in cat_from.relationships and cat_from.ID in partner.relationships:
            if not cat_from.relationships[partner_id].relationship_qualifies(
                current_to_new_condition
            ) or not partner.relationships[cat_from.ID].relationship_qualifies(
                current_to_new_condition
            ):
                return False

    return True


def _check_against_grief(cat_from: Cat, cat_to: Cat) -> bool:
    """
    Checks if cat_to will still attempt to become partner with a grief stricken cat_from.
    :return: True if they will attempt, False if they won't
    """
    if "grief stricken" not in cat_to.illnesses:
        return True

    chance = get_config("mates.approach_grief.chance")
    # some cats might not be reading the room
    if cat_from.personality.trait in ("oblivious", "loving"):
        chance += get_config("mates.approach_grief.specific_trait_influence")
    for threshold_reached in [
        cat_from.personality.lawfulness < 8,
        cat_from.personality.sociability < 8,
        cat_from.personality.aggression > 8,
    ]:
        if threshold_reached:
            chance += get_config("mates.approach_grief.facet_influence")

    return random.random() < chance


def _get_existing_partners(cat_from: Cat, cat_to: Cat) -> tuple[list[str], list[str]]:
    """
    Returns living and present partners for cat_from and cat_to.
    return: Tuple with a list of IDs for each cat's partners
    """
    existing_from_cat_partners = [
        partner
        for partner in cat_from.partner
        if cat_from.fetch_cat(partner).status.group_ID == cat_from.status.group_ID
    ]
    existing_to_cat_partners = [
        partner
        for partner in cat_to.partner
        if cat_to.fetch_cat(partner).status.group_ID == cat_to.status.group_ID
    ]
    return existing_from_cat_partners, existing_to_cat_partners


def _get_relationship_change_dict(
    confession_changes: dict[str, dict], variability: tuple[int, int]
) -> tuple[dict, dict]:
    """
    Compiles rel change dictionaries for both cats according to the given base dictionary. Variability is applied to the values.
    """
    cat_from_change = confession_changes["cat_from"]
    for change in cat_from_change:
        cat_from_change[change] += random.randint(variability[0], variability[1])
    cat_to_change = confession_changes["cat_to"]
    for change in cat_to_change:
        cat_to_change[change] += random.randint(variability[0], variability[1])
    return cat_from_change, cat_to_change


def _get_partner_string(
    key: Literal[
        "high_like",
        "low_like",
        "romance_to_like",
        "rejected",
        "high_like_makeup",
        "low_like_makeup",
        "makeup_fail",
    ],
    poly: bool,
    cat_from_partners: list[str],
    cat_to_partners: list[str],
) -> str:
    """Returns a partner string within the given dictionary key based on given partners and poly status."""
    _rebuild_dicts()
    if not poly:
        return choice(PARTNER_DICTS[key])
    else:
        poly_key = ""
        if cat_from_partners and cat_to_partners:
            poly_key = "both_partners"
        elif not cat_to_partners and cat_from_partners:
            poly_key = "m_c_partners"
        elif not cat_from_partners and cat_to_partners:
            poly_key = "r_c_partners"
        if not poly_key:
            # none of the other involved partners are alive
            return choice(PARTNER_DICTS[key])
        return choice(POLY_PARTNER_DICTS[key][poly_key])


def _rebuild_dicts():
    global current_loaded_lang
    global PARTNER_DICTS
    global BREAKUP_STRINGS
    global POLY_PARTNER_DICTS

    if current_loaded_lang == i18n.config.get("locale"):
        return

    path = "events/relationship_events/"
    PARTNER_DICTS = load_lang_resource(f"{path}become_partners.json")
    BREAKUP_STRINGS = load_lang_resource(f"{path}breakup_partners.json")
    POLY_PARTNER_DICTS = load_lang_resource(f"{path}become_partners_poly.json")

    current_loaded_lang = i18n.config.get("locale")
