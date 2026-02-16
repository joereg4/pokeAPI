#!/usr/bin/env python
# scripts/warm_sprite_cache.py
"""Pre-warm the species ID -> artwork ID cache for multi-form Pokemon.

Official artwork sprites on GitHub are keyed by species (National Dex) ID.
Pokemon forms (IDs >= 10000) don't have artwork at their form ID, so we
need to resolve form_id -> species_id.  This script pre-resolves all known
multi-form Pokemon so the first request doesn't trigger an API call.

Usage:
    # From the project root:
    python scripts/warm_sprite_cache.py

    # Or via Flask CLI (if integrated):
    flask warm-sprite-cache

Design:
    The heavy lifting is done by pokedex.species_resolver.warm_cache(),
    which calls resolve_species_id() for each form ID.  Each resolution
    checks Redis first, calls the API on cache miss, and stores the result
    in Redis with a 30-day TTL.

    This script can be run safely multiple times (idempotent).  Cached
    entries are refreshed on each run.

Source of form IDs:
    Known multi-form Pokemon from PokéAPI.  Form IDs start at 10001
    and are assigned sequentially.  This list was compiled from
    https://pokeapi.co/api/v2/pokemon?limit=100000 and filtered for
    IDs >= 10000.
"""

import sys
import os
import logging

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Well-known multi-form Pokemon with their form IDs and species IDs.
# Format: (form_id, species_id, description)
# This list covers the most commonly encountered forms that cause
# artwork 404s when not pre-resolved.
KNOWN_FORMS = [
    # Deoxys forms (species 386)
    (10001, 386, "deoxys-attack"),
    (10002, 386, "deoxys-defense"),
    (10003, 386, "deoxys-speed"),
    # Wormadam forms (species 413)
    (10004, 413, "wormadam-sandy"),
    (10005, 413, "wormadam-trash"),
    # Shaymin (species 492)
    (10006, 492, "shaymin-sky"),
    # Giratina (species 487)
    (10007, 487, "giratina-origin"),
    # Rotom forms (species 479)
    (10008, 479, "rotom-heat"),
    (10009, 479, "rotom-wash"),
    (10010, 479, "rotom-frost"),
    (10011, 479, "rotom-fan"),
    (10012, 479, "rotom-mow"),
    # Castform forms (species 351)
    (10013, 351, "castform-sunny"),
    (10014, 351, "castform-rainy"),
    (10015, 351, "castform-snowy"),
    # Basculin (species 550)
    (10016, 550, "basculin-blue-striped"),
    # Darmanitan (species 555)
    (10017, 555, "darmanitan-zen"),
    # Meloetta (species 648)
    (10018, 648, "meloetta-pirouette"),
    # Tornadus, Thundurus, Landorus therian forms (species 641, 642, 645)
    (10019, 641, "tornadus-therian"),
    (10020, 642, "thundurus-therian"),
    (10021, 645, "landorus-therian"),
    # Kyurem forms (species 646)
    (10022, 646, "kyurem-black"),
    (10023, 646, "kyurem-white"),
    # Keldeo (species 647)
    (10024, 647, "keldeo-resolute"),
    # Meowstic female (species 678)
    (10025, 678, "meowstic-female"),
    # Aegislash (species 681)
    (10026, 681, "aegislash-blade"),
    # Pumpkaboo / Gourgeist size variants (species 710, 711)
    (10027, 710, "pumpkaboo-small"),
    (10028, 710, "pumpkaboo-large"),
    (10029, 710, "pumpkaboo-super"),
    (10030, 711, "gourgeist-small"),
    (10031, 711, "gourgeist-large"),
    (10032, 711, "gourgeist-super"),
    # Venusaur, Charizard, Blastoise megas (species 3, 6, 9)
    (10033, 3, "venusaur-mega"),
    (10034, 6, "charizard-mega-x"),
    (10035, 6, "charizard-mega-y"),
    (10036, 9, "blastoise-mega"),
    # Alakazam, Gengar, Kangaskhan, Pinsir megas
    (10037, 65, "alakazam-mega"),
    (10038, 94, "gengar-mega"),
    (10039, 115, "kangaskhan-mega"),
    (10040, 127, "pinsir-mega"),
    # Gyarados, Aerodactyl megas
    (10041, 130, "gyarados-mega"),
    (10042, 142, "aerodactyl-mega"),
    # Mewtwo megas
    (10043, 150, "mewtwo-mega-x"),
    (10044, 150, "mewtwo-mega-y"),
    # Ampharos, Scizor, Heracross, Houndoom megas
    (10045, 181, "ampharos-mega"),
    (10046, 212, "scizor-mega"),
    (10047, 214, "heracross-mega"),
    (10048, 229, "houndoom-mega"),
    # Tyranitar, Blaziken, Gardevoir, Mawile, Aggron, Medicham megas
    (10049, 248, "tyranitar-mega"),
    (10050, 257, "blaziken-mega"),
    (10051, 282, "gardevoir-mega"),
    (10052, 303, "mawile-mega"),
    (10053, 306, "aggron-mega"),
    (10054, 308, "medicham-mega"),
    # Manectric, Banette, Absol, Garchomp, Lucario, Abomasnow megas
    (10055, 310, "manectric-mega"),
    (10056, 354, "banette-mega"),
    (10057, 359, "absol-mega"),
    (10058, 445, "garchomp-mega"),
    (10059, 448, "lucario-mega"),
    (10060, 460, "abomasnow-mega"),
    # Hoopa (species 720)
    (10086, 720, "hoopa-unbound"),
    # Oricorio forms (species 741)
    (10123, 741, "oricorio-pom-pom"),
    (10124, 741, "oricorio-pau"),
    (10125, 741, "oricorio-sensu"),
    # Lycanroc forms (species 745)
    (10126, 745, "lycanroc-midnight"),
    (10152, 745, "lycanroc-dusk"),
    # Wishiwashi (species 746)
    (10127, 746, "wishiwashi-school"),
    # Minior (species 774)
    (10136, 774, "minior-red-meteor"),
    # Mimikyu (species 778)
    (10143, 778, "mimikyu-busted"),
    # Necrozma forms (species 800)
    (10155, 800, "necrozma-dusk"),
    (10156, 800, "necrozma-dawn"),
    (10157, 800, "necrozma-ultra"),
    # Toxtricity (species 849)
    (10184, 849, "toxtricity-low-key"),
    # Urshifu (species 892)
    (10191, 892, "urshifu-rapid-strike"),
    # Calyrex forms (species 898)
    (10193, 898, "calyrex-ice"),
    (10194, 898, "calyrex-shadow"),
    # Enamorus (species 905)
    (10249, 905, "enamorus-therian"),
    # Palafin (species 964)
    (10256, 964, "palafin-hero"),
    # Tatsugiri forms (species 978)
    (10257, 978, "tatsugiri-droopy"),
    (10258, 978, "tatsugiri-stretchy"),
    # Dudunsparce (species 982)
    (10259, 982, "dudunsparce-three-segment"),
    # Gimmighoul (species 999)
    (10260, 999, "gimmighoul-roaming"),
    # Ogerpon forms (species 1017)
    (10273, 1017, "ogerpon-wellspring-mask"),
    (10274, 1017, "ogerpon-hearthflame-mask"),
    (10275, 1017, "ogerpon-cornerstone-mask"),
]


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger(__name__)

    from pokedex.species_resolver import warm_cache

    form_ids = [form_id for form_id, _, _ in KNOWN_FORMS]

    logger.info("Warming sprite cache for %d known form Pokemon...", len(form_ids))
    results = warm_cache(form_ids)

    logger.info(
        "Cache warming complete: %d/%d forms resolved successfully.",
        len(results),
        len(form_ids),
    )

    # Verify against known mappings
    mismatches = []
    for form_id, expected_species_id, name in KNOWN_FORMS:
        actual = results.get(form_id)
        if actual is not None and actual != expected_species_id:
            mismatches.append(
                f"  {name} (form {form_id}): expected species {expected_species_id}, "
                f"got {actual}"
            )

    if mismatches:
        logger.warning(
            "Species ID mismatches detected:\n%s", "\n".join(mismatches)
        )
    else:
        logger.info("All resolved species IDs match expected values.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
