"""Ventana principal de la aplicación.

Organiza las áreas de trabajo en pestañas (Equipos, Selección, Combate y
Cobertura), ofrece la barra de herramientas con acciones de equipo,
importación/exportación Showdown, selección de modo de combate y cambio de
tema.

Creado por RyLayn — https://github.com/RyLayn — © 2026 RyLayn.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import (
    APP_AUTHOR,
    APP_AUTHOR_URL,
    APP_COPYRIGHT,
    APP_NAME,
    APP_VERSION,
    MODE_DOUBLES,
    MODE_LABELS,
    MODE_SINGLES,
)
from app.services.database_service import DatabaseService
from app.services.search_service import SearchService
from app.services.sprite_service import SpriteService
from app.services.team_service import TeamService
from app.ui.themes.theme_manager import ThemeManager
from app.ui.widgets.battle_screen import BattleScreen
from app.ui.widgets.battle_tracker import BattleTracker
from app.services.battle_state import BattleState
from app.ui.widgets.coverage_panel import CoveragePanel
from app.ui.widgets.enemy_panel import EnemyPanel
from app.ui.widgets.pick_panel import PickPanel
from app.ui.widgets.team_builder import TeamBuilder
from app.utils.logger import get_logger
from app.utils.paths import icon_path

logger = get_logger(__name__)


class ShowdownDialog(QDialog):
    """Diálogo de texto para pegar/copiar equipos en formato Showdown."""

    def __init__(self, title: str, text: str = "", read_only: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(520, 460)
        layout = QVBoxLayout(self)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(text)
        self.editor.setReadOnly(read_only)
        layout.addWidget(self.editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self.editor.toPlainText()


class MainWindow(QMainWindow):
    """Ventana principal con pestañas y barra de herramientas."""

    def __init__(
        self,
        db: DatabaseService,
        team_service: TeamService,
        sprite_service: SpriteService,
        theme_manager: ThemeManager,
        mode: str = MODE_SINGLES,
    ) -> None:
        super().__init__()
        self._db = db
        self._teams = team_service
        self._sprites = sprite_service
        self._theme = theme_manager
        self._mode = mode
        self._db.set_language(getattr(theme_manager.settings, "language", "es"))

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1200, 800)
        if icon_path().exists():
            self.setWindowIcon(QIcon(str(icon_path())))

        self._pokemon_search = SearchService(db.all_pokemon_names())
        self._move_search = SearchService(db.all_move_names())
        self._item_search = SearchService(db.all_item_names())
        self._ability_search = SearchService(db.all_ability_names())

        self._battle_state = BattleState()

        self._build_tabs()
        self._build_toolbar()
        self.statusBar().showMessage(f"Modo: {MODE_LABELS[self._mode]}")
        self._battle_state.changed.connect(self.battle_screen.refresh)
        self._bind_teams()

    # --- Construcción ------------------------------------------------------

    def _build_tabs(self) -> None:
        self.tabs = QTabWidget()

        # Pestaña Equipos.
        teams_tab = QWidget()
        teams_layout = QHBoxLayout(teams_tab)
        teams_layout.setContentsMargins(4, 4, 4, 4)
        splitter = QSplitter(Qt.Horizontal)
        self.team_builder = TeamBuilder(
            self._db, self._sprites, self._pokemon_search,
            self._move_search, self._item_search, self._ability_search,
        )
        self.enemy_panel = EnemyPanel(self._db, self._sprites, self._pokemon_search)
        splitter.addWidget(self.team_builder)
        splitter.addWidget(self.enemy_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        teams_layout.addWidget(splitter)
        self.tabs.addTab(teams_tab, "Equipos")

        # Pestaña Selección.
        self.pick_panel = PickPanel(self._db, self._sprites, self._mode)
        pick_wrap = QWidget()
        pl = QVBoxLayout(pick_wrap)
        pl.setContentsMargins(8, 8, 8, 8)
        pl.addWidget(self.pick_panel)
        self.tabs.addTab(pick_wrap, "Selección")

        # Pestaña Combate.
        self.battle_screen = BattleScreen(self._db, self._sprites, self._mode,
                                          state=self._battle_state)
        battle_wrap = QWidget()
        bl = QVBoxLayout(battle_wrap)
        bl.setContentsMargins(8, 8, 8, 8)
        bl.addWidget(self.battle_screen)
        self.tabs.addTab(battle_wrap, "Combate")

        # Pestaña Marcador (estado en vivo: debilitados y derribos).
        self.battle_tracker = BattleTracker(self._db, self._sprites, self._battle_state)
        track_wrap = QWidget()
        tl = QVBoxLayout(track_wrap)
        tl.setContentsMargins(8, 8, 8, 8)
        tl.addWidget(self.battle_tracker)
        self.tabs.addTab(track_wrap, "Marcador")

        # Pestaña Cobertura.
        self.coverage_panel = CoveragePanel(self._db)
        cov_wrap = QWidget()
        cl = QVBoxLayout(cov_wrap)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.addWidget(self.coverage_panel)
        self.tabs.addTab(cov_wrap, "Cobertura")

        self.setCentralWidget(self.tabs)

        self.team_builder.teamChanged.connect(self._on_teams_changed)
        self.enemy_panel.teamChanged.connect(self._on_teams_changed)
        self.pick_panel.picksChanged.connect(self._on_picks_changed)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Acciones")
        toolbar.setMovable(False)

        # Selector de modo.
        toolbar.addWidget(QLabel("Modo: "))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(MODE_LABELS[MODE_SINGLES], MODE_SINGLES)
        self.mode_combo.addItem(MODE_LABELS[MODE_DOUBLES], MODE_DOUBLES)
        self.mode_combo.setCurrentIndex(0 if self._mode == MODE_SINGLES else 1)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_combo)
        toolbar.addWidget(self.mode_combo)
        toolbar.addSeparator()

        # Selector de idioma.
        toolbar.addWidget(QLabel("Idioma: "))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Español (España)", "es")
        self.lang_combo.addItem("Español (Latino)", "latam")
        current_lang = getattr(self._theme.settings, "language", "es")
        self.lang_combo.setCurrentIndex(1 if current_lang == "latam" else 0)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_combo)
        toolbar.addWidget(self.lang_combo)
        toolbar.addSeparator()

        def add(text: str, slot, tip: str = "") -> QAction:
            action = QAction(text, self)
            action.triggered.connect(slot)
            if tip:
                action.setToolTip(tip)
            toolbar.addAction(action)
            return action

        add("Nuevo", self._new_team, "Vaciar el equipo del usuario")
        add("Guardar", self._save_team, "Guardar el equipo del usuario")
        add("Cargar", self._load_team, "Cargar un equipo guardado")
        add("Duplicar", self._duplicate_team, "Duplicar el equipo del usuario")
        toolbar.addSeparator()
        add("Importar", self._import_showdown, "Importar desde formato Showdown")
        add("Exportar", self._export_showdown, "Exportar a formato Showdown")
        toolbar.addSeparator()
        add("Tema", self._toggle_theme, "Alternar tema claro/oscuro")
        toolbar.addSeparator()
        add("Acerca de", self._show_about, "Información y autoría")

        # Crédito de autoría permanente y clicable en el pie de la ventana.
        credit = QLabel(
            f'Creado por <a href="{APP_AUTHOR_URL}" '
            f'style="color:#ff5350;text-decoration:none;font-weight:700;">{APP_AUTHOR}</a>'
        )
        credit.setObjectName("Credit")
        credit.setTextFormat(Qt.RichText)
        credit.setOpenExternalLinks(True)
        credit.setToolTip(APP_AUTHOR_URL)
        self.statusBar().addPermanentWidget(credit)

    def _show_about(self) -> None:
        link = (f'<a href="{APP_AUTHOR_URL}" '
                f'style="color:#ff5350;font-weight:700;">{APP_AUTHOR}</a>')
        box = QMessageBox(self)
        box.setWindowTitle("Acerca de")
        box.setTextFormat(Qt.RichText)
        box.setText(
            f"<h3>{APP_NAME}</h3>"
            f"<p>Versión {APP_VERSION}</p>"
            f"<p>Asistente de combate Pokémon offline "
            f"(hasta Leyendas Z-A y Pokémon Champions).</p>"
            f"<p><b>Creado por {link}</b><br>"
            f"<span style='color:#8b9096'>{APP_AUTHOR_URL}</span></p>"
            f"<p style='color:#8b9096'>{APP_COPYRIGHT}. "
            f"Puedes modificarlo y ampliarlo conservando esta atribución.</p>"
        )
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

    # --- Vinculación de datos ---------------------------------------------

    def _bind_teams(self) -> None:
        self.team_builder.set_team(self._teams.user_team)
        self.enemy_panel.set_team(self._teams.enemy_team)
        self.pick_panel.set_teams(self._teams.user_team, self._teams.enemy_team)
        self.coverage_panel.set_team(self._teams.user_team)
        self.battle_screen.set_battle(self.pick_panel.picks(), self._teams.enemy_team)
        self.battle_tracker.set_teams(self._teams.user_team, self._teams.enemy_team)

    def _on_teams_changed(self) -> None:
        # Editar equipos en sitio: refrescar selección y análisis sin reiniciar.
        self.pick_panel.sync()
        self.coverage_panel.set_team(self._teams.user_team)

    def _on_picks_changed(self) -> None:
        self.battle_screen.set_battle(self.pick_panel.picks(), self._teams.enemy_team)

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if widget and widget.findChild(BattleScreen):
            self.battle_screen.refresh()
        elif widget and widget.findChild(CoveragePanel):
            self.coverage_panel.refresh()

    # --- Modo --------------------------------------------------------------

    def _on_mode_combo(self, _index: int) -> None:
        mode = self.mode_combo.currentData()
        self._apply_mode(mode)

    def _on_lang_combo(self, _index: int) -> None:
        lang = self.lang_combo.currentData()
        self._db.set_language(lang)
        self._theme.settings.language = lang
        self._theme.save_settings()
        # Las sugerencias pasan a mostrarse en el idioma elegido.
        self._pokemon_search.set_names(self._db.all_pokemon_names())
        self._move_search.set_names(self._db.all_move_names())
        self._item_search.set_names(self._db.all_item_names())
        self._ability_search.set_names(self._db.all_ability_names())
        # Refrescar nombres mostrados (habilidades, ranuras, combates).
        self._bind_teams()
        label = "Español (Latino)" if lang == "latam" else "Español (España)"
        self.statusBar().showMessage(f"Idioma: {label}")

    def _apply_mode(self, mode: str) -> None:
        self._mode = mode
        self.pick_panel.set_mode(mode)
        self.battle_screen.set_mode(mode)
        self._theme.settings.mode = mode
        self._theme.save_settings()
        self.statusBar().showMessage(f"Modo: {MODE_LABELS[mode]}")

    # --- Acciones de equipo ------------------------------------------------

    def _new_team(self) -> None:
        from app.models.team import Team

        self._teams.user_team = Team(name="Mi equipo")
        self._battle_state.reset()
        self._bind_teams()
        self.statusBar().showMessage("Equipo nuevo creado.")

    def _save_team(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Guardar equipo", "Nombre del equipo:",
            text=self._teams.user_team.name,
        )
        if not ok:
            return
        self._teams.user_team.name = name or "Mi equipo"
        try:
            self._teams.save(self._teams.user_team)
            self.statusBar().showMessage(f"Equipo «{name}» guardado.")
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {exc}")

    def _load_team(self) -> None:
        teams = self._teams.load_all()
        if not teams:
            QMessageBox.information(self, "Cargar equipo", "No hay equipos guardados.")
            return
        names = [f"{t.name}  ·  {t.team_id[:8]}" for t in teams]
        choice, ok = QInputDialog.getItem(
            self, "Cargar equipo", "Selecciona un equipo:", names, 0, False
        )
        if not ok:
            return
        selected = teams[names.index(choice)]
        if selected.is_enemy:
            self._teams.enemy_team = selected
        else:
            self._teams.user_team = selected
            self._battle_state.reset()
        self._bind_teams()
        self.statusBar().showMessage(f"Equipo «{selected.name}» cargado.")

    def _duplicate_team(self) -> None:
        try:
            clone = self._teams.duplicate(self._teams.user_team)
            self.statusBar().showMessage(f"Equipo duplicado como «{clone.name}».")
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"No se pudo duplicar: {exc}")

    # --- Showdown ----------------------------------------------------------

    def _import_showdown(self) -> None:
        as_enemy = (
            QMessageBox.question(
                self, "Importar Showdown",
                "¿Importar como equipo RIVAL?\n(No = equipo del usuario)",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            ) == QMessageBox.Yes
        )
        dialog = ShowdownDialog("Pegar equipo Showdown", parent=self)
        buttons = dialog.findChild(QDialogButtonBox)
        if buttons is not None:
            open_btn = buttons.addButton("Abrir archivo…", QDialogButtonBox.ActionRole)
            open_btn.clicked.connect(lambda: self._load_import_file(dialog))
        if dialog.exec() != QDialog.Accepted:
            return
        text = dialog.text().strip()
        if not text:
            return
        try:
            self._teams.import_showdown(text, as_enemy=as_enemy)
            self._battle_state.reset()
            self._bind_teams()
            self.statusBar().showMessage("Equipo importado desde Showdown.")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fallo al importar Showdown")
            QMessageBox.critical(self, "Error de importación", str(exc))

    def _load_import_file(self, dialog: "ShowdownDialog") -> None:
        path, _f = QFileDialog.getOpenFileName(
            self, "Abrir equipo", "", "Texto (*.txt);;Todos los archivos (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                dialog.editor.setPlainText(fh.read())
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"No se pudo abrir: {exc}")

    def _export_showdown(self) -> None:
        text = self._teams.export_showdown(self._teams.user_team)
        dialog = ShowdownDialog("Exportación Showdown", text=text, read_only=True, parent=self)
        # Botón extra para guardar a archivo.
        save_btn = dialog.findChild(QDialogButtonBox)
        if save_btn is not None:
            btn = save_btn.addButton("Guardar como…", QDialogButtonBox.ActionRole)
            btn.clicked.connect(lambda: self._save_export_to_file(text))
        dialog.exec()

    def _save_export_to_file(self, text: str) -> None:
        suggested = (self._teams.user_team.name or "equipo").replace(" ", "_") + ".txt"
        path, _filter = QFileDialog.getSaveFileName(
            self, "Guardar equipo", suggested, "Texto (*.txt);;Todos los archivos (*)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            self.statusBar().showMessage(f"Equipo exportado a {path}")
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {exc}")

    # --- Tema --------------------------------------------------------------

    def _toggle_theme(self) -> None:
        new_theme = self._theme.toggle()
        self.statusBar().showMessage(
            f"Tema: {'claro' if new_theme == 'light' else 'oscuro'}."
        )
