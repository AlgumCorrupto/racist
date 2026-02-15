from io import BufferedRandom, BufferedReader, FileIO
from PySide6.QtGui import (
    QIcon, QPixmap, QStandardItemModel, QStandardItem
)
from .core import *
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QSpinBox, QLineEdit,
    QFormLayout, QLabel, QPushButton, QStackedWidget, QWidget,
    QVBoxLayout, QListView, QFrame, QTabWidget, QTableView,
    QMessageBox, QPushButton, QHBoxLayout, QComboBox, QHeaderView
)


from PySide6.QtWidgets import QAbstractItemView
from mymcplus.ps2mc import ps2mc, DF_DIR, DF_EXISTS
from typing import cast
from PySide6.QtCore import Qt
import qt_themes

from PySide6.QtCore import QObject, Signal
import re
import sys

from configparser import ConfigParser

def resource(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
    return os.path.join(base_path, relative_path)

class History(QObject):
    def __init__(self):
        super().__init__()
        self.profile: str | None = None
        self.memcard_path: Path | None = None
        self.extract_output_directory: Path | None = None
        self.pack_race_file: Path | None = None

        self.get_ini(Path('./.goodies.ini'))

    def get_ini(self, ini_file: Path) -> None:
        if not ini_file.exists():
            return
    
        goodies = ConfigParser()
        goodies.read(ini_file)
    
        section = "last_sesh"
    
        if not goodies.has_section(section):
            return
    
        profile = goodies[section].get("profile")
        if profile:
            self.profile = profile
    
        memcard_path = goodies[section].get("memcard_path")
        if memcard_path:
            self.memcard_path = Path(memcard_path)
    
        extract_dir = goodies[section].get("extract_output_directory")
        if extract_dir:
            self.extract_output_directory = Path(extract_dir)
    
        pack_race = goodies[section].get("pack_race_file")
        if pack_race:
            self.pack_race_file = Path(pack_race)
    
    
    def set_ini(self, ini_file: Path) -> None:
        goodies = ConfigParser()
        section = "last_sesh"
    
        goodies.add_section(section)
    
        if self.profile:
            goodies[section]["profile"] = self.profile
    
        if self.memcard_path:
            goodies[section]["memcard_path"] = str(self.memcard_path)
    
        if self.extract_output_directory:
            goodies[section]["extract_output_directory"] = str(self.extract_output_directory)
    
        if self.pack_race_file:
            goodies[section]["pack_race_file"] = str(self.pack_race_file)
    
        with open(ini_file, "w") as f:
            goodies.write(f)

class AppState(QObject):
    profileChanged = Signal(object)
    memcardChanged = Signal(object)

    windowPushed   = Signal(QWidget)
    windowPopped   = Signal()

    def __init__(self):
        super().__init__()
        self._profile: str | None = None
        self._memcard: ps2mc | None = None
        self._memcard_file: BufferedRandom | None = None
        self._memcard_path: Path | None = None
        self.history =  History()

    @property
    def profile(self) -> str:
        assert self._profile is not None, "Profile is not set! Why get it?"
        return self._profile

    @profile.setter
    def profile(self, value: str):
        self._profile = value
        self.profileChanged.emit(value)

    @property
    def memcard(self) -> ps2mc:
        if self._memcard_path is None or not Path(self._memcard_path).exists():
            raise FileNotFoundError(f"Memory card file '{self._memcard_path}' does not exist!")
        assert self._memcard is not None, "Memory card is no set! Why get it?"

        return self._memcard

    @memcard.setter
    def memcard(self, value: Path):
        self._memcard_path = value
        self._memcard_file = open(value, "r+b")
        self._memcard = ps2mc(self._memcard_file)
        self.memcardChanged.emit(self._memcard)

    def shutdown(self):
        self.close_memcard()
        self.history.set_ini(Path('./.goodies.ini'))

    def close_memcard(self):
        if self._memcard is not None:
            self._memcard.close()
        if self._memcard_file is not None:
            self._memcard_file.close()

class MainView(QWidget):
    stack: QStackedWidget
    state: AppState

    def __init__(self):
        super().__init__()
    
        self.stack = QStackedWidget()
        self.history = []
        self.state = AppState()
    
        # Back button
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.back)
        self.back_button.setEnabled(False)
    
        # Header image
        self.header_label = QLabel()
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_img = resource("assets/header.png")
        pixmap = QPixmap(header_img)
        
        if pixmap.isNull():
            print("HEADER FAILED TO LOAD")
        
        scaled = pixmap.scaled(
            350,
            60,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.header_label.setPixmap(scaled)
        self.header_label.setMinimumHeight(40)

    
        # ---- Layout ----
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # Header at top
        main_layout.addWidget(self.header_label)
        
        # Stack fills available space
        main_layout.addWidget(self.stack, stretch=1)
        
        # Bottom row (back button)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()                 # push button to center
        bottom_layout.addWidget(self.back_button)
        bottom_layout.addStretch()
        
        main_layout.addLayout(bottom_layout)
    
        # Signals
        self.state.windowPushed.connect(self.push)
        self.state.windowPopped.connect(self.pop)
    
        # First page
        first = MemcardSelect(self.state)
        self.state.windowPushed.emit(first)


    def push(self, widget):
        self.stack.addWidget(widget)
        self.history.append(widget)
        self.stack.setCurrentWidget(widget)
        # Enable back button if there’s more than one window
        self.back_button.setEnabled(len(self.history) > 1)
    
    def pop(self):
        if len(self.history) > 1:
            widget = self.history.pop()
            self.stack.removeWidget(widget)
            widget.deleteLater()
            self.stack.setCurrentWidget(self.history[-1])
        # Disable back button if we are back at first window
        self.back_button.setEnabled(len(self.history) > 1)

    def back(self):
        self.pop()
    
    def shutdown(self):
        self.state.shutdown()

class ProfileSelect(QWidget):
    state: AppState
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
    
        form_layout = QFormLayout(self)
    
        profile_name_label = QLabel("Profile:")
    
        profile_combo = QComboBox()
        profile_combo.setPlaceholderText("Select a profile")
    
        # Populate with existing profiles
        profiles = self.find_all_profiles()
        profile_combo.addItems(profiles)
    
        form_layout.addRow(profile_name_label, profile_combo)
    
        submit = QPushButton("Next")
        form_layout.addRow(submit)
    
        submit.clicked.connect(
            lambda: self.submit(profile_combo.currentText())
        )


    def submit(self, profile: str) -> None:
        result = self.validate(profile)
        if result is not None:
            self.show_error_dlg(result)
        else:
            self.commit(profile)
            self.next()

    # if None, OK
    # else, error
    def validate(self, profile: str) -> str | None:
        if len(profile) == 0:
            return "Profile name not informed!"
        profiles = self.find_all_profiles()
        if profile not in profiles:
            return "This profile is not in the memory card!"
        return None

    def find_all_profiles(self) -> list[str]:
        memcard = cast(ps2mc, self.state.memcard)
    
        profile_pattern = re.compile(r"^BASLUS-21355(.+)$")
        profiles: list[str] = []
    
        dir = memcard.dir_open("/")
        try:
            for ent in dir:
                mode = ent[0]
    
                if (mode & DF_EXISTS) == 0:
                    continue
    
                name = ent[8].decode("ascii", errors="ignore")
    
                if (mode & DF_DIR):
                    match = profile_pattern.match(name)
                    if match:
                        profiles.append(match.group(1))
        finally:
            dir.close()
    
        return profiles

    def show_error_dlg(self, error: str) -> None:
        QMessageBox.critical(self, "Error", error)
        return

    def commit(self, profile: str):
        self.state.profile = profile
        self.state.history.profile = profile

    def next(self) -> None:
        next = ActionSelect(self.state)
        self.state.windowPushed.emit(next)

class MemcardSelect(QWidget):
    state: AppState

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
    
        layout = QFormLayout(self)
    
        # Path input + browse button
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Choose .ps2 memory card file")
        if self.state.history.memcard_path is not None:
            self.path_edit.setText(str(self.state.history.memcard_path))
    
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.open_file_dlg)
    
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
    
        layout.addRow("Memory Card:", path_layout)
    
        # Submit button (spans full width)
        submit_btn = QPushButton("Next")
        submit_btn.clicked.connect(lambda: self.submit(self.path_edit.text()))
        layout.addRow(submit_btn)

    def submit(self, path_text: str) -> None:
        path_text = path_text.strip()
    
        result = self.validate(path_text)
        if result is not None:
            self.show_error_dlg(result)
            return
    
        memcard_path = Path(path_text)
        self.commit(memcard_path)
        self.next()

    # if None, OK
    # else, error message
    def validate(self, path_text: str) -> None | str:
        path_text = path_text.strip()
    
        if not path_text:
            return "Please select a memory card file."
    
        memcard_path = Path(path_text)
    
        if not memcard_path.exists() or not memcard_path.is_file():
            return "The memory card path does not exist!"
    
        try:
            with open(memcard_path, "rb") as f:
                memcard = ps2mc(f)
                memcard.check()
        except Exception:
            return "Memory card not valid!"
    
        return None

    
    def show_error_dlg(self, error: str) -> None:
        QMessageBox.critical(self, "Error", error)

    def commit(self, memcard_path: Path) -> None:
        self.state.memcard = memcard_path
        self.state.history.memcard_path = memcard_path

    def open_file_dlg(self) -> None:
        dir = Path(self.path_edit.text()).parent
        dir_str = str(dir) if dir.exists() else ""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PS2 Memory Card",
            dir_str,
            "PS2 Memory Card (*.ps2 *.bin);;All Files (*)"
        )

        if file_path:
            self.path_edit.setText(file_path)

    def next(self) -> None:
        next_widget = ProfileSelect(self.state)
        self.state.windowPushed.emit(next_widget)

class ActionSelect(QWidget):
    state: AppState
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Extract button
        extract_btn = QPushButton("Extract")
        extract_btn.clicked.connect(self.goto_extract_view)

        # Pack button
        pack_btn = QPushButton("Pack")
        pack_btn.clicked.connect(self.goto_pack_view)

        # View button (disabled for now)
        view_btn = QPushButton("View")
        view_btn.setEnabled(False)

        # Add to layout
        layout.addStretch()          # push buttons toward center
        layout.addWidget(extract_btn)
        layout.addWidget(pack_btn)
        layout.addWidget(view_btn)
        layout.addStretch()

    def goto_extract_view(self) -> None:
        next = ExtractView(self.state)
        self.state.windowPushed.emit(next)

    def goto_pack_view(self) -> None:
        next = PackView(self.state)
        self.state.windowPushed.emit(next)

class ExtractView(QWidget):
    state: AppState

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state

        main_layout = QVBoxLayout(self)

        dir_layout = QHBoxLayout()

        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("Select destination directory")
        if self.state.history.extract_output_directory is not None:
            self.dir_edit.setText(str(self.state.history.extract_output_directory))

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.open_directory_dlg)

        dir_layout.addWidget(QLabel("Output Directory:"))
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(browse_btn)

        main_layout.addLayout(dir_layout)

        self.table = QTableView()
        self.table.setModel(self.build_race_model())
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)

        main_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        extract_selected_btn = QPushButton("Extract Selected")
        extract_selected_btn.clicked.connect(self.handle_extract_selected)

        extract_all_btn = QPushButton("Extract All")
        extract_all_btn.clicked.connect(self.handle_extract_all)

        btn_layout.addStretch()
        btn_layout.addWidget(extract_selected_btn)
        btn_layout.addWidget(extract_all_btn)

        main_layout.addLayout(btn_layout)

    def open_directory_dlg(self) -> None:
        dir = Path(self.dir_edit.text())
        dir_txt = str(dir) if dir.exists() else ""
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory",  dir_txt)
        if directory:
            self.dir_edit.setText(directory)

    def validate_directory(self, path_text: str) -> None | str:
        if not path_text:
            return "Please select an output directory."

        path = Path(path_text)

        if not path.exists() or not path.is_dir():
            return "The selected directory is invalid."

        return None

    def handle_extract_selected(self) -> None:
        path_text = self.dir_edit.text().strip()
        error = self.validate_directory(path_text)
        if error:
            QMessageBox.critical(self, "Error", error)
            return

        selected_indexes = self.table.selectionModel().selectedRows()

        if not selected_indexes:
            QMessageBox.critical(self, "Error", "No races selected.")
            return

        races = tuple(index.data() for index in selected_indexes)

        self.extract_selected(races, Path(path_text))

    def handle_extract_all(self) -> None:
        path_text = self.dir_edit.text().strip()
        error = self.validate_directory(path_text)
        if error:
            QMessageBox.critical(self, "Error", error)
            return

        self.extract_all(Path(path_text))

    def build_race_model(self) -> QStandardItemModel: 
        memcard = self.state.memcard 
        profile = self.state.profile 
        racefile = get_races_file(memcard, profile) 
        race_info = get_all_race_info(racefile) # Create the model 
        model = QStandardItemModel() 
        model.setHorizontalHeaderLabels(["Name", "City", "Slot", "Offset"]) 
        for name, offset, city, code in race_info: 
            # Create items for each column 
            name_item   = QStandardItem(name) 
            city_item   = QStandardItem(city) 
            code_item   = QStandardItem(str(code)) 
            offset_item = QStandardItem(hex(offset)) # Add the row to the model 
            model.appendRow([name_item, city_item, code_item, offset_item]) 
        return model

    def extract_selected(self, races: tuple[str], directory: Path) -> None:
        memcard = self.state.memcard
        profile = self.state.profile

        for race in races:
            extract_from_name(memcard, profile, race, None, str(directory) + "/")

        QMessageBox.information(self, "Success!", f"Races extracted at {directory}")

    def extract_all(self, directory: Path) -> None:
        memcard = self.state.memcard
        profile = self.state.profile

        extract_all(memcard, profile, str(directory))
        self.state.history.extract_output_directory = directory

        QMessageBox.information(self, "Success!", f"Races extracted at {directory}")

class PackView(QWidget):
    state: AppState
    user_sure = Signal(bool)

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state

        main_layout = QVBoxLayout(self)

        self.table = QTableView()
        self.table.setModel(self.build_race_model())
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(QLabel("Current Races on Memory Card:"))
        main_layout.addWidget(self.table)

        form_layout = QFormLayout()

        # Name input
        self.race_name = QLineEdit()
        self.race_name.setMaxLength(MAX_NAME)
        self.race_name.setPlaceholderText("Name of the race")
        form_layout.addRow("Name:", self.race_name)

        # File input
        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Select race file to pack")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.open_file_dlg)
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(browse_btn)
        form_layout.addRow("Race File:", file_layout)

        # Slot input
        self.slot_spin = QSpinBox()
        self.slot_spin.setRange(0, RACE_QTD - 1)
        form_layout.addRow("Slot:", self.slot_spin)

        main_layout.addLayout(form_layout)

        submit_btn = QPushButton("Pack Race")
        submit_btn.clicked.connect(self.submit)  # directly call submit
        main_layout.addWidget(submit_btn, alignment=Qt.AlignmentFlag.AlignRight)

        if self.state.history.pack_race_file is not None:
            self.set_file(str(self.state.history.pack_race_file))

    def submit(self) -> None:
        """
        Gather inputs from widgets and run validation + confirmation + pack
        """
        file_text = self.file_edit.text().strip()  # string path
        position = self.slot_spin.value()
        new_name = self.race_name.text().strip()  # could add QLineEdit for custom name if desired

        error = self.validate(file_text, position, new_name)
        if error:
            self.show_error_dlg(error)
            return

        self.state.history.pack_race_file = Path(file_text)

        self.show_are_you_sure_dlg(file_text, position, new_name)

    def validate(self, file: str, position: int, new_name: str) -> None | str:
        path = Path(file)
        if not new_name.replace(" ", "").isalnum():
            return "No special symbols in the name"

        try:
            ascii_name = new_name.encode("ascii")
        except UnicodeEncodeError:
            return "Race name must contain only ASCII characters"
        length = len(ascii_name)
        if length == 0 or length > MAX_NAME:
            return f"Race names need to be between 1..{MAX_NAME} characters long"

        # Slot validation
        if position < 0 or position > RACE_QTD - 1:
            return f"The slot needs to be between 0..{RACE_QTD - 1}"

        # File validation
        if not path.exists() or not path.is_file():
            return "This file does not exist"

        with open(path, "rb") as f:
            file_contents = f.read()

        if file_contents[0:4] != MAGIC:
            return "This race is invalid"

        # Extract city from input file
        city_bytes = file_contents[0x8:0xF]
        city = city_bytes.decode("ascii").strip("\0")

        # Load memory card races
        racefile = bytearray(get_races_file(cast(ps2mc, self.state.memcard), cast(str, self.state.profile)))
        race_loc = get_offset_from_city_and_code(city, position)

        # Duplicate name validation
        all_race_names_and_idx = get_all_race_info(racefile)
        if new_name is not None:
            for name, offset, city_dup, code_dup in all_race_names_and_idx:
                if name == new_name and offset != race_loc:
                    return f"There's already a race named '{new_name}' at {city_dup}_{code_dup}. Choose a different name."

        return None

    def pack(self, file: str, position: int, new_name: str | None) -> None:
        memcard = self.state.memcard
        profile = self.state.profile
        pack(memcard, profile, str(file), position, new_name)
        QMessageBox.information(self, "Success", "Race packed!")
        self.table.setModel(self.build_race_model())

    def open_file_dlg(self) -> None:
        dir = Path(self.file_edit.text()).parent
        dir_text = str(dir) if dir.exists() else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Race File",
            dir_text,
            "Race Files (*.mc3race);;All Files (*)"
        )
        if file_path:
            self.set_file(file_path)

    def set_file(self, file_path: str) -> None:
        self.file_edit.setText(file_path)
        filename = os.path.basename(file_path)
        # Expect format: name.city.mc3race
        if filename.lower().endswith(".mc3race"):
            base = filename[:-len(".mc3race")]
            # Remove last ".city"
            name = base.rsplit(".", 1)[0]
            self.race_name.setText(name)


    def show_error_dlg(self, error: str) -> None:
        QMessageBox.critical(self, "Error", error)

    def build_race_model(self) -> QStandardItemModel:
        memcard = self.state.memcard
        profile = self.state.profile
        racefile = get_races_file(memcard, profile)
        race_info = get_all_race_info(racefile)
    
        # Create the model
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Name", "City", "Slot", "Offset"])
    
        for name, offset, city, code in race_info:
            # Create items for each column
            name_item = QStandardItem(name)
            city_item = QStandardItem(city)
            code_item = QStandardItem(str(code))
            offset_item = QStandardItem(hex(offset))
    
            # Add the row to the model
            model.appendRow([name_item, city_item, code_item, offset_item])
    
        return model

    def show_are_you_sure_dlg(self, file: str, position: int, new_name: str | None) -> None:
        reply = QMessageBox.question(
            self,
            "Are you sure?",
            (
                "This race slot will be overridden and your save game "
                "may become corrupted.\n\n"
                "Are you REALLY sure you want to do it?\n"
                "Please backup your memory card before proceeding."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.pack(file, position, new_name)

def main():
    app = QApplication()
    qt_themes.set_theme('monokai')

    main_wind = MainView()
    main_wind.setWindowTitle("Race Instrument")
    main_wind.setWindowIcon(QIcon(resource("assets/icon.png")))

    main_wind.setWindowFlags(
        Qt.WindowType.Window |
        Qt.WindowType.WindowMinimizeButtonHint |
        Qt.WindowType.WindowCloseButtonHint
    )

    # Set initial size (floating, not fullscreen)
    main_wind.resize(400, 300)

    app.aboutToQuit.connect(main_wind.state.shutdown)

    main_wind.show()
    app.exec()

