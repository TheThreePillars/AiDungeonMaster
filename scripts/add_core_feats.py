"""Add missing core Pathfinder feats to feats.json."""

import json
from pathlib import Path

# Core feats to add
CORE_FEATS = [
    # General Combat Feats
    {
        "name": "Toughness",
        "type": "General",
        "description": "You have enhanced physical stamina.",
        "prerequisites": "",
        "benefit": "You gain +3 hit points. For every Hit Die you possess beyond 3, you gain an additional +1 hit point. If you have more than 3 Hit Dice, you gain +1 hit points whenever you gain a Hit Die."
    },
    {
        "name": "Improved Initiative",
        "type": "Combat",
        "description": "Your quick reflexes allow you to react rapidly to danger.",
        "prerequisites": "",
        "benefit": "You get a +4 bonus on initiative checks."
    },
    {
        "name": "Cleave",
        "type": "Combat",
        "description": "You can strike two adjacent foes with a single swing.",
        "prerequisites": "Str 13, Power Attack, base attack bonus +1",
        "benefit": "As a standard action, you can make a single attack at your full base attack bonus against a foe within reach. If you hit, you deal damage normally and can make an additional attack at your full base attack bonus against a foe adjacent to the first and within reach."
    },
    {
        "name": "Great Cleave",
        "type": "Combat",
        "description": "You can strike many adjacent foes with a single blow.",
        "prerequisites": "Str 13, Cleave, Power Attack, base attack bonus +4",
        "benefit": "As a standard action, you can make a single attack at your full base attack bonus against a foe within reach. If you hit, you deal damage normally and can make additional attacks against foes adjacent to the previous foe at your full base attack bonus, as long as they are within reach."
    },
    {
        "name": "Vital Strike",
        "type": "Combat",
        "description": "You make a single attack that deals significantly more damage than normal.",
        "prerequisites": "Base attack bonus +6",
        "benefit": "When you use the attack action, you can make one attack at your highest base attack bonus that deals additional damage. Roll the weapon's damage dice for the attack twice and add the results together before adding bonuses."
    },
    {
        "name": "Improved Vital Strike",
        "type": "Combat",
        "description": "You can make a single attack that deals a large amount of damage.",
        "prerequisites": "Vital Strike, base attack bonus +11",
        "benefit": "When you use the attack action, you can make one attack at your highest base attack bonus that deals additional damage. Roll the weapon's damage dice for the attack three times and add the results together."
    },
    {
        "name": "Greater Vital Strike",
        "type": "Combat",
        "description": "You can make a single attack that deals tremendous damage.",
        "prerequisites": "Improved Vital Strike, Vital Strike, base attack bonus +16",
        "benefit": "When you use the attack action, you can make one attack at your highest base attack bonus that deals additional damage. Roll the weapon's damage dice for the attack four times and add the results together."
    },

    # Combat Expertise Chain
    {
        "name": "Combat Expertise",
        "type": "Combat",
        "description": "You can increase your defense at the expense of your accuracy.",
        "prerequisites": "Int 13",
        "benefit": "You can choose to take a -1 penalty on melee attack rolls and combat maneuver checks to gain a +1 dodge bonus to your Armor Class. This penalty increases by -1 for every +4 base attack bonus you have. You can only choose to use this feat when you declare an attack."
    },
    {
        "name": "Improved Trip",
        "type": "Combat",
        "description": "You are skilled at sending your opponents to the ground.",
        "prerequisites": "Int 13, Combat Expertise",
        "benefit": "You do not provoke an attack of opportunity when performing a trip combat maneuver. In addition, you receive a +2 bonus on checks made to trip a foe. You also receive a +2 bonus to your Combat Maneuver Defense whenever an opponent tries to trip you."
    },
    {
        "name": "Greater Trip",
        "type": "Combat",
        "description": "You can make free attacks on foes that you knock down.",
        "prerequisites": "Int 13, Combat Expertise, Improved Trip, base attack bonus +6",
        "benefit": "You receive a +2 bonus on checks made to trip a foe. This bonus stacks with the bonus granted by Improved Trip. Whenever you successfully trip an opponent, that opponent provokes attacks of opportunity."
    },
    {
        "name": "Improved Disarm",
        "type": "Combat",
        "description": "You are skilled at knocking weapons from a foe's grasp.",
        "prerequisites": "Int 13, Combat Expertise",
        "benefit": "You do not provoke an attack of opportunity when performing a disarm combat maneuver. In addition, you receive a +2 bonus on checks made to disarm a foe. You also receive a +2 bonus to your CMD when an opponent tries to disarm you."
    },
    {
        "name": "Greater Disarm",
        "type": "Combat",
        "description": "You can knock weapons far from an enemy's grasp.",
        "prerequisites": "Int 13, Combat Expertise, Improved Disarm, base attack bonus +6",
        "benefit": "You receive a +2 bonus on checks made to disarm a foe. This bonus stacks with Improved Disarm. Whenever you successfully disarm an opponent, the weapon lands 15 feet away in a random direction."
    },
    {
        "name": "Improved Feint",
        "type": "Combat",
        "description": "You are skilled at fooling your opponents in combat.",
        "prerequisites": "Int 13, Combat Expertise",
        "benefit": "You can make a Bluff check to feint in combat as a move action."
    },
    {
        "name": "Greater Feint",
        "type": "Combat",
        "description": "You are skilled at making foes overreact to your attacks.",
        "prerequisites": "Int 13, Combat Expertise, Improved Feint, base attack bonus +6",
        "benefit": "Whenever you use feint to cause an opponent to lose his Dexterity bonus, he loses that bonus until the beginning of your next turn, in addition to losing his Dexterity bonus against your next attack."
    },

    # Ranged Combat Feats
    {
        "name": "Point-Blank Shot",
        "type": "Combat",
        "description": "You are especially accurate when making ranged attacks against close targets.",
        "prerequisites": "",
        "benefit": "You get a +1 bonus on attack and damage rolls with ranged weapons at ranges of up to 30 feet."
    },
    {
        "name": "Precise Shot",
        "type": "Combat",
        "description": "You are adept at firing ranged attacks into melee.",
        "prerequisites": "Point-Blank Shot",
        "benefit": "You can shoot or throw ranged weapons at an opponent engaged in melee without taking the standard -4 penalty on your attack roll."
    },
    {
        "name": "Improved Precise Shot",
        "type": "Combat",
        "description": "Your ranged attacks ignore anything but total concealment and cover.",
        "prerequisites": "Dex 19, Point-Blank Shot, Precise Shot, base attack bonus +11",
        "benefit": "Your ranged attacks ignore the AC bonus granted to targets by anything less than total cover, and the miss chance granted to targets by anything less than total concealment."
    },
    {
        "name": "Rapid Shot",
        "type": "Combat",
        "description": "You can make an extra ranged attack.",
        "prerequisites": "Dex 13, Point-Blank Shot",
        "benefit": "When making a full-attack action with a ranged weapon, you can fire one additional time this round at your highest bonus. All of your attack rolls take a -2 penalty when using Rapid Shot."
    },
    {
        "name": "Manyshot",
        "type": "Combat",
        "description": "You can fire multiple arrows at a single target.",
        "prerequisites": "Dex 17, Point-Blank Shot, Rapid Shot, base attack bonus +6",
        "benefit": "When making a full-attack action with a bow, your first attack fires two arrows. If the attack hits, both arrows hit. Apply precision-based damage only once. Critical hits and other effects only apply to one arrow."
    },
    {
        "name": "Deadly Aim",
        "type": "Combat",
        "description": "You can make exceptionally deadly ranged attacks by pinpointing a foe's weak spot.",
        "prerequisites": "Dex 13, base attack bonus +1",
        "benefit": "You can choose to take a -1 penalty on all ranged attack rolls to gain a +2 bonus on all ranged damage rolls. For every +4 base attack bonus, the penalty increases by -1 and the bonus to damage increases by +2."
    },
    {
        "name": "Far Shot",
        "type": "Combat",
        "description": "You are more accurate at longer ranges.",
        "prerequisites": "Point-Blank Shot",
        "benefit": "You only suffer a -1 penalty per full range increment between you and your target when using a ranged weapon."
    },
    {
        "name": "Shot on the Run",
        "type": "Combat",
        "description": "You can move, fire a ranged weapon, and move again before your foes can react.",
        "prerequisites": "Dex 13, Dodge, Mobility, Point-Blank Shot, base attack bonus +4",
        "benefit": "As a full-round action, you can move up to your speed and make a single ranged attack at any point during your movement."
    },

    # Metamagic Feats
    {
        "name": "Empower Spell",
        "type": "Metamagic",
        "description": "You can increase the power of your spells, causing them to deal more damage.",
        "prerequisites": "",
        "benefit": "All variable, numeric effects of an empowered spell are increased by half including bonuses to those dice rolls. An empowered spell uses up a spell slot two levels higher than the spell's actual level."
    },
    {
        "name": "Maximize Spell",
        "type": "Metamagic",
        "description": "Your spells have the maximum possible effect.",
        "prerequisites": "",
        "benefit": "All variable, numeric effects of a spell are maximized. A maximized spell uses up a spell slot three levels higher than the spell's actual level."
    },
    {
        "name": "Quicken Spell",
        "type": "Metamagic",
        "description": "You can cast spells in a fraction of the normal time.",
        "prerequisites": "",
        "benefit": "Casting a quickened spell is a swift action. You can perform another action, even casting another spell, in the same round. A quickened spell uses up a spell slot four levels higher than the spell's actual level."
    },
    {
        "name": "Silent Spell",
        "type": "Metamagic",
        "description": "You can cast your spells without making any sound.",
        "prerequisites": "",
        "benefit": "A silent spell can be cast with no verbal components. A silent spell uses up a spell slot one level higher than the spell's actual level."
    },
    {
        "name": "Still Spell",
        "type": "Metamagic",
        "description": "You can cast spells without moving.",
        "prerequisites": "",
        "benefit": "A stilled spell can be cast with no somatic components. A stilled spell uses up a spell slot one level higher than the spell's actual level."
    },
    {
        "name": "Extend Spell",
        "type": "Metamagic",
        "description": "You can make your spells last twice as long.",
        "prerequisites": "",
        "benefit": "An extended spell lasts twice as long as normal. An extended spell uses up a spell slot one level higher than the spell's actual level."
    },
    {
        "name": "Heighten Spell",
        "type": "Metamagic",
        "description": "You can cast a spell as if it were a higher level.",
        "prerequisites": "",
        "benefit": "A heightened spell has a higher spell level than normal (up to 9th level). Unlike other metamagic feats, Heighten Spell actually increases the effective level of the spell."
    },
    {
        "name": "Widen Spell",
        "type": "Metamagic",
        "description": "You can increase the area of your spells.",
        "prerequisites": "",
        "benefit": "You can alter a burst, emanation, or spread-shaped spell to increase its area. Any numeric measurements of the spell's area increase by 100%. A widened spell uses up a spell slot three levels higher than the spell's actual level."
    },
    {
        "name": "Enlarge Spell",
        "type": "Metamagic",
        "description": "You can increase the range of your spells.",
        "prerequisites": "",
        "benefit": "You can alter a spell with a range of close, medium, or long to increase its range by 100%. An enlarged spell uses up a spell slot one level higher than the spell's actual level."
    },

    # Save Bonus Feats
    {
        "name": "Lightning Reflexes",
        "type": "General",
        "description": "You have faster reflexes than normal.",
        "prerequisites": "",
        "benefit": "You get a +2 bonus on all Reflex saving throws."
    },
    {
        "name": "Improved Lightning Reflexes",
        "type": "General",
        "description": "You have an uncanny ability to avoid danger.",
        "prerequisites": "Lightning Reflexes",
        "benefit": "Once per day, you may reroll a Reflex save. You must decide to use this ability before the results are revealed. You must take the second roll, even if it is worse."
    },
    {
        "name": "Great Fortitude",
        "type": "General",
        "description": "You are resistant to poisons, diseases, and other maladies.",
        "prerequisites": "",
        "benefit": "You get a +2 bonus on all Fortitude saving throws."
    },
    {
        "name": "Improved Great Fortitude",
        "type": "General",
        "description": "You have remarkable stamina.",
        "prerequisites": "Great Fortitude",
        "benefit": "Once per day, you may reroll a Fortitude save. You must decide to use this ability before the results are revealed. You must take the second roll, even if it is worse."
    },
    {
        "name": "Iron Will",
        "type": "General",
        "description": "You are more resistant to mental effects.",
        "prerequisites": "",
        "benefit": "You get a +2 bonus on all Will saving throws."
    },
    {
        "name": "Improved Iron Will",
        "type": "General",
        "description": "Your clarity of thought allows you to resist mental attacks.",
        "prerequisites": "Iron Will",
        "benefit": "Once per day, you may reroll a Will save. You must decide to use this ability before the results are revealed. You must take the second roll, even if it is worse."
    },

    # Two-Weapon Fighting
    {
        "name": "Two-Weapon Fighting",
        "type": "Combat",
        "description": "You can fight with a weapon wielded in each of your hands.",
        "prerequisites": "Dex 15",
        "benefit": "Your penalties on attack rolls for fighting with two weapons are reduced. The penalty for your primary hand lessens by 2 and the one for your off hand lessens by 6."
    },
    {
        "name": "Improved Two-Weapon Fighting",
        "type": "Combat",
        "description": "You are skilled at fighting with two weapons.",
        "prerequisites": "Dex 17, Two-Weapon Fighting, base attack bonus +6",
        "benefit": "In addition to the standard single extra attack you get with an off-hand weapon, you get a second attack with it, albeit at a -5 penalty."
    },
    {
        "name": "Greater Two-Weapon Fighting",
        "type": "Combat",
        "description": "You are incredibly skilled at fighting with two weapons at the same time.",
        "prerequisites": "Dex 19, Improved Two-Weapon Fighting, Two-Weapon Fighting, base attack bonus +11",
        "benefit": "You get a third attack with your off-hand weapon, albeit at a -10 penalty."
    },
    {
        "name": "Two-Weapon Defense",
        "type": "Combat",
        "description": "You are skilled at defending yourself while dual-wielding.",
        "prerequisites": "Dex 15, Two-Weapon Fighting",
        "benefit": "When wielding a double weapon or two weapons, you gain a +1 shield bonus to your AC. When you are fighting defensively or using the total defense action, this shield bonus increases to +2."
    },
    {
        "name": "Double Slice",
        "type": "Combat",
        "description": "Your off-hand weapon strikes with greater power.",
        "prerequisites": "Dex 15, Two-Weapon Fighting",
        "benefit": "Add your Strength bonus to damage rolls made with your off-hand weapon."
    },

    # Other Core Combat Feats
    {
        "name": "Weapon Finesse",
        "type": "Combat",
        "description": "You are trained in using your agility in melee combat.",
        "prerequisites": "",
        "benefit": "With a light weapon, elven curve blade, rapier, whip, or spiked chain made for a creature of your size category, you may use your Dexterity modifier instead of your Strength modifier on attack rolls."
    },
    {
        "name": "Weapon Focus",
        "type": "Combat",
        "description": "Choose one type of weapon. You are especially good at using this type of weapon.",
        "prerequisites": "Proficiency with selected weapon, base attack bonus +1",
        "benefit": "You gain a +1 bonus on all attack rolls you make using the selected weapon."
    },
    {
        "name": "Greater Weapon Focus",
        "type": "Combat",
        "description": "Choose one type of weapon for which you have already selected Weapon Focus. You are a master at using this type of weapon.",
        "prerequisites": "Proficiency with selected weapon, Weapon Focus with selected weapon, fighter level 8th",
        "benefit": "You gain a +1 bonus on attack rolls you make using the selected weapon. This bonus stacks with other bonuses on attack rolls, including the one from Weapon Focus."
    },
    {
        "name": "Weapon Specialization",
        "type": "Combat",
        "description": "Choose one type of weapon for which you have already selected Weapon Focus. You deal extra damage when using this type of weapon.",
        "prerequisites": "Proficiency with selected weapon, Weapon Focus with selected weapon, fighter level 4th",
        "benefit": "You gain a +2 bonus on all damage rolls you make using the selected weapon."
    },
    {
        "name": "Greater Weapon Specialization",
        "type": "Combat",
        "description": "Choose one type of weapon for which you have already selected Weapon Specialization. You deal even more damage when using this type of weapon.",
        "prerequisites": "Proficiency with selected weapon, Greater Weapon Focus, Weapon Focus, Weapon Specialization, fighter level 12th",
        "benefit": "You gain a +2 bonus on all damage rolls you make using the selected weapon. This bonus stacks with other bonuses on damage rolls, including the one from Weapon Specialization."
    },

    # Combat Maneuver Feats
    {
        "name": "Improved Grapple",
        "type": "Combat",
        "description": "You are skilled at grappling opponents.",
        "prerequisites": "Dex 13, Improved Unarmed Strike",
        "benefit": "You do not provoke an attack of opportunity when performing a grapple combat maneuver. In addition, you receive a +2 bonus on checks made to grapple a foe. You also receive a +2 bonus to your CMD whenever an opponent tries to grapple you."
    },
    {
        "name": "Greater Grapple",
        "type": "Combat",
        "description": "Maintaining a grapple is second nature to you.",
        "prerequisites": "Dex 13, Improved Grapple, Improved Unarmed Strike, base attack bonus +6",
        "benefit": "You receive a +2 bonus on checks made to grapple a foe. This bonus stacks with Improved Grapple. Once you have grappled a creature, maintaining the grapple is a move action."
    },
    {
        "name": "Improved Bull Rush",
        "type": "Combat",
        "description": "You are skilled at pushing your foes around.",
        "prerequisites": "Str 13, Power Attack",
        "benefit": "You do not provoke an attack of opportunity when performing a bull rush combat maneuver. In addition, you receive a +2 bonus on checks made to bull rush a foe. You also receive a +2 bonus to your CMD whenever an opponent tries to bull rush you."
    },
    {
        "name": "Greater Bull Rush",
        "type": "Combat",
        "description": "Your bull rush attacks throw enemies off balance.",
        "prerequisites": "Str 13, Improved Bull Rush, Power Attack, base attack bonus +6",
        "benefit": "You receive a +2 bonus on checks made to bull rush a foe. This bonus stacks with Improved Bull Rush. Whenever you bull rush an opponent, his movement provokes attacks of opportunity from all of your allies."
    },
    {
        "name": "Improved Sunder",
        "type": "Combat",
        "description": "You are skilled at damaging your foes' weapons and armor.",
        "prerequisites": "Str 13, Power Attack",
        "benefit": "You do not provoke an attack of opportunity when performing a sunder combat maneuver. In addition, you receive a +2 bonus on checks made to sunder an item. You also receive a +2 bonus to your CMD when an opponent tries to sunder your gear."
    },
    {
        "name": "Greater Sunder",
        "type": "Combat",
        "description": "Your devastating strikes cleave through weapons and armor and into their wielders.",
        "prerequisites": "Str 13, Improved Sunder, Power Attack, base attack bonus +6",
        "benefit": "You receive a +2 bonus on checks made to sunder an item. This bonus stacks with Improved Sunder. Whenever you sunder to destroy a weapon, shield, or suit of armor, any excess damage is applied to the item's wielder."
    },
    {
        "name": "Improved Overrun",
        "type": "Combat",
        "description": "You are skilled at running down your foes.",
        "prerequisites": "Str 13, Power Attack",
        "benefit": "You do not provoke an attack of opportunity when performing an overrun combat maneuver. In addition, you receive a +2 bonus on checks made to overrun a foe. You also receive a +2 bonus to your CMD when an opponent tries to overrun you."
    },
    {
        "name": "Greater Overrun",
        "type": "Combat",
        "description": "Enemies must dive to avoid your dangerous overruns.",
        "prerequisites": "Str 13, Improved Overrun, Power Attack, base attack bonus +6",
        "benefit": "You receive a +2 bonus on checks made to overrun a foe. This bonus stacks with Improved Overrun. Whenever you overrun opponents, they provoke attacks of opportunity if they are knocked prone."
    },

    # Movement Feats
    {
        "name": "Dodge",
        "type": "Combat",
        "description": "Your training and reflexes allow you to react swiftly to avoid an opponent's attacks.",
        "prerequisites": "Dex 13",
        "benefit": "You gain a +1 dodge bonus to your AC. A condition that makes you lose your Dex bonus to AC also makes you lose the benefits of this feat."
    },
    {
        "name": "Mobility",
        "type": "Combat",
        "description": "You can easily move through a dangerous melee.",
        "prerequisites": "Dex 13, Dodge",
        "benefit": "You get a +4 dodge bonus to Armor Class against attacks of opportunity caused when you move out of or within a threatened area."
    },
    {
        "name": "Spring Attack",
        "type": "Combat",
        "description": "You can deftly move up to a foe, strike, and withdraw before he can react.",
        "prerequisites": "Dex 13, Dodge, Mobility, base attack bonus +4",
        "benefit": "As a full-round action, you can move up to your speed and make a single melee attack without provoking any attacks of opportunity from the target of your attack."
    },
    {
        "name": "Wind Stance",
        "type": "Combat",
        "description": "Your erratic movements make it difficult for enemies to pinpoint your location.",
        "prerequisites": "Dex 15, Dodge, base attack bonus +6",
        "benefit": "If you move more than 5 feet this turn, you gain 20% concealment for 1 round."
    },
    {
        "name": "Lightning Stance",
        "type": "Combat",
        "description": "The speed at which you move makes it nearly impossible for opponents to strike you.",
        "prerequisites": "Dex 17, Dodge, Wind Stance, base attack bonus +11",
        "benefit": "If you take two actions to move or a withdraw action in a turn, you gain 50% concealment for 1 round."
    },

    # Unarmed/Monk Style
    {
        "name": "Improved Unarmed Strike",
        "type": "Combat",
        "description": "You are skilled at fighting while unarmed.",
        "prerequisites": "",
        "benefit": "You are considered to be armed even when unarmed. You do not provoke attacks of opportunity when you attack foes while unarmed. You can make an unarmed attack as either a main hand or off-hand attack."
    },
    {
        "name": "Stunning Fist",
        "type": "Combat",
        "description": "You know just where to strike to temporarily stun a foe.",
        "prerequisites": "Dex 13, Wis 13, Improved Unarmed Strike, base attack bonus +8",
        "benefit": "You must declare that you are using this feat before you make your attack roll. Stunning Fist forces a foe damaged by your unarmed attack to make a Fortitude saving throw (DC 10 + 1/2 your character level + your Wis modifier), in addition to dealing damage normally. A defender who fails this saving throw is stunned for 1 round."
    },
    {
        "name": "Deflect Arrows",
        "type": "Combat",
        "description": "You can knock arrows and other projectiles off course.",
        "prerequisites": "Dex 13, Improved Unarmed Strike",
        "benefit": "You must have at least one hand free to use this feat. Once per round when you would normally be hit with an attack from a ranged weapon, you may deflect it so that you take no damage from it."
    },
    {
        "name": "Snatch Arrows",
        "type": "Combat",
        "description": "Instead of knocking an arrow aside, you can catch it in mid-flight.",
        "prerequisites": "Dex 15, Deflect Arrows, Improved Unarmed Strike",
        "benefit": "When using the Deflect Arrows feat you may catch the weapon instead of just deflecting it. Thrown weapons can immediately be thrown back as an attack against the original attacker."
    },

    # Shield Feats
    {
        "name": "Shield Focus",
        "type": "Combat",
        "description": "You are skilled at deflecting blows with your shield.",
        "prerequisites": "Shield Proficiency, base attack bonus +1",
        "benefit": "Increase the AC bonus granted by any shield you are using by 1."
    },
    {
        "name": "Greater Shield Focus",
        "type": "Combat",
        "description": "You are skilled at deflecting blows with your shield.",
        "prerequisites": "Shield Focus, Shield Proficiency, fighter level 8th",
        "benefit": "Increase the AC bonus granted by any shield you are using by 1. This bonus stacks with the bonus granted by Shield Focus."
    },
    {
        "name": "Shield Slam",
        "type": "Combat",
        "description": "In the right position, your shield can be used to send opponents flying.",
        "prerequisites": "Improved Shield Bash, Shield Proficiency, Two-Weapon Fighting, base attack bonus +6",
        "benefit": "Any opponents hit by your shield bash are also hit with a free bull rush attack, substituting your attack roll for the combat maneuver check."
    },
    {
        "name": "Improved Shield Bash",
        "type": "Combat",
        "description": "You can protect yourself with your shield, even if you use it to attack.",
        "prerequisites": "Shield Proficiency",
        "benefit": "When you perform a shield bash, you may still apply the shield's shield bonus to your AC."
    },

    # Critical Feats
    {
        "name": "Critical Focus",
        "type": "Combat",
        "description": "You are trained in the art of causing pain.",
        "prerequisites": "Base attack bonus +9",
        "benefit": "You receive a +4 circumstance bonus on attack rolls made to confirm critical hits."
    },
    {
        "name": "Bleeding Critical",
        "type": "Combat, Critical",
        "description": "Your critical hits cause opponents to bleed profusely.",
        "prerequisites": "Critical Focus, base attack bonus +11",
        "benefit": "Whenever you score a critical hit with a slashing or piercing weapon, your opponent takes 2d6 points of bleed damage each round on his turn, in addition to the damage dealt by the critical hit."
    },
    {
        "name": "Blinding Critical",
        "type": "Combat, Critical",
        "description": "Your critical hits blind your opponents.",
        "prerequisites": "Critical Focus, base attack bonus +15",
        "benefit": "Whenever you score a critical hit, your opponent is permanently blinded. A successful Fortitude save reduces this to dazzled for 1d4 rounds. The DC is 10 + your base attack bonus."
    },
    {
        "name": "Staggering Critical",
        "type": "Combat, Critical",
        "description": "Your critical hits cause opponents to slow down.",
        "prerequisites": "Critical Focus, base attack bonus +13",
        "benefit": "Whenever you score a critical hit, your opponent becomes staggered for 1d4+1 rounds. A successful Fortitude save reduces the duration to 1 round. The DC is 10 + your base attack bonus."
    },
    {
        "name": "Stunning Critical",
        "type": "Combat, Critical",
        "description": "Your critical hits stun your opponents.",
        "prerequisites": "Critical Focus, Staggering Critical, base attack bonus +17",
        "benefit": "Whenever you score a critical hit, your opponent becomes stunned for 1d4 rounds. A successful Fortitude save reduces this to staggered for 1d4 rounds. The DC is 10 + your base attack bonus."
    },

    # Spell Feats
    {
        "name": "Spell Focus",
        "type": "General",
        "description": "Choose a school of magic. Any spells you cast of that school are more difficult to resist.",
        "prerequisites": "",
        "benefit": "Add +1 to the Difficulty Class for all saving throws against spells from the school of magic you select."
    },
    {
        "name": "Greater Spell Focus",
        "type": "General",
        "description": "Choose a school of magic for which you have already selected Spell Focus. Spells of this school are even harder to resist.",
        "prerequisites": "Spell Focus",
        "benefit": "Add +1 to the Difficulty Class for all saving throws against spells from the school of magic you select. This bonus stacks with Spell Focus."
    },
    {
        "name": "Spell Penetration",
        "type": "General",
        "description": "Your spells break through spell resistance more easily than most.",
        "prerequisites": "",
        "benefit": "You get a +2 bonus on caster level checks (1d20 + caster level) made to overcome a creature's spell resistance."
    },
    {
        "name": "Greater Spell Penetration",
        "type": "General",
        "description": "Your spells are remarkably potent, breaking through spell resistance with ease.",
        "prerequisites": "Spell Penetration",
        "benefit": "You get a +2 bonus on caster level checks made to overcome a creature's spell resistance. This bonus stacks with Spell Penetration."
    },
    {
        "name": "Combat Casting",
        "type": "General",
        "description": "You are adept at spellcasting when threatened or distracted.",
        "prerequisites": "",
        "benefit": "You get a +4 bonus on concentration checks made to cast a spell or use a spell-like ability when casting on the defensive or while grappled."
    },

    # Skill Enhancement Feats
    {
        "name": "Skill Focus",
        "type": "General",
        "description": "Choose a skill. You are particularly adept at that skill.",
        "prerequisites": "",
        "benefit": "You get a +3 bonus on all checks involving the chosen skill. If you have 10 or more ranks in that skill, this bonus increases to +6."
    },
    {
        "name": "Alertness",
        "type": "General",
        "description": "You often notice things that others might miss.",
        "prerequisites": "",
        "benefit": "You get a +2 bonus on Perception and Sense Motive skill checks. If you have 10 or more ranks in one of these skills, the bonus increases to +4 for that skill."
    },
    {
        "name": "Stealthy",
        "type": "General",
        "description": "You are good at avoiding unwanted attention and slipping out of bonds.",
        "prerequisites": "",
        "benefit": "You get a +2 bonus on Escape Artist and Stealth skill checks. If you have 10 or more ranks in one of these skills, the bonus increases to +4 for that skill."
    },
    {
        "name": "Acrobatic",
        "type": "General",
        "description": "You have excellent body awareness and coordination.",
        "prerequisites": "",
        "benefit": "You get a +2 bonus on Acrobatics and Fly skill checks. If you have 10 or more ranks in one of these skills, the bonus increases to +4 for that skill."
    },
    {
        "name": "Athletic",
        "type": "General",
        "description": "You possess inherent physical prowess.",
        "prerequisites": "",
        "benefit": "You get a +2 bonus on Climb and Swim skill checks. If you have 10 or more ranks in one of these skills, the bonus increases to +4 for that skill."
    },
    {
        "name": "Persuasive",
        "type": "General",
        "description": "You are skilled at swaying attitudes and intimidating others into your way of thinking.",
        "prerequisites": "",
        "benefit": "You get a +2 bonus on Diplomacy and Intimidate skill checks. If you have 10 or more ranks in one of these skills, the bonus increases to +4 for that skill."
    },
    {
        "name": "Deceitful",
        "type": "General",
        "description": "You are skilled at deceiving others.",
        "prerequisites": "",
        "benefit": "You get a +2 bonus on Bluff and Disguise skill checks. If you have 10 or more ranks in one of these skills, the bonus increases to +4 for that skill."
    },

    # Mounted Combat Feats
    {
        "name": "Mounted Combat",
        "type": "Combat",
        "description": "You are adept at guiding your mount through combat.",
        "prerequisites": "Ride 1 rank",
        "benefit": "Once per round when your mount is hit in combat, you may attempt a Ride check to negate the hit. The hit is negated if your Ride check result is greater than the opponent's attack roll."
    },
    {
        "name": "Ride-By Attack",
        "type": "Combat",
        "description": "While mounted and charging, you can move, strike at a foe, and then continue moving.",
        "prerequisites": "Ride 1 rank, Mounted Combat",
        "benefit": "When you are mounted and use the charge action, you may move and attack as if with a standard charge and then move again. Your total movement for the round can't exceed double your mounted speed."
    },
    {
        "name": "Spirited Charge",
        "type": "Combat",
        "description": "Your mounted charge attacks deal a tremendous amount of damage.",
        "prerequisites": "Ride 1 rank, Mounted Combat, Ride-By Attack",
        "benefit": "When mounted and using the charge action, you deal double damage with a melee weapon (or triple damage with a lance)."
    },
    {
        "name": "Trample",
        "type": "Combat",
        "description": "While mounted, you can ride down opponents and trample them under your mount.",
        "prerequisites": "Ride 1 rank, Mounted Combat",
        "benefit": "When you attempt to overrun an opponent while mounted, your target may not choose to avoid you. Your mount may make one hoof attack against any target you knock down."
    },

    # Item Creation Feats
    {
        "name": "Scribe Scroll",
        "type": "Item Creation",
        "description": "You can create magic scrolls.",
        "prerequisites": "Caster level 1st",
        "benefit": "You can create a scroll of any spell that you know. Scribing a scroll takes 2 hours if its base price is 250 gp or less, otherwise scribing a scroll takes 1 day for each 1,000 gp in its base price."
    },
    {
        "name": "Brew Potion",
        "type": "Item Creation",
        "description": "You can create magic potions.",
        "prerequisites": "Caster level 3rd",
        "benefit": "You can create a potion of any 3rd-level or lower spell that you know and that targets one or more creatures or objects. Brewing a potion takes 2 hours if its base price is 250 gp or less."
    },
    {
        "name": "Craft Wondrous Item",
        "type": "Item Creation",
        "description": "You can create wondrous items, a type of magic item.",
        "prerequisites": "Caster level 3rd",
        "benefit": "You can create a wide variety of magic wondrous items. Crafting a wondrous item takes 1 day for each 1,000 gp in its price."
    },
    {
        "name": "Craft Magic Arms and Armor",
        "type": "Item Creation",
        "description": "You can create magic armor, shields, and weapons.",
        "prerequisites": "Caster level 5th",
        "benefit": "You can create magic weapons, armor, or shields. Enhancing a weapon, suit of armor, or shield takes 1 day for each 1,000 gp in the price of its magical features."
    },
    {
        "name": "Craft Wand",
        "type": "Item Creation",
        "description": "You can create magic wands.",
        "prerequisites": "Caster level 5th",
        "benefit": "You can create a wand of any 4th-level or lower spell that you know. Crafting a wand takes 1 day for each 1,000 gp in its base price."
    },
    {
        "name": "Craft Rod",
        "type": "Item Creation",
        "description": "You can create magic rods.",
        "prerequisites": "Caster level 9th",
        "benefit": "You can create magic rods. Crafting a rod takes 1 day for each 1,000 gp in its base price."
    },
    {
        "name": "Craft Staff",
        "type": "Item Creation",
        "description": "You can create magic staves.",
        "prerequisites": "Caster level 11th",
        "benefit": "You can create any staff whose prerequisites you meet. Crafting a staff takes 1 day for each 1,000 gp in its base price."
    },
    {
        "name": "Forge Ring",
        "type": "Item Creation",
        "description": "You can create magic rings.",
        "prerequisites": "Caster level 7th",
        "benefit": "You can create magic rings. Crafting a ring takes 1 day for each 1,000 gp in its base price."
    },

    # Other Important Feats
    {
        "name": "Run",
        "type": "General",
        "description": "You are swift of foot.",
        "prerequisites": "",
        "benefit": "When running, you move five times your normal speed (if wearing medium, light, or no armor and carrying no more than a medium load) or four times your speed (if wearing heavy armor or carrying a heavy load). You retain your Dexterity bonus to AC when running."
    },
    {
        "name": "Endurance",
        "type": "General",
        "description": "Harsh conditions or long exertions do not easily tire you.",
        "prerequisites": "",
        "benefit": "You gain a +4 bonus on the following checks and saves: Swim checks made to resist nonlethal damage from exhaustion; Constitution checks made to continue running; Constitution checks made to avoid nonlethal damage from a forced march; Constitution checks made to hold your breath; Constitution checks made to avoid nonlethal damage from starvation or thirst; Fortitude saves made to avoid nonlethal damage from hot or cold environments; and Fortitude saves made to resist damage from suffocation."
    },
    {
        "name": "Diehard",
        "type": "General",
        "description": "You are especially hard to kill.",
        "prerequisites": "Endurance",
        "benefit": "When your hit point total is below 0, but you are not dead, you automatically stabilize. You do not need to make a Constitution check each round to avoid losing additional hit points. You may choose to act as if you were disabled, rather than dying."
    },
    {
        "name": "Fleet",
        "type": "General",
        "description": "You are faster than most.",
        "prerequisites": "",
        "benefit": "While you are wearing light or no armor, your base speed increases by 5 feet. You lose the benefits of this feat if you carry a medium or heavy load."
    },
    {
        "name": "Blind-Fight",
        "type": "Combat",
        "description": "You are skilled at attacking opponents that you cannot clearly perceive.",
        "prerequisites": "",
        "benefit": "In melee, every time you miss because of concealment, you can reroll your miss chance percentile roll one time to see if you actually hit. An invisible attacker gets no advantages related to hitting you in melee."
    },
    {
        "name": "Improved Blind-Fight",
        "type": "Combat",
        "description": "Your battle instincts make you more deadly against hidden foes.",
        "prerequisites": "Perception 10 ranks, Blind-Fight",
        "benefit": "Your melee attacks ignore the miss chance for less than total concealment. You may still reroll your miss chance percentile roll for total concealment."
    },
    {
        "name": "Greater Blind-Fight",
        "type": "Combat",
        "description": "Your senses sharpen to such a degree that your opponents cannot hide from you.",
        "prerequisites": "Perception 15 ranks, Improved Blind-Fight, Blind-Fight",
        "benefit": "Your melee attacks ignore the miss chance for less than total concealment, and you treat opponents with total concealment as if they had normal concealment (20% miss chance)."
    },
    {
        "name": "Stand Still",
        "type": "Combat",
        "description": "You can stop foes that try to move past you.",
        "prerequisites": "Combat Reflexes",
        "benefit": "When a foe provokes an attack of opportunity from you, you can give up that attack and instead attempt to stop the foe in his tracks. Make a combat maneuver check. If successful, the foe cannot move until your next turn."
    },
    {
        "name": "Combat Reflexes",
        "type": "Combat",
        "description": "You can make additional attacks of opportunity.",
        "prerequisites": "",
        "benefit": "You may make a number of additional attacks of opportunity per round equal to your Dexterity bonus. With this feat, you may also make attacks of opportunity while flat-footed."
    },
    {
        "name": "Step Up",
        "type": "Combat",
        "description": "You can close the distance when a foe tries to move away.",
        "prerequisites": "Base attack bonus +1",
        "benefit": "Whenever an adjacent foe attempts to take a 5-foot step away from you, you may also make a 5-foot step as an immediate action so long as you end up adjacent to the foe that triggered this ability."
    },
    {
        "name": "Following Step",
        "type": "Combat",
        "description": "You can follow foes that try to move away.",
        "prerequisites": "Dex 13, Step Up",
        "benefit": "When using Step Up, you may move up to 10 feet. You still cannot move farther than your speed."
    },
    {
        "name": "Step Up and Strike",
        "type": "Combat",
        "description": "When a foe tries to move away, you can follow and make an attack.",
        "prerequisites": "Dex 13, Following Step, Step Up, base attack bonus +6",
        "benefit": "When using Step Up or Following Step to follow an adjacent foe, you may also make a single melee attack against that foe at your highest base attack bonus."
    },
    {
        "name": "Lunge",
        "type": "Combat",
        "description": "You can strike foes that would normally be out of reach.",
        "prerequisites": "Base attack bonus +6",
        "benefit": "You can increase the reach of your melee attacks by 5 feet until the end of your turn by taking a -2 penalty to your AC until your next turn."
    },
    {
        "name": "Improved Natural Attack",
        "type": "Monster",
        "description": "Attacks made by one of this creature's natural attacks leave vicious wounds.",
        "prerequisites": "Natural weapon, base attack bonus +4",
        "benefit": "Choose one of the creature's natural attack forms. The damage for this natural attack increases by one step."
    },
    {
        "name": "Extra Channel",
        "type": "General",
        "description": "You can channel divine energy more often.",
        "prerequisites": "Channel energy class feature",
        "benefit": "You can channel energy two additional times per day."
    },
    {
        "name": "Selective Channeling",
        "type": "General",
        "description": "You can choose whom to affect when you channel energy.",
        "prerequisites": "Cha 13, channel energy class feature",
        "benefit": "When you channel energy, you can choose a number of targets in the area up to your Charisma modifier. These targets are not affected by your channeled energy."
    },
    {
        "name": "Improved Channel",
        "type": "General",
        "description": "Your channeled energy is harder to resist.",
        "prerequisites": "Channel energy class feature",
        "benefit": "Add 2 to the DC of saving throws made to resist the effects of your channel energy ability."
    },
    {
        "name": "Natural Spell",
        "type": "General",
        "description": "You can cast spells even while in a form that cannot normally cast spells.",
        "prerequisites": "Wis 13, wild shape class feature",
        "benefit": "You can complete the verbal and somatic components of spells while in a wild shape. You substitute various noises and gestures for the normal verbal and somatic components of a spell."
    },
    {
        "name": "Augment Summoning",
        "type": "General",
        "description": "Your summoned creatures are more powerful and robust.",
        "prerequisites": "Spell Focus (conjuration)",
        "benefit": "Each creature you conjure with any summon spell gains a +4 enhancement bonus to Strength and Constitution for the duration of the spell."
    },
    {
        "name": "Extra Rage",
        "type": "General",
        "description": "You can use your rage ability more than normal.",
        "prerequisites": "Rage class feature",
        "benefit": "You can rage for 6 additional rounds per day."
    },
    {
        "name": "Extra Ki",
        "type": "General",
        "description": "You can use your ki pool more times per day than most.",
        "prerequisites": "Ki pool class feature",
        "benefit": "Your ki pool increases by 2."
    },
]


def main():
    """Add core feats to feats.json."""
    feats_path = Path(__file__).parent.parent / "data" / "srd" / "feats.json"

    # Load existing feats
    with open(feats_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both {"feats": [...]} and [...] formats
    if isinstance(data, dict) and "feats" in data:
        existing_feats = data["feats"]
        is_wrapped = True
    else:
        existing_feats = data
        is_wrapped = False

    # Create a set of existing feat names (case-insensitive)
    existing_names = {f["name"].lower() for f in existing_feats}

    # Add missing feats (also add "normal" and "special" fields for consistency)
    added_count = 0
    for feat in CORE_FEATS:
        if feat["name"].lower() not in existing_names:
            # Ensure consistent schema with existing feats
            new_feat = {
                "name": feat["name"],
                "prerequisites": feat.get("prerequisites", ""),
                "benefit": feat["benefit"],
                "normal": "",
                "special": ""
            }
            existing_feats.append(new_feat)
            existing_names.add(feat["name"].lower())
            added_count += 1
            print(f"Added: {feat['name']}")
        else:
            print(f"Skipped (exists): {feat['name']}")

    # Sort by name
    existing_feats.sort(key=lambda x: x["name"])

    # Save updated feats
    output_data = {"feats": existing_feats} if is_wrapped else existing_feats
    with open(feats_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Added {added_count} new feats.")
    print(f"Total feats now: {len(existing_feats)}")


if __name__ == "__main__":
    main()
