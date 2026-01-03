import os
import platform
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QFileInfo, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFileIconProvider,
    QFrame,
    QHBoxLayout,
    QLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import determine_launch, load_tiles_file, save_tiles_file

APP_NAME = "AppBoard"
DATA_FILE = Path(__file__).with_name("shortcuts.json")


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=10):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0

        for item in self._items:
            next_x = x + item.sizeHint().width() + self.spacing()
            if next_x - self.spacing() > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + self.spacing()
                next_x = x + item.sizeHint().width() + self.spacing()
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class AddTileDialog(QDialog):
    def __init__(self, parent=None, defaults=None):
        super().__init__(parent)
        self.setWindowTitle("Add Tile")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")

        path_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Path to app or script")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse)
        path_row.addWidget(self.path_input)
        path_row.addWidget(browse_button)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Description")
        self.desc_input.setFixedHeight(90)

        button_row = QHBoxLayout()
        button_row.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        self.submit_button = QPushButton("Add")
        self.submit_button.clicked.connect(self._accept)
        self.submit_button.setDefault(True)
        button_row.addWidget(cancel_button)
        button_row.addWidget(self.submit_button)

        layout.addWidget(QLabel("Tile name"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Application or script"))
        layout.addLayout(path_row)
        layout.addWidget(QLabel("Description"))
        layout.addWidget(self.desc_input)
        layout.addLayout(button_row)

        if defaults:
            self.setWindowTitle("Edit Tile")
            self.submit_button.setText("Save")
            self.name_input.setText(defaults.get("name", ""))
            self.path_input.setText(defaults.get("path", ""))
            self.desc_input.setText(defaults.get("description", ""))

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select application or script")
        if path:
            self.path_input.setText(path)
            if not self.name_input.text().strip():
                self.name_input.setText(Path(path).stem)

    def _accept(self):
        name = self.name_input.text().strip()
        path = self.path_input.text().strip()
        if not name or not path:
            QMessageBox.warning(self, "Missing info", "Name and path are required.")
            return
        self.accept()

    def values(self):
        return {
            "name": self.name_input.text().strip(),
            "path": self.path_input.text().strip(),
            "description": self.desc_input.toPlainText().strip(),
        }


class TileWidget(QFrame):
    def __init__(self, tile, icon_provider, launch_callback, edit_callback, remove_callback, parent=None):
        super().__init__(parent)
        self.tile = tile
        self.launch_callback = launch_callback
        self.edit_callback = edit_callback
        self.remove_callback = remove_callback
        self.setObjectName("tile")
        self.setFixedSize(260, 160)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        top_row = QHBoxLayout()
        icon_label = QLabel()
        icon = icon_provider.icon(QFileInfo(tile["path"])) if tile.get("path") else QIcon()
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.SP_DesktopIcon)
        icon_label.setPixmap(icon.pixmap(32, 32))

        name_label = QLabel(tile.get("name", "Untitled"))
        name_label.setObjectName("tileTitle")
        name_label.setWordWrap(True)

        top_row.addWidget(icon_label)
        top_row.addWidget(name_label, 1)

        desc_label = QLabel(tile.get("description", ""))
        desc_label.setObjectName("tileDesc")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignTop)

        button_row = QHBoxLayout()
        launch_button = QPushButton("Open")
        launch_button.setObjectName("tileButton")
        launch_button.clicked.connect(lambda: self.launch_callback(self.tile))
        edit_button = QPushButton("Edit")
        edit_button.setObjectName("tileEditButton")
        edit_button.clicked.connect(lambda: self.edit_callback(self.tile))
        remove_button = QPushButton("Remove")
        remove_button.setObjectName("tileRemoveButton")
        remove_button.clicked.connect(lambda: self.remove_callback(self.tile))
        button_row.addWidget(launch_button)
        button_row.addWidget(edit_button)
        button_row.addWidget(remove_button)

        layout.addLayout(top_row)
        layout.addWidget(desc_label, 1)
        layout.addLayout(button_row)


class AppBoard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 600)

        self.icon_provider = QFileIconProvider()
        self.tiles = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        add_button = QPushButton("Add Tile")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self.add_tile)
        header.addWidget(add_button)
        main_layout.addLayout(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.tiles_widget = QWidget()
        self.flow_layout = FlowLayout(self.tiles_widget, margin=0, spacing=16)
        self.tiles_widget.setLayout(self.flow_layout)

        self.scroll_area.setWidget(self.tiles_widget)
        main_layout.addWidget(self.scroll_area, 1)

        self.empty_label = QLabel("No tiles yet. Add your first shortcut to get started.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setObjectName("empty")
        main_layout.addWidget(self.empty_label)

        self.load_tiles()
        self.refresh_tiles()

    def load_tiles(self):
        self.tiles = load_tiles_file(DATA_FILE)

    def save_tiles(self):
        save_tiles_file(DATA_FILE, self.tiles)

    def add_tile(self):
        dialog = AddTileDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.tiles.append(dialog.values())
            self.save_tiles()
            self.refresh_tiles()

    def refresh_tiles(self):
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        for tile in self.tiles:
            tile_widget = TileWidget(
                tile,
                self.icon_provider,
                self.launch_tile,
                self.edit_tile,
                self.remove_tile,
            )
            self.flow_layout.addWidget(tile_widget)

        has_tiles = len(self.tiles) > 0
        self.empty_label.setVisible(not has_tiles)
        self.scroll_area.setVisible(has_tiles)

    def launch_tile(self, tile):
        path = tile.get("path")
        if not path:
            return
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            QMessageBox.warning(self, "Missing", f"Path not found: {path}")
            return

        try:
            self._open_target(path)
        except Exception as exc:
            QMessageBox.critical(self, "Launch failed", str(exc))

    def remove_tile(self, tile):
        name = tile.get("name", "this tile")
        message = f"Remove '{name}'?"
        result = QMessageBox.question(self, "Remove tile", message)
        if result != QMessageBox.Yes:
            return
        try:
            self.tiles.remove(tile)
        except ValueError:
            return
        self.save_tiles()
        self.refresh_tiles()

    def edit_tile(self, tile):
        dialog = AddTileDialog(self, defaults=tile)
        if dialog.exec() != QDialog.Accepted:
            return
        updated = dialog.values()
        tile.update(updated)
        self.save_tiles()
        self.refresh_tiles()

    def _open_target(self, path):
        method, payload = determine_launch(
            path,
            platform.system(),
            os.access(path, os.X_OK),
            os.path.isfile(path),
            sys.executable,
        )
        if method == "startfile":
            os.startfile(payload)
        else:
            subprocess.Popen(payload)


def apply_theme(app):
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor("#f5f2ec"))
    palette.setColor(QPalette.WindowText, QColor("#1f1f1f"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ButtonText, QColor("#1f1f1f"))
    palette.setColor(QPalette.Highlight, QColor("#b55a30"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QWidget {
            font-family: "Segoe UI", "SF Pro Text", "Helvetica Neue", sans-serif;
            font-size: 13px;
        }
        QLabel#title {
            font-size: 26px;
            font-weight: 600;
        }
        QLabel#empty {
            color: #5c5a56;
            font-size: 14px;
        }
        QScrollArea {
            border: none;
        }
        QFrame#tile {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ffffff, stop:1 #f1e7dc);
            border: 1px solid #e0d6c9;
            border-radius: 16px;
        }
        QLabel#tileTitle {
            font-size: 16px;
            font-weight: 600;
        }
        QLabel#tileDesc {
            color: #5c5a56;
        }
        QPushButton#tileButton {
            background: #1f1f1f;
            color: #ffffff;
            border-radius: 8px;
            padding: 6px 12px;
        }
        QPushButton#tileButton:hover {
            background: #3b3b3b;
        }
        QPushButton#tileRemoveButton {
            background: #ffffff;
            color: #1f1f1f;
            border: 1px solid #d2c9bc;
            border-radius: 8px;
            padding: 6px 12px;
        }
        QPushButton#tileRemoveButton:hover {
            background: #f0e8dd;
        }
        QPushButton#tileEditButton {
            background: #ffffff;
            color: #1f1f1f;
            border: 1px solid #d2c9bc;
            border-radius: 8px;
            padding: 6px 12px;
        }
        QPushButton#tileEditButton:hover {
            background: #f7f0e6;
        }
        QPushButton#primaryButton {
            background: #b55a30;
            color: #ffffff;
            border-radius: 10px;
            padding: 8px 16px;
            font-weight: 600;
        }
        QPushButton#primaryButton:hover {
            background: #a04f2a;
        }
        """
    )


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    window = AppBoard()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
