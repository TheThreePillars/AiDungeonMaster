"""Add core Pathfinder monsters to monsters.json."""

import json
from pathlib import Path

# Core monsters to add - covering CR 0-20 and various types
CORE_MONSTERS = [
    # CR 1/4 - 1/2
    {"name": "Giant Rat", "cr": 0.25, "xp": 100, "alignment": "N", "size": "Small", "type": "animal", "ac": 14, "hp": 5, "speed": "40 ft., climb 20 ft., swim 20 ft."},
    {"name": "Stirge", "cr": 0.5, "xp": 200, "alignment": "N", "size": "Tiny", "type": "magical beast", "ac": 16, "hp": 5, "speed": "10 ft., fly 40 ft. (average)"},
    {"name": "Giant Centipede", "cr": 0.5, "xp": 200, "alignment": "N", "size": "Medium", "type": "vermin", "ac": 14, "hp": 5, "speed": "40 ft., climb 40 ft."},

    # CR 1
    {"name": "Giant Frog", "cr": 1, "xp": 400, "alignment": "N", "size": "Medium", "type": "animal", "ac": 12, "hp": 15, "speed": "30 ft., swim 30 ft."},
    {"name": "Hobgoblin", "cr": 1, "xp": 400, "alignment": "LE", "size": "Medium", "type": "humanoid (goblinoid)", "ac": 16, "hp": 17, "speed": "30 ft."},
    {"name": "Ghoul", "cr": 1, "xp": 400, "alignment": "CE", "size": "Medium", "type": "undead", "ac": 14, "hp": 13, "speed": "30 ft."},
    {"name": "Gnoll", "cr": 1, "xp": 400, "alignment": "CE", "size": "Medium", "type": "humanoid (gnoll)", "ac": 15, "hp": 11, "speed": "30 ft."},
    {"name": "Fire Beetle", "cr": 1, "xp": 400, "alignment": "N", "size": "Small", "type": "vermin", "ac": 12, "hp": 6, "speed": "30 ft."},

    # CR 2
    {"name": "Worg", "cr": 2, "xp": 600, "alignment": "NE", "size": "Medium", "type": "magical beast", "ac": 14, "hp": 26, "speed": "50 ft."},
    {"name": "Boar", "cr": 2, "xp": 600, "alignment": "N", "size": "Medium", "type": "animal", "ac": 14, "hp": 18, "speed": "40 ft."},
    {"name": "Crocodile", "cr": 2, "xp": 600, "alignment": "N", "size": "Large", "type": "animal", "ac": 14, "hp": 22, "speed": "20 ft., swim 30 ft."},
    {"name": "Giant Leech", "cr": 2, "xp": 600, "alignment": "N", "size": "Medium", "type": "vermin", "ac": 11, "hp": 19, "speed": "5 ft., swim 20 ft."},
    {"name": "Wererat (hybrid)", "cr": 2, "xp": 600, "alignment": "LE", "size": "Medium", "type": "humanoid (human, shapechanger)", "ac": 16, "hp": 20, "speed": "30 ft."},
    {"name": "Troglodyte", "cr": 2, "xp": 600, "alignment": "CE", "size": "Medium", "type": "humanoid (reptilian)", "ac": 15, "hp": 13, "speed": "30 ft."},

    # CR 3
    {"name": "Bugbear", "cr": 3, "xp": 800, "alignment": "CE", "size": "Medium", "type": "humanoid (goblinoid)", "ac": 17, "hp": 27, "speed": "30 ft."},
    {"name": "Wight", "cr": 3, "xp": 800, "alignment": "LE", "size": "Medium", "type": "undead", "ac": 15, "hp": 26, "speed": "30 ft."},
    {"name": "Werewolf (hybrid)", "cr": 3, "xp": 800, "alignment": "CE", "size": "Medium", "type": "humanoid (human, shapechanger)", "ac": 16, "hp": 32, "speed": "30 ft."},
    {"name": "Cockatrice", "cr": 3, "xp": 800, "alignment": "N", "size": "Small", "type": "magical beast", "ac": 15, "hp": 27, "speed": "20 ft., fly 60 ft. (poor)"},
    {"name": "Doppelganger", "cr": 3, "xp": 800, "alignment": "N", "size": "Medium", "type": "monstrous humanoid (shapechanger)", "ac": 16, "hp": 26, "speed": "30 ft."},
    {"name": "Shadow", "cr": 3, "xp": 800, "alignment": "CE", "size": "Medium", "type": "undead (incorporeal)", "ac": 14, "hp": 19, "speed": "fly 40 ft. (good)"},
    {"name": "Giant Scorpion", "cr": 3, "xp": 800, "alignment": "N", "size": "Large", "type": "vermin", "ac": 16, "hp": 37, "speed": "50 ft."},

    # CR 4
    {"name": "Minotaur", "cr": 4, "xp": 1200, "alignment": "CE", "size": "Large", "type": "monstrous humanoid", "ac": 14, "hp": 45, "speed": "30 ft."},
    {"name": "Gargoyle", "cr": 4, "xp": 1200, "alignment": "CE", "size": "Medium", "type": "monstrous humanoid (earth)", "ac": 16, "hp": 42, "speed": "40 ft., fly 60 ft. (average)"},
    {"name": "Ettin", "cr": 6, "xp": 2400, "alignment": "CE", "size": "Large", "type": "humanoid (giant)", "ac": 18, "hp": 65, "speed": "40 ft."},
    {"name": "Basilisk", "cr": 5, "xp": 1600, "alignment": "N", "size": "Medium", "type": "magical beast", "ac": 17, "hp": 52, "speed": "20 ft."},
    {"name": "Wraith", "cr": 5, "xp": 1600, "alignment": "LE", "size": "Medium", "type": "undead (incorporeal)", "ac": 18, "hp": 47, "speed": "fly 60 ft. (good)"},
    {"name": "Mummy", "cr": 5, "xp": 1600, "alignment": "LE", "size": "Medium", "type": "undead", "ac": 20, "hp": 60, "speed": "20 ft."},

    # CR 5-6
    {"name": "Griffon", "cr": 4, "xp": 1200, "alignment": "N", "size": "Large", "type": "magical beast", "ac": 17, "hp": 42, "speed": "30 ft., fly 80 ft. (average)"},
    {"name": "Manticore", "cr": 5, "xp": 1600, "alignment": "LE", "size": "Large", "type": "magical beast", "ac": 17, "hp": 57, "speed": "30 ft., fly 50 ft. (clumsy)"},
    {"name": "Hill Giant", "cr": 7, "xp": 3200, "alignment": "CE", "size": "Large", "type": "humanoid (giant)", "ac": 21, "hp": 85, "speed": "40 ft."},
    {"name": "Wyvern", "cr": 6, "xp": 2400, "alignment": "N", "size": "Large", "type": "dragon", "ac": 19, "hp": 73, "speed": "20 ft., fly 60 ft. (poor)"},
    {"name": "Chimera", "cr": 7, "xp": 3200, "alignment": "CE", "size": "Large", "type": "magical beast", "ac": 19, "hp": 85, "speed": "30 ft., fly 50 ft. (poor)"},

    # CR 7-9
    {"name": "Stone Giant", "cr": 8, "xp": 4800, "alignment": "N", "size": "Large", "type": "humanoid (giant)", "ac": 22, "hp": 102, "speed": "40 ft."},
    {"name": "Frost Giant", "cr": 9, "xp": 6400, "alignment": "CE", "size": "Large", "type": "humanoid (giant, cold)", "ac": 21, "hp": 133, "speed": "40 ft."},
    {"name": "Fire Giant", "cr": 10, "xp": 9600, "alignment": "LE", "size": "Large", "type": "humanoid (giant, fire)", "ac": 24, "hp": 142, "speed": "40 ft."},
    {"name": "Hydra (5-headed)", "cr": 4, "xp": 1200, "alignment": "N", "size": "Huge", "type": "magical beast", "ac": 15, "hp": 47, "speed": "20 ft., swim 20 ft."},
    {"name": "Hydra (7-headed)", "cr": 6, "xp": 2400, "alignment": "N", "size": "Huge", "type": "magical beast", "ac": 15, "hp": 73, "speed": "20 ft., swim 20 ft."},
    {"name": "Hydra (9-headed)", "cr": 8, "xp": 4800, "alignment": "N", "size": "Huge", "type": "magical beast", "ac": 15, "hp": 99, "speed": "20 ft., swim 20 ft."},
    {"name": "Medusa", "cr": 7, "xp": 3200, "alignment": "LE", "size": "Medium", "type": "monstrous humanoid", "ac": 15, "hp": 76, "speed": "30 ft."},
    {"name": "Naga, Spirit", "cr": 9, "xp": 6400, "alignment": "CE", "size": "Large", "type": "aberration", "ac": 23, "hp": 95, "speed": "40 ft., swim 20 ft."},
    {"name": "Spectre", "cr": 7, "xp": 3200, "alignment": "LE", "size": "Medium", "type": "undead (incorporeal)", "ac": 15, "hp": 52, "speed": "fly 80 ft. (perfect)"},

    # CR 10-12
    {"name": "Cloud Giant", "cr": 11, "xp": 12800, "alignment": "NG", "size": "Huge", "type": "humanoid (giant)", "ac": 25, "hp": 168, "speed": "50 ft."},
    {"name": "Storm Giant", "cr": 13, "xp": 25600, "alignment": "CG", "size": "Huge", "type": "humanoid (giant)", "ac": 28, "hp": 199, "speed": "50 ft., swim 40 ft."},
    {"name": "Adult Black Dragon", "cr": 11, "xp": 12800, "alignment": "CE", "size": "Large", "type": "dragon (water)", "ac": 28, "hp": 161, "speed": "60 ft., fly 200 ft. (poor), swim 60 ft."},
    {"name": "Adult Green Dragon", "cr": 12, "xp": 19200, "alignment": "LE", "size": "Large", "type": "dragon (air)", "ac": 28, "hp": 172, "speed": "40 ft., fly 200 ft. (poor), swim 40 ft."},
    {"name": "Adult Blue Dragon", "cr": 13, "xp": 25600, "alignment": "LE", "size": "Huge", "type": "dragon (earth)", "ac": 28, "hp": 184, "speed": "40 ft., burrow 20 ft., fly 200 ft. (poor)"},
    {"name": "Adult White Dragon", "cr": 10, "xp": 9600, "alignment": "CE", "size": "Large", "type": "dragon (cold)", "ac": 26, "hp": 149, "speed": "30 ft., burrow 30 ft., fly 200 ft. (poor), swim 60 ft."},
    {"name": "Vampire", "cr": 9, "xp": 6400, "alignment": "CE", "size": "Medium", "type": "undead (augmented humanoid)", "ac": 23, "hp": 102, "speed": "30 ft."},
    {"name": "Roper", "cr": 12, "xp": 19200, "alignment": "CE", "size": "Large", "type": "aberration", "ac": 27, "hp": 162, "speed": "10 ft."},

    # CR 13-16 (High level encounters)
    {"name": "Adult Red Dragon", "cr": 14, "xp": 38400, "alignment": "CE", "size": "Huge", "type": "dragon (fire)", "ac": 29, "hp": 212, "speed": "40 ft., fly 200 ft. (poor)"},
    {"name": "Beholder", "cr": 13, "xp": 25600, "alignment": "LE", "size": "Large", "type": "aberration", "ac": 26, "hp": 180, "speed": "5 ft., fly 20 ft. (good)"},
    {"name": "Purple Worm", "cr": 12, "xp": 19200, "alignment": "N", "size": "Gargantuan", "type": "magical beast", "ac": 26, "hp": 200, "speed": "20 ft., burrow 20 ft., swim 10 ft."},
    {"name": "Iron Golem", "cr": 13, "xp": 25600, "alignment": "N", "size": "Large", "type": "construct", "ac": 28, "hp": 129, "speed": "20 ft."},
    {"name": "Lich", "cr": 12, "xp": 19200, "alignment": "NE", "size": "Medium", "type": "undead (augmented humanoid)", "ac": 25, "hp": 111, "speed": "30 ft."},
    {"name": "Efreeti", "cr": 8, "xp": 4800, "alignment": "LE", "size": "Large", "type": "outsider (extraplanar, fire)", "ac": 19, "hp": 95, "speed": "20 ft., fly 40 ft. (perfect)"},
    {"name": "Djinni", "cr": 5, "xp": 1600, "alignment": "CG", "size": "Large", "type": "outsider (air, extraplanar)", "ac": 18, "hp": 52, "speed": "20 ft., fly 60 ft. (perfect)"},

    # Demons & Devils
    {"name": "Dretch", "cr": 2, "xp": 600, "alignment": "CE", "size": "Small", "type": "outsider (chaotic, demon, evil, extraplanar)", "ac": 14, "hp": 18, "speed": "20 ft."},
    {"name": "Quasit", "cr": 2, "xp": 600, "alignment": "CE", "size": "Tiny", "type": "outsider (chaotic, demon, evil, extraplanar)", "ac": 16, "hp": 16, "speed": "20 ft., fly 50 ft. (perfect)"},
    {"name": "Succubus", "cr": 7, "xp": 3200, "alignment": "CE", "size": "Medium", "type": "outsider (chaotic, demon, evil, extraplanar)", "ac": 20, "hp": 84, "speed": "30 ft., fly 50 ft. (average)"},
    {"name": "Vrock", "cr": 9, "xp": 6400, "alignment": "CE", "size": "Large", "type": "outsider (chaotic, demon, evil, extraplanar)", "ac": 22, "hp": 112, "speed": "30 ft., fly 50 ft. (average)"},
    {"name": "Hezrou", "cr": 11, "xp": 12800, "alignment": "CE", "size": "Large", "type": "outsider (chaotic, demon, evil, extraplanar)", "ac": 25, "hp": 145, "speed": "30 ft., swim 30 ft."},
    {"name": "Glabrezu", "cr": 13, "xp": 25600, "alignment": "CE", "size": "Huge", "type": "outsider (chaotic, demon, evil, extraplanar)", "ac": 28, "hp": 186, "speed": "40 ft."},
    {"name": "Nalfeshnee", "cr": 14, "xp": 38400, "alignment": "CE", "size": "Huge", "type": "outsider (chaotic, demon, evil, extraplanar)", "ac": 29, "hp": 203, "speed": "30 ft., fly 40 ft. (poor)"},
    {"name": "Marilith", "cr": 17, "xp": 102400, "alignment": "CE", "size": "Large", "type": "outsider (chaotic, demon, evil, extraplanar)", "ac": 32, "hp": 264, "speed": "40 ft."},
    {"name": "Balor", "cr": 20, "xp": 307200, "alignment": "CE", "size": "Large", "type": "outsider (chaotic, demon, evil, extraplanar)", "ac": 36, "hp": 370, "speed": "40 ft., fly 90 ft. (good)"},
    {"name": "Imp", "cr": 2, "xp": 600, "alignment": "LE", "size": "Tiny", "type": "outsider (devil, evil, extraplanar, lawful)", "ac": 17, "hp": 16, "speed": "20 ft., fly 50 ft. (perfect)"},
    {"name": "Lemure", "cr": 1, "xp": 400, "alignment": "LE", "size": "Medium", "type": "outsider (devil, evil, extraplanar, lawful)", "ac": 14, "hp": 13, "speed": "20 ft."},
    {"name": "Bearded Devil", "cr": 5, "xp": 1600, "alignment": "LE", "size": "Medium", "type": "outsider (devil, evil, extraplanar, lawful)", "ac": 19, "hp": 57, "speed": "40 ft."},
    {"name": "Erinyes", "cr": 8, "xp": 4800, "alignment": "LE", "size": "Medium", "type": "outsider (devil, evil, extraplanar, lawful)", "ac": 23, "hp": 94, "speed": "30 ft., fly 50 ft. (good)"},
    {"name": "Bone Devil", "cr": 9, "xp": 6400, "alignment": "LE", "size": "Large", "type": "outsider (devil, evil, extraplanar, lawful)", "ac": 25, "hp": 105, "speed": "40 ft., fly 60 ft. (good)"},
    {"name": "Horned Devil", "cr": 16, "xp": 76800, "alignment": "LE", "size": "Large", "type": "outsider (devil, evil, extraplanar, lawful)", "ac": 35, "hp": 217, "speed": "30 ft., fly 50 ft. (average)"},
    {"name": "Ice Devil", "cr": 13, "xp": 25600, "alignment": "LE", "size": "Large", "type": "outsider (devil, evil, extraplanar, lawful)", "ac": 32, "hp": 161, "speed": "40 ft., fly 60 ft. (good)"},
    {"name": "Pit Fiend", "cr": 20, "xp": 307200, "alignment": "LE", "size": "Large", "type": "outsider (devil, evil, extraplanar, lawful)", "ac": 38, "hp": 350, "speed": "40 ft., fly 60 ft. (average)"},

    # Elementals
    {"name": "Small Fire Elemental", "cr": 1, "xp": 400, "alignment": "N", "size": "Small", "type": "outsider (elemental, extraplanar, fire)", "ac": 16, "hp": 11, "speed": "50 ft."},
    {"name": "Medium Fire Elemental", "cr": 3, "xp": 800, "alignment": "N", "size": "Medium", "type": "outsider (elemental, extraplanar, fire)", "ac": 17, "hp": 30, "speed": "50 ft."},
    {"name": "Large Fire Elemental", "cr": 5, "xp": 1600, "alignment": "N", "size": "Large", "type": "outsider (elemental, extraplanar, fire)", "ac": 18, "hp": 60, "speed": "50 ft."},
    {"name": "Huge Fire Elemental", "cr": 7, "xp": 3200, "alignment": "N", "size": "Huge", "type": "outsider (elemental, extraplanar, fire)", "ac": 19, "hp": 95, "speed": "60 ft."},
    {"name": "Elder Fire Elemental", "cr": 11, "xp": 12800, "alignment": "N", "size": "Huge", "type": "outsider (elemental, extraplanar, fire)", "ac": 24, "hp": 152, "speed": "60 ft."},
    {"name": "Small Water Elemental", "cr": 1, "xp": 400, "alignment": "N", "size": "Small", "type": "outsider (elemental, extraplanar, water)", "ac": 17, "hp": 13, "speed": "20 ft., swim 90 ft."},
    {"name": "Large Water Elemental", "cr": 5, "xp": 1600, "alignment": "N", "size": "Large", "type": "outsider (elemental, extraplanar, water)", "ac": 19, "hp": 68, "speed": "20 ft., swim 90 ft."},
    {"name": "Elder Water Elemental", "cr": 11, "xp": 12800, "alignment": "N", "size": "Huge", "type": "outsider (elemental, extraplanar, water)", "ac": 24, "hp": 152, "speed": "20 ft., swim 90 ft."},
    {"name": "Small Earth Elemental", "cr": 1, "xp": 400, "alignment": "N", "size": "Small", "type": "outsider (earth, elemental, extraplanar)", "ac": 17, "hp": 13, "speed": "20 ft., burrow 20 ft."},
    {"name": "Large Earth Elemental", "cr": 5, "xp": 1600, "alignment": "N", "size": "Large", "type": "outsider (earth, elemental, extraplanar)", "ac": 18, "hp": 68, "speed": "20 ft., burrow 20 ft."},
    {"name": "Elder Earth Elemental", "cr": 11, "xp": 12800, "alignment": "N", "size": "Huge", "type": "outsider (earth, elemental, extraplanar)", "ac": 23, "hp": 152, "speed": "20 ft., burrow 20 ft."},
    {"name": "Small Air Elemental", "cr": 1, "xp": 400, "alignment": "N", "size": "Small", "type": "outsider (air, elemental, extraplanar)", "ac": 17, "hp": 9, "speed": "fly 100 ft. (perfect)"},
    {"name": "Large Air Elemental", "cr": 5, "xp": 1600, "alignment": "N", "size": "Large", "type": "outsider (air, elemental, extraplanar)", "ac": 21, "hp": 68, "speed": "fly 100 ft. (perfect)"},
    {"name": "Elder Air Elemental", "cr": 11, "xp": 12800, "alignment": "N", "size": "Huge", "type": "outsider (air, elemental, extraplanar)", "ac": 27, "hp": 152, "speed": "fly 100 ft. (perfect)"},

    # More classic monsters
    {"name": "Gelatinous Cube", "cr": 3, "xp": 800, "alignment": "N", "size": "Large", "type": "ooze", "ac": 4, "hp": 50, "speed": "15 ft."},
    {"name": "Black Pudding", "cr": 7, "xp": 3200, "alignment": "N", "size": "Huge", "type": "ooze", "ac": 3, "hp": 105, "speed": "20 ft., climb 20 ft."},
    {"name": "Ochre Jelly", "cr": 5, "xp": 1600, "alignment": "N", "size": "Large", "type": "ooze", "ac": 4, "hp": 63, "speed": "10 ft., climb 10 ft."},
    {"name": "Gray Ooze", "cr": 4, "xp": 1200, "alignment": "N", "size": "Medium", "type": "ooze", "ac": 5, "hp": 50, "speed": "10 ft."},
    {"name": "Rust Monster", "cr": 3, "xp": 800, "alignment": "N", "size": "Medium", "type": "aberration", "ac": 18, "hp": 27, "speed": "40 ft., climb 10 ft."},
    {"name": "Otyugh", "cr": 4, "xp": 1200, "alignment": "N", "size": "Large", "type": "aberration", "ac": 17, "hp": 39, "speed": "20 ft."},
    {"name": "Gibbering Mouther", "cr": 5, "xp": 1600, "alignment": "N", "size": "Medium", "type": "aberration", "ac": 19, "hp": 46, "speed": "10 ft., swim 20 ft."},
    {"name": "Mind Flayer", "cr": 8, "xp": 4800, "alignment": "LE", "size": "Medium", "type": "aberration", "ac": 15, "hp": 83, "speed": "30 ft."},
    {"name": "Aboleth", "cr": 7, "xp": 3200, "alignment": "LE", "size": "Huge", "type": "aberration (aquatic)", "ac": 20, "hp": 84, "speed": "10 ft., swim 60 ft."},
    {"name": "Carrion Crawler", "cr": 4, "xp": 1200, "alignment": "N", "size": "Large", "type": "aberration", "ac": 17, "hp": 51, "speed": "30 ft., climb 30 ft."},
    {"name": "Cloaker", "cr": 5, "xp": 1600, "alignment": "CN", "size": "Large", "type": "aberration", "ac": 19, "hp": 51, "speed": "10 ft., fly 40 ft. (average)"},
    {"name": "Displacer Beast", "cr": 4, "xp": 1200, "alignment": "LE", "size": "Large", "type": "magical beast", "ac": 16, "hp": 51, "speed": "40 ft."},
    {"name": "Phase Spider", "cr": 5, "xp": 1600, "alignment": "N", "size": "Large", "type": "magical beast", "ac": 17, "hp": 51, "speed": "40 ft., climb 20 ft."},
    {"name": "Bulette", "cr": 7, "xp": 3200, "alignment": "N", "size": "Huge", "type": "magical beast", "ac": 22, "hp": 84, "speed": "40 ft., burrow 20 ft."},
    {"name": "Behir", "cr": 8, "xp": 4800, "alignment": "N", "size": "Huge", "type": "magical beast", "ac": 21, "hp": 105, "speed": "40 ft., climb 20 ft."},
    {"name": "Ankheg", "cr": 3, "xp": 800, "alignment": "N", "size": "Large", "type": "magical beast", "ac": 16, "hp": 28, "speed": "30 ft., burrow 20 ft."},
    {"name": "Ettercap", "cr": 3, "xp": 800, "alignment": "NE", "size": "Medium", "type": "aberration", "ac": 15, "hp": 30, "speed": "30 ft., climb 30 ft."},
    {"name": "Harpy", "cr": 4, "xp": 1200, "alignment": "CE", "size": "Medium", "type": "monstrous humanoid", "ac": 16, "hp": 38, "speed": "20 ft., fly 80 ft. (average)"},
    {"name": "Centaur", "cr": 3, "xp": 800, "alignment": "N", "size": "Large", "type": "monstrous humanoid", "ac": 17, "hp": 30, "speed": "50 ft."},
    {"name": "Nymph", "cr": 7, "xp": 3200, "alignment": "CG", "size": "Medium", "type": "fey", "ac": 23, "hp": 60, "speed": "30 ft., swim 20 ft."},
    {"name": "Dryad", "cr": 3, "xp": 800, "alignment": "CG", "size": "Medium", "type": "fey", "ac": 17, "hp": 27, "speed": "30 ft."},
    {"name": "Satyr", "cr": 4, "xp": 1200, "alignment": "CN", "size": "Medium", "type": "fey", "ac": 18, "hp": 44, "speed": "40 ft."},
    {"name": "Pixie", "cr": 4, "xp": 1200, "alignment": "NG", "size": "Small", "type": "fey", "ac": 18, "hp": 18, "speed": "20 ft., fly 60 ft. (good)"},
    {"name": "Treant", "cr": 8, "xp": 4800, "alignment": "NG", "size": "Huge", "type": "plant", "ac": 21, "hp": 114, "speed": "30 ft."},
    {"name": "Shambling Mound", "cr": 6, "xp": 2400, "alignment": "N", "size": "Large", "type": "plant", "ac": 19, "hp": 67, "speed": "20 ft., swim 20 ft."},
]


def main():
    """Add core monsters to monsters.json."""
    monsters_path = Path(__file__).parent.parent / "data" / "srd" / "monsters.json"

    # Load existing monsters
    with open(monsters_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both formats
    if isinstance(data, dict) and "monsters" in data:
        existing = data["monsters"]
        is_wrapped = True
    else:
        existing = data
        is_wrapped = False

    # Get existing names
    existing_names = {m["name"].lower() for m in existing}

    # Add new monsters
    added = 0
    for monster in CORE_MONSTERS:
        if monster["name"].lower() not in existing_names:
            # Add consistent fields
            new_monster = {
                "name": monster["name"],
                "cr": monster["cr"],
                "xp": monster["xp"],
                "alignment": monster["alignment"],
                "size": monster["size"],
                "type": monster["type"],
                "subtype": "",
                "initiative": 0,
                "senses": "",
                "ac": monster["ac"],
                "hp": monster["hp"],
                "speed": monster["speed"],
                "attacks": "",
                "special_attacks": "",
                "special_qualities": "",
                "saves": "",
                "abilities": "",
                "skills": "",
                "feats": "",
                "environment": "",
                "organization": "",
                "treasure": "standard",
            }
            existing.append(new_monster)
            existing_names.add(monster["name"].lower())
            added += 1
            print(f"Added: {monster['name']} (CR {monster['cr']})")

    # Sort by CR then name
    existing.sort(key=lambda x: (float(x.get("cr", 0)), x.get("name", "")))

    # Save
    output = {"monsters": existing} if is_wrapped else existing
    with open(monsters_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nAdded {added} monsters. Total: {len(existing)}")


if __name__ == "__main__":
    main()
