"""
Configuration and action definitions for Chinchilla Agent.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

# ============================================================================
# ACTION CATEGORIES AND DEFINITIONS
# ============================================================================

class ActionCategory(Enum):
    """74 action categories from specification."""
    
    # Базовые потребности (10)
    EAT_PELLETS = "eat_pellets"
    EAT_HAY = "eat_hay"
    EAT_TREAT = "eat_treat"
    DRINK_WATER = "drink_water"
    GNAW_MINERAL = "gnaw_mineral"
    SLEEP_HOUSE = "sleep_house"
    DOZE_SHELF = "doze_shelf"
    REST_LOAF = "rest_loaf"
    TOILET_MAIN = "toilet_main"
    TOILET_MARK = "toilet_mark"
    
    # Локомоция (9)
    RUN_WHEEL = "run_wheel"
    JUMP_SHELF_UP = "jump_shelf_up"
    JUMP_SHELF_DOWN = "jump_shelf_down"
    JUMP_HOP_PLAY = "jump_hop_play"
    PATROL_FLOOR = "patrol_floor"
    SNIFF_CORNERS = "sniff_corners"
    SNIFF_AIR = "sniff_air"
    STAND_UPRIGHT = "stand_upright"
    CLIMB_BARS = "climb_bars"
    HANG_BARS = "hang_bars"
    
    # Исследование / игра (14)
    EXPLORE_CORNER = "explore_corner"
    OBSERVE_ROOM = "observe_room"
    PLAY_TOY = "play_toy"
    TOSS_TOY = "toss_toy"
    CHASE_TOY = "chase_toy"
    GNAW_TOY = "gnaw_toy"
    GNAW_WOOD = "gnaw_wood"
    REARRANGE_BEDDING = "rearrange_bedding"
    DIG_BEDDING = "dig_bedding"
    CACHE_FOOD = "cache_food"
    CARRY_OBJECT = "carry_object"
    INSPECT_NEW_OBJ = "inspect_new_obj"
    PROBLEM_SOLVE = "problem_solve"
    DUST_BATH = "dust_bath"
    
    # Груминг (10)
    GROOM_FACE = "groom_face"
    GROOM_BODY = "groom_body"
    GROOM_TAIL = "groom_tail"
    GROOM_PAWS = "groom_paws"
    SCRATCH_HEAD = "scratch_head"
    STRETCH_BODY = "stretch_body"
    YAWN = "yawn"
    BODY_SHAKE = "body_shake"
    OVERGROOM_FUR = "overgroom_fur"
    OVERGROOM_OTHER = "overgroom_other"
    
    # Социальное (12)
    APPROACH_DOOR = "approach_door"
    VOCALIZE_CHIRP = "vocalize_chirp"
    VOCALIZE_SQUEAK = "vocalize_squeak"
    VOCALIZE_BARK = "vocalize_bark"
    VOCALIZE_ALARM = "vocalize_alarm"
    VOCALIZE_TEETH = "vocalize_teeth"
    SNIFF_HAND = "sniff_hand"
    TAKE_TREAT = "take_treat"
    ALLOW_PET = "allow_pet"
    SOLICIT_PET = "solicit_pet"
    AVOID_HAND = "avoid_hand"
    WATCH_OWNER = "watch_owner"
    FOLLOW_FINGER = "follow_finger"
    
    # Стресс / защита (9)
    FREEZE = "freeze"
    HIDE_HOUSE = "hide_house"
    FLEE_CORNER = "flee_corner"
    ALARM_CALL = "alarm_call"
    THUMP_HIND = "thump_hind"
    FUR_SLIP = "fur_slip"
    BAR_CHEWING = "bar_chewing"
    STEREOTYPY_PACING = "stereotypy_pacing"
    WALL_JUMP = "wall_jump"
    
    # Постуральные / микро (7)
    EAR_FORWARD = "ear_forward"
    EAR_FLAT = "ear_flat"
    WHISKER_TWITCH = "whisker_twitch"
    TAIL_RAISE = "tail_raise"
    PRESS_FLAT = "press_flat"
    EYE_HALF_CLOSE = "eye_half_close"
    NOSE_TWITCH = "nose_twitch"


class ActionLayer(Enum):
    """Rendering layers for actions."""
    ACTION = "action"      # Main action layer
    POSTURAL = "postural"  # Overlays on top of action
    MICRO = "micro"        # Short reflexes, don't block action


# ============================================================================
# POSITION DEFINITIONS (18 zones in the enclosure)
# ============================================================================

class Position(Enum):
    """Named positions in the enclosure."""
    FLOOR = "floor"
    HOUSE = "house"
    BOWL_PELLETS = "bowl_pellets"
    BOWL_HAY = "bowl_hay"
    WATERER = "waterer"
    MINERAL = "mineral"
    LITTER = "litter"
    WHEEL = "wheel"
    SHELF_LOWER = "shelf_lower"
    SHELF_MID = "shelf_mid"
    SHELF_UPPER = "shelf_upper"
    BARS = "bars"
    BARS_TOP = "bars_top"
    CORNER = "corner"
    DOOR = "door"
    TOY = "toy"
    DUSTBATH = "dustbath"
    OBJECT = "object"
    CURRENT = "current"  # No sprite movement


# ============================================================================
# ACTION METADATA
# ============================================================================

@dataclass
class ActionMetadata:
    """Metadata for action rendering and behavior."""
    action_id: str
    display_name: str
    layer: ActionLayer
    default_position: Position
    valid_positions: List[Position]
    is_loop: bool = True
    is_loopable: bool = False  # Can be used in behavioral chains
    duration_min: int = 1
    duration_max: int = 30
    default_sfx: Optional[str] = None
    subtitle_ru: str = ""
    is_pathological: bool = False  # True for bar_chewing, stereotypy, overgroom
    wellbeing_flag: bool = False  # Indicates stress/pathos


# ============================================================================
# ACTION LIBRARY - Complete action definitions
# ============================================================================

ACTION_LIBRARY: Dict[str, ActionMetadata] = {
    # Базовые потребности
    "eat_pellets": ActionMetadata(
        action_id="eat_pellets",
        display_name="Eating Pellets",
        layer=ActionLayer.ACTION,
        default_position=Position.BOWL_PELLETS,
        valid_positions=[Position.BOWL_PELLETS],
        duration_min=10, duration_max=30,
        default_sfx="chewing",
        subtitle_ru="ест гранулы",
        is_loopable=True,
    ),
    "eat_hay": ActionMetadata(
        action_id="eat_hay",
        display_name="Eating Hay",
        layer=ActionLayer.ACTION,
        default_position=Position.BOWL_HAY,
        valid_positions=[Position.BOWL_HAY],
        duration_min=10, duration_max=30,
        default_sfx="chewing",
        subtitle_ru="ест сено",
        is_loopable=True,
    ),
    "eat_treat": ActionMetadata(
        action_id="eat_treat",
        display_name="Eating Treat",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR, Position.BOWL_PELLETS, Position.DOOR],
        duration_min=5, duration_max=15,
        default_sfx="chewing",
        subtitle_ru="ест лакомство",
    ),
    "drink_water": ActionMetadata(
        action_id="drink_water",
        display_name="Drinking Water",
        layer=ActionLayer.ACTION,
        default_position=Position.WATERER,
        valid_positions=[Position.WATERER],
        duration_min=5, duration_max=15,
        default_sfx="drinking",
        subtitle_ru="пьет воду",
    ),
    "gnaw_mineral": ActionMetadata(
        action_id="gnaw_mineral",
        display_name="Gnawing Mineral",
        layer=ActionLayer.ACTION,
        default_position=Position.MINERAL,
        valid_positions=[Position.MINERAL],
        duration_min=10, duration_max=40,
        default_sfx="gnawing",
        subtitle_ru="грызет минерал",
    ),
    "sleep_house": ActionMetadata(
        action_id="sleep_house",
        display_name="Sleeping",
        layer=ActionLayer.ACTION,
        default_position=Position.HOUSE,
        valid_positions=[Position.HOUSE],
        duration_min=240, duration_max=960,
        default_sfx=None,
        subtitle_ru="спит в домике",
        is_loopable=True,
    ),
    "doze_shelf": ActionMetadata(
        action_id="doze_shelf",
        display_name="Dozing",
        layer=ActionLayer.ACTION,
        default_position=Position.SHELF_LOWER,
        valid_positions=[Position.SHELF_LOWER, Position.SHELF_MID, Position.SHELF_UPPER],
        duration_min=30, duration_max=120,
        default_sfx=None,
        subtitle_ru="дремлет на полке",
    ),
    "rest_loaf": ActionMetadata(
        action_id="rest_loaf",
        display_name="Resting (Loaf)",
        layer=ActionLayer.ACTION,
        default_position=Position.FLOOR,
        valid_positions=[Position.FLOOR, Position.SHELF_LOWER, Position.SHELF_MID],
        duration_min=15, duration_max=60,
        default_sfx=None,
        subtitle_ru="отдыхает",
    ),
    "toilet_main": ActionMetadata(
        action_id="toilet_main",
        display_name="Using Toilet",
        layer=ActionLayer.ACTION,
        default_position=Position.LITTER,
        valid_positions=[Position.LITTER],
        duration_min=2, duration_max=6,
        default_sfx="rustling",
        subtitle_ru="в туалете",
    ),
    "toilet_mark": ActionMetadata(
        action_id="toilet_mark",
        display_name="Territorial Marking",
        layer=ActionLayer.ACTION,
        default_position=Position.LITTER,
        valid_positions=[Position.LITTER, Position.FLOOR, Position.CORNER],
        duration_min=3, duration_max=8,
        default_sfx="rustling",
        subtitle_ru="метит территорию",
    ),
    
    # Локомоция
    "run_wheel": ActionMetadata(
        action_id="run_wheel",
        display_name="Running Wheel",
        layer=ActionLayer.ACTION,
        default_position=Position.WHEEL,
        valid_positions=[Position.WHEEL],
        duration_min=10, duration_max=80,
        default_sfx="wheel_spin",
        subtitle_ru="на колесе",
        is_loopable=True,
    ),
    "jump_shelf_up": ActionMetadata(
        action_id="jump_shelf_up",
        display_name="Jumping Up to Shelf",
        layer=ActionLayer.ACTION,
        default_position=Position.SHELF_UPPER,
        valid_positions=[Position.SHELF_MID, Position.SHELF_UPPER],
        duration_min=3, duration_max=8,
        default_sfx="jump_land",
        subtitle_ru="прыгает на полку",
    ),
    "jump_shelf_down": ActionMetadata(
        action_id="jump_shelf_down",
        display_name="Jumping Down from Shelf",
        layer=ActionLayer.ACTION,
        default_position=Position.FLOOR,
        valid_positions=[Position.FLOOR],
        duration_min=3, duration_max=8,
        default_sfx="jump_land",
        subtitle_ru="прыгает вниз",
    ),
    "jump_hop_play": ActionMetadata(
        action_id="jump_hop_play",
        display_name="Playing Hops/Jumps",
        layer=ActionLayer.ACTION,
        default_position=Position.FLOOR,
        valid_positions=[Position.FLOOR, Position.SHELF_LOWER],
        duration_min=5, duration_max=20,
        default_sfx="jump_land",
        subtitle_ru="прыгает и играет",
    ),
    "patrol_floor": ActionMetadata(
        action_id="patrol_floor",
        display_name="Patrolling Floor",
        layer=ActionLayer.ACTION,
        default_position=Position.FLOOR,
        valid_positions=[Position.FLOOR, Position.CORNER],
        duration_min=5, duration_max=25,
        default_sfx="steps_soft",
        subtitle_ru="патрулирует территорию",
        is_loopable=True,
    ),
    "sniff_corners": ActionMetadata(
        action_id="sniff_corners",
        display_name="Sniffing Corners",
        layer=ActionLayer.ACTION,
        default_position=Position.CORNER,
        valid_positions=[Position.CORNER, Position.FLOOR],
        duration_min=5, duration_max=15,
        default_sfx="sniff",
        subtitle_ru="обнюхивает углы",
    ),
    "sniff_air": ActionMetadata(
        action_id="sniff_air",
        display_name="Sniffing Air",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=3, duration_max=10,
        default_sfx=None,
        subtitle_ru="обнюхивает воздух",
    ),
    "stand_upright": ActionMetadata(
        action_id="stand_upright",
        display_name="Standing Upright",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=3, duration_max=12,
        default_sfx=None,
        subtitle_ru="стоит на задних лапах",
    ),
    "climb_bars": ActionMetadata(
        action_id="climb_bars",
        display_name="Climbing Bars",
        layer=ActionLayer.ACTION,
        default_position=Position.BARS,
        valid_positions=[Position.BARS, Position.BARS_TOP],
        duration_min=5, duration_max=20,
        default_sfx="scratch_bars",
        subtitle_ru="лазит по прутьям",
        is_loopable=True,
    ),
    "hang_bars": ActionMetadata(
        action_id="hang_bars",
        display_name="Hanging on Bars",
        layer=ActionLayer.ACTION,
        default_position=Position.BARS_TOP,
        valid_positions=[Position.BARS_TOP],
        duration_min=3, duration_max=15,
        default_sfx=None,
        subtitle_ru="висит на прутьях",
    ),
    
    # Исследование / игра
    "explore_corner": ActionMetadata(
        action_id="explore_corner",
        display_name="Exploring Corner",
        layer=ActionLayer.ACTION,
        default_position=Position.CORNER,
        valid_positions=[Position.CORNER, Position.FLOOR],
        duration_min=5, duration_max=20,
        default_sfx="rustling",
        subtitle_ru="исследует угол",
    ),
    "observe_room": ActionMetadata(
        action_id="observe_room",
        display_name="Observing Room",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.SHELF_UPPER, Position.DOOR],
        duration_min=5, duration_max=30,
        default_sfx=None,
        subtitle_ru="наблюдает",
    ),
    "play_toy": ActionMetadata(
        action_id="play_toy",
        display_name="Playing with Toy",
        layer=ActionLayer.ACTION,
        default_position=Position.TOY,
        valid_positions=[Position.TOY, Position.FLOOR],
        duration_min=5, duration_max=30,
        default_sfx="toy_rattle",
        subtitle_ru="играет с игрушкой",
    ),
    "toss_toy": ActionMetadata(
        action_id="toss_toy",
        display_name="Tossing Toy",
        layer=ActionLayer.ACTION,
        default_position=Position.TOY,
        valid_positions=[Position.TOY],
        duration_min=3, duration_max=10,
        default_sfx="toy_rattle",
        subtitle_ru="бросает игрушку",
    ),
    "chase_toy": ActionMetadata(
        action_id="chase_toy",
        display_name="Chasing Toy",
        layer=ActionLayer.ACTION,
        default_position=Position.FLOOR,
        valid_positions=[Position.FLOOR, Position.TOY],
        duration_min=5, duration_max=25,
        default_sfx="steps_fast",
        subtitle_ru="гонится за игрушкой",
    ),
    "gnaw_toy": ActionMetadata(
        action_id="gnaw_toy",
        display_name="Gnawing Toy",
        layer=ActionLayer.ACTION,
        default_position=Position.TOY,
        valid_positions=[Position.TOY, Position.FLOOR],
        duration_min=10, duration_max=40,
        default_sfx="gnawing",
        subtitle_ru="грызет игрушку",
    ),
    "gnaw_wood": ActionMetadata(
        action_id="gnaw_wood",
        display_name="Gnawing Wood",
        layer=ActionLayer.ACTION,
        default_position=Position.OBJECT,
        valid_positions=[Position.OBJECT, Position.FLOOR, Position.SHELF_LOWER, Position.SHELF_MID, Position.SHELF_UPPER],
        duration_min=10, duration_max=40,
        default_sfx="gnaw_wood",
        subtitle_ru="грызет дерево",
    ),
    "rearrange_bedding": ActionMetadata(
        action_id="rearrange_bedding",
        display_name="Rearranging Bedding",
        layer=ActionLayer.ACTION,
        default_position=Position.HOUSE,
        valid_positions=[Position.HOUSE, Position.FLOOR, Position.LITTER],
        duration_min=10, duration_max=40,
        default_sfx="rustling",
        subtitle_ru="переделает подстилку",
        is_loopable=True,
    ),
    "dig_bedding": ActionMetadata(
        action_id="dig_bedding",
        display_name="Digging Bedding",
        layer=ActionLayer.ACTION,
        default_position=Position.HOUSE,
        valid_positions=[Position.HOUSE, Position.FLOOR, Position.LITTER],
        duration_min=10, duration_max=40,
        default_sfx="rustling",
        subtitle_ru="копает подстилку",
    ),
    "cache_food": ActionMetadata(
        action_id="cache_food",
        display_name="Caching Food",
        layer=ActionLayer.ACTION,
        default_position=Position.HOUSE,
        valid_positions=[Position.HOUSE, Position.FLOOR, Position.CORNER],
        duration_min=5, duration_max=20,
        default_sfx="rustling",
        subtitle_ru="прячет корм",
    ),
    "carry_object": ActionMetadata(
        action_id="carry_object",
        display_name="Carrying Object",
        layer=ActionLayer.ACTION,
        default_position=Position.OBJECT,
        valid_positions=[Position.OBJECT, Position.FLOOR, Position.HOUSE],
        duration_min=5, duration_max=30,
        default_sfx=None,
        subtitle_ru="носит предмет",
    ),
    "inspect_new_obj": ActionMetadata(
        action_id="inspect_new_obj",
        display_name="Inspecting New Object",
        layer=ActionLayer.ACTION,
        default_position=Position.OBJECT,
        valid_positions=[Position.OBJECT, Position.DOOR],
        duration_min=5, duration_max=20,
        default_sfx="sniff",
        subtitle_ru="осматривает новый предмет",
    ),
    "problem_solve": ActionMetadata(
        action_id="problem_solve",
        display_name="Problem Solving",
        layer=ActionLayer.ACTION,
        default_position=Position.OBJECT,
            valid_positions=[Position.OBJECT, Position.FLOOR, Position.BARS],
        duration_min=5, duration_max=30,
        default_sfx=None,
        subtitle_ru="решает задачу",
    ),
    "dust_bath": ActionMetadata(
        action_id="dust_bath",
        display_name="Dust Bathing",
        layer=ActionLayer.ACTION,
        default_position=Position.DUSTBATH,
        valid_positions=[Position.DUSTBATH],
        duration_min=10, duration_max=40,
        default_sfx="rustling",
        subtitle_ru="купается в пыли",
    ),
    
    # Груминг
    "groom_face": ActionMetadata(
        action_id="groom_face",
        display_name="Grooming Face",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=3, duration_max=10,
        default_sfx=None,
        subtitle_ru="умывается",
        is_loop=False,
    ),
    "groom_body": ActionMetadata(
        action_id="groom_body",
        display_name="Grooming Body",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=10, duration_max=30,
        default_sfx=None,
        subtitle_ru="чистит шерсть",
        is_loopable=True,
    ),
    "groom_tail": ActionMetadata(
        action_id="groom_tail",
        display_name="Grooming Tail",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=5, duration_max=15,
        default_sfx=None,
        subtitle_ru="чистит хвост",
    ),
    "groom_paws": ActionMetadata(
        action_id="groom_paws",
        display_name="Grooming Paws",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=5, duration_max=15,
        default_sfx=None,
        subtitle_ru="чистит лапы",
    ),
    "scratch_head": ActionMetadata(
        action_id="scratch_head",
        display_name="Scratching Head",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=2, duration_max=8,
        default_sfx=None,
        subtitle_ru="чешет голову",
    ),
    "stretch_body": ActionMetadata(
        action_id="stretch_body",
        display_name="Stretching",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=2, duration_max=5,
        default_sfx=None,
        subtitle_ru="потягивается",
        is_loop=False,
    ),
    "yawn": ActionMetadata(
        action_id="yawn",
        display_name="Yawning",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=2, duration_max=2,
        default_sfx=None,
        subtitle_ru="зевает",
        is_loop=False,
    ),
    "body_shake": ActionMetadata(
        action_id="body_shake",
        display_name="Shaking Body",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=2, duration_max=5,
        default_sfx="fur_rustle",
        subtitle_ru="встряхивается",
        is_loop=False,
    ),
    "overgroom_fur": ActionMetadata(
        action_id="overgroom_fur",
        display_name="Overgrooming Fur",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=15, duration_max=60,
        default_sfx=None,
        subtitle_ru="чрезмерно чистит шерсть",
        is_pathological=True,
        wellbeing_flag=True,
    ),
    "overgroom_other": ActionMetadata(
        action_id="overgroom_other",
        display_name="Overgrooming Other",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=15, duration_max=60,
        default_sfx=None,
        subtitle_ru="грызет собственную шерсть",
        is_pathological=True,
        wellbeing_flag=True,
    ),
    
    # Социальное
    "approach_door": ActionMetadata(
        action_id="approach_door",
        display_name="Approaching Door",
        layer=ActionLayer.ACTION,
        default_position=Position.DOOR,
        valid_positions=[Position.DOOR],
        duration_min=3, duration_max=10,
        default_sfx="steps_soft",
        subtitle_ru="подходит к двери",
    ),
    "vocalize_chirp": ActionMetadata(
        action_id="vocalize_chirp",
        display_name="Chirping",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.DOOR],
        duration_min=1, duration_max=3,
        default_sfx="chirp",
        subtitle_ru="издает звук",
        is_loop=False,
    ),
    "vocalize_squeak": ActionMetadata(
        action_id="vocalize_squeak",
        display_name="Squeaking",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.DOOR],
        duration_min=1, duration_max=3,
        default_sfx="squeak_soft",
        subtitle_ru="пищит",
        is_loop=False,
    ),
    "vocalize_bark": ActionMetadata(
        action_id="vocalize_bark",
        display_name="Barking",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT],
        duration_min=1, duration_max=4,
        default_sfx="bark",
        subtitle_ru="лает",
        is_loop=False,
    ),
    "vocalize_alarm": ActionMetadata(
        action_id="vocalize_alarm",
        display_name="Alarm Call",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT],
        duration_min=1, duration_max=3,
        default_sfx="alarm_call",
        subtitle_ru="кричит от страха",
        is_loop=False,
    ),
    "vocalize_teeth": ActionMetadata(
        action_id="vocalize_teeth",
        display_name="Teeth Clicking",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT],
        duration_min=1, duration_max=3,
        default_sfx="teeth_click",
        subtitle_ru="стучит зубами",
        is_loop=False,
    ),
    "sniff_hand": ActionMetadata(
        action_id="sniff_hand",
        display_name="Sniffing Hand",
        layer=ActionLayer.ACTION,
        default_position=Position.DOOR,
        valid_positions=[Position.DOOR, Position.CURRENT],
        duration_min=3, duration_max=10,
        default_sfx="sniff",
        subtitle_ru="обнюхивает руку",
    ),
    "take_treat": ActionMetadata(
        action_id="take_treat",
        display_name="Taking Treat",
        layer=ActionLayer.ACTION,
        default_position=Position.DOOR,
        valid_positions=[Position.DOOR, Position.CURRENT],
        duration_min=4, duration_max=10,
        default_sfx="chewing_soft",
        subtitle_ru="берет лакомство",
    ),
    "allow_pet": ActionMetadata(
        action_id="allow_pet",
        display_name="Allowing Petting",
        layer=ActionLayer.ACTION,
        default_position=Position.DOOR,
        valid_positions=[Position.DOOR, Position.CURRENT],
        duration_min=5, duration_max=20,
        default_sfx=None,
        subtitle_ru="позволяет себя гладить",
    ),
    "solicit_pet": ActionMetadata(
        action_id="solicit_pet",
        display_name="Soliciting Petting",
        layer=ActionLayer.ACTION,
        default_position=Position.DOOR,
        valid_positions=[Position.DOOR, Position.CURRENT],
        duration_min=5, duration_max=20,
        default_sfx=None,
        subtitle_ru="просит поглаживаний",
    ),
    "avoid_hand": ActionMetadata(
        action_id="avoid_hand",
        display_name="Avoiding Hand",
        layer=ActionLayer.ACTION,
        default_position=Position.FLOOR,
        valid_positions=[Position.FLOOR, Position.CORNER],
        duration_min=3, duration_max=10,
        default_sfx=None,
        subtitle_ru="избегает руки",
    ),
    "watch_owner": ActionMetadata(
        action_id="watch_owner",
        display_name="Watching Owner",
        layer=ActionLayer.ACTION,
        default_position=Position.DOOR,
        valid_positions=[Position.DOOR, Position.SHELF_UPPER],
        duration_min=5, duration_max=30,
        default_sfx=None,
        subtitle_ru="наблюдает за хозяином",
    ),
    "follow_finger": ActionMetadata(
        action_id="follow_finger",
        display_name="Following Finger",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR, Position.DOOR],
        duration_min=3, duration_max=15,
        default_sfx=None,
        subtitle_ru="следит за пальцем",
    ),
    
    # Стресс / защита
    "freeze": ActionMetadata(
        action_id="freeze",
        display_name="Freezing",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=2, duration_max=8,
        default_sfx=None,
        subtitle_ru="замирает",
    ),
    "hide_house": ActionMetadata(
        action_id="hide_house",
        display_name="Hiding in House",
        layer=ActionLayer.ACTION,
        default_position=Position.HOUSE,
        valid_positions=[Position.HOUSE],
        duration_min=30, duration_max=180,
        default_sfx=None,
        subtitle_ru="прячется в домике",
    ),
    "flee_corner": ActionMetadata(
        action_id="flee_corner",
        display_name="Fleeing to Corner",
        layer=ActionLayer.ACTION,
        default_position=Position.CORNER,
        valid_positions=[Position.CORNER],
        duration_min=3, duration_max=10,
        default_sfx="steps_fast",
        subtitle_ru="убегает в угол",
    ),
    "alarm_call": ActionMetadata(
        action_id="alarm_call",
        display_name="Alarm Call",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT],
        duration_min=1, duration_max=3,
        default_sfx="alarm_call",
        subtitle_ru="издает тревожный звук",
    ),
    "thump_hind": ActionMetadata(
        action_id="thump_hind",
        display_name="Thumping Hind Legs",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=1, duration_max=4,
        default_sfx="thump_loud",
        subtitle_ru="барабанит лапами",
        is_loop=False,
    ),
    "fur_slip": ActionMetadata(
        action_id="fur_slip",
        display_name="Fur Slip",
        layer=ActionLayer.ACTION,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.FLOOR],
        duration_min=2, duration_max=5,
        default_sfx="fur_rustle",
        subtitle_ru="теряет шерсть от страха",
    ),
    "bar_chewing": ActionMetadata(
        action_id="bar_chewing",
        display_name="Bar Chewing",
        layer=ActionLayer.ACTION,
        default_position=Position.BARS,
        valid_positions=[Position.BARS, Position.BARS_TOP],
        duration_min=10, duration_max=60,
        default_sfx="gnaw_metal",
        subtitle_ru="грызет прутья клетки",
        is_pathological=True,
        wellbeing_flag=True,
        is_loopable=True,
    ),
    "stereotypy_pacing": ActionMetadata(
        action_id="stereotypy_pacing",
        display_name="Stereotypic Pacing",
        layer=ActionLayer.ACTION,
        default_position=Position.FLOOR,
        valid_positions=[Position.FLOOR, Position.CORNER],
        duration_min=15, duration_max=120,
        default_sfx="steps_fast",
        subtitle_ru="однообразно ходит по клетке",
        is_pathological=True,
        wellbeing_flag=True,
        is_loopable=True,
    ),
    "wall_jump": ActionMetadata(
        action_id="wall_jump",
        display_name="Wall Jumping",
        layer=ActionLayer.ACTION,
        default_position=Position.BARS,
        valid_positions=[Position.BARS, Position.BARS_TOP],
        duration_min=2, duration_max=5,
        default_sfx="jump_land",
        subtitle_ru="прыгает в стену",
    ),
    
    # Постуральные / микро
    "ear_forward": ActionMetadata(
        action_id="ear_forward",
        display_name="Ears Forward",
        layer=ActionLayer.POSTURAL,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT],
        duration_min=1, duration_max=10,
        default_sfx=None,
        subtitle_ru="уши вперед",
        is_loopable=True,
    ),
    "ear_flat": ActionMetadata(
        action_id="ear_flat",
        display_name="Ears Flat",
        layer=ActionLayer.POSTURAL,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT],
        duration_min=1, duration_max=20,
        default_sfx=None,
        subtitle_ru="уши прижаты",
        is_loopable=True,
    ),
    "whisker_twitch": ActionMetadata(
        action_id="whisker_twitch",
        display_name="Whisker Twitch",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT],
        duration_min=1, duration_max=2,
        default_sfx=None,
        subtitle_ru="вибрирует усами",
        is_loop=False,
    ),
    "tail_raise": ActionMetadata(
        action_id="tail_raise",
        display_name="Tail Raised",
        layer=ActionLayer.POSTURAL,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT],
        duration_min=1, duration_max=15,
        default_sfx=None,
        subtitle_ru="хвост поднят",
        is_loopable=True,
    ),
    "press_flat": ActionMetadata(
        action_id="press_flat",
        display_name="Pressing Flat",
        layer=ActionLayer.POSTURAL,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.HOUSE],
        duration_min=2, duration_max=15,
        default_sfx=None,
        subtitle_ru="прижимается к земле",
        is_loopable=True,
    ),
    "eye_half_close": ActionMetadata(
        action_id="eye_half_close",
        display_name="Eyes Half-Closed",
        layer=ActionLayer.POSTURAL,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT, Position.DOOR],
        duration_min=2, duration_max=30,
        default_sfx=None,
        subtitle_ru="полуприкрытые глаза",
        is_loopable=True,
    ),
    "nose_twitch": ActionMetadata(
        action_id="nose_twitch",
        display_name="Nose Twitch",
        layer=ActionLayer.MICRO,
        default_position=Position.CURRENT,
        valid_positions=[Position.CURRENT],
        duration_min=1, duration_max=2,
        default_sfx=None,
        subtitle_ru="вибрирует нос",
        is_loop=False,
    ),
}


# ============================================================================
# BEHAVIORAL CHAINS (14 templates from specification)
# ============================================================================

BEHAVIORAL_CHAINS: Dict[str, List[str]] = {
    "morning_awakening": [
        ("sleep_house",   1.0),
        ("stretch_body",  1.0),
        ("yawn",          0.8),
        ("groom_face",    0.9),
        ("drink_water",   0.6),   # не каждое утро
        ("eat_pellets",   1.0),
        ("patrol_floor",  0.7),
        ("run_wheel",     0.5),
    ],
    "eating_and_grooming": [
        ("eat_pellets",   1.0),
        ("eat_hay",       0.8),
        ("eat_treat",     0.3),   # редкое угощение
        ("drink_water",   0.7),
        ("groom_face",    1.0),
        ("groom_body",    0.8),
        ("rest_loaf",     0.9),
    ],
    "activity_burst": [
        ("stand_upright", 1.0),
        ("sniff_air",     1.0),
        ("run_wheel",     1.0),
        ("jump_hop_play", 1.0),
        ("play_toy",      1.0),
        ("toss_toy",      1.0),
        ("chase_toy",     1.0),
        ("jump_shelf_up", 1.0),
        ("observe_room",  1.0),
        ("drink_water",   0.5),
    ],
    "exploration": [
        ("nose_twitch",       1.0),
        ("sniff_air",         1.0),
        ("stand_upright",     1.0),
        ("explore_corner",    1.0),
        ("inspect_new_obj",   1.0),
        ("problem_solve",     0.7),
        ("sniff_hand",        1.0),
        ("gnaw_toy",          0.8),
        ("gnaw_wood",         0.6),
        ("carry_object",      1.0),
        ("rearrange_bedding", 1.0),
    ],
    "full_grooming": [
        ("groom_face",    1.0),
        ("groom_body",    1.0),
        ("groom_paws",    1.0),
        ("groom_tail",    1.0),
        ("scratch_head",  1.0),
        ("body_shake",    1.0),
        ("rest_loaf",     0.8),
    ],
    "dust_bathing": [
        ("inspect_new_obj", 1.0),
        ("dust_bath",       1.0),
        ("body_shake",      1.0),
        ("groom_body",      1.0),
        ("groom_tail",      1.0),
        ("rest_loaf",       0.8),
    ],
    "social_contact": [
        ("watch_owner",   1.0),
        ("follow_finger", 1.0),
        ("approach_door", 1.0),
        ("vocalize_chirp",1.0),
        ("sniff_hand",    1.0),
        ("take_treat",    1.0),
        ("allow_pet",     1.0),
        ("avoid_hand",    0.25),  # не всегда отдёргивается
        ("solicit_pet",   1.0),
    ],
    "mild_fear": [
        ("vocalize_squeak", 1.0),
        ("ear_forward",     1.0),
        ("whisker_twitch",  1.0),
        ("thump_hind",      1.0),
        ("freeze",          1.0),
        ("ear_flat",        1.0),
        ("press_flat",      1.0),
        ("sniff_air",       1.0),
        ("stand_upright",   1.0),
        ("patrol_floor",    1.0),
    ],
    "extreme_fear": [
        ("vocalize_alarm", 1.0),
        ("alarm_call",     1.0),
        ("wall_jump",      0.5),
        ("flee_corner",    1.0),
        ("fur_slip",       0.4),
        ("freeze",         1.0),
        ("hide_house",     1.0),
        ("press_flat",     1.0),
        ("eye_half_close", 1.0),
        ("doze_shelf",     1.0),
    ],
    "chronic_stress": [
        ("observe_room",      1.0),
        ("bar_chewing",       1.0),
        ("vocalize_teeth",    1.0),
        ("stereotypy_pacing", 1.0),
        ("overgroom_fur",     1.0),
        ("overgroom_other",   1.0),
        ("hide_house",        1.0),
        ("vocalize_bark",     1.0),
    ],
    "bedtime_routine": [
        ("eat_hay",           1.0),
        ("drink_water",       0.5),
        ("groom_body",        1.0),
        ("toilet_main",       1.0),
        ("rearrange_bedding", 1.0),
        ("cache_food",        1.0),
        ("hide_house",        1.0),
        ("sleep_house",       1.0),
    ],
    "territorial_patrol": [
        ("stretch_body",      1.0),
        ("patrol_floor",      1.0),
        ("sniff_corners",     1.0),
        ("toilet_mark",       1.0),
        ("gnaw_mineral",      1.0),
        ("stand_upright",     1.0),
        ("tail_raise",        1.0),
        ("climb_bars",        1.0),
        ("observe_room",      1.0),
    ],
    "nesting": [
        ("rearrange_bedding", 1.0),
        ("dig_bedding",       1.0),
        ("gnaw_wood",         1.0),
        ("carry_object",      1.0),
        ("cache_food",        1.0),
        ("rearrange_bedding", 1.0),
    ],
    "hyperactivity": [
        ("jump_hop_play",     1.0),
        ("run_wheel",         1.0),
        ("climb_bars",        1.0),
        ("hang_bars",         1.0),
        ("jump_shelf_up",     1.0),
        ("jump_shelf_down",   1.0),
        ("toss_toy",          1.0),
        ("chase_toy",         1.0),
        ("drink_water",       0.5),
    ],
}


# ============================================================================
# CONSTANTS
# ============================================================================

# Drive parameters (from specification Section 4.1)
DRIVE_ACCUMULATION_RATES = {
    "curiosity": 0.020,
    "social_drive": 0.010,
    "goal_tension": 0.012,
    "exploration": 0.011,
    "energy_need": 0.004,
}

DRIVE_DISCHARGE_RATES = {
    "curiosity": 0.001,
    "social_drive": 0.0015,
    "goal_tension": 0.0010,
    "exploration": 0.0012,
    "energy_need": 0.0010,
}

DRIVE_THRESHOLD = 0.35
ACTIVE_DRIVE_DISCHARGE = -0.18  # per dt
SPEECH_DRIVE_DISCHARGE = -0.22  # per dt

# Energy system (Section 4.2)
IDLE_ENERGY_COST = 0.06
INTERNAL_CYCLE_COST = 0.28
SPEECH_EVENT_COST = 0.18
ENERGY_RECOVERY_RATE = 0.050
ENERGY_SUPPRESSION_THRESHOLD = 0.25
ENERGY_DEADLOCK_THRESHOLD = 0.05
ENERGY_DEADLOCK_TICKS = 8

# Affect regulation (Section 5)
AFFECT_OVERLOAD_THRESHOLD = 0.80
REGULATION_STRESS_REDUCTION = -0.45
REGULATION_AROUSAL_REDUCTION = -0.35
REGULATION_STABILITY_INCREASE = 0.30

# Neuromodulator parameters (Section 6)
NEUROMOD_BASE_LEVEL = 0.10
NEUROMOD_HALF_LIFE = 90  # seconds / ticks

# TD Learning (Section 9.1)
TD_DISCOUNT_GAMMA = 0.95
TD_LEARNING_RATE = 0.05
DA_LEARNING_RATE_BONUS = 1.0  # multiplier

# Constraints (Section 10)
INTERNAL_CYCLES_PER_WINDOW = 8
INTERNAL_CYCLES_WINDOW_SIZE = 60
MAX_SPEECH_EVENTS_PER_INTERVAL = 5
SPEECH_EVENT_COOLDOWN = 5
MAX_ACTIVE_MEMORY_RECALLS = 6
RECALL_IMPULSE_SHARE_MAX = 0.4
DT_CLAMP_MIN = 0.05
DT_CLAMP_MAX = 1.0

# Behavioral chains
MIN_CHAIN_LENGTH = 2
MAX_CHAIN_LENGTH = 9

# UI
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 20  # max 20 fps = 0.05 s per frame
