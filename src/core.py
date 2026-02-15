import argparse
from pathlib import Path
from mymcplus.ps2mc import ps2mc
import struct
import os
from math import floor

RACE_BASE = 0x4
CITIES = ["SD", "ATL", "DET", "TOK"]
CITIES_ADDR = {
    "SD": 0x06-0x02,
    "ATL": 0xCEA-0x2,
    "DET": 0x19CE-0x2,
    "TOK": 0X26B2-0x2,
}

RACE_SIZE = 0xDC
RACE_QTD  = 15

VERSION = 1
MAGIC   = b'RATO'
MAX_NAME = 17

def get_city_from_race_loc(race_loc: int) -> str:
    race_index = (race_loc - RACE_BASE) // RACE_SIZE
    city_index = race_index // RACE_QTD
    return CITIES[city_index]

def get_offset_from_city_and_code(city: str, code: int) -> int:
    return CITIES_ADDR[city] + code * RACE_SIZE

def extract_from_name(memcard: ps2mc, profile: str, name: str, filename: str | None, directory: str = './') -> None:
    racefile = get_races_file(memcard, profile)
    race_name = name.encode(encoding='ascii')
    race_name = race_name[:MAX_NAME]
    race_loc = racefile.find(race_name) - 0x2
    if race_loc < 0:
        raise Exception(f"Race {name} not found in memory card!")
    extract(memcard, profile, race_loc, filename, directory)

def get_all_race_info(racefile) -> list[tuple[str, int, str, int]]:
    racenames = []
    for city in CITIES:
        for code in range(RACE_QTD):
            race_loc = get_offset_from_city_and_code(city, code)
            race = racefile[race_loc : race_loc + RACE_SIZE]
            name = race[0x02 : 0x02 + MAX_NAME].decode("ascii", errors="ignore").rstrip('\x00')
            racenames.append((name, race_loc, city, code))
    return racenames

def extract(
    memcard: ps2mc,
    profile: str,
    race_loc: int,
    filename: str | None = None,
    directory: str = "./"
) -> None:

    racefile = get_races_file(memcard, profile)

    # Determine city
    city_str = get_city_from_race_loc(race_loc)        # e.g. "ATL"
    city_bytes = city_str.encode("ascii").ljust(8, b"\x00")

    # Extract race block
    race = racefile[race_loc:race_loc + RACE_SIZE]
    if len(race) != RACE_SIZE:
        raise ValueError("Invalid race block size")

    # Build header
    header = struct.pack(">4sI8s", MAGIC, VERSION, city_bytes)

    filename = (
        race[0x2:0x2 + MAX_NAME]
        .decode("ascii", errors="ignore")
        .replace("\x00", "")
    )

    # Ensure correct extension
    base, ext = os.path.splitext(filename)
    city_lower = city_str.lower()

    expected_ext = f".{city_lower}.mc3race"
    if ext.lower() != expected_ext:
        filename = f"{base}{expected_ext}"

    # Write file safely
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)

    with open(filepath, "wb") as f:
        f.write(header)
        f.write(race)

def extract_all(memcard: ps2mc, profile: str, directory: str) -> None:
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    for city in CITIES:
        for code in range(RACE_QTD):
            extract(memcard, profile, get_offset_from_city_and_code(city, code), directory=str(dir_path)+'/')

def print_info(memcard: ps2mc, profile: str) -> None:
    racefile = get_races_file(memcard, profile)
    info = get_all_race_info(racefile)
    sd_races = [race for race in info if race [2] == 'SD']
    atl_races = [race for race in info if race[2] == 'ATL']
    det_races = [race for race in info if race[2] == 'DET']
    tok_races = [race for race in info if race[2] == 'TOK']

    print("-- San Diego --")
    for race in sd_races:
        print(f'"{race[0]}"')
    print("-- Atlanta --")
    for race in atl_races:
        print(f'"{race[0]}"')
    print("-- Detroit --")
    for race in det_races:
        print(f'"{race[0]}"')
    print("-- Tokyo --")
    for race in tok_races:
        print(f'"{race[0]}"')

def get_race_names(racefile: bytes) -> list[str]:
    info = get_all_race_info(racefile)
    return [race[0] for race in info]

def pack(memcard: ps2mc, profile: str, filename: str, position: int, new_name: str | None = None) -> None:
    # Read input race file
    with open(filename, 'rb') as f:
        input_bytes = bytearray(f.read())

    if input_bytes[:0x4] != MAGIC:
        raise Exception("Not a valid race file!")

    # Extract city from header
    city_bytes = input_bytes[0x8:0xF]
    city = city_bytes.decode('ascii').strip('\0')

    # Load memory card racefile
    racefile = bytearray(get_races_file(memcard, profile))
    race_loc = get_offset_from_city_and_code(city, position)
    if race_loc == -1:
        raise Exception(f"Race {city}_{position} not found in memory card!")

    # Determine the name to write / check duplicates
    if new_name is not None:
        current_race_name = new_name
    else:
        # Read name from input file race block
        current_race_name = input_bytes[0x10 + 0x02 : 0x10 + 0x02 + MAX_NAME].decode('ascii', errors='ignore').rstrip('\x00')

    # Check for duplicate names
    all_race_names_and_idx = get_all_race_info(racefile)
    all_race_names = [name for name, _, _, _ in all_race_names_and_idx]
    try:
        custom_race_pos = all_race_names.index(current_race_name)
    except ValueError:
        custom_race_pos = -1

    if custom_race_pos != -1:
        _, offset, city_dup, code_dup = all_race_names_and_idx[custom_race_pos]
        if offset == race_loc:
            print(f"Replacing race at slot {position}")
        else:
            raise Exception(f"There's a race with this exact same name at {city_dup}_{code_dup}! Use -R to rename it.")

    # Copy race block into memory card
    racefile[race_loc : race_loc + RACE_SIZE] = input_bytes[0x10:]

    # Overwrite race name if a new name is given
    if new_name is not None:
        racefile[race_loc + 0x02 : race_loc + 0x02 + MAX_NAME] = new_name.encode('ascii').ljust(MAX_NAME, b'\x00')

    # Write updated racefile back to memory card
    write_races_file(memcard, profile, bytes(racefile))


def get_races_file(memcard: ps2mc, profile: str) -> bytes:
    f =  memcard.open(f'BASLUS-21355{profile}/file01', "rb")
    if f is None:
        raise Exception("Save game not found! Is the profile name correct?")
    
    file = bytes(f.read())
    f.close()
    return file


def write_races_file(memcard: ps2mc, profile: str, racefile: bytes) -> None:
    f = memcard.open(f'BASLUS-21355{profile}/file01', "wb")
    f.write(racefile)
    f.close()
    memcard.close()
