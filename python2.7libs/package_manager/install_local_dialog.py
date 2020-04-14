try:
    from PyQt5.QtWidgets import *
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
except ImportError:
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *

import hou


class FolderField(QWidget):
    def __init__(self, content=''):
        super(FolderField, self).__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.edit = QLineEdit(content)
        layout.addWidget(self.edit)

        self.pick_folder_button = QPushButton()
        self.pick_folder_button.setToolTip('Pick location')
        self.pick_folder_button.setFixedSize(24, 24)
        self.pick_folder_button.setIcon(hou.qt.Icon('BUTTONS_chooser_folder', 16, 16))
        self.pick_folder_button.clicked.connect(self._pickLocation)
        layout.addWidget(self.pick_folder_button)

    def text(self):
        return self.edit.text()

    def path(self):
        return hou.expandString(self.edit.text())

    def _pickLocation(self):
        path = QFileDialog.getExistingDirectory(self, 'Package Folder', self.path())
        if path:
            path = path.replace('\\', '/')
            self.edit.setText(path)


class InstallFromFolderPathDialog(QDialog):
    def __init__(self, parent=None):
        super(InstallFromFolderPathDialog, self).__init__(parent)

        self.setWindowTitle('Install from Local Folder')
        self.resize(500, 50)

        # Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(4, 0, 0, 2)
        form_layout.setSpacing(4)
        main_layout.addLayout(form_layout)

        self.folder_path_field = FolderField()
        form_layout.addRow('Folder Path', self.folder_path_field)

        self.setup_scheme_combo = QComboBox()
        self.setup_scheme_combo.setDisabled(True)
        form_layout.addRow('Setup Scheme', self.setup_scheme_combo)

        buttons_layout = QHBoxLayout()
        main_layout.addLayout(buttons_layout)

        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Ignored)
        buttons_layout.addSpacerItem(spacer)

        ok_button = QPushButton('OK')
        ok_button.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_button)

        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

    @classmethod
    def getInstallationData(cls, parent=None):
        dialog = cls(parent)
        return dialog.exec_(), dialog.folder_path_field.text()
