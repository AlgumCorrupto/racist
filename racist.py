import argparse
from pathlib import Path
from mymcplus.ps2mc import ps2mc
import struct
import os

CITIES = {"SD": "San Diego", "DET": "Detroit", "ATL": "Atlanta", "TOK": "Tokyo"}
CODES_MAX = 14
VERSION = 1
MAGIC   = b'RATO'

def extract_single(memcard: ps2mc, profile: str, city: str, code: int, filename: str) -> None:
    racefile = get_races_file(memcard, profile)
    race_info = " ".join([city, str(code)]).encode(encoding='ascii')
    race_info = race_info[:8]
    race_loc = racefile.find(race_info)
    if race_loc == -1:
        raise Exception(f"Race {city}-{code} not found in memory card!")
    
    race =  racefile[race_loc:race_loc + 0xDC]

    race_info = race_info.ljust(8, b'\x00')
    header = struct.pack(">4sI8s", MAGIC, VERSION, race_info)

    base, ext = os.path.splitext(filename)
    if ext.lower() != ".mc3race":
        filename = f"{base}.mc3race"

    with open(filename, 'wb') as f:
        f.write(header)
        f.write(race)
        f.close()

def extract_all(memcard: ps2mc, profile: str, directory: str) -> None:
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    for city in CITIES:
        for code in range(CODES_MAX+1):
            if city == 'TOK' and code == 0:
                continue
            extract_single(memcard, profile, city, code, str(dir_path.joinpath(f"{city}-{code}.mc3race")))

def pack(memcard: ps2mc, profile: str, city: str, code: str, filename: str)-> None:
    input_bytes: bytes
    with open(filename, 'rb') as f:
        input_bytes = f.read()
        f.close()
    if input_bytes[:0x4] != MAGIC:
        raise Exception(f"Not a valid race file!")
    if city == 'TOK' and code == 0:
        raise Exception(f"Cannot write tokyo race with index 0")
    
    city_i_bytes = input_bytes[0x8:0xF]      # slice bytes
    city_i_str = city_i_bytes.decode('ascii') # decode to string
    city_i_str = city_i_str.strip('\0')       # remove null padding

    # split the string into city and code
    city_i, _ = city_i_str.split(' ')

    if city_i != city:
        raise Exception(f"This race is for {city_i} ({CITIES[city_i]})")
    
    racefile = bytearray(get_races_file(memcard, profile))
    race_info = " ".join([city, str(code)]).encode(encoding='ascii')
    output_bytes = bytearray(input_bytes[0x10:])
    output_bytes[0x0:0x7] = bytearray(race_info).ljust(8, b'\x00')
    race_loc = racefile.find(race_info)
    if race_loc == -1:
        raise Exception(f"Race {city}-{code} not found in memory card!")

    racefile[race_loc:race_loc+0xDC] = output_bytes
    write_races_file(memcard, profile, bytes(racefile))


def get_races_file(memcard: ps2mc, profile: str) -> bytes:
    f =  memcard.open(f'BASLUS-21355{profile}/file01', "rb")
    if f == None:
        raise Exception("Save game not found! Is the profile name correct?")
    
    file = bytes(f.read())
    f.close()

    return file


def write_races_file(memcard: ps2mc, profile: str, racefile: bytes) -> None:
    f = memcard.open(f'BASLUS-21355{profile}/file01', "wb")
    f.write(racefile)
    f.close()
    memcard.close()

def parse_race_id(race_id: str) -> tuple[str, int]:
    if race_id == None:
        raise Exception("Not informed the race id")
    race_identifier = race_id.split('_')
    if len(race_identifier) != 2:
        raise Exception("Race identifier malformed")
    city, code = race_identifier
    if not code.isdigit():
        raise Exception("Race identifier malformed")
    code = int(code)
    if code > CODES_MAX or code < 0:
        raise Exception("Race code needs to be between 0-14")
    
    city = city.upper()

    if city not in CITIES.keys():
        raise Exception("That city is not valid!")

    return (city, code)


def cmd_main():
    parser = argparse.ArgumentParser(
    prog='Racist',
    description='Python utility for sharing custom Midnight Club 3 races',
    usage="""
racist -x  <memory-card-file> <profile-name> -r <race-id> -f <output-file>
racist -xa <memory-card-file> <profile-name> -d <output-directory>
racist -p  <memory-card-file> <profile-name> -r <race-id> -f <input-file>
    """,
    epilog="Remember to backup your save!"
)
    parser.add_argument('memcard', help='.ps2 Memory card file')
    parser.add_argument('profile', help='Profile name of the save file')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-x', '--extract', action='store_true', help='Extract race mode')
    group.add_argument('-p', '--pack', action='store_true', help='Pack race mode')
    parser.add_argument('-f', '--file', help='File to write/read the race file')
    parser.add_argument('-a', '--all', action='store_true', help='Extract all races')
    parser.add_argument('-d', '--directory', help='Directory to write the extracted races with the -a mode')
    parser.add_argument('-r', '--race_id', help='Race ID to extract/pack, E.g: SD-1, DET-8, ATL-3, TOK-6')
    args = parser.parse_args()

    if not os.path.exists(args.memcard):
        raise Exception("Path to the memory card does not exist or it is wrong")
    memcard: ps2mc
    with open(args.memcard, "rb+") as f:
        memcard = ps2mc(f)
        mem = memcard.open(f'BASLUS-21355{args.profile}/file01', "rb")
        if mem == None:
            raise Exception(f"{args.profile} profile does not exist in this memory card1")
        mem.close()
        if args.extract:
            if args.all:
                directory = args.directory
                if directory == None:
                    directory = "./extracted_races"
                    print("No output directory informed, using the default directory name! Use -d <directory> to set the output directory next time!")
                extract_all(memcard, args.profile, directory)
            else:
                city, code = parse_race_id(args.race_id)
                file = args.file
                if file == None:
                    file = "./" + "_".join([city, code])
                    print("No output file informed, using the default file name! Use -f <file> to set the output file next time!")
                extract_single(memcard, args.profile, city, code, file)
        elif args.pack:
            city, code = parse_race_id(args.race_id)
            if args.file == None:
                raise Exception("No input race file informed! Use -f <file> next time when unpacking")
            if not os.path.exists(args.file):
                raise Exception("Race informed is does not exist or the path is wrong!")
            pack(memcard, args.profile, city, code, args.file)
        memcard.close()
        f.close()


if __name__ == "__main__":
    cmd_main()
