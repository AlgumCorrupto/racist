import src.cmd as cmd
import src.gui as gui
import sys

if __name__ == "__main__":
    try:
        if len(sys.argv) != 1:
            cmd.main()
        else:
            gui.main()
    except Exception as e:
        print(f"Error: {e}")

