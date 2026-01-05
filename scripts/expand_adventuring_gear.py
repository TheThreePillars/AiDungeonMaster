"""Expand adventuring gear in equipment.json."""

import json
from pathlib import Path

# Additional adventuring gear to add
NEW_GEAR = [
    # Containers
    {"name": "Barrel", "cost": 2, "weight": 30, "description": "Holds 10 cubic feet of liquid or dry goods"},
    {"name": "Basket", "cost": 0.4, "weight": 1, "description": "Holds 2 cubic feet of goods"},
    {"name": "Bucket", "cost": 0.5, "weight": 2, "description": "Holds 1 cubic foot of liquid"},
    {"name": "Case, Map or Scroll", "cost": 1, "weight": 0.5, "description": "Leather tube for maps and scrolls"},
    {"name": "Chest, Small", "cost": 2, "weight": 25, "description": "Holds 2 cubic feet of goods"},
    {"name": "Chest, Medium", "cost": 5, "weight": 50, "description": "Holds 4 cubic feet of goods"},
    {"name": "Chest, Large", "cost": 10, "weight": 100, "description": "Holds 8 cubic feet of goods"},
    {"name": "Flask", "cost": 0.03, "weight": 0, "description": "Holds 1 pint of liquid"},
    {"name": "Jug, Clay", "cost": 0.03, "weight": 1, "description": "Holds 1 gallon of liquid"},
    {"name": "Vial", "cost": 1, "weight": 0, "description": "Holds 1 ounce of liquid"},
    {"name": "Bottle, Wine Glass", "cost": 2, "weight": 0, "description": "Holds 1.5 pints of liquid"},

    # Light sources
    {"name": "Lamp, Common", "cost": 0.1, "weight": 1, "description": "Burns 6 hours on 1 pint of oil, 15-ft radius"},
    {"name": "Candles (10)", "cost": 0.1, "weight": 0, "description": "10 candles, each burns 1 hour, 5-ft dim light"},
    {"name": "Torches (10)", "cost": 0.1, "weight": 10, "description": "10 torches, each burns 1 hour, 20-ft normal light"},
    {"name": "Sunrod", "cost": 2, "weight": 1, "description": "Glows for 6 hours, 30-ft normal light"},

    # Food and drink
    {"name": "Ale (gallon)", "cost": 0.2, "weight": 8, "description": "Common ale"},
    {"name": "Ale (mug)", "cost": 0.04, "weight": 1, "description": "Single serving of ale"},
    {"name": "Wine, Common (pitcher)", "cost": 0.2, "weight": 6, "description": "Common table wine"},
    {"name": "Wine, Fine (bottle)", "cost": 10, "weight": 1.5, "description": "Quality vintage wine"},
    {"name": "Bread (loaf)", "cost": 0.02, "weight": 0.5, "description": "Standard loaf of bread"},
    {"name": "Cheese (hunk)", "cost": 0.1, "weight": 0.5, "description": "Wedge of cheese"},
    {"name": "Meat, Chunk", "cost": 0.3, "weight": 0.5, "description": "Chunk of cooked meat"},
    {"name": "Meal, Common", "cost": 0.3, "weight": 0, "description": "Bread, cheese, and drink"},
    {"name": "Meal, Good", "cost": 0.5, "weight": 0, "description": "Meat, bread, vegetables, and drink"},
    {"name": "Banquet (per person)", "cost": 10, "weight": 0, "description": "Extravagant feast"},
    {"name": "Feed (per day)", "cost": 0.05, "weight": 10, "description": "Animal feed for one day"},

    # Clothing
    {"name": "Artisan's Outfit", "cost": 1, "weight": 4, "description": "Shirt, pants, boots, apron"},
    {"name": "Cleric's Vestments", "cost": 5, "weight": 6, "description": "Religious ceremonial clothing"},
    {"name": "Cold Weather Outfit", "cost": 8, "weight": 7, "description": "Wool coat, linen shirt, wool cap, gloves, cloak, boots"},
    {"name": "Courtier's Outfit", "cost": 30, "weight": 6, "description": "Fancy clothing for noble courts"},
    {"name": "Entertainer's Outfit", "cost": 3, "weight": 4, "description": "Flashy clothes for performers"},
    {"name": "Explorer's Outfit", "cost": 10, "weight": 8, "description": "Boots, breeches, belt, shirt, jacket, gloves, cloak"},
    {"name": "Monk's Outfit", "cost": 5, "weight": 2, "description": "Simple loose clothing"},
    {"name": "Noble's Outfit", "cost": 75, "weight": 10, "description": "Silk, velvet, fur trim"},
    {"name": "Peasant's Outfit", "cost": 0.1, "weight": 2, "description": "Loose shirt, breeches, sandals"},
    {"name": "Royal Outfit", "cost": 200, "weight": 15, "description": "Jeweled, finest materials"},
    {"name": "Scholar's Outfit", "cost": 5, "weight": 6, "description": "Robe, belt, cap, soft shoes"},
    {"name": "Traveler's Outfit", "cost": 1, "weight": 5, "description": "Boots, wool breeches, sturdy belt, shirt, jacket"},
    {"name": "Cloak", "cost": 0.5, "weight": 2, "description": "Simple cloth cloak"},
    {"name": "Cloak, Winter", "cost": 5, "weight": 3, "description": "Heavy wool cloak"},
    {"name": "Hat", "cost": 0.1, "weight": 0, "description": "Simple hat"},
    {"name": "Boots", "cost": 1, "weight": 1, "description": "Leather boots"},
    {"name": "Gloves", "cost": 1, "weight": 0, "description": "Leather gloves"},

    # Tools and kits
    {"name": "Alchemist's Lab", "cost": 200, "weight": 40, "description": "+2 to Craft (alchemy) checks"},
    {"name": "Artisan's Tools", "cost": 5, "weight": 5, "description": "Tools for a specific craft"},
    {"name": "Artisan's Tools, Masterwork", "cost": 55, "weight": 5, "description": "+2 to specific Craft checks"},
    {"name": "Climber's Kit", "cost": 80, "weight": 5, "description": "+2 to Climb checks"},
    {"name": "Disguise Kit", "cost": 50, "weight": 8, "description": "+2 to Disguise checks"},
    {"name": "Healer's Kit", "cost": 50, "weight": 1, "description": "10 uses, +2 to Heal checks"},
    {"name": "Holly and Mistletoe", "cost": 0, "weight": 0, "description": "Druid divine focus"},
    {"name": "Holy Symbol, Wooden", "cost": 1, "weight": 0, "description": "Wooden divine focus"},
    {"name": "Holy Symbol, Silver", "cost": 25, "weight": 1, "description": "Silver divine focus"},
    {"name": "Magnifying Glass", "cost": 100, "weight": 0, "description": "+2 to Appraise for small items"},
    {"name": "Musical Instrument, Common", "cost": 5, "weight": 3, "description": "Flute, lute, mandolin, etc."},
    {"name": "Musical Instrument, Masterwork", "cost": 100, "weight": 3, "description": "+2 to Perform checks"},
    {"name": "Scale, Merchant", "cost": 2, "weight": 1, "description": "Balance and weights"},
    {"name": "Spell Component Pouch", "cost": 5, "weight": 2, "description": "Holds material components"},
    {"name": "Spellbook, Blank", "cost": 15, "weight": 3, "description": "100 pages for spells"},
    {"name": "Writing Kit", "cost": 10, "weight": 1, "description": "Ink, inkpens, paper"},

    # Adventuring supplies
    {"name": "Block and Tackle", "cost": 5, "weight": 5, "description": "+5 to Strength for lifting"},
    {"name": "Fishing Net", "cost": 4, "weight": 5, "description": "25 sq. ft. net"},
    {"name": "Ladder, 10-ft.", "cost": 0.05, "weight": 20, "description": "Wooden ladder"},
    {"name": "Saw", "cost": 0.04, "weight": 2, "description": "Hand saw"},
    {"name": "Shovel", "cost": 2, "weight": 8, "description": "Digging tool"},
    {"name": "Sledge", "cost": 1, "weight": 10, "description": "Heavy hammer"},
    {"name": "Signal Whistle", "cost": 0.8, "weight": 0, "description": "Audible for 1/4 mile"},
    {"name": "Soap", "cost": 0.5, "weight": 1, "description": "1 lb. bar of soap"},
    {"name": "Signet Ring", "cost": 5, "weight": 0, "description": "Personal seal"},
    {"name": "Sealing Wax", "cost": 1, "weight": 1, "description": "For sealing letters"},
    {"name": "Sewing Needle", "cost": 0.5, "weight": 0, "description": "Steel needle"},
    {"name": "Bell", "cost": 1, "weight": 0, "description": "Small bell"},
    {"name": "Parchment (sheet)", "cost": 0.2, "weight": 0, "description": "Animal skin writing surface"},
    {"name": "Hourglass", "cost": 25, "weight": 1, "description": "Measures 1 hour"},
    {"name": "Compass", "cost": 10, "weight": 0.5, "description": "+2 to avoid getting lost"},

    # Alchemical items
    {"name": "Alchemist's Fire", "cost": 20, "weight": 1, "description": "1d6 fire damage, burns for 2 rounds"},
    {"name": "Acid (flask)", "cost": 10, "weight": 1, "description": "1d6 acid damage"},
    {"name": "Antitoxin", "cost": 50, "weight": 0, "description": "+5 alchemical bonus vs poison for 1 hour"},
    {"name": "Holy Water (flask)", "cost": 25, "weight": 1, "description": "2d4 damage to undead/evil outsiders"},
    {"name": "Smokestick", "cost": 20, "weight": 0.5, "description": "Creates 10-ft cube of smoke"},
    {"name": "Tanglefoot Bag", "cost": 50, "weight": 4, "description": "Entangles target"},
    {"name": "Thunderstone", "cost": 30, "weight": 1, "description": "DC 15 Fort or deafened 1 hour"},
    {"name": "Tindertwig", "cost": 1, "weight": 0, "description": "Ignites as move action"},

    # Mounts and related
    {"name": "Saddle, Riding", "cost": 10, "weight": 25, "description": "Standard riding saddle"},
    {"name": "Saddle, Military", "cost": 20, "weight": 30, "description": "+2 to Ride checks to stay mounted"},
    {"name": "Saddle, Pack", "cost": 5, "weight": 15, "description": "For pack animals"},
    {"name": "Saddlebags", "cost": 4, "weight": 8, "description": "Holds 20 lbs. each side"},
    {"name": "Bit and Bridle", "cost": 2, "weight": 1, "description": "For controlling mounts"},
    {"name": "Barding, Leather", "cost": 40, "weight": 30, "description": "Light armor for mount"},
    {"name": "Barding, Chain", "cost": 300, "weight": 80, "description": "Medium armor for mount"},
    {"name": "Stabling (per day)", "cost": 0.5, "weight": 0, "description": "Care and shelter for mount"},

    # Services (cost per day/use)
    {"name": "Inn Stay, Common (per night)", "cost": 0.5, "weight": 0, "description": "Bed in common room"},
    {"name": "Inn Stay, Good (per night)", "cost": 2, "weight": 0, "description": "Small private room"},
    {"name": "Inn Stay, Luxury (per night)", "cost": 5, "weight": 0, "description": "Large suite"},
    {"name": "Hireling, Untrained (per day)", "cost": 0.1, "weight": 0, "description": "Laborer, porter"},
    {"name": "Hireling, Trained (per day)", "cost": 0.3, "weight": 0, "description": "Scribe, teamster"},
    {"name": "Messenger (per mile)", "cost": 0.02, "weight": 0, "description": "Deliver a message"},
    {"name": "Road/Gate Toll", "cost": 0.01, "weight": 0, "description": "Typical toll"},
    {"name": "Ship Passage (per mile)", "cost": 0.1, "weight": 0, "description": "Standard passage"},

    # Miscellaneous
    {"name": "Blanket, Winter", "cost": 0.5, "weight": 3, "description": "Heavy wool blanket"},
    {"name": "Firewood (per day)", "cost": 0.01, "weight": 20, "description": "Bundle of firewood"},
    {"name": "String (50 ft.)", "cost": 0.01, "weight": 0.5, "description": "Light cord"},
    {"name": "Thread (50 ft.)", "cost": 0.01, "weight": 0, "description": "Sewing thread"},
    {"name": "Wire (1 ft.)", "cost": 5, "weight": 0, "description": "Metal wire"},
    {"name": "Powder (packet)", "cost": 0.01, "weight": 0, "description": "Cosmetic powder"},
    {"name": "Perfume (dose)", "cost": 5, "weight": 0, "description": "Fine perfume"},
]


def main():
    equipment_path = Path(__file__).parent.parent / "data" / "srd" / "equipment.json"

    with open(equipment_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Get existing names
    existing_names = {item["name"].lower() for item in data.get("adventuring_gear", [])}

    # Add new items
    added = 0
    for item in NEW_GEAR:
        if item["name"].lower() not in existing_names:
            data["adventuring_gear"].append(item)
            existing_names.add(item["name"].lower())
            added += 1
            print(f"Added: {item['name']}")

    # Sort by name
    data["adventuring_gear"].sort(key=lambda x: x["name"])

    # Save
    with open(equipment_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nAdded {added} adventuring gear items")
    print(f"Total adventuring gear: {len(data['adventuring_gear'])}")


if __name__ == "__main__":
    main()
