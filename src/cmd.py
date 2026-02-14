from .core import *

def main():
    parser = argparse.ArgumentParser(
    prog='Racist',
    description='Python utility for sharing custom Midnight Club 3 races',
    usage="""
racist <memory-card-file> <profile-name> -x  -n <race-name> -f <output-file> (extracts single race)
racist <memory-card-file> <profile-name> -xa -d <output-directory> (extracts all races from the save file)
racist <memory-card-file> <profile-name> -p  -r <race-id> -f <input-file> (upload race to savegame)
racist <memory-card-file> <profile-name> -l (list all races of the savegame)
    """,
    epilog="Remember to backup your save!"
)
    parser.add_argument('memcard', help='.ps2 Memory card file')
    parser.add_argument('profile', help='Profile name of the save file')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-x', '--extract', action='store_true', help='Extract race mode')
    group.add_argument('-p', '--pack', action='store_true', help='Pack race mode')
    group.add_argument('-l', '--list_races', action='store_true', help='List races from save file')
    parser.add_argument('-f', '--file', help='File to write/read the race file')
    parser.add_argument('-a', '--all', action='store_true', help='Extract alraces')
    parser.add_argument('-d', '--directory', help='Directory to write the extracted races with the -a mode')
    parser.add_argument('-s', '--store_at', help='A slot 0-14 to store the race', type=int)
    parser.add_argument('-n', '--race_name', help='The name of the race as shown in the editor')
    parser.add_argument('-R', '--rename', help='The name of the race as shown in the editor')
    args = parser.parse_args()

    if not os.path.exists(args.memcard):
        raise Exception("Path to the memory card does not exist or it is wrong")
    memcard: ps2mc
    with open(args.memcard, "rb+") as f:
        memcard = ps2mc(f)
        mem = memcard.open(f'BASLUS-21355{args.profile}/file01', "rb")
        if mem is None:
            raise Exception(f"{args.profile} profile does not exist in this memory card1")
        mem.close()
        if args.extract:
            if args.all:
                directory = args.directory
                if directory is None:
                    directory = "./extracted_races"
                    print("No output directory informed, using the default directory name! Use -d <directory> to set the output directory next time!")
                extract_all(memcard, args.profile, directory)
            else:
                file = args.file
                if file is None:
                    print("No output file informed, using the default file name! Use -f <file> to set the output file next time!")
                if args.race_name is None:
                    raise Exception("No race name to be extracted informe! Use -n <race-name> next time!")
                if args.directory is None:
                    args.directory = "./"
                extract_from_name(memcard, args.profile, args.race_name, file, args.directory)
        elif args.pack:
            if args.store_at is None:
                raise Exception("Where to store the race? Use -s <position>")
            if args.file is None:
                raise Exception("No input race file informed! Use -f <file> next time when unpacking")
            if not os.path.exists(args.file):
                raise Exception("Race informed is does not exist or the path is wrong!")
            if args.store_at is None:
                raise Exception("Index to store at not set! Use -s <position> (needs to be between 0..14) next time.")
            if args.store_at < 0 or args.store_at > 14:
                raise Exception("Can't store race at this location! You can only store stuff between 0..14")
            if args.rename is not None:
                rename_bytes = args.rename.encode('ascii')
                if len(rename_bytes) > MAX_NAME:
                    raise Exception("Can't have a race name bigger than 17 characters")

            pack(memcard, args.profile, args.file, args.store_at, args.rename)
        elif args.list_races:
            print_info(memcard, args.profile)

        memcard.close()
        f.close()



