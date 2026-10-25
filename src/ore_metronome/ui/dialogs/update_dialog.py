from enum import Enum

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ore_metronome.domain.update import ReleaseInfo


class UpdateChoice(Enum):
    INSTALL = "install"
    LATER = "later"
    SKIP = "skip"


class UpdateDialog(QDialog):
    def __init__(
        self,
        current_version: str,
        release: ReleaseInfo,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("アップデートのお知らせ")
        self.setMinimumWidth(480)
        self.choice = UpdateChoice.LATER

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(f"新しいバージョン v{release.version} があります（現在 v{current_version}）。")
        )
        notes = QTextBrowser()
        notes.setMarkdown(release.notes or "リリースノートはありません。")
        notes.setOpenExternalLinks(True)
        layout.addWidget(notes)

        install = QPushButton("更新する")
        install.setDefault(True)
        later = QPushButton("後で")
        skip = QPushButton("この版をスキップ")
        install.clicked.connect(lambda: self._choose(UpdateChoice.INSTALL))
        later.clicked.connect(lambda: self._choose(UpdateChoice.LATER))
        skip.clicked.connect(lambda: self._choose(UpdateChoice.SKIP))

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(install)
        buttons.addWidget(later)
        buttons.addWidget(skip)
        layout.addLayout(buttons)

    def _choose(self, choice: UpdateChoice) -> None:
        self.choice = choice
        self.accept()
