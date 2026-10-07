#!/usr/bin/env python3
"""
DCIM Sorter  ·  43 - 13/09/2026 à 22:30
Organise photos et vidéos par jour via données EXIF
"""

import sys
import os
import re
import json
import subprocess
import math
import logging
import traceback
import threading
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QSizeGrip, QGridLayout,
    QFileDialog, QDialog, QLineEdit, QComboBox, QMessageBox, QStackedWidget,
    QGraphicsOpacityEffect, QListWidget, QToolTip, QTabWidget,
    QCheckBox, QDateEdit, QProgressBar, QSpinBox, QListWidgetItem, QMenu
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, QRunnable, QThreadPool, QPropertyAnimation,
    QEasingCurve, pyqtSignal, pyqtProperty, QObject, QSettings, QRectF, QRect,
    QEvent, QDate, QSize
)
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QLinearGradient, QRadialGradient,
    QPen, QFont, QBrush, QPixmap, QIcon, QCursor, QFontMetrics
)

# ── Versioning ─────────────────────────────────────────────────────────────
VERSION      = 43
CREATED      = "13/09/2026 à 22:30"
APP_NAME     = "DCIM Sorter"
WINDOW_TITLE = f"{APP_NAME}  ·  {VERSION} - {CREATED}"

# ── Logging ─────────────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).parent / "log"
_LOG_DIR.mkdir(exist_ok=True)
_log_file = _LOG_DIR / f"{VERSION}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("photo_organiser")
log.info("Démarrage — version %s", VERSION)

# ── Defaults ───────────────────────────────────────────────────────────────
DEFAULT_ROOT = r"E:\Photos"
DEFAULT_PRIORITY  = "_Priority"
DEFAULT_EXIF = "exiftool.exe"
PHOTO_EXT    = {'.jpg', '.jpeg', '.png', '.arw', '.cr2', '.cr3'}
VIDEO_EXT    = {'.mp4', '.mov'}
PAGE_SIZE    = 15

# ── Themes ─────────────────────────────────────────────────────────────────
THEMES = {
    'cyberpunk': {
        'name': 'Cyberpunk',
        'bg':      [(5, 5, 16), (10, 5, 24)],
        'a1':      '#00d4ff', 'a2':   '#7b2fff',
        'text':    '#e0e0f0', 'dim':  '#505070',
        'prio':     '#ff6ec7',
        'ok':      '#00ff88', 'warn': '#ffaa00', 'err': '#ff4466',
        'panel':   (15, 15, 40, 215), 'border': (80, 80, 180, 70),
        'card_bg': (14, 15, 35, 255),
        'btn_bg': (10, 10, 22),
        'orbs': [
            (0.15, 0.25, 320, (0,   100, 255, 14)),
            (0.85, 0.75, 260, (120,   0, 255, 11)),
            (0.50, 0.05, 200, (0,   180, 255,  7)),
        ],
    },
    'premium': {
        'name': 'Premium Dark',
        'bg':      [(17, 20, 24), (13, 18, 24)],
        'a1':      '#5e9cf5', 'a2':   '#a78bfa',
        'text':    '#f0f0f4', 'dim':  '#5a5a6a',
        'prio':     '#f472b6',
        'ok':      '#34d399', 'warn': '#fbbf24', 'err': '#f87171',
        'panel':   (24, 28, 38, 220), 'border': (60, 65, 100, 75),
        'card_bg': (22, 25, 40, 255),
        'btn_bg': (17, 20, 35),
        'orbs': [
            (0.10, 0.20, 350, (94,  156, 245, 8)),
            (0.90, 0.80, 300, (167, 139, 250, 7)),
        ],
    },
    'sunset': {
        'name': 'Sunset',
        'bg':      [(13, 5, 16), (21, 8, 24)],
        'a1':      '#ff6b35', 'a2':   '#f7931e',
        'text':    '#ffe8d6', 'dim':  '#6b4a3a',
        'prio':     '#ff99cc',
        'ok':      '#7fff7f', 'warn': '#ffdd44', 'err': '#ff4444',
        'panel':   (30, 15, 20, 215), 'border': (180, 100, 50, 55),
        'card_bg': (28, 14, 20, 255),
        'btn_bg': (20, 10, 15),
        'orbs': [
            (0.20, 0.30, 300, (255, 100,  50, 10)),
            (0.80, 0.60, 250, (200,  50, 150,  8)),
        ],
    },
    'lumiere': {
        'name': 'Lumière',
        'bg':      [(232, 238, 252), (222, 230, 250)],
        'a1':      '#2563eb', 'a2':   '#7c3aed',
        'text':    '#1e1b4b', 'dim':  '#8b8faf',
        'prio':     '#be185d',
        'ok':      '#059669', 'warn': '#d97706', 'err': '#dc2626',
        'panel':   (255, 255, 255, 200), 'border': (99, 102, 241, 55),
        'card_bg': (255, 255, 255, 255),
        'btn_bg': (235, 240, 255),
        'orbs': [
            (0.15, 0.25, 380, (100, 140, 255, 22)),
            (0.85, 0.75, 320, (160, 100, 255, 16)),
        ],
    },
    'ocean': {
        'name': 'Océan',
        'bg':      [(5, 15, 30), (8, 20, 40)],
        'a1':      '#00b4d8', 'a2':   '#0077b6',
        'text':    '#caf0f8', 'dim':  '#4a7c8c',
        'prio':     '#48cae4',
        'ok':      '#52b788', 'warn': '#f4a261', 'err': '#e76f51',
        'panel':   (8, 20, 45, 215), 'border': (0, 150, 200, 60),
        'card_bg': (7, 18, 38, 255), 'btn_bg': (5, 15, 30),
        'orbs': [(0.3, 0.5, 350, (0, 150, 200, 12)), (0.8, 0.2, 280, (0, 80, 150, 9))],
    },
    'forest': {
        'name': 'Forêt',
        'bg':      [(4, 15, 8), (6, 20, 10)],
        'a1':      '#52b788', 'a2':   '#40916c',
        'text':    '#d8f3dc', 'dim':  '#3a6b4a',
        'prio':     '#95d5b2',
        'ok':      '#74c69d', 'warn': '#f4a261', 'err': '#e63946',
        'panel':   (8, 22, 12, 215), 'border': (50, 120, 70, 60),
        'card_bg': (6, 18, 9, 255), 'btn_bg': (4, 14, 7),
        'orbs': [(0.2, 0.3, 300, (40, 150, 80, 12)), (0.8, 0.7, 250, (20, 100, 50, 9))],
    },
    'rose': {
        'name': 'Rose',
        'bg':      [(20, 8, 16), (25, 8, 20)],
        'a1':      '#f72585', 'a2':   '#b5179e',
        'text':    '#ffe0f0', 'dim':  '#6b3050',
        'prio':     '#ff85b3',
        'ok':      '#52b788', 'warn': '#f4a261', 'err': '#ff4d6d',
        'panel':   (30, 10, 22, 215), 'border': (180, 30, 100, 60),
        'card_bg': (26, 8, 18, 255), 'btn_bg': (20, 6, 15),
        'orbs': [(0.3, 0.4, 320, (200, 30, 120, 12)), (0.7, 0.6, 260, (120, 0, 180, 9))],
    },
    'neon_green': {
        'name': 'Neon Vert',
        'bg':      [(4, 14, 4), (5, 16, 5)],
        'a1':      '#39ff14', 'a2':   '#7fff00',
        'text':    '#e0ffe0', 'dim':  '#3a5a3a',
        'prio':     '#a8ff78',
        'ok':      '#39ff14', 'warn': '#ffee00', 'err': '#ff1744',
        'panel':   (5, 18, 5, 215), 'border': (50, 200, 50, 60),
        'card_bg': (4, 14, 4, 255), 'btn_bg': (3, 12, 3),
        'orbs': [(0.3, 0.4, 300, (50, 200, 50, 12)), (0.7, 0.6, 250, (30, 150, 30, 9))],
    },
    'amber': {
        'name': 'Ambre',
        'bg':      [(18, 12, 2), (24, 16, 3)],
        'a1':      '#ffb700', 'a2':   '#ff8800',
        'text':    '#fff3cd', 'dim':  '#6b5020',
        'prio':     '#ffd60a',
        'ok':      '#52b788', 'warn': '#ffb700', 'err': '#e63946',
        'panel':   (25, 17, 4, 215), 'border': (180, 140, 20, 60),
        'card_bg': (20, 13, 3, 255), 'btn_bg': (16, 10, 2),
        'orbs': [(0.3, 0.4, 300, (200, 150, 20, 12)), (0.7, 0.6, 250, (150, 100, 10, 9))],
    },
    'arctic': {
        'name': 'Arctique',
        'bg':      [(230, 240, 252), (220, 235, 250)],
        'a1':      '#0ea5e9', 'a2':   '#38bdf8',
        'text':    '#0c1a2e', 'dim':  '#6b8aaa',
        'prio':     '#0284c7',
        'ok':      '#059669', 'warn': '#d97706', 'err': '#dc2626',
        'panel':   (255, 255, 255, 200), 'border': (14, 165, 233, 50),
        'card_bg': (248, 252, 255, 255), 'btn_bg': (228, 240, 252),
        'orbs': [(0.2, 0.3, 350, (50, 180, 240, 20)), (0.8, 0.7, 280, (30, 140, 220, 15))],
    },
    'cherry': {
        'name': 'Cerise',
        'bg':      [(18, 4, 6), (24, 5, 8)],
        'a1':      '#ff0a54', 'a2':   '#c9184a',
        'text':    '#ffe5ec', 'dim':  '#6b2030',
        'prio':     '#ff4d6d',
        'ok':      '#52b788', 'warn': '#f4a261', 'err': '#ff0a54',
        'panel':   (26, 5, 8, 215), 'border': (200, 20, 50, 60),
        'card_bg': (20, 4, 6, 255), 'btn_bg': (16, 3, 5),
        'orbs': [(0.3, 0.4, 300, (200, 20, 50, 12)), (0.7, 0.6, 250, (150, 10, 30, 9))],
    },
    'midnight': {
        'name': 'Minuit',
        'bg':      [(2, 4, 20), (3, 5, 25)],
        'a1':      '#4361ee', 'a2':   '#3a0ca3',
        'text':    '#e0e5ff', 'dim':  '#3a3f6b',
        'prio':     '#7b2d8b',
        'ok':      '#52b788', 'warn': '#f4a261', 'err': '#ef233c',
        'panel':   (5, 8, 30, 215), 'border': (50, 70, 180, 60),
        'card_bg': (4, 6, 22, 255), 'btn_bg': (2, 4, 18),
        'orbs': [(0.3, 0.4, 300, (50, 70, 200, 10)), (0.7, 0.6, 250, (30, 10, 150, 8))],
    },
    'plasma': {
        'name': 'Plasma',
        'bg':      [(12, 4, 20), (16, 5, 28)],
        'a1':      '#e040fb', 'a2':   '#aa00ff',
        'text':    '#f3e5f5', 'dim':  '#5a3a6b',
        'prio':     '#ff80ff',
        'ok':      '#69f0ae', 'warn': '#ffee58', 'err': '#ff5252',
        'panel':   (18, 5, 30, 215), 'border': (180, 40, 255, 60),
        'card_bg': (14, 4, 22, 255), 'btn_bg': (10, 3, 18),
        'orbs': [(0.3, 0.4, 320, (180, 40, 255, 12)), (0.7, 0.6, 260, (100, 0, 200, 9))],
    },
    'earth': {
        'name': 'Terre',
        'bg':      [(20, 12, 6), (26, 14, 7)],
        'a1':      '#c77c37', 'a2':   '#a0522d',
        'text':    '#fdf0e0', 'dim':  '#6b4a30',
        'prio':     '#dda15e',
        'ok':      '#606c38', 'warn': '#dda15e', 'err': '#bc4749',
        'panel':   (28, 15, 8, 215), 'border': (150, 100, 50, 60),
        'card_bg': (22, 12, 6, 255), 'btn_bg': (18, 10, 5),
        'orbs': [(0.3, 0.4, 300, (160, 100, 40, 12)), (0.7, 0.6, 250, (120, 60, 20, 9))],
    },
    'matrix': {
        'name': 'Matrix',
        'bg':      [(0, 8, 0), (0, 10, 0)],
        'a1':      '#00ff41', 'a2':   '#008f11',
        'text':    '#00ff41', 'dim':  '#1a5c20',
        'prio':     '#00e676',
        'ok':      '#00ff41', 'warn': '#ffff00', 'err': '#ff1744',
        'panel':   (0, 10, 0, 215), 'border': (0, 180, 0, 60),
        'card_bg': (0, 8, 0, 255), 'btn_bg': (0, 6, 0),
        'orbs': [(0.3, 0.4, 300, (0, 180, 0, 12)), (0.7, 0.6, 250, (0, 120, 0, 9))],
    },
    'ice': {
        'name': 'Glace',
        'bg':      [(235, 242, 248), (228, 237, 246)],
        'a1':      '#64b5f6', 'a2':   '#90caf9',
        'text':    '#1a2433', 'dim':  '#7a9ab8',
        'prio':     '#42a5f5',
        'ok':      '#4caf50', 'warn': '#ff9800', 'err': '#f44336',
        'panel':   (255, 255, 255, 210), 'border': (100, 181, 246, 55),
        'card_bg': (248, 252, 255, 255), 'btn_bg': (225, 238, 250),
        'orbs': [(0.2, 0.3, 350, (100, 181, 246, 20)), (0.8, 0.7, 280, (144, 202, 249, 15))],
    },
    'volcano': {
        'name': 'Volcan',
        'bg':      [(18, 4, 0), (24, 6, 0)],
        'a1':      '#ff5722', 'a2':   '#ff1744',
        'text':    '#fbe9e7', 'dim':  '#6b2c18',
        'prio':     '#ff8a65',
        'ok':      '#69f0ae', 'warn': '#ffee58', 'err': '#ff1744',
        'panel':   (26, 5, 0, 215), 'border': (200, 60, 0, 60),
        'card_bg': (20, 4, 0, 255), 'btn_bg': (16, 3, 0),
        'orbs': [(0.3, 0.4, 300, (200, 60, 0, 14)), (0.7, 0.6, 250, (150, 20, 0, 10))],
    },
    'galaxy': {
        'name': 'Galaxie',
        'bg':      [(5, 3, 18), (8, 4, 24)],
        'a1':      '#7c4dff', 'a2':   '#448aff',
        'text':    '#e8eaf6', 'dim':  '#4a4a7a',
        'prio':     '#e040fb',
        'ok':      '#69f0ae', 'warn': '#ffee58', 'err': '#ff5252',
        'panel':   (10, 5, 26, 215), 'border': (100, 60, 200, 60),
        'card_bg': (7, 4, 20, 255), 'btn_bg': (5, 3, 16),
        'orbs': [(0.3, 0.4, 350, (100, 60, 220, 12)), (0.7, 0.6, 280, (60, 30, 180, 9))],
    },
    'mint': {
        'name': 'Menthe',
        'bg':      [(5, 18, 16), (6, 22, 20)],
        'a1':      '#64ffda', 'a2':   '#1de9b6',
        'text':    '#e0f7f4', 'dim':  '#3a6b60',
        'prio':     '#a7ffeb',
        'ok':      '#64ffda', 'warn': '#f4a261', 'err': '#ff5252',
        'panel':   (7, 22, 20, 215), 'border': (50, 200, 180, 60),
        'card_bg': (5, 18, 16, 255), 'btn_bg': (4, 14, 12),
        'orbs': [(0.3, 0.4, 300, (50, 200, 180, 12)), (0.7, 0.6, 250, (30, 150, 130, 9))],
    },
    'coral': {
        'name': 'Corail',
        'bg':      [(22, 8, 5), (28, 10, 6)],
        'a1':      '#ff6b6b', 'a2':   '#ff8e53',
        'text':    '#fff0ee', 'dim':  '#6b3a30',
        'prio':     '#ffa0a0',
        'ok':      '#52b788', 'warn': '#ffb700', 'err': '#ff0a54',
        'panel':   (30, 10, 7, 215), 'border': (200, 90, 70, 60),
        'card_bg': (24, 8, 5, 255), 'btn_bg': (18, 6, 4),
        'orbs': [(0.3, 0.4, 300, (200, 90, 60, 12)), (0.7, 0.6, 250, (150, 50, 30, 9))],
    },
    'sakura': {
        'name': 'Sakura',
        'bg':      [(252, 238, 244), (248, 230, 240)],
        'a1':      '#e91e8c', 'a2':   '#c2185b',
        'text':    '#2d1a26', 'dim':  '#9a7080',
        'prio':     '#c2185b',
        'ok':      '#43a047', 'warn': '#fb8c00', 'err': '#e53935',
        'panel':   (255, 248, 252, 210), 'border': (233, 30, 140, 50),
        'card_bg': (255, 248, 252, 255), 'btn_bg': (248, 225, 238),
        'orbs': [(0.2, 0.3, 350, (233, 100, 180, 22)), (0.8, 0.7, 280, (180, 50, 120, 16))],
    },
    'slate': {
        'name': 'Ardoise',
        'bg':      [(18, 20, 24), (22, 24, 28)],
        'a1':      '#90a4ae', 'a2':   '#607d8b',
        'text':    '#eceff1', 'dim':  '#546e7a',
        'prio':     '#b0bec5',
        'ok':      '#a5d6a7', 'warn': '#ffe082', 'err': '#ef9a9a',
        'panel':   (24, 28, 34, 220), 'border': (80, 100, 120, 65),
        'card_bg': (20, 24, 30, 255), 'btn_bg': (16, 18, 22),
        'orbs': [(0.3, 0.4, 300, (80, 100, 140, 8)), (0.7, 0.6, 250, (60, 80, 110, 6))],
    },
    'copper': {
        'name': 'Cuivre',
        'bg':      [(20, 10, 4), (26, 13, 5)],
        'a1':      '#b87333', 'a2':   '#cd7f32',
        'text':    '#fdf4ec', 'dim':  '#6b4a28',
        'prio':     '#daa520',
        'ok':      '#52b788', 'warn': '#daa520', 'err': '#dc143c',
        'panel':   (28, 13, 5, 215), 'border': (160, 100, 40, 60),
        'card_bg': (22, 10, 4, 255), 'btn_bg': (18, 8, 3),
        'orbs': [(0.3, 0.4, 300, (160, 100, 40, 12)), (0.7, 0.6, 250, (120, 60, 20, 9))],
    },
    'vapor': {
        'name': 'Vaporwave',
        'bg':      [(10, 4, 20), (14, 4, 26)],
        'a1':      '#ff71ce', 'a2':   '#01cdfe',
        'text':    '#ffe4f5', 'dim':  '#5a3060',
        'prio':     '#b967ff',
        'ok':      '#05ffa1', 'warn': '#fffb96', 'err': '#ff6b97',
        'panel':   (15, 5, 28, 215), 'border': (200, 80, 200, 60),
        'card_bg': (12, 4, 22, 255), 'btn_bg': (9, 3, 18),
        'orbs': [(0.3, 0.4, 320, (200, 80, 200, 12)), (0.7, 0.6, 260, (1, 180, 220, 10))],
    },
    'coffee': {
        'name': 'Café',
        'bg':      [(16, 10, 6), (20, 13, 7)],
        'a1':      '#c8a96e', 'a2':   '#a0785a',
        'text':    '#f5f0e8', 'dim':  '#6b5040',
        'prio':     '#d4a96e',
        'ok':      '#81b29a', 'warn': '#e9c46a', 'err': '#e76f51',
        'panel':   (22, 13, 8, 215), 'border': (140, 100, 60, 60),
        'card_bg': (18, 11, 6, 255), 'btn_bg': (14, 8, 5),
        'orbs': [(0.3, 0.4, 300, (140, 100, 50, 12)), (0.7, 0.6, 250, (100, 60, 30, 9))],
    },
    'jade': {
        'name': 'Jade',
        'bg':      [(4, 16, 12), (5, 20, 15)],
        'a1':      '#00b4a0', 'a2':   '#007d6e',
        'text':    '#e0f5f2', 'dim':  '#306b5a',
        'prio':     '#64d8cb',
        'ok':      '#52b788', 'warn': '#f4a261', 'err': '#e63946',
        'panel':   (6, 20, 15, 215), 'border': (0, 150, 120, 60),
        'card_bg': (4, 16, 12, 255), 'btn_bg': (3, 13, 10),
        'orbs': [(0.3, 0.4, 300, (0, 150, 120, 12)), (0.7, 0.6, 250, (0, 100, 80, 9))],
    },
    'indigo': {
        'name': 'Indigo',
        'bg':      [(8, 6, 22), (10, 8, 28)],
        'a1':      '#5c6bc0', 'a2':   '#3949ab',
        'text':    '#e8eaf6', 'dim':  '#3c3f70',
        'prio':     '#9fa8da',
        'ok':      '#80cbc4', 'warn': '#ffee58', 'err': '#ef5350',
        'panel':   (12, 10, 32, 215), 'border': (80, 90, 200, 60),
        'card_bg': (9, 7, 24, 255), 'btn_bg': (7, 5, 20),
        'orbs': [(0.3, 0.4, 300, (80, 90, 200, 12)), (0.7, 0.6, 250, (50, 60, 160, 9))],
    },
    'crimson': {
        'name': 'Cramoisi',
        'bg':      [(16, 3, 6), (20, 4, 8)],
        'a1':      '#dc143c', 'a2':   '#8b0000',
        'text':    '#ffe4e8', 'dim':  '#5a1a22',
        'prio':     '#ff6b8a',
        'ok':      '#52b788', 'warn': '#f4a261', 'err': '#dc143c',
        'panel':   (22, 4, 8, 215), 'border': (180, 20, 40, 60),
        'card_bg': (18, 3, 6, 255), 'btn_bg': (14, 2, 5),
        'orbs': [(0.3, 0.4, 300, (180, 20, 40, 12)), (0.7, 0.6, 250, (120, 10, 20, 9))],
    },
    'dusk': {
        'name': 'Crépuscule',
        'bg':      [(14, 8, 22), (18, 10, 28)],
        'a1':      '#9b59b6', 'a2':   '#6c3483',
        'text':    '#f3e5f5', 'dim':  '#5a3a70',
        'prio':     '#ce93d8',
        'ok':      '#a8e6cf', 'warn': '#ffe082', 'err': '#ef5350',
        'panel':   (20, 10, 30, 215), 'border': (130, 70, 180, 60),
        'card_bg': (16, 8, 24, 255), 'btn_bg': (12, 6, 20),
        'orbs': [(0.3, 0.4, 320, (130, 70, 200, 12)), (0.7, 0.6, 260, (80, 30, 140, 9))],
    },
    'spring': {
        'name': 'Printemps',
        'bg':      [(236, 250, 238), (228, 246, 230)],
        'a1':      '#2e7d32', 'a2':   '#43a047',
        'text':    '#1a2f1a', 'dim':  '#7a9a7a',
        'prio':     '#1b5e20',
        'ok':      '#2e7d32', 'warn': '#f57f17', 'err': '#c62828',
        'panel':   (255, 255, 255, 205), 'border': (76, 175, 80, 55),
        'card_bg': (248, 255, 248, 255), 'btn_bg': (228, 248, 228),
        'orbs': [(0.2, 0.3, 350, (76, 200, 80, 22)), (0.8, 0.7, 280, (50, 180, 60, 15))],
    },
    'neon_pink': {
        'name': 'Neon Rose',
        'bg':      [(16, 4, 14), (20, 5, 18)],
        'a1':      '#ff0090', 'a2':   '#ff69b4',
        'text':    '#ffe0f0', 'dim':  '#6b1a50',
        'prio':     '#ff69b4',
        'ok':      '#39ff14', 'warn': '#ffee00', 'err': '#ff1744',
        'panel':   (22, 5, 20, 215), 'border': (220, 0, 130, 60),
        'card_bg': (18, 4, 16, 255), 'btn_bg': (14, 3, 12),
        'orbs': [(0.3, 0.4, 320, (220, 0, 140, 12)), (0.7, 0.6, 260, (160, 0, 100, 9))],
    },
    'cobalt': {
        'name': 'Cobalt',
        'bg':      [(4, 8, 22), (5, 10, 28)],
        'a1':      '#4169e1', 'a2':   '#0047ab',
        'text':    '#e8f0ff', 'dim':  '#304080',
        'prio':     '#6495ed',
        'ok':      '#52b788', 'warn': '#f4a261', 'err': '#e63946',
        'panel':   (6, 10, 30, 215), 'border': (40, 80, 200, 60),
        'card_bg': (4, 8, 24, 255), 'btn_bg': (3, 6, 20),
        'orbs': [(0.3, 0.4, 300, (40, 80, 200, 12)), (0.7, 0.6, 250, (20, 50, 160, 9))],
    },
    'lemon': {
        'name': 'Citron',
        'bg':      [(14, 16, 4), (18, 20, 5)],
        'a1':      '#ffd600', 'a2':   '#aeea00',
        'text':    '#fffff0', 'dim':  '#5a5a20',
        'prio':     '#ffff00',
        'ok':      '#aeea00', 'warn': '#ffd600', 'err': '#ff1744',
        'panel':   (18, 20, 5, 215), 'border': (200, 200, 0, 60),
        'card_bg': (14, 16, 4, 255), 'btn_bg': (12, 14, 3),
        'orbs': [(0.3, 0.4, 300, (200, 200, 0, 12)), (0.7, 0.6, 250, (150, 180, 0, 9))],
    },
    'titanium': {
        'name': 'Titane',
        'bg':      [(16, 18, 20), (20, 22, 24)],
        'a1':      '#bdbdbd', 'a2':   '#9e9e9e',
        'text':    '#fafafa', 'dim':  '#5a5a5a',
        'prio':     '#e0e0e0',
        'ok':      '#80cbc4', 'warn': '#ffee58', 'err': '#ef5350',
        'panel':   (22, 24, 27, 220), 'border': (130, 140, 150, 65),
        'card_bg': (18, 20, 23, 255), 'btn_bg': (14, 16, 18),
        'orbs': [(0.3, 0.4, 300, (130, 140, 160, 8)), (0.7, 0.6, 250, (100, 110, 130, 6))],
    },
    'burgundy': {
        'name': 'Bourgogne',
        'bg':      [(16, 5, 8), (20, 6, 10)],
        'a1':      '#a0002a', 'a2':   '#800020',
        'text':    '#f8e8ec', 'dim':  '#5a2030',
        'prio':     '#c04060',
        'ok':      '#52b788', 'warn': '#f4a261', 'err': '#dc143c',
        'panel':   (22, 6, 10, 215), 'border': (140, 20, 40, 60),
        'card_bg': (18, 5, 8, 255), 'btn_bg': (14, 4, 6),
        'orbs': [(0.3, 0.4, 300, (140, 20, 40, 12)), (0.7, 0.6, 250, (100, 10, 25, 9))],
    },
    'teal': {
        'name': 'Sarcelle',
        'bg':      [(4, 16, 18), (5, 20, 22)],
        'a1':      '#00bcd4', 'a2':   '#0097a7',
        'text':    '#e0f7fa', 'dim':  '#30606a',
        'prio':     '#4dd0e1',
        'ok':      '#52b788', 'warn': '#f4a261', 'err': '#e63946',
        'panel':   (6, 20, 24, 215), 'border': (0, 160, 180, 60),
        'card_bg': (4, 16, 20, 255), 'btn_bg': (3, 13, 15),
        'orbs': [(0.3, 0.4, 300, (0, 160, 180, 12)), (0.7, 0.6, 250, (0, 120, 140, 9))],
    },
    'lavender': {
        'name': 'Lavande',
        'bg':      [(240, 234, 252), (234, 226, 250)],
        'a1':      '#7c3aed', 'a2':   '#6d28d9',
        'text':    '#2e1a47', 'dim':  '#9a86c0',
        'prio':     '#5b21b6',
        'ok':      '#059669', 'warn': '#d97706', 'err': '#dc2626',
        'panel':   (255, 252, 255, 210), 'border': (124, 58, 237, 50),
        'card_bg': (252, 248, 255, 255), 'btn_bg': (232, 220, 255),
        'orbs': [(0.2, 0.3, 350, (150, 100, 240, 22)), (0.8, 0.7, 280, (120, 80, 200, 15))],
    },
    'noir': {
        'name': 'Noir',
        'bg':      [(5, 5, 5), (8, 8, 8)],
        'a1':      '#ffffff', 'a2':   '#aaaaaa',
        'text':    '#ffffff', 'dim':  '#555555',
        'prio':     '#cccccc',
        'ok':      '#00e676', 'warn': '#ffea00', 'err': '#ff1744',
        'panel':   (12, 12, 12, 220), 'border': (80, 80, 80, 60),
        'card_bg': (8, 8, 8, 255), 'btn_bg': (5, 5, 5),
        'orbs': [(0.3, 0.4, 300, (50, 50, 50, 8)), (0.7, 0.6, 250, (30, 30, 30, 6))],
    },
    'saffron': {
        'name': 'Safran',
        'bg':      [(20, 10, 3), (26, 13, 4)],
        'a1':      '#ff9800', 'a2':   '#ff6f00',
        'text':    '#fff8e1', 'dim':  '#6b4418',
        'prio':     '#ffcc80',
        'ok':      '#aed581', 'warn': '#ff9800', 'err': '#e53935',
        'panel':   (28, 13, 4, 215), 'border': (200, 130, 0, 60),
        'card_bg': (22, 10, 3, 255), 'btn_bg': (18, 8, 2),
        'orbs': [(0.3, 0.4, 300, (200, 130, 0, 12)), (0.7, 0.6, 250, (150, 80, 0, 9))],
    },
    'aurora': {
        'name': 'Aurore',
        'bg':      [(4, 16, 14), (6, 20, 18)],
        'a1':      '#00ff88', 'a2':   '#7b2fff',
        'text':    '#e0fff8', 'dim':  '#2a6b5a',
        'prio':     '#80ffdf',
        'ok':      '#00ff88', 'warn': '#ffaa00', 'err': '#ff4466',
        'panel':   (6, 20, 18, 215), 'border': (0, 200, 150, 55),
        'card_bg': (4, 16, 14, 255), 'btn_bg': (3, 13, 11),
        'orbs': [(0.3, 0.4, 350, (0, 200, 150, 12)), (0.7, 0.6, 280, (100, 40, 220, 10))],
    },
}

_theme_key = 'cyberpunk'

def T() -> dict:
    return THEMES[_theme_key]


# ── Theme Signal ───────────────────────────────────────────────────────────
class _ThemeSignals(QObject):
    changed = pyqtSignal()

theme_sig = _ThemeSignals()


# ── Settings ───────────────────────────────────────────────────────────────
_settings: QSettings | None = None

def _s() -> QSettings:
    global _settings
    if _settings is None:
        _settings = QSettings("PhotoOrganiser", "PhotoOrganiser")
    return _settings

def get_root():  return _s().value("root",  DEFAULT_ROOT)
def get_exif():  return _s().value("exif",  DEFAULT_EXIF)
def get_theme(): return _s().value("theme", "cyberpunk")
def set_root(v): _s().setValue("root",  v)
def set_exif(v): _s().setValue("exif",  v)
def set_theme(v):_s().setValue("theme", v)

def get_prios() -> list[str]:
    """Retourne la liste des noms de sous-dossiers prioritaires."""
    raw = _s().value("evas", None)
    if raw is None:
        # Rétrocompatibilité : ancienne clé "prio" (valeur unique)
        old = _s().value("eva", DEFAULT_PRIORITY)
        return [old] if old else [DEFAULT_PRIORITY]
    return [s.strip() for s in raw.split("||") if s.strip()]

def set_prios(lst: list[str]):
    _s().setValue("evas", "||".join(lst))

def get_extra_formats() -> list[str]:
    """Extensions ajoutées par l'utilisateur (sans les défauts)."""
    raw = _s().value("extra_formats", "")
    return [s.strip() for s in raw.split("||") if s.strip()]

def set_extra_formats(lst: list[str]):
    _s().setValue("extra_formats", "||".join(lst))

def get_all_ext() -> set[str]:
    """Toutes les extensions reconnues (défauts + extras utilisateur)."""
    extra = {'.' + e.lstrip('.').lower() for e in get_extra_formats()}
    return PHOTO_EXT | VIDEO_EXT | extra

DEFAULT_USB_TARGET = r"E:\Photos"

def get_mtp_move_support(device: str) -> str:
    """'yes' / 'no' / '' (inconnu) — appris lors du premier Copier + Déplacer."""
    return _s().value(f"mtp_move/{device}", "")


def set_mtp_move_support(device: str, v: str):
    _s().setValue(f"mtp_move/{device}", v)


def get_usb_target(): return _s().value("usb_target", DEFAULT_USB_TARGET)
def set_usb_target(v): _s().setValue("usb_target", v)

DEFAULT_USB_TIMEOUT  = 10   # secondes
DEFAULT_USB_WORKERS  = min(8, max(1, os.cpu_count() or 4))

def get_usb_timeout() -> int:
    return int(_s().value("usb_scan_timeout", DEFAULT_USB_TIMEOUT))
def set_usb_timeout(v: int): _s().setValue("usb_scan_timeout", v)

def get_usb_workers() -> int:
    return int(_s().value("usb_copy_workers", DEFAULT_USB_WORKERS))
def set_usb_workers(v: int): _s().setValue("usb_copy_workers", v)


def _fmt_bytes(n: int) -> str:
    if n >= 1_073_741_824:
        return f"{n / 1_073_741_824:.1f} Go"
    if n >= 1_048_576:
        return f"{n / 1_048_576:.0f} Mo"
    if n >= 1024:
        return f"{n / 1024:.0f} Ko"
    return f"{n} o"


def find_usb_dcim() -> tuple[str, str] | None:
    """Retourne (lettre_lecteur, chemin_DCIM) si une clé USB avec DCIM est trouvée."""
    try:
        import ctypes
        DRIVE_REMOVABLE = 2
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            try:
                if ctypes.windll.kernel32.GetDriveTypeW(drive) == DRIVE_REMOVABLE:
                    dcim = os.path.join(drive, "DCIM")
                    if os.path.isdir(dcim):
                        log.info("Clé USB DCIM trouvée : %s", dcim)
                        return (drive, dcim)
            except Exception as e:
                log.debug("find_usb_dcim lettre %s : %s", letter, e)
    except Exception:
        log.exception("find_usb_dcim exception inattendue")
    return None


# Noms de racines de stockage MTP (indice pour la descente récursive)
_MTP_STORAGE_HINTS = (
    "internal storage", "internal", "phone", "mémoire", "memoire",
    "stockage", "storage", "interne", "sd card", "carte sd", "sdcard",
)


def _mtp_is_drive(dev_item) -> bool:
    """True si l'item « Ce PC » est un lecteur classique (C:, E:, …)."""
    try:
        path = dev_item.Path or ""
    except Exception:
        return False
    # Un appareil MTP a un chemin shell « ::{GUID}\… » : path[1] vaut aussi
    # « : », d'où le test explicite sur la lettre de lecteur.
    return (len(path) >= 3 and path[0].isalpha()
            and path[1] == ":" and path[2] in ("\\", "/"))


def _mtp_this_pc():
    """NameSpace « Ce PC » (thread COM déjà initialisé)."""
    import win32com.client
    shell = win32com.client.Dispatch("Shell.Application")
    return shell.NameSpace(17)


def _mtp_devices() -> list:
    """Items « téléphone / appareil photo » branchés en MTP, hors lecteurs."""
    this_pc = _mtp_this_pc()
    if this_pc is None:
        return []
    devices = []
    for dev_item in this_pc.Items():
        if not dev_item.IsFolder or _mtp_is_drive(dev_item):
            continue
        try:
            if dev_item.GetFolder is None:
                continue
        except Exception:
            continue
        devices.append(dev_item)
    return devices


def _mtp_child(item, name: str):
    """Sous-dossier nommé `name` (comparaison insensible à la casse)."""
    low = name.lower()
    try:
        for sub in item.GetFolder.Items():
            if sub.IsFolder and sub.Name.lower() == low:
                return sub
    except Exception:
        pass
    return None


def _mtp_resolve_path(parts: list[str]):
    """Résout un chemin MTP [appareil, racine, dossier, …] en FolderItem.

    Doit être appelé depuis un thread COM initialisé (CoInitialize).
    """
    if not parts:
        return None
    dev_low = parts[0].lower()
    for dev_item in _mtp_devices():
        if dev_item.Name.lower() != dev_low:
            continue
        item = dev_item
        for name in parts[1:]:
            item = _mtp_child(item, name)
            if item is None:
                return None
        return item
    return None


def _mtp_find_dcim_paths(item, base: list[str], depth: int = 0,
                         out: list | None = None) -> list:
    """Collecte les chemins des dossiers DCIM sous une racine de stockage.

    Un téléphone expose plusieurs racines (mémoire interne, carte SD) et
    chacune peut contenir un DCIM — souvent vide côté carte SD.
    """
    if out is None:
        out = []
    if depth > 3 or not item.IsFolder:
        return out
    name  = item.Name
    parts = base + [name]
    if name.lower() == "dcim":
        out.append(parts)
        return out
    # depth 0 = racine de stockage : on descend quel que soit son nom
    # (« Mémoire de stockage interne », « Carte SD », « Internal shared storage »…)
    if depth == 0 or any(h in name.lower() for h in _MTP_STORAGE_HINTS):
        try:
            folder = item.GetFolder
            if folder:
                for sub in folder.Items():
                    _mtp_find_dcim_paths(sub, parts, depth + 1, out)
        except Exception:
            pass
    return out


def _mtp_dcim_paths() -> list[list[str]]:
    """Chemins de tous les DCIM de tous les appareils MTP connectés."""
    paths: list[list[str]] = []
    for dev_item in _mtp_devices():
        try:
            for root_item in dev_item.GetFolder.Items():
                _mtp_find_dcim_paths(root_item, [dev_item.Name], 0, paths)
        except Exception:
            continue
    return paths


def _mtp_item_count(item) -> int:
    """Nombre d'éléments d'un dossier MTP (appel COM unique, rapide)."""
    try:
        return int(item.GetFolder.Items().Count)
    except Exception:
        return 0


def _mtp_default_path(subdir: str = 'Camera') -> list[str] | None:
    """Chemin du DCIM/<subdir> le plus fourni (une carte SD vide ne gagne pas).

    Retombe sur le DCIM lui-même si aucun sous-dossier <subdir> n'existe.
    """
    subdir_low = subdir.lower()
    best, best_count = None, -1
    fallback = None
    for dcim_parts in _mtp_dcim_paths():
        dcim = _mtp_resolve_path(dcim_parts)
        if dcim is None:
            continue
        if fallback is None:
            fallback = dcim_parts
        try:
            subs = list(dcim.GetFolder.Items())
        except Exception:
            continue
        for sub in subs:
            if not sub.IsFolder or sub.Name.lower() != subdir_low:
                continue
            count = _mtp_item_count(sub)
            if count > best_count:
                best, best_count = dcim_parts + [sub.Name], count
    if best is not None:
        log.debug("Dossier MTP retenu : %s (%d éléments)",
                  "/".join(best[1:]), best_count)
        return best
    return fallback


def _mtp_children(parts: list[str]) -> list[dict]:
    """Sous-dossiers d'un chemin MTP : [{'name', 'parts', 'items'}, …].

    `parts` vide = racines de stockage de chaque appareil connecté.
    """
    out: list[dict] = []
    if not parts:
        for dev_item in _mtp_devices():
            try:
                for root_item in dev_item.GetFolder.Items():
                    if root_item.IsFolder:
                        out.append({'name':  root_item.Name,
                                    'parts': [dev_item.Name, root_item.Name],
                                    'items': _mtp_item_count(root_item)})
            except Exception:
                continue
        return out
    item = _mtp_resolve_path(parts)
    if item is None:
        return out
    try:
        for sub in item.GetFolder.Items():
            if sub.IsFolder:
                out.append({'name':  sub.Name,
                            'parts': parts + [sub.Name],
                            'items': _mtp_item_count(sub)})
    except Exception:
        pass
    return out


def _mtp_media_names(parts: list[str], stop=None, on_progress=None) -> list[str]:
    """Noms des photos/vidéos contenues directement dans un dossier MTP."""
    item = _mtp_resolve_path(parts)
    if item is None:
        return []
    all_ext = get_all_ext()
    found: list[str] = []
    try:
        for sub in item.GetFolder.Items():
            if stop is not None and stop():
                break
            if not sub.IsFolder and Path(sub.Name).suffix.lower() in all_ext:
                found.append(sub.Name)
                if on_progress is not None:
                    on_progress(len(found))
    except Exception:
        log.exception("_mtp_media_names %s", parts)
    return found


def _mtp_path_label(parts: list[str], full: bool = False) -> str:
    """Libellé lisible d'un chemin MTP : « DCIM › Camera »."""
    if not parts:
        return ""
    names = list(parts) if full else parts[1:]
    if not names:
        return parts[0]
    if not full and len(names) > 2:
        names = names[-2:]
    return "  ›  ".join(names)


def _mtp_shell_item(automation_obj):
    """IShellItem depuis un objet Shell Automation (FolderItem / Folder).

    Les chemins d'analyse MTP (« ::{GUID}\… ») sont refusés par
    SHCreateItemFromParsingName ; on passe donc par le PIDL de l'objet.
    """
    from win32com.shell import shell
    pidl = shell.SHGetIDListFromObject(automation_obj._oleobj_)
    return shell.SHCreateItemFromIDList(pidl, shell.IID_IShellItem)


def _mtp_new_fileop():
    """IFileOperation configuré sans aucune interface ni confirmation.

    Contrairement à CopyHere / InvokeVerbEx("delete"), aucune fenêtre de
    progression ne flashe et Windows ne demande pas de confirmation par
    fichier. Doit être appelé depuis un thread COM initialisé.
    """
    import pythoncom
    from win32com.shell import shell, shellcon
    fo = pythoncom.CoCreateInstance(
        shell.CLSID_FileOperation, None,
        pythoncom.CLSCTX_ALL, shell.IID_IFileOperation)
    fo.SetOperationFlags(
        shellcon.FOF_SILENT | shellcon.FOF_NOCONFIRMATION |
        shellcon.FOF_NOERRORUI | shellcon.FOF_NOCONFIRMMKDIR)
    return fo


def _mtp_ensure_child_folder(parts: list[str], name: str):
    """FolderItem du sous-dossier `name` de `parts`, créé s'il n'existe pas.
    Doit être appelé depuis un thread COM initialisé.
    """
    import time as _time
    parent = _mtp_resolve_path(parts)
    if parent is None:
        return None
    child = _mtp_child(parent, name)
    if child is not None:
        return child
    fo = _mtp_new_fileop()
    fo.NewItem(_mtp_shell_item(parent), 0x10, name, None, None)  # dossier
    fo.PerformOperations()
    for _ in range(20):        # le dossier peut mettre un instant à apparaître
        parent = _mtp_resolve_path(parts)
        child = _mtp_child(parent, name) if parent else None
        if child is not None:
            return child
        _time.sleep(0.3)
    return None


def find_mtp_camera() -> tuple[str, str] | None:
    """Retourne (nom_appareil, 'MTP') si un téléphone avec DCIM est connecté en MTP."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
        for dev_item in _mtp_devices():
            try:
                for root_item in dev_item.GetFolder.Items():
                    if _mtp_find_dcim_paths(root_item, [dev_item.Name]):
                        log.info("MTP DCIM trouvé sur : %s", dev_item.Name)
                        return (dev_item.Name, 'MTP')
            except Exception:
                continue
    except Exception:
        log.exception("find_mtp_camera exception")
    finally:
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass
    return None


def apply_theme(key: str | None = None):
    global _theme_key
    if key:
        set_theme(key)
    _theme_key = get_theme()
    t = T()
    app = QApplication.instance()
    if app:
        c   = QColor(t['a1'])
        scr = f"rgba({c.red()},{c.green()},{c.blue()},90)"
        app.setStyleSheet(f"""
            QWidget      {{ font-family: 'Segoe UI'; font-size: 11pt; color: {t['text']}; }}
            QScrollBar:vertical     {{ background: rgba(255,255,255,8); width: 7px; border-radius: 3px; }}
            QScrollBar::handle:vertical {{ background: {scr}; border-radius: 3px; min-height: 20px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal   {{ height: 0; }}
            QMessageBox             {{ background: rgb({t['panel'][0]},{t['panel'][1]},{t['panel'][2]}); }}
            QMessageBox QPushButton {{ padding: 6px 20px; }}
            QToolTip {{
                background: rgb({t['panel'][0]},{t['panel'][1]},{t['panel'][2]});
                color: {t['text']};
                border: 1px solid {t['a1']};
                border-radius: 10px;
                padding: 10px 14px;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }}
        """)
    theme_sig.changed.emit()


def create_app_icon() -> QIcon:
    size = 256
    pix  = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Gradient rounded square background
    bg = QLinearGradient(0, 0, size, size)
    bg.setColorAt(0, QColor('#00d4ff'))
    bg.setColorAt(1, QColor('#7b2fff'))
    p.setBrush(QBrush(bg))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, size, size, 52, 52)
    # Photo frame (white outline)
    p.setPen(QPen(QColor(255, 255, 255, 210), 13))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(36, 60, 184, 148, 16, 16)
    # Lens outer circle
    p.setPen(QPen(QColor(255, 255, 255, 210), 10))
    p.drawEllipse(76, 80, 104, 104)
    # Lens inner dot
    p.setBrush(QColor(255, 255, 255, 190))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(102, 106, 52, 52)
    p.end()
    return QIcon(pix)


def find_xnview() -> str | None:
    for p in [
        r"C:\Program Files\XnViewMP\xnviewmp.exe",
        r"C:\Program Files (x86)\XnViewMP\xnviewmp.exe",
        r"C:\Program Files\XnView\xnview.exe",
        r"C:\Program Files (x86)\XnView\xnview.exe",
    ]:
        if Path(p).exists():
            return p
    return None

_xnview_path: str | None = None

def open_in_explorer(path: str):
    subprocess.Popen(['explorer', path])

def open_in_xnview(path: str):
    global _xnview_path
    if _xnview_path is None:
        _xnview_path = find_xnview()
    if _xnview_path:
        subprocess.Popen([_xnview_path, path])
    else:
        QMessageBox.warning(None, "XnView introuvable",
            "XnView n'a pas été trouvé sur ce système.\n"
            "Vérifiez que XnViewMP est bien installé.")


def find_exiftool() -> str | None:
    path = get_exif()
    if path != DEFAULT_EXIF and Path(path).exists():
        return path
    try:
        r = subprocess.run([DEFAULT_EXIF, '-ver'],
                           capture_output=True, text=True, timeout=5,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode == 0:
            return DEFAULT_EXIF
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    if path != DEFAULT_EXIF:
        return None
    return None


# ── Workers ────────────────────────────────────────────────────────────────

class FolderScanWorker(QThread):
    folder_found = pyqtSignal(dict)
    done         = pyqtSignal()

    def __init__(self, root: str, prios: list[str]):
        super().__init__()
        self.root  = Path(root)
        self.prios  = prios
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            all_years = sorted(
                [int(d.name) for d in self.root.iterdir()
                 if d.is_dir() and d.name.isdigit() and len(d.name) == 4],
                reverse=True
            )
        except Exception:
            all_years = []
        for year in all_years:
            if self._stop:
                return
            year_path = self.root / str(year)
            if not year_path.exists():
                continue
            try:
                months = sorted(
                    [d for d in year_path.iterdir()
                     if d.is_dir() and d.name[:2].isdigit()
                     and 1 <= int(d.name[:2]) <= 12],
                    key=lambda d: d.name, reverse=True
                )
            except Exception:
                continue
            for m in months:
                if self._stop:
                    return
                for prio_name in self.prios:
                    try:
                        prio_path = m / prio_name
                        if prio_path.exists():
                            self.folder_found.emit({
                                'path': str(prio_path),
                                'display': f"{year}\\{m.name}\\{prio_name}",
                                'is_prio': True, 'count': -1
                            })
                    except Exception:
                        pass
                self.folder_found.emit({
                    'path': str(m),
                    'display': f"{year}\\{m.name}",
                    'is_prio': False, 'count': -1
                })
        self.done.emit()


class CountWorker(QRunnable):
    class _Sig(QObject):
        done = pyqtSignal(str, int)

    def __init__(self, path: str):
        super().__init__()
        self.path    = path
        self.signals = self._Sig()
        self.setAutoDelete(True)

    def run(self):
        try:
            n = sum(1 for f in Path(self.path).iterdir()
                    if f.is_file() and f.suffix.lower() in get_all_ext())
        except Exception:
            n = 0
        self.signals.done.emit(self.path, n)


class OrganiseWorker(QThread):
    log_entry = pyqtSignal(str, str)         # kind, message
    progress  = pyqtSignal(int, int)         # current, total
    done      = pyqtSignal(int, int, int, float)  # moved, skipped, errors, secs

    def __init__(self, path: str, exif_cmd: str):
        super().__init__()
        self.path     = path
        self.exif_cmd = exif_cmd

    def _photo_date(self, f: Path) -> datetime | None:
        try:
            r = subprocess.run(
                [self.exif_cmd, '-DateTimeOriginal', '-s', '-s', '-s',
                 '-d', '%Y-%m-%d %H:%M:%S', str(f)],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            out = r.stdout.strip()
            if r.returncode == 0 and out:
                return datetime.strptime(out, "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        return None

    def run(self):
        folder  = Path(self.path)
        all_ext = get_all_ext()
        files   = [f for f in folder.iterdir()
                   if f.is_file() and f.suffix.lower() in all_ext]
        total   = len(files)
        if total == 0:
            self.done.emit(0, 0, 0, 0.0)
            return

        moved = skipped = errors = 0
        t0 = datetime.now()

        for i, f in enumerate(files):
            self.progress.emit(i + 1, total)
            ext  = f.suffix.lower()
            date = None

            if ext in VIDEO_EXT:
                s    = f.stat()
                date = datetime.fromtimestamp(min(s.st_ctime, s.st_mtime))
            else:  # photos + formats extra → EXIF d'abord, fallback date fichier
                date = self._photo_date(f)
                if not date:
                    date = datetime.fromtimestamp(f.stat().st_ctime)

            if not date:
                self.log_entry.emit('skip', f"Pas de date : {f.name}")
                skipped += 1
                continue

            day_dir = folder / f"{date.day:02d}"
            new_dir = not day_dir.exists()
            try:
                day_dir.mkdir(exist_ok=True)
                if new_dir:
                    self.log_entry.emit('new', f"Dossier créé : {date.day:02d}")
            except Exception as e:
                self.log_entry.emit('error', f"Création dossier : {e}")
                errors += 1
                continue

            dest = day_dir / f.name
            if dest.exists():
                self.log_entry.emit('skip', f"Existe déjà : {f.name}")
                skipped += 1
            else:
                try:
                    f.rename(dest)
                    self.log_entry.emit('move', f"{f.name}  →  {date.day:02d}")
                    moved += 1
                except Exception as e:
                    self.log_entry.emit('error', f"{f.name} : {e}")
                    errors += 1

        elapsed = (datetime.now() - t0).total_seconds()
        self.done.emit(moved, skipped, errors, elapsed)


# ── ExifTool helpers ────────────────────────────────────────────────────────

def _check_exiftool(cmd: str) -> bool:
    try:
        r = subprocess.run([cmd, '-ver'], capture_output=True, timeout=5,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        return r.returncode == 0
    except Exception:
        return False


class _ExiftoolDownloadWorker(QThread):
    progress = pyqtSignal(int, int)   # downloaded_bytes, total_bytes
    done     = pyqtSignal(str)        # path to exiftool.exe
    error    = pyqtSignal(str)

    def run(self):
        import urllib.request, zipfile
        try:
            # 1 — trouver le lien de la dernière version Windows
            with urllib.request.urlopen("https://exiftool.org/", timeout=15) as r:
                html = r.read().decode('utf-8', errors='replace')
            m = re.search(r'href="(exiftool-[\d.]+(?:_64)?\.zip)"', html)
            if not m:
                self.error.emit("Lien introuvable sur exiftool.org")
                return
            zip_name = m.group(1)
            url = f"https://exiftool.org/{zip_name}"

            # 2 — télécharger le zip
            dest_dir = Path(__file__).parent
            zip_path = dest_dir / zip_name
            with urllib.request.urlopen(url, timeout=120) as resp:
                total      = int(resp.headers.get('Content-Length', 0))
                downloaded = 0
                with open(zip_path, 'wb') as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)

            # 3 — extraire et renommer en exiftool.exe
            with zipfile.ZipFile(zip_path) as zf:
                exe = next((n for n in zf.namelist() if n.lower().endswith('.exe')), None)
                if not exe:
                    self.error.emit("Aucun exécutable dans l'archive")
                    zip_path.unlink(missing_ok=True)
                    return
                zf.extract(exe, dest_dir)
            zip_path.unlink(missing_ok=True)
            extracted = dest_dir / exe
            final = dest_dir / "exiftool.exe"
            extracted.replace(final)
            self.done.emit(str(final))
        except Exception as e:
            self.error.emit(str(e))


class _ExiftoolDownloadDialog(QDialog):
    installed = pyqtSignal(str)   # path to the installed exe

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ExifTool introuvable")
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        lbl = QLabel(
            "<b>exiftool</b> est introuvable sur ce système.<br>"
            "Voulez-vous le télécharger automatiquement depuis "
            "<i>exiftool.org</i> ?")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        self._prog = QProgressBar()
        self._prog.setRange(0, 100)
        self._prog.setVisible(False)
        lay.addWidget(self._prog)

        self._status = QLabel()
        self._status.setWordWrap(True)
        lay.addWidget(self._status)

        btn_row = QHBoxLayout()
        self._btn_dl  = QPushButton("⬇  Télécharger automatiquement")
        btn_manual    = QPushButton("📁  Sélectionner manuellement")
        btn_cancel    = QPushButton("Annuler")
        btn_row.addWidget(self._btn_dl)
        btn_row.addWidget(btn_manual)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        self._btn_dl.clicked.connect(self._start_download)
        btn_manual.clicked.connect(self._manual)
        btn_cancel.clicked.connect(self.reject)
        self._worker = None

    def _start_download(self):
        self._btn_dl.setEnabled(False)
        self._prog.setVisible(True)
        self._prog.setRange(0, 0)   # indéterminé tant qu'on n'a pas le total
        self._status.setText("Connexion à exiftool.org…")
        self._worker = _ExiftoolDownloadWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, downloaded: int, total: int):
        if total > 0:
            self._prog.setRange(0, 100)
            self._prog.setValue(int(downloaded * 100 / total))
            self._status.setText(
                f"Téléchargement… {downloaded // 1024} Ko / {total // 1024} Ko")
        else:
            self._status.setText(f"Téléchargement… {downloaded // 1024} Ko")

    def _on_done(self, path: str):
        set_exif(path)
        self.installed.emit(path)
        self.accept()

    def _on_error(self, msg: str):
        self._prog.setVisible(False)
        self._status.setText(f"Erreur : {msg}")
        self._btn_dl.setEnabled(True)

    def _manual(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner exiftool.exe", "", "Executables (*.exe)")
        if path:
            set_exif(path)
            self.installed.emit(path)
            self.accept()


# ── USB Copy Worker ─────────────────────────────────────────────────────────

class UsbCopyWorker(QThread):
    log_entry  = pyqtSignal(str, str)              # kind, message
    log_thumb  = pyqtSignal(str, str, str)         # kind, message, local_filepath
    batch_info = pyqtSignal(str)                   # label texte phase
    progress   = pyqtSignal(int, int)              # current, total
    done       = pyqtSignal(int, int, int, float)  # copied, skipped, errors, secs

    MODE_COPY        = 'copy'
    MODE_COPY_DELETE = 'copy_delete'
    MODE_COPY_MOVE   = 'copy_move'
    MODE_DRY_RUN     = 'dry_run'

    _EXIF_CHUNK = 500                              # fichiers par appel exiftool
    _THUMB_EXT  = {'.jpg', '.jpeg', '.png'}        # extensions avec vignette

    def __init__(self, dcim_path: str, target: str, mode: str, exif_cmd: str,
                 dcim_root: str | None = None):
        super().__init__()
        self.dcim_path = dcim_path
        self.target    = target
        self.mode      = mode
        self.exif_cmd  = exif_cmd
        self.dcim_root = dcim_root or dcim_path   # où vit DCIM/_old
        self._stop     = False

    def stop(self):
        self._stop = True

    def _batch_get_dates(self, files: list[Path]) -> dict[str, datetime | None]:
        """Lecture EXIF en batch (un seul processus exiftool pour tous les fichiers photo)."""
        dates: dict[str, datetime | None] = {}
        photo_files = [f for f in files if f.suffix.lower() not in VIDEO_EXT]
        video_files = [f for f in files if f.suffix.lower() in VIDEO_EXT]

        # Vidéos : date filesystem (pas besoin d'exiftool)
        for f in video_files:
            try:
                s = f.stat()
                dates[str(f.resolve())] = datetime.fromtimestamp(min(s.st_ctime, s.st_mtime))
            except Exception:
                dates[str(f.resolve())] = None

        # Photos : appels batch par chunks
        total_chunks = max(1, (len(photo_files) + self._EXIF_CHUNK - 1) // self._EXIF_CHUNK)
        for ci, start in enumerate(range(0, len(photo_files), self._EXIF_CHUNK)):
            if self._stop:
                break
            chunk = photo_files[start:start + self._EXIF_CHUNK]
            self.batch_info.emit(
                f"Phase 1/2 — Lecture EXIF… {ci + 1}/{total_chunks}")
            try:
                r = subprocess.run(
                    [self.exif_cmd, '-json', '-d', '%Y-%m-%d %H:%M:%S',
                     '-DateTimeOriginal', '-CreateDate', '-q',
                     *[str(f) for f in chunk]],
                    capture_output=True, text=True, timeout=60,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                data = json.loads(r.stdout) if r.stdout.strip() else []
                for item in data:
                    src_key = str(Path(item.get('SourceFile', '')).resolve())
                    dt_str  = item.get('DateTimeOriginal') or item.get('CreateDate')
                    if dt_str and not str(dt_str).startswith('0000'):
                        try:
                            dates[src_key] = datetime.strptime(str(dt_str), "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            pass
            except subprocess.TimeoutExpired:
                log.warning("Batch EXIF timeout sur chunk %d/%d — fallback date fichier",
                            ci + 1, total_chunks)
                self.batch_info.emit(
                    f"Phase 1/2 — chunk {ci + 1}/{total_chunks} : délai exiftool dépassé,"
                    " fallback date fichier…")
            except Exception as e:
                log.warning("Batch EXIF chunk %d/%d : %s", ci + 1, total_chunks, e)
                self.batch_info.emit(
                    f"Phase 1/2 — chunk {ci + 1}/{total_chunks} : erreur EXIF, "
                    "fallback date fichier…")

        # Fallback filesystem pour les photos sans date EXIF
        for f in photo_files:
            key = str(f.resolve())
            if key not in dates:
                try:
                    dates[key] = datetime.fromtimestamp(f.stat().st_ctime)
                except Exception:
                    dates[key] = None

        return dates

    def _unique_dest(self, dest: Path) -> Path:
        if not dest.exists():
            return dest
        stem, suffix = dest.stem, dest.suffix
        i = 2
        while True:
            candidate = dest.parent / f"{stem}_{i}{suffix}"
            if not candidate.exists():
                return candidate
            i += 1

    def run(self):
        import shutil
        import concurrent.futures

        all_ext = get_all_ext()
        dcim    = Path(self.dcim_path)
        # _old contient les fichiers déjà importés : jamais repris
        files   = [f for f in dcim.rglob("*")
                   if f.is_file() and f.suffix.lower() in all_ext
                   and not any(part.lower() == "_old" for part in f.parts)]
        total   = len(files)
        if total == 0:
            self.done.emit(0, 0, 0, 0.0)
            return

        t0 = datetime.now()

        # Tailles de fichiers pour la barre en octets
        file_sizes: dict[str, int] = {}
        for f in files:
            try:
                file_sizes[str(f.resolve())] = f.stat().st_size
            except Exception:
                file_sizes[str(f.resolve())] = 0
        total_bytes = sum(file_sizes.values())

        # Phase 1 : lecture EXIF batch
        self.batch_info.emit("Phase 1/2 — Lecture EXIF…")
        dates = self._batch_get_dates(files)
        self.batch_info.emit("Phase 2/2 — Copie des fichiers…")

        copied       = 0
        skipped      = 0
        errors       = 0
        bytes_done   = 0
        copied_paths: list[Path] = []
        dest_lock    = threading.Lock()   # protège _unique_dest et copied_paths
        n_workers    = get_usb_workers()

        def _copy_one(f: Path):
            fsize = file_sizes.get(str(f.resolve()), 0)
            if self._stop:
                return 'skip', f"Annulé : {f.name}", None, None, 0
            date = dates.get(str(f.resolve()))
            if not date:
                return 'skip', f"Pas de date : {f.name}", None, None, 0

            label = (f"{date.year}/to_sort/"
                     f"{date.month:02d}/{date.day:02d}")
            dest_dir = Path(self.target) / str(date.year) / "to_sort" \
                       / f"{date.month:02d}" / f"{date.day:02d}"

            if self.mode == self.MODE_DRY_RUN:
                return 'move', f"[Simulation] {f.name}  →  {label}", None, None, fsize

            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                plain = dest_dir / f.name
                try:
                    if plain.exists() and plain.stat().st_size == f.stat().st_size:
                        # copie déjà vérifiée : éligible au rangement/suppression
                        return 'skip', f"Déjà présent : {f.name}", f, None, fsize
                except Exception:
                    pass
                with dest_lock:
                    dest = self._unique_dest(plain)
                shutil.copy2(str(f), str(dest))
                thumb = str(dest) if f.suffix.lower() in self._THUMB_EXT else None
                return 'move', f"{f.name}  →  {label}", f, thumb, fsize
            except Exception as e:
                return 'error', f"{f.name} : {e}", None, None, 0

        done_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
            fut_map = {executor.submit(_copy_one, f): f for f in files}
            for fut in concurrent.futures.as_completed(fut_map):
                done_count += 1
                try:
                    kind, msg, src_path, thumb, fsize = fut.result()
                except Exception as e:
                    self.log_entry.emit('error', f"Exception : {e}")
                    errors += 1
                    self.progress.emit(bytes_done, total_bytes)
                    continue

                if kind == 'move':
                    copied += 1
                    bytes_done += fsize
                    if src_path is not None:
                        with dest_lock:
                            copied_paths.append(src_path)
                    if thumb:
                        self.log_thumb.emit(kind, msg, thumb)
                    else:
                        self.log_entry.emit(kind, msg)
                elif kind == 'skip':
                    skipped += 1
                    if src_path is not None:
                        with dest_lock:
                            copied_paths.append(src_path)
                    self.log_entry.emit(kind, msg)
                else:
                    errors += 1
                    self.log_entry.emit(kind, msg)

                self.progress.emit(bytes_done, total_bytes)
                n_active = min(n_workers, total - done_count)
                self.batch_info.emit(
                    f"Phase 2/2 — {done_count}/{total} fichiers"
                    + (f"  ·  {n_active} en cours" if n_active > 0 else "")
                )

        # Déplacement des sources vers DCIM/_old (mode copy_move) : les
        # fichiers importés sont rangés, jamais supprimés du support.
        if self.mode == self.MODE_COPY_MOVE and copied_paths:
            import time as _time
            root    = Path(self.dcim_root)
            old_dir = root / "_old"
            n_move  = len(copied_paths)
            self.log_entry.emit('new',
                f"Déplacement de {n_move} fichiers vers DCIM/_old…")
            moved = 0
            t_move = _time.time()
            self.progress.emit(0, n_move)
            for idx, src in enumerate(copied_paths):
                if self._stop:
                    break
                try:
                    try:
                        rel = src.relative_to(root)
                    except ValueError:
                        rel = Path(src.name)
                    dest = old_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest = self._unique_dest(dest)
                    shutil.move(str(src), str(dest))
                    moved += 1
                except Exception as e:
                    self.log_entry.emit('error', f"Déplacement : {src.name} : {e}")
                if moved and (idx % 10 == 0 or idx == n_move - 1):
                    eta = (_time.time() - t_move) / (idx + 1) * (n_move - idx - 1)
                    self.batch_info.emit(
                        f"Déplacement vers DCIM/_old : {idx + 1}/{n_move} "
                        f"fichiers  ·  reste ~{_fmt_eta(eta)}…")
                    self.progress.emit(idx + 1, n_move)
            self.progress.emit(moved, n_move)
            self.log_entry.emit('new', f"✓ {moved} fichiers rangés dans DCIM/_old")

        # Suppression source si mode copy_delete et aucune erreur.
        # On supprime même si stoppé en cours : les fichiers copiés sont sur disque.
        if self.mode == self.MODE_COPY_DELETE and errors == 0:
            for src in copied_paths:
                try:
                    src.unlink()
                except Exception as e:
                    self.log_entry.emit('error', f"Suppression : {src.name} : {e}")
            for dirpath, _dirs, _files in os.walk(str(dcim), topdown=False):
                if dirpath == str(dcim):
                    continue
                try:
                    Path(dirpath).rmdir()
                except OSError:
                    pass

        elapsed = (datetime.now() - t0).total_seconds()
        self.done.emit(copied, skipped, errors, elapsed)


# ── MTP Copy Worker ─────────────────────────────────────────────────────────

class _MtpDialogSuppressor(threading.Thread):
    """Masque les fenêtres de progression Windows Shell pendant un transfert MTP."""

    def __init__(self):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        import time as _time
        import win32gui, win32con, win32process, win32api
        own_pid = win32api.GetCurrentProcessId()

        def _cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid != own_pid:
                    return True
            except Exception:
                return True
            title = win32gui.GetWindowText(hwnd)
            cls   = win32gui.GetClassName(hwnd)
            if cls == "OperationStatusWindow" or \
               any(k in title for k in ("Copie", "Copy", "Déplacer", "Moving")):
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            return True

        while not self._stop_event.is_set():
            try:
                win32gui.EnumWindows(_cb, None)
            except Exception:
                pass
            _time.sleep(0.05)


# Formats de noms reconnus : « 20260818_… », « IMG20260818190313.jpg » (OPPO),
# « VID20260818… », « IMG_20260818… », « PXL_20260818… », « Screenshot_20260818… »
_FILENAME_DATE_RE = re.compile(
    r"(?:^|[^0-9])(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?=[^0-9]|\d{6})")


def _date_from_filename(name: str) -> datetime | None:
    """Date déduite d'un nom de fichier photo/vidéo (None si illisible)."""
    m = _FILENAME_DATE_RE.search(name)
    if m:
        try:
            return datetime(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            pass
    return None


def _fmt_eta(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60} min {s % 60:02d}" if s >= 60 else f"{s} s"


def _filter_names_from_date(names: list[str],
                            date_from: datetime | None) -> int:
    """Nombre de fichiers retenus par le filtre « à partir du ».

    Les fichiers dont la date n'est pas lisible dans le nom sont conservés,
    comme le fait la copie.
    """
    if not date_from:
        return len(names)
    return sum(1 for n in names
               if not ((fd := _date_from_filename(n)) and fd < date_from))


class MtpCopyWorker(QThread):
    log_entry  = pyqtSignal(str, str)       # kind, message
    log_thumb  = pyqtSignal(str, str, str)  # kind, message, local_filepath
    batch_info = pyqtSignal(str)            # label text
    progress   = pyqtSignal(int, int)       # current, total
    done       = pyqtSignal(int, int, int, float)
    ask_slow_move = pyqtSignal(int)         # n fichiers — demande continuer/arrêter

    MODE_COPY        = 'copy'
    MODE_COPY_DELETE = 'copy_delete'
    MODE_COPY_MOVE   = 'copy_move'
    MODE_DRY_RUN     = 'dry_run'

    _THUMB_EXT = {'.jpg', '.jpeg', '.png'}

    def __init__(self, target: str, mode: str,
                 path_parts: list[str] | None = None,
                 date_from: datetime | None = None,
                 exif_cmd: str = 'exiftool.exe'):
        super().__init__()
        self.target     = target
        self.mode       = mode
        self.path_parts = list(path_parts or [])
        self.date_from  = date_from
        self.exif_cmd   = exif_cmd
        self._stop      = False
        self._slow_move_reply = threading.Event()
        self._slow_move_ok    = False

    def reply_slow_move(self, accept: bool):
        """Réponse de l'utilisateur au dialogue « rangement lent »."""
        self._slow_move_ok = accept
        self._slow_move_reply.set()

    @property
    def folder_label(self) -> str:
        return _mtp_path_label(self.path_parts) or "le téléphone"

    def _dcim_root_parts(self) -> list[str]:
        """Chemin du dossier qui accueillera _old : le DCIM ancêtre,
        sinon le parent du dossier source."""
        for i, name in enumerate(self.path_parts):
            if name.lower() == "dcim":
                return self.path_parts[:i + 1]
        if len(self.path_parts) > 1:
            return self.path_parts[:-1]
        return list(self.path_parts)

    def _fresh_items(self, names: set[str]) -> list:
        """FolderItems actuels du dossier source pour ces noms.

        Après une longue phase de copie, les références COM d'origine
        peuvent être périmées : on ré-énumère toujours avant d'agir.
        """
        src = _mtp_resolve_path(self.path_parts)
        if src is None:
            return []
        return [i for i in src.GetFolder.Items()
                if not i.IsFolder and i.Name in names]

    _MOVE_CHUNK = 20   # fichiers par lot IFileOperation (progression fluide)

    def _move_items_to_old(self, names: set[str],
                           local_map: dict[str, Path]) -> int:
        """Range les fichiers `names` du dossier source dans DCIM/_old.

        Sonde d'abord le déplacement direct (MoveItem) sur un fichier ;
        la plupart des téléphones l'interdisent en MTP, on renvoie alors la
        copie déjà faite sur le PC vers _old puis on supprime l'original —
        uniquement après vérification de la copie. Travaille par petits
        lots : progression, temps restant et bouton Arrêter fonctionnent.
        Les noms déjà pris dans _old ne sont jamais écrasés (suffixe (2)…).
        """
        import time as _time
        from win32com.shell import shell as _shell

        items = self._fresh_items(names)
        missing = len(names) - len(items)
        if missing:
            self.log_entry.emit('error',
                f"{missing} fichiers introuvables sur le support")
        if not items:
            return 0

        old_parts = self._dcim_root_parts() + ["_old"]
        old_item = _mtp_ensure_child_folder(self._dcim_root_parts(), "_old")
        if old_item is None:
            self.log_entry.emit('error',
                "Impossible de créer DCIM/_old sur le support")
            return 0

        def _old_names() -> set[str]:
            it = _mtp_resolve_path(old_parts)
            if it is None:
                return set()
            return {s.Name for s in it.GetFolder.Items() if not s.IsFolder}

        # Nom final unique dans _old pour chaque fichier
        taken = _old_names()
        final: dict[str, str] = {}
        for it in items:
            name = it.Name
            if name in taken:
                stem, dot, ext = name.rpartition(".")
                base = stem if dot else name
                tail = ("." + ext) if dot else ""
                k = 2
                while f"{base} ({k}){tail}" in taken:
                    k += 1
                name = f"{base} ({k}){tail}"
            final[it.Name] = name
            taken.add(name)

        total = len(items)
        moved = 0
        t0    = _time.time()

        def _tick():
            self.progress.emit(moved, total)
            txt = f"Déplacement vers DCIM/_old : {moved}/{total} fichiers"
            if 0 < moved < total:
                eta = (_time.time() - t0) / moved * (total - moved)
                txt += f"  ·  reste ~{_fmt_eta(eta)}"
            self.batch_info.emit(txt + "…")

        _tick()

        # ── Sonde : ce support accepte-t-il le déplacement direct ? ────────
        probe = items[0]
        direct_ok = False
        try:
            fo = _mtp_new_fileop()
            fo.MoveItem(_mtp_shell_item(probe),
                        _mtp_shell_item(old_item), final[probe.Name], None)
            fo.PerformOperations()
            direct_ok = final[probe.Name] in _old_names()
        except Exception:
            direct_ok = False

        try:
            set_mtp_move_support(self.path_parts[0],
                                 'yes' if direct_ok else 'no')
        except Exception:
            pass

        if direct_ok:
            moved = 1
            _tick()
            rest = items[1:]
            for i in range(0, len(rest), self._MOVE_CHUNK):
                if self._stop:
                    break
                chunk = rest[i:i + self._MOVE_CHUNK]
                try:
                    fo  = _mtp_new_fileop()
                    dst = _mtp_shell_item(old_item)
                    for it in chunk:
                        fo.MoveItem(_mtp_shell_item(it), dst,
                                    final[it.Name], None)
                    fo.PerformOperations()
                except Exception as e:
                    self.log_entry.emit('error', f"Déplacement : {e}")
                moved += len(chunk)
                _tick()
            # Bilan réel : ce qui reste dans le dossier source fait foi
            left = {i.Name for i in self._fresh_items(names)}
            return total - len(left)

        # ── Repli : envoi de la copie PC vers _old, puis suppression ───────
        # C'est lent (les fichiers repassent par l'USB) : on demande d'abord.
        self.log_entry.emit('skip',
            "Ce téléphone ne sait pas déplacer ses fichiers directement")
        self._slow_move_reply.clear()
        self.ask_slow_move.emit(total)
        self._slow_move_reply.wait()
        if self._stop or not self._slow_move_ok:
            self.log_entry.emit('skip',
                "Rangement annulé — les photos sont copiées sur le PC ; "
                "rien n'a été modifié sur le téléphone")
            self.batch_info.emit("Rangement vers _old annulé")
            return 0
        sendable = [it for it in items
                    if it.Name in local_map and local_map[it.Name].exists()]
        for it in items:
            if it not in sendable:
                self.log_entry.emit('error',
                    f"Copie locale introuvable pour {it.Name}")

        for i in range(0, len(sendable), self._MOVE_CHUNK):
            if self._stop:
                break
            chunk = sendable[i:i + self._MOVE_CHUNK]
            try:
                fo  = _mtp_new_fileop()
                dst = _mtp_shell_item(old_item)
                for it in chunk:
                    src_local = _shell.SHCreateItemFromParsingName(
                        str(local_map[it.Name]), None, _shell.IID_IShellItem)
                    fo.CopyItem(src_local, dst, final[it.Name], None)
                fo.PerformOperations()
            except Exception as e:
                self.log_entry.emit('error', f"Copie vers _old : {e}")
                continue
            in_old = _old_names()
            deletable = [it for it in chunk if final[it.Name] in in_old]
            for it in chunk:
                if it not in deletable:
                    self.log_entry.emit('error', f"Non rangé : {it.Name}")
            if deletable:
                try:
                    fo2 = _mtp_new_fileop()
                    for it in deletable:
                        fo2.DeleteItem(_mtp_shell_item(it), None)
                    fo2.PerformOperations()
                    moved += len(deletable)
                except Exception as e:
                    self.log_entry.emit('error', f"Suppression : {e}")
            _tick()
        return moved

    def stop(self):
        self._stop = True
        self._slow_move_reply.set()   # débloque une éventuelle question en attente

    def _date_from_name(self, name: str) -> datetime | None:
        return _date_from_filename(name)

    def _get_date_exif(self, path: Path) -> datetime | None:
        if path.suffix.lower() in VIDEO_EXT:
            try:
                s = path.stat()
                return datetime.fromtimestamp(min(s.st_ctime, s.st_mtime))
            except Exception:
                return None
        try:
            r = subprocess.run(
                [self.exif_cmd, '-DateTimeOriginal', '-CreateDate',
                 '-s', '-s', '-s', '-d', '%Y-%m-%d %H:%M:%S', str(path)],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW)
            for line in r.stdout.strip().splitlines():
                line = line.strip()
                if line and not line.startswith('0000'):
                    try:
                        return datetime.strptime(line, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
        except Exception:
            pass
        return self._date_from_name(path.name)

    def _unique_dest(self, dest: Path) -> Path:
        if not dest.exists():
            return dest
        stem, suffix = dest.stem, dest.suffix
        i = 2
        while True:
            c = dest.parent / f"{stem}_{i}{suffix}"
            if not c.exists():
                return c
            i += 1

    def run(self):
        suppressor = _MtpDialogSuppressor()
        suppressor.start()
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                self._run_inner()
            finally:
                pythoncom.CoUninitialize()
        except Exception:
            log.exception("MtpCopyWorker exception")
            self.done.emit(0, 0, 1, 0.0)
        finally:
            suppressor.stop()

    def _run_inner(self):
        import win32com.client
        import shutil
        import time
        t0 = datetime.now()

        cam_item = _mtp_resolve_path(self.path_parts)
        if cam_item is None:
            self.log_entry.emit('error',
                f"Dossier « {self.folder_label} » introuvable — "
                "reconnectez le téléphone en mode transfert de fichiers")
            self.done.emit(0, 0, 1, 0.0)
            return

        all_ext  = get_all_ext()
        all_mtp  = [item for item in cam_item.GetFolder.Items()
                    if not item.IsFolder
                    and Path(item.Name).suffix.lower() in all_ext]

        # Filtre par date appliqué AVANT tout : seuls les fichiers retenus
        # sont copiés — et eux seuls pourront être supprimés du téléphone.
        to_copy = [i for i in all_mtp
                   if not (self.date_from
                           and (fd := self._date_from_name(i.Name))
                           and fd < self.date_from)]
        excluded  = len(all_mtp) - len(to_copy)
        total_mtp = len(to_copy)

        if excluded:
            self.log_entry.emit('skip',
                f"{excluded} fichiers ignorés (antérieurs au "
                f"{self.date_from:%d/%m/%Y})")
        if total_mtp == 0:
            self.log_entry.emit('skip', f"Aucun fichier dans « {self.folder_label} »")
            self.done.emit(0, 0, 0, 0.0)
            return

        # ── Simulation ───────────────────────────────────────────────────────
        if self.mode == self.MODE_DRY_RUN:
            sim = to_copy
            self.log_entry.emit('new',
                f"[Simulation] {len(sim)} fichiers → {self.target}")
            for idx, item in enumerate(sim):
                if self._stop:
                    break
                fd = self._date_from_name(item.Name)
                dst = (f"{fd.year}/to_sort/{fd.month:02d}/{fd.day:02d}"
                       if fd else "sans_date")
                self.log_entry.emit('move', f"[Sim] {item.Name}  →  {dst}")
                self.progress.emit(idx + 1, len(sim))
            elapsed = (datetime.now() - t0).total_seconds()
            self.done.emit(0, len(sim), 0, elapsed)
            return

        # ── Phase 1 : batch copy MTP → dossier temporaire ────────────────────
        temp_dir = Path(self.target) / "._mtp_import_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        self.batch_info.emit(f"Phase 1/2 — MTP → PC : 0/{total_mtp} fichiers…")
        self.log_entry.emit('new',
            f"Phase 1 : copie {total_mtp} fichiers depuis le téléphone…")

        # PerformOperations bloque le thread appelant — thread dédié.
        # IFileOperation en mode silencieux : aucune fenêtre de progression
        # Windows ne s'ouvre (le suivi est affiché par l'appli elle-même).
        _parts = list(self.path_parts)
        _names = {i.Name for i in to_copy}
        _target_str = str(temp_dir)
        copy_done  = threading.Event()
        copy_error: list = [None]

        def _do_copy():
            import pythoncom
            from win32com.shell import shell as _shell
            pythoncom.CoInitialize()
            try:
                _cam = _mtp_resolve_path(_parts)
                if _cam is None:
                    copy_error[0] = "Dossier introuvable dans le thread de copie"
                    return
                fo  = _mtp_new_fileop()
                dst = _shell.SHCreateItemFromParsingName(
                    _target_str, None, _shell.IID_IShellItem)
                queued = 0
                for it in _cam.GetFolder.Items():
                    if not it.IsFolder and it.Name in _names:
                        fo.CopyItem(_mtp_shell_item(it), dst, None, None)
                        queued += 1
                if queued:
                    fo.PerformOperations()
            except Exception as _e:
                copy_error[0] = _e
            finally:
                try: pythoncom.CoUninitialize()
                except: pass
                copy_done.set()

        copy_thread = threading.Thread(target=_do_copy, daemon=True)
        copy_thread.start()

        # Polling pendant que CopyHere tourne dans l'autre thread
        timeout_s, waited = 600.0, 0.0
        while not copy_done.is_set() and waited < timeout_s:
            if self._stop:
                break
            n = sum(1 for f in temp_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in all_ext)
            self.progress.emit(n, total_mtp)
            self.batch_info.emit(f"Phase 1/2 — MTP → PC : {n}/{total_mtp} fichiers…")
            time.sleep(0.4)
            waited += 0.4
        copy_done.wait(timeout=10)

        temp_files = sorted(f for f in temp_dir.iterdir()
                            if f.is_file() and f.suffix.lower() in all_ext)

        # ── Phase 2 : organisation EXIF ───────────────────────────────────────
        dest_base   = Path(self.target)
        n_files     = len(temp_files)
        self.batch_info.emit(f"Phase 2/2 — Organisation EXIF : {n_files} fichiers…")
        self.log_entry.emit('new', f"Phase 2 : organisation EXIF de {n_files} fichiers…")
        self.progress.emit(0, n_files)

        copied = skipped = errors = 0
        imported_ok: set[str] = set()      # noms sûrs à supprimer du téléphone
        imported_dest: dict[str, Path] = {}  # nom source → copie sur le disque
        current_batch = ""

        for idx, f in enumerate(temp_files):
            if self._stop:
                break

            # Filtre par date (appliqué après copie MTP)
            if self.date_from:
                fd = self._date_from_name(f.name)
                if fd and fd < self.date_from:
                    f.unlink(missing_ok=True)
                    skipped += 1
                    self.progress.emit(idx + 1, n_files)
                    continue

            date = self._get_date_exif(f)
            if date:
                dest_dir = (dest_base / str(date.year) / "to_sort"
                            / f"{date.month:02d}" / f"{date.day:02d}")
                dest_str = f"{date.year}/to_sort/{date.month:02d}/{date.day:02d}"
            else:
                dest_dir = dest_base / "sans_date"
                dest_str = "sans_date"

            if dest_str != current_batch:
                current_batch = dest_str
                self.batch_info.emit(f"Lot : {dest_str}")

            plain = dest_dir / f.name
            try:
                already = (plain.exists()
                           and plain.stat().st_size == f.stat().st_size)
            except Exception:
                already = False
            if already:
                self.log_entry.emit('skip', f"Déjà présent : {f.name}")
                f.unlink(missing_ok=True)
                imported_ok.add(f.name)
                imported_dest[f.name] = plain
                skipped += 1
                self.progress.emit(idx + 1, n_files)
                continue

            dest_file = self._unique_dest(plain)

            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(dest_file))
                copied += 1
                imported_ok.add(f.name)
                imported_dest[f.name] = dest_file
                thumb = str(dest_file) if f.suffix.lower() in self._THUMB_EXT else ""
                self.log_thumb.emit('move', f"{f.name}  →  {dest_str}", thumb)
            except Exception as e:
                errors += 1
                self.log_entry.emit('error', f"{f.name} : {e}")
            self.progress.emit(idx + 1, n_files)

        # Nettoyage dossier temp
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

        # Déplacement vers DCIM/_old (mode copy_move) : un seul lot
        # IFileOperation silencieux, uniquement les fichiers importés.
        if self.mode == self.MODE_COPY_MOVE and not self._stop:
            src_in_old = any(pp.lower() == "_old" for pp in self.path_parts)
            if src_in_old:
                self.log_entry.emit('skip',
                    "Source déjà dans _old — aucun déplacement")
            elif imported_ok:
                self.log_entry.emit('new',
                    f"Déplacement de {len(imported_ok)} fichiers vers DCIM/_old…")
                try:
                    moved = self._move_items_to_old(set(imported_ok),
                                                    imported_dest)
                    if moved < len(imported_ok):
                        self.log_entry.emit('error',
                            f"{len(imported_ok) - moved} fichiers n'ont pas "
                            "pu être déplacés — ils restent dans le dossier "
                            "d'origine")
                    if moved:
                        self.log_entry.emit('new',
                            f"✓ {moved} fichiers rangés dans DCIM/_old")
                except Exception as e:
                    self.log_entry.emit('error', f"Déplacement : {e}")

        # Suppression depuis le téléphone (mode copy+delete).
        # Un seul lot IFileOperation silencieux : pas de confirmation Windows
        # (l'appli a déjà demandé), et uniquement les fichiers dont la copie
        # sur le disque est vérifiée.
        if self.mode == self.MODE_COPY_DELETE and not self._stop:
            to_delete = self._fresh_items(set(imported_ok))
            if to_delete:
                self.batch_info.emit(
                    f"Suppression de {len(to_delete)} fichiers du téléphone…")
                self.log_entry.emit('new',
                    f"Suppression de {len(to_delete)} fichiers du téléphone…")
                try:
                    fo = _mtp_new_fileop()
                    for it in to_delete:
                        fo.DeleteItem(_mtp_shell_item(it), None)
                    fo.PerformOperations()
                    if fo.GetAnyOperationsAborted():
                        self.log_entry.emit('error',
                            "Suppression incomplète — des fichiers restent "
                            "sur le téléphone")
                    else:
                        self.log_entry.emit('new',
                            f"✓ {len(to_delete)} fichiers supprimés du téléphone")
                except Exception as e:
                    self.log_entry.emit('error', f"Suppression : {e}")
            not_deleted = total_mtp - len(to_delete)
            if not_deleted:
                self.log_entry.emit('skip',
                    f"{not_deleted} fichiers non importés conservés "
                    "sur le téléphone")

        self.batch_info.emit("✓ Terminé")
        elapsed = (datetime.now() - t0).total_seconds()
        self.done.emit(copied, skipped, errors, elapsed)


# ── Base Glass Panel ───────────────────────────────────────────────────────

class GlassPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        theme_sig.changed.connect(self.update)

    def paintEvent(self, _):
        t  = T()
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r  = self.rect().adjusted(1, 1, -1, -1)
        p.setBrush(QColor(*t['panel']))
        p.setPen(QPen(QColor(*t['border']), 1))
        p.drawRoundedRect(r, 12, 12)


# ── Tab Button ─────────────────────────────────────────────────────────────

class _TabButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._active = False
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self._refresh()
        theme_sig.changed.connect(self._refresh)

    def set_active(self, active: bool):
        self._active = active
        self._refresh()

    def _refresh(self):
        t = T()
        light = sum(t['bg'][0]) / 3 > 128
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {t['a1']}, stop:1 {t['a2']});
                    color: #000; font-weight: bold; font-size: 10pt;
                    border: none; border-radius: 8px;
                    padding: 4px 18px;
                }}
            """)
        else:
            bg  = "rgba(0,0,0,10)"  if light else "rgba(255,255,255,12)"
            fg  = t['dim']
            hov = "rgba(0,0,0,20)"  if light else "rgba(255,255,255,22)"
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {bg}; color: {fg};
                    font-size: 10pt; border: none;
                    border-radius: 8px; padding: 4px 18px;
                }}
                QPushButton:hover {{ background: {hov}; color: {t['text']}; }}
            """)


# ── Ghost Tab (recherche d'appareil) ───────────────────────────────────────

class _GhostTab(QWidget):
    """Onglet « fantôme » affiché pendant la recherche d'un appareil.

    Même gabarit que les onglets, bordure pointillée, spinner rotatif et
    temps d'attente écoulé — l'utilisateur voit où l'onglet apparaîtra.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedHeight(34)
        self._angle   = 0
        self._started = datetime.now()
        self._text    = ""
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(40)
        self._spin_timer.timeout.connect(self._tick)
        self.set_text("Recherche d'une carte SD ou d'un téléphone…")
        theme_sig.changed.connect(self.update)

    def set_text(self, text: str):
        if text != self._text:
            self._text = text
            fm = QFontMetrics(QFont("Segoe UI", 9))
            self.setFixedWidth(fm.horizontalAdvance(text) + 110)
            self.update()

    def start(self):
        if not self.isVisible():
            self._started = datetime.now()
            self.setVisible(True)
        if not self._spin_timer.isActive():
            self._spin_timer.start()

    def stop(self):
        self._spin_timer.stop()
        self.setVisible(False)

    def _tick(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, _):
        t = T()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        light = sum(t['bg'][0]) / 3 > 128

        # Fond très discret + bordure pointillée (emplacement du futur onglet)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 6) if light else QColor(255, 255, 255, 8))
        p.drawRoundedRect(r, 8, 8)
        pen = QPen(QColor(t['dim']), 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, 8, 8)

        # Spinner : arc rotatif aux couleurs du thème
        arc = QRectF(r.left() + 12, r.center().y() - 7, 14, 14)
        sp = QPen(QColor(t['a1']), 2.2)
        sp.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(sp)
        p.drawArc(arc, -self._angle * 16, 110 * 16)

        # Texte + temps écoulé
        elapsed = int((datetime.now() - self._started).total_seconds())
        mins, secs = divmod(elapsed, 60)
        clock = f"{mins} min {secs:02d}" if mins else f"{secs} s"
        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(t['dim']))
        p.drawText(r.adjusted(36, 0, -12, 0),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   f"{self._text}  {clock}")


# ── Instant tooltip helper ─────────────────────────────────────────────────

class _InstantTip(QObject):
    """Event filter that shows a widget's tooltip immediately on hover."""
    def eventFilter(self, obj, e):
        if e.type() == QEvent.Type.Enter and obj.toolTip():
            QToolTip.showText(QCursor.pos(), obj.toolTip(), obj)
        return False

_instant_tip = _InstantTip()


# ── Gradient Button ────────────────────────────────────────────────────────

class GradientButton(QPushButton):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self._h    = 0.0
        self._anim = QPropertyAnimation(self, b'_hov', self)
        self._anim.setDuration(180)
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        theme_sig.changed.connect(self.update)

    def _get_h(self): return self._h
    def _set_h(self, v): self._h = v; self.update()
    _hov = pyqtProperty(float, _get_h, _set_h)

    def enterEvent(self, e): self._anim.stop(); self._anim.setEndValue(1.0); self._anim.start()
    def leaveEvent(self, e): self._anim.stop(); self._anim.setEndValue(0.0); self._anim.start()

    def paintEvent(self, _):
        t      = T()
        p      = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r      = self.rect().adjusted(1, 1, -1, -1)
        radius = r.height() / 2.0

        # Gradient (used for border + hover fill)
        grad = QLinearGradient(0, 0, r.width(), 0)
        grad.setColorAt(0, QColor(t['a1']))
        grad.setColorAt(1, QColor(t['a2']))

        # Outer pill — gradient fill (visible as border)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(r), radius, radius)

        # Inner fill — theme-coloured, shrinks to reveal border
        inner  = QRectF(r).adjusted(1.5, 1.5, -1.5, -1.5)
        bg_rgb = t.get('btn_bg', (10, 10, 22))
        dark   = QColor(bg_rgb[0], bg_rgb[1], bg_rgb[2], int(210 - 100 * self._h))
        p.setBrush(dark)
        p.drawRoundedRect(inner, radius - 1.5, radius - 1.5)

        # Text: accent color → white (dark themes) or text color (light theme) on hover
        if self._h > 0.5:
            bright = sum(bg_rgb) / 3
            p.setPen(QColor('#ffffff') if bright < 128 else QColor(t['text']))
        else:
            p.setPen(QColor(t['a1']))
        f = p.font(); f.setPointSize(10); f.setBold(True); p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())


class SmallButton(QPushButton):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh()
        theme_sig.changed.connect(self._refresh)

    def _refresh(self):
        t = T()
        light = sum(t['bg'][0]) / 3 > 128
        bg     = "rgba(0,0,0,10)"   if light else "rgba(255,255,255,18)"
        border = "rgba(0,0,0,18)"   if light else "rgba(255,255,255,28)"
        hover  = "rgba(0,0,0,20)"   if light else "rgba(255,255,255,30)"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg}; color: {t['text']};
                border: 1px solid {border}; border-radius: 8px;
                padding: 0 14px; font-size: 10pt;
            }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:disabled {{ color: {t['dim']}; }}
        """)


# ── Icon Button ────────────────────────────────────────────────────────────

class DangerButton(QPushButton):
    """Bouton d'interruption : rouge pastel dérivé du thème actif."""

    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh()
        theme_sig.changed.connect(self._refresh)

    def _refresh(self):
        t = T()
        c = QColor(t['err'])
        r_, g_, b_ = c.red(), c.green(), c.blue()
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba({r_},{g_},{b_},26);
                color: {t['err']};
                border: 1.5px solid rgba({r_},{g_},{b_},140);
                border-radius: 19px; padding: 0 28px;
                font-size: 10pt; font-weight: bold;
            }}
            QPushButton:hover  {{ background: rgba({r_},{g_},{b_},48); }}
            QPushButton:disabled {{
                color: {t['dim']};
                border-color: rgba({r_},{g_},{b_},60);
                background: rgba({r_},{g_},{b_},12);
            }}
        """)


class IconButton(QPushButton):
    """Small square button that paints a vector icon (no emoji)."""

    def __init__(self, icon_type: str, tip: str, parent=None):
        super().__init__(parent)
        self._icon_type = icon_type   # 'folder' or 'photo'
        self._h         = 0.0
        self._anim      = QPropertyAnimation(self, b'_hov', self)
        self._anim.setDuration(150)
        self.setFixedSize(28, 28)
        self.setToolTip(tip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        theme_sig.changed.connect(self.update)

    def _get_h(self): return self._h
    def _set_h(self, v): self._h = v; self.update()
    _hov = pyqtProperty(float, _get_h, _set_h)

    def enterEvent(self, e): self._anim.stop(); self._anim.setEndValue(1.0); self._anim.start()
    def leaveEvent(self, e): self._anim.stop(); self._anim.setEndValue(0.0); self._anim.start()

    def paintEvent(self, _):
        t  = T()
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Hover background circle
        if self._h > 0.01:
            p.setBrush(QColor(255, 255, 255, int(28 * self._h)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(1, 1, 26, 26), 5, 5)

        ic = QColor(t['a1'])
        ic.setAlpha(int(160 + 95 * self._h))
        p.setBrush(ic)
        p.setPen(Qt.PenStyle.NoPen)

        if self._icon_type == 'folder':
            # Tab flap
            p.drawRoundedRect(QRectF(4, 8, 9, 4), 2, 2)
            # Body
            p.drawRoundedRect(QRectF(4, 10, 20, 12), 2, 2)
        else:   # 'photo'
            # Frame outline
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ic, 1.5))
            p.drawRoundedRect(QRectF(4, 5, 20, 18), 3, 3)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ic)
            # Sun circle
            p.drawEllipse(QRectF(17, 8, 4, 4))
            # Mountain triangle
            path = QPainterPath()
            path.moveTo(5, 21); path.lineTo(13, 11); path.lineTo(21, 21)
            path.closeSubpath()
            p.fillPath(path, ic)


# ── Folder Card ────────────────────────────────────────────────────────────

class FolderCard(QWidget):
    clicked  = pyqtSignal(dict)
    open_exp = pyqtSignal(str)
    open_xnv = pyqtSignal(str)

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data  = data
        self._h    = 0.0
        self._anim = QPropertyAnimation(self, b'_hov', self)
        self._anim.setDuration(180)
        self.setFixedHeight(54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        theme_sig.changed.connect(self.update)

        # Watchdog: force _h to 0 if mouse drifted away without triggering leaveEvent
        self._watchdog = QTimer(self)
        self._watchdog.timeout.connect(self._check_hover_out)
        self._watchdog.start(120)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 0, 8, 0)
        lay.setSpacing(6)

        self._lbl_path = QLabel(data.get('display', ''))
        f = self._lbl_path.font(); f.setPointSize(11)
        if data.get('is_prio', False): f.setBold(True)
        self._lbl_path.setFont(f)
        lay.addWidget(self._lbl_path, 1)

        count = data.get('count', -1)
        cnt_s = f"({count} fichier{'s' if count > 1 else ''})" if count > 0 else "…"
        self._lbl_count = QLabel(cnt_s)
        f2 = self._lbl_count.font(); f2.setPointSize(10); self._lbl_count.setFont(f2)
        self._lbl_count.setFixedWidth(115)
        self._lbl_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._lbl_count)

        self._btn_exp = IconButton('folder', "Ouvrir dans l'Explorateur")
        self._btn_xnv = IconButton('photo',  "Ouvrir dans XnView")
        self._btn_exp.clicked.connect(lambda: self.open_exp.emit(self.data['path']))
        self._btn_xnv.clicked.connect(lambda: self.open_xnv.emit(self.data['path']))
        lay.addWidget(self._btn_exp)
        lay.addWidget(self._btn_xnv)

        # Relay child enter/leave so hover animation stays smooth
        for w in [self._lbl_path, self._lbl_count, self._btn_exp, self._btn_xnv]:
            w.installEventFilter(self)

        self._apply_theme()
        theme_sig.changed.connect(self._apply_theme)

    def _apply_theme(self):
        t = T()
        self._lbl_path.setStyleSheet(f"background: transparent; color: {t['text']};")
        self._lbl_count.setStyleSheet(f"background: transparent; color: {t['dim']};")

    def eventFilter(self, obj, e):
        if e.type() == e.Type.Enter:
            self._anim.stop(); self._anim.setEndValue(1.0); self._anim.start()
        elif e.type() == e.Type.Leave:
            QTimer.singleShot(0, self._check_hover_out)
        return super().eventFilter(obj, e)

    def _check_hover_out(self):
        pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(pos):
            self._anim.stop(); self._anim.setEndValue(0.0); self._anim.start()

    def _get_h(self): return self._h
    def _set_h(self, v):
        self._h = v
        self.update()
    _hov = pyqtProperty(float, _get_h, _set_h)

    def enterEvent(self, e): self._anim.stop(); self._anim.setEndValue(1.0); self._anim.start()
    def leaveEvent(self, e): QTimer.singleShot(0, self._check_hover_out)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.data)

    def paintEvent(self, _):
        t      = T()
        count  = self.data.get('count', -1)
        is_prio = self.data.get('is_prio', False)
        if count == 0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -3)
        accent = QColor(t['prio'] if is_prio else t['a1'])

        # Opaque base from theme — guarantees readable text regardless of compositing
        p.setBrush(QColor(*t.get('card_bg', (14, 15, 35, 255))))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 8, 8)

        # Subtle accent tint on hover
        if self._h > 0.02:
            tint = QColor(accent); tint.setAlpha(int(50 * self._h))
            p.setBrush(tint)
            p.drawRoundedRect(r, 8, 8)

        # Left accent bar
        bar = QColor(accent); bar.setAlpha(int(160 + 95 * self._h))
        p.setBrush(bar)
        p.drawRoundedRect(QRect(r.x(), r.y(), 4, r.height()), 2, 2)

        # "Trier ce dossier" hint — fades in on hover, drawn in path label area
        if self._h > 0.01:
            path_geo = self._lbl_path.geometry()
            hint_r   = QRect(path_geo.left(), path_geo.top(),
                             path_geo.width() - 8, path_geo.height())
            p.setOpacity(self._h)
            p.setPen(QColor(t['a1']))
            hf = p.font(); hf.setPointSize(9); hf.setItalic(True); p.setFont(hf)
            p.drawText(hint_r,
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       "▶  Trier ce dossier")
            p.setOpacity(1.0)


# ── Animated Progress Bar ──────────────────────────────────────────────────

class AnimatedProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._val   = 0.0
        self._shift = 0.0
        self.setFixedHeight(22)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._val_anim = QPropertyAnimation(self, b'_pval', self)
        self._val_anim.setDuration(300)
        self._val_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._ticker = QTimer(self)
        self._ticker.timeout.connect(self._tick)
        self._ticker.start(16)
        theme_sig.changed.connect(self.update)

    def _tick(self):
        if self._val > 0.001:
            self._shift = (self._shift + 0.011) % 1.0
            self.update()

    def _get_v(self): return self._val
    def _set_v(self, v): self._val = v; self.update()
    _pval = pyqtProperty(float, _get_v, _set_v)

    def set_progress(self, cur: int, total: int):
        target = cur / total if total else 0.0
        self._val_anim.stop()
        self._val_anim.setEndValue(target)
        self._val_anim.start()

    def paintEvent(self, _):
        t  = T()
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r  = self.rect()

        # Track
        p.setBrush(QColor(20, 20, 45))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 11, 11)

        fw = int(r.width() * self._val)
        if fw < 6:
            return

        fr = QRect(r.x(), r.y(), fw, r.height())

        # Animated gradient fill
        c1   = QColor(t['a1']); c2 = QColor(t['a2'])
        s    = self._shift
        grad = QLinearGradient(fr.left(), 0, fr.right(), 0)
        grad.setColorAt(s % 1.0,           c1)
        grad.setColorAt((s + 0.5) % 1.0,   c2)
        if s + 0.5 > 1.0:
            grad.setColorAt(0.0, c2)
        p.setBrush(grad)
        p.drawRoundedRect(fr, 11, 11)

        # Shimmer sweep
        sx = fr.left() + int(fr.width() * (self._shift % 1.0))
        sg = QLinearGradient(sx - 45, 0, sx + 45, 0)
        sg.setColorAt(0,   QColor(255, 255, 255, 0))
        sg.setColorAt(0.5, QColor(255, 255, 255, 50))
        sg.setColorAt(1,   QColor(255, 255, 255, 0))
        p.setBrush(sg)
        p.drawRoundedRect(fr, 11, 11)


# ── Log Widget ─────────────────────────────────────────────────────────────

class LogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea, QWidget { background: transparent; border: none; }")

        self._box = QWidget()
        self._box.setStyleSheet("background: transparent;")
        self._vbox = QVBoxLayout(self._box)
        self._vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._vbox.setSpacing(1)
        self._vbox.setContentsMargins(10, 8, 10, 8)
        self._scroll.setWidget(self._box)
        lay.addWidget(self._scroll)

    def add(self, kind: str, msg: str):
        t = T()
        color_map = {
            'move':  t['a1'],  'skip':  t['dim'],
            'error': t['err'], 'new':   t['ok'],  'info': t['warn'],
        }
        prefix_map = {
            'move':  '[DÉPLACÉ]', 'skip':  '[IGNORÉ ]',
            'error': '[ERREUR ]', 'new':   '[NOUVEAU]', 'info': '[INFO   ]',
        }
        color  = color_map.get(kind,  t['text'])
        prefix = prefix_map.get(kind, '[      ]')

        lbl = QLabel(
            f'<span style="color:{color};font-family:Consolas,monospace;">{prefix}</span>'
            f'<span style="color:{t["text"]};font-family:Consolas,monospace;">  {msg}</span>'
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet("background: transparent; font-size: 10pt;")

        eff  = QGraphicsOpacityEffect(lbl); eff.setOpacity(0)
        lbl.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(280); anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(); lbl._anim = anim

        self._vbox.addWidget(lbl)
        QTimer.singleShot(40, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()))

    def clear(self):
        while self._vbox.count():
            item = self._vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# ── Stat Card ──────────────────────────────────────────────────────────────

class StatCard(GlassPanel):
    def __init__(self, label: str, color_key: str, parent=None):
        super().__init__(parent)
        self.color_key = color_key
        self.setFixedSize(145, 108)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._num = QLabel("0")
        self._num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl = QLabel(label)
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._num)
        lay.addWidget(self._lbl)
        self._refresh_style()
        theme_sig.changed.connect(self._refresh_style)

    def _refresh_style(self):
        t = T()
        color = t.get(self.color_key, t['text'])
        self._num.setStyleSheet(
            f"font-size: 26pt; font-weight: bold; color: {color}; background: transparent;")
        self._lbl.setStyleSheet(
            f"font-size: 9pt; color: {t['dim']}; letter-spacing: 1px; background: transparent;")

    def animate_to(self, target: int):
        self._target = target
        self._cur    = 0.0
        self._step   = max(1.0, target / 25.0)
        self._ctimer = QTimer(self)
        self._ctimer.timeout.connect(self._tick)
        self._ctimer.start(18)

    def _tick(self):
        self._cur = min(self._cur + self._step, self._target)
        self._num.setText(str(int(self._cur)))
        if self._cur >= self._target:
            self._num.setText(str(self._target))
            self._ctimer.stop()


# ── Fade Stacked Widget ────────────────────────────────────────────────────

class FadeStack(QStackedWidget):
    def switch_to(self, index: int):
        if index == self.currentIndex():
            return
        nw = self.widget(index)
        if not nw:
            return
        eff = QGraphicsOpacityEffect(nw)
        eff.setOpacity(0)
        nw.setGraphicsEffect(eff)
        super().setCurrentIndex(index)
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(260)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: nw.setGraphicsEffect(None))
        anim.start()
        self._sw_anim = anim


# ── Folder List View ───────────────────────────────────────────────────────

class FolderListView(QWidget):
    folder_selected  = pyqtSignal(dict)
    browse_requested = pyqtSignal()
    options_opened   = pyqtSignal()
    about_opened     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._folders = []
        self._page    = 0
        self._pool    = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(8)
        self._worker  = None
        self._refresh_debounce = QTimer()
        self._refresh_debounce.setSingleShot(True)
        self._refresh_debounce.setInterval(60)
        self._refresh_debounce.timeout.connect(self._do_refresh_page)
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(14)

        # Header : titre à gauche — À propos / Options en haut à droite,
        # compteur de dossiers juste en dessous
        hdr = QHBoxLayout()
        self._title = QLabel("Sélectionner un dossier")
        hdr.addWidget(self._title)
        hdr.addStretch()
        right_col = QVBoxLayout()
        right_col.setSpacing(4)
        btns = QHBoxLayout()
        btns.setSpacing(8)
        self._btn_about = GradientButton("ℹ  À propos")
        self._btn_about.setFixedWidth(126)
        self._btn_about.clicked.connect(self.about_opened)
        self._btn_options = GradientButton("⚙  Options")
        self._btn_options.setFixedWidth(126)
        self._btn_options.clicked.connect(self.options_opened)
        btns.addWidget(self._btn_about)
        btns.addWidget(self._btn_options)
        right_col.addLayout(btns)
        self._status = QLabel("…")
        self._status.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._status)
        hdr.addLayout(right_col)
        lay.addLayout(hdr)

        # Cards panel
        self._panel = GlassPanel()
        p_lay = QVBoxLayout(self._panel)
        p_lay.setContentsMargins(10, 10, 10, 10)

        self._cards_w = QWidget()
        self._cards_w.setStyleSheet("background: transparent;")
        self._cards_lay = QVBoxLayout(self._cards_w)
        self._cards_lay.setContentsMargins(0, 0, 0, 0)
        self._cards_lay.setSpacing(4)
        self._cards_lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        scr = QScrollArea()
        scr.setWidget(self._cards_w)
        scr.setWidgetResizable(True)
        scr.setFrameShape(QFrame.Shape.NoFrame)
        scr.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scr.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        p_lay.addWidget(scr)
        lay.addWidget(self._panel, 1)

        # Bottom bar
        bot = QHBoxLayout()
        self._btn_prev = SmallButton("◀  Précédent")
        self._btn_prev.setFixedWidth(130)
        self._btn_prev.clicked.connect(self._go_prev)
        self._page_lbl = QLabel()
        self._page_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_next = SmallButton("Suivant  ▶")
        self._btn_next.setFixedWidth(130)
        self._btn_next.clicked.connect(self._go_next)

        bot.addStretch(1)
        bot.addWidget(self._btn_prev)
        bot.addWidget(self._page_lbl)
        bot.addWidget(self._btn_next)
        bot.addStretch(1)

        self._btn_browse  = GradientButton("📁  Parcourir")
        self._btn_browse.setFixedWidth(148)
        self._btn_browse.setToolTip(
            "<b style='font-size:11pt;'>📁 Parcourir</b><br/><br/>"
            "Sélectionne un <b>dossier racine</b> à explorer<br/>"
            "et affiche les sous-dossiers qu'il contient.<br/><br/>"
            "<span style='opacity:0.7;'>Structure attendue :</span><br/>"
            "&nbsp;&nbsp;racine / <b>année</b> / <b>mois</b><br/>"
            "<span style='font-size:9pt; opacity:0.55;'>"
            "ex&nbsp;: E:\\Photos\\2026\\03&nbsp;Mars</span>")
        self._btn_browse.clicked.connect(self.browse_requested)
        self._btn_browse.installEventFilter(_instant_tip)

        bot.addWidget(self._btn_browse)
        lay.addLayout(bot)

        self._refresh_theme_labels()
        theme_sig.changed.connect(self._refresh_theme_labels)

    def _refresh_theme_labels(self):
        t = T()
        self._title.setStyleSheet(
            f"font-size: 18pt; font-weight: bold; color: {t['a1']}; background: transparent;")
        self._status.setStyleSheet(
            f"color: {t['dim']}; font-size: 10pt; background: transparent;")
        self._page_lbl.setStyleSheet(
            f"color: {t['dim']}; background: transparent; min-width: 80px;")

    def start_scan(self, root: str | None = None):
        self._folders = []
        self._page    = 0
        self._clear_cards()
        self._status.setText("Scan en cours…")
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(800)
        self._worker = FolderScanWorker(root or get_root(), get_prios())
        self._worker.folder_found.connect(self._on_folder)
        self._worker.done.connect(self._on_scan_done)
        self._worker.start()

    def _on_folder(self, data: dict):
        self._folders.append(data)
        w = CountWorker(data['path'])
        w.signals.done.connect(self._on_count)
        self._pool.start(w)
        self._refresh_page()

    def _on_count(self, path: str, n: int):
        for f in self._folders:
            if f['path'] == path:
                f['count'] = n
                break
        self._refresh_page()

    def _on_scan_done(self):
        self._status.setText(f"{len(self._visible())} dossier(s) trouvé(s)")
        self._refresh_page()

    def _refresh_page(self):
        self._refresh_debounce.start()

    def _visible(self):
        return [f for f in self._folders if f.get('count', -1) != 0]

    def _clear_cards(self):
        while self._cards_lay.count():
            item = self._cards_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _do_refresh_page(self):
        vis   = self._visible()
        total = max(1, math.ceil(len(vis) / PAGE_SIZE))
        self._page = min(self._page, total - 1)
        items = vis[self._page * PAGE_SIZE : (self._page + 1) * PAGE_SIZE]

        self._clear_cards()
        for fd in items:
            card = FolderCard(fd)
            card.clicked.connect(self.folder_selected)
            card.open_exp.connect(open_in_explorer)
            card.open_xnv.connect(open_in_xnview)

            eff  = QGraphicsOpacityEffect(card)
            eff.setOpacity(0)
            card.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", card)
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(lambda c=card: c.setGraphicsEffect(None))
            anim.start()
            card._fade_anim = anim
            self._cards_lay.addWidget(card)

        self._page_lbl.setText(f"Page {self._page + 1} / {total}")
        self._btn_prev.setEnabled(self._page > 0)
        self._btn_next.setEnabled(self._page < total - 1)

    def _go_prev(self):
        if self._page > 0:
            self._page -= 1
            self._refresh_page()

    def _go_next(self):
        vis = self._visible()
        if self._page < math.ceil(len(vis) / PAGE_SIZE) - 1:
            self._page += 1
            self._refresh_page()


# ── Process View ───────────────────────────────────────────────────────────

class ProcessView(QWidget):
    done = pyqtSignal(int, int, int, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(14)

        self._title = QLabel("Organisation en cours…")
        lay.addWidget(self._title)

        self._path_lbl = QLabel()
        self._path_lbl.setWordWrap(True)
        lay.addWidget(self._path_lbl)

        prog_panel = GlassPanel()
        p_lay = QVBoxLayout(prog_panel)
        p_lay.setContentsMargins(18, 14, 18, 14)
        self._bar = AnimatedProgressBar()
        p_lay.addWidget(self._bar)
        self._prog_lbl = QLabel("Démarrage…")
        self._prog_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_lay.addWidget(self._prog_lbl)
        lay.addWidget(prog_panel)

        log_panel = GlassPanel()
        l_lay = QVBoxLayout(log_panel)
        l_lay.setContentsMargins(0, 0, 0, 0)
        self._log = LogWidget()
        l_lay.addWidget(self._log)
        lay.addWidget(log_panel, 1)

        self._refresh_theme()
        theme_sig.changed.connect(self._refresh_theme)

    def _refresh_theme(self):
        t = T()
        self._title.setStyleSheet(
            f"font-size: 18pt; font-weight: bold; color: {t['a1']}; background: transparent;")
        self._path_lbl.setStyleSheet(
            f"color: {t['dim']}; font-size: 10pt; background: transparent;")
        self._prog_lbl.setStyleSheet(
            f"color: {t['text']}; margin-top: 5px; background: transparent;")

    def start(self, folder_data: dict):
        exif = find_exiftool()
        if not exif:
            QMessageBox.warning(self, "ExifTool introuvable",
                "ExifTool n'a pas été trouvé.\nConfigurez son emplacement dans Options.")
            return

        self._path_lbl.setText(folder_data['path'])
        self._log.clear()
        self._bar.set_progress(0, 1)
        self._prog_lbl.setText("Démarrage…")

        self._worker = OrganiseWorker(folder_data['path'], exif)
        self._worker.log_entry.connect(self._on_log)
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self.done)
        self._worker.start()

    def _on_log(self, kind: str, msg: str):
        self._log.add(kind, msg)

    def _on_progress(self, cur: int, total: int):
        self._bar.set_progress(cur, total)
        pct = int(cur / total * 100) if total else 0
        self._prog_lbl.setText(f"{cur} / {total} fichiers  —  {pct}%")


# ── Summary View ───────────────────────────────────────────────────────────

class SummaryView(QWidget):
    back = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 50, 28, 50)
        lay.setSpacing(28)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._done_lbl = QLabel("✓  TERMINÉ")
        self._done_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._done_lbl)

        row = QHBoxLayout()
        row.setSpacing(14)
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._c_total   = StatCard("TOTAL",    'text')
        self._c_moved   = StatCard("DÉPLACÉS", 'a1')
        self._c_skipped = StatCard("IGNORÉS",  'warn')
        self._c_errors  = StatCard("ERREURS",  'err')
        for c in [self._c_total, self._c_moved, self._c_skipped, self._c_errors]:
            row.addWidget(c)
        lay.addLayout(row)

        self._dur_lbl = QLabel()
        self._dur_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._dur_lbl)

        btn_back = GradientButton("← Retour à la liste")
        btn_back.setFixedWidth(210)
        btn_back.clicked.connect(self.back)
        brow = QHBoxLayout()
        brow.addStretch(); brow.addWidget(btn_back); brow.addStretch()
        lay.addLayout(brow)

        self._refresh_theme()
        theme_sig.changed.connect(self._refresh_theme)

    def _refresh_theme(self):
        t = T()
        self._done_lbl.setStyleSheet(
            f"font-size: 30pt; font-weight: bold; color: {t['ok']}; background: transparent;")
        self._dur_lbl.setStyleSheet(
            f"color: {t['dim']}; background: transparent;")

    def show_results(self, moved: int, skipped: int, errors: int, elapsed: float):
        total = moved + skipped + errors
        for card, val in [(self._c_total, total), (self._c_moved, moved),
                          (self._c_skipped, skipped), (self._c_errors, errors)]:
            card.animate_to(val)
        self._dur_lbl.setText(f"Durée : {elapsed:.2f} s")

        eff  = QGraphicsOpacityEffect(self._done_lbl)
        eff.setOpacity(0)
        self._done_lbl.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(700); anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(); self._done_anim = anim


# ── USB Count Worker ───────────────────────────────────────────────────────

class _UsbCountWorker(QThread):
    result   = pyqtSignal(int)   # final count
    partial  = pyqtSignal(int)   # intermediate updates
    names    = pyqtSignal(list)  # noms des fichiers trouvés

    def __init__(self, dcim_path: str):
        super().__init__()
        self._dcim = dcim_path
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            all_ext = get_all_ext()
            found: list[str] = []
            for root, dirs, files in os.walk(self._dcim):
                dirs[:] = [d for d in dirs if d.lower() != "_old"]
                if self._stop:
                    break
                for fname in files:
                    if os.path.splitext(fname)[1].lower() in all_ext:
                        found.append(fname)
                self.partial.emit(len(found))
            count = len(found)
            log.debug("_UsbCountWorker : %d fichiers dans %s", count, self._dcim)
            self.names.emit(found)
            self.result.emit(count)
        except Exception:
            log.exception("_UsbCountWorker exception")
            self.names.emit([])
            self.result.emit(0)


# ── MTP Scan Worker (détection appareil) ────────────────────────────────────

class _MtpScanWorker(QThread):
    found     = pyqtSignal(str)   # device_name
    not_found = pyqtSignal()

    def run(self):
        try:
            result = find_mtp_camera()
            if result:
                self.found.emit(result[0])
            else:
                self.not_found.emit()
        except Exception:
            log.exception("_MtpScanWorker exception")
            self.not_found.emit()


# ── MTP : chemin par défaut (DCIM/Camera) ───────────────────────────────────

class _MtpDefaultPathWorker(QThread):
    """Trouve DCIM/Camera et liste ses dossiers voisins (pour le menu)."""
    result = pyqtSignal(list, list)   # parts, voisins [{'name','parts','items'}]

    def run(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                parts = _mtp_default_path('Camera') or []
                siblings = _mtp_children(parts[:-1]) if len(parts) > 1 else []
                self.result.emit(parts, siblings)
            finally:
                pythoncom.CoUninitialize()
        except Exception:
            log.exception("_MtpDefaultPathWorker exception")
            self.result.emit([], [])


# ── MTP : contenu d'un dossier (navigateur) ─────────────────────────────────

class _MtpBrowseWorker(QThread):
    """Liste les sous-dossiers d'un chemin MTP + le nombre de photos qu'il contient."""
    result = pyqtSignal(list, list, int)   # parts, sous-dossiers, nb médias

    def __init__(self, parts: list[str]):
        super().__init__()
        self._parts = list(parts)

    def run(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                children = _mtp_children(self._parts)
                media    = (len(_mtp_media_names(self._parts))
                            if self._parts else 0)
                self.result.emit(self._parts, children, media)
            finally:
                pythoncom.CoUninitialize()
        except Exception:
            log.exception("_MtpBrowseWorker exception")
            self.result.emit(self._parts, [], 0)


# ── Menu déroulant (style « bouton pop-up » macOS) ──────────────────────────

class PopupSelect(QPushButton):
    """Sélecteur clair : libellé + chevron, menu au clic.

    Plus lisible qu'une QComboBox : on voit tout de suite que c'est cliquable.
    """
    BROWSE = "__browse__"

    selected = pyqtSignal(object)   # donnée associée à l'entrée choisie
    browse_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[tuple[str, object]] = []
        self._current = None
        self._browse_label = ""
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self.setMinimumWidth(240)
        self.clicked.connect(self._open_menu)
        self._refresh_style()
        theme_sig.changed.connect(self._refresh_style)

    # ── API ────────────────────────────────────────────────────────────────
    def set_entries(self, entries: list[tuple[str, object]]):
        self._entries = list(entries)

    def set_browse(self, label: str):
        """Ajoute une entrée « Parcourir… » en bas du menu."""
        self._browse_label = label

    def set_current(self, label: str, data=None):
        self._current = data
        self.setText(label)
        self.update()

    def current_data(self):
        return self._current

    # ── Rendu ──────────────────────────────────────────────────────────────
    def _refresh_style(self):
        t = T()
        light = sum(t['bg'][0]) / 3 > 128
        bg    = "rgba(255,255,255,235)" if light else "rgba(255,255,255,16)"
        hov   = "rgba(255,255,255,255)" if light else "rgba(255,255,255,26)"
        brd   = "rgba(0,0,0,28)"        if light else "rgba(255,255,255,38)"
        menu_bg = "#ffffff" if light else f"rgb{t['panel'][:3]}"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg}; color: {t['text']};
                border: 1px solid {brd}; border-radius: 9px;
                padding: 0 34px 0 14px; font-size: 10pt; text-align: left;
            }}
            QPushButton:hover  {{ background: {hov}; border-color: {t['a1']}; }}
            QPushButton:disabled {{ color: {t['dim']}; }}
            QMenu {{
                background: {menu_bg}; color: {t['text']};
                border: 1px solid {brd}; border-radius: 10px; padding: 6px;
            }}
            QMenu::item {{ padding: 7px 26px 7px 14px; border-radius: 6px; }}
            QMenu::item:selected {{ background: {t['a1']}; color: {'#000' if light else '#fff'}; }}
            QMenu::separator {{ height: 1px; background: {brd}; margin: 6px 8px; }}
        """)
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        t = T()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Chevron « ▾ » dessiné à droite : signale sans ambiguïté un menu
        cx, cy = self.width() - 20, self.height() / 2
        pen = QPen(QColor(t['a1']), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(int(cx - 5), int(cy - 2), int(cx), int(cy + 3))
        p.drawLine(int(cx), int(cy + 3), int(cx + 5), int(cy - 2))

    # ── Menu ───────────────────────────────────────────────────────────────
    def _open_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self.styleSheet())
        for label, data in self._entries:
            act = menu.addAction(("✓  " if data == self._current else "     ") + label)
            act.triggered.connect(lambda _=False, d=data, l=label: self._choose(l, d))
        if self._browse_label:
            if self._entries:
                menu.addSeparator()
            act = menu.addAction(self._browse_label)
            act.triggered.connect(lambda _=False: self.browse_requested.emit())
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def _choose(self, label: str, data):
        self.set_current(label, data)
        self.selected.emit(data)


# ── Ligne de dossier du navigateur téléphone ────────────────────────────────

class _MtpFolderRow(QWidget):
    """Ligne « dossier » : nom, nombre d'éléments, chevron d'ouverture."""

    def __init__(self, name: str, items: int, parent=None):
        super().__init__(parent)
        t = T()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(12)
        icon = QLabel("📁")
        icon.setStyleSheet("font-size: 15pt; background: transparent;")
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"font-size: 11pt; color: {t['text']}; background: transparent;")
        count_lbl = QLabel("vide" if items == 0
                           else f"{items} élément" + ("s" if items > 1 else ""))
        count_lbl.setStyleSheet(
            f"font-size: 9pt; color: {t['dim']}; background: transparent;")
        chev = QLabel("›")
        chev.setStyleSheet(
            f"font-size: 15pt; color: {t['dim']}; background: transparent;")
        lay.addWidget(icon)
        lay.addWidget(name_lbl)
        lay.addStretch()
        lay.addWidget(count_lbl)
        lay.addWidget(chev)


# ── Navigateur de dossiers du téléphone ─────────────────────────────────────

class MtpFolderDialog(QDialog):
    """Choix visuel d'un dossier sur le téléphone (un clic = on entre)."""

    def __init__(self, device: str, start_parts: list[str], parent=None):
        super().__init__(parent)
        self._device = device
        self._parts  = list(start_parts) or [device]
        self._chosen: list[str] | None = None
        self._media  = 0
        self._worker: _MtpBrowseWorker | None = None
        self.setWindowTitle("Choisir un dossier sur le téléphone")
        self.setMinimumSize(620, 520)
        self._build_style()
        self._setup_ui()
        theme_sig.changed.connect(self._build_style)
        self._load(self._parts)

    # ── Style ──────────────────────────────────────────────────────────────
    def _build_style(self):
        t = T()
        r, g, b = t['panel'][:3]
        light = (r + g + b) / 3 > 128
        row_bg  = "rgba(0,0,0,8)"   if light else "rgba(255,255,255,10)"
        row_hov = "rgba(0,0,0,18)"  if light else "rgba(255,255,255,22)"
        btn_bg  = "rgba(0,0,0,10)"  if light else "rgba(255,255,255,18)"
        btn_brd = "rgba(0,0,0,18)"  if light else "rgba(255,255,255,28)"
        self.setStyleSheet(f"""
            QDialog {{ background: rgb({r},{g},{b}); }}
            QLabel  {{ color: {t['text']}; background: transparent; }}
            QListWidget {{
                background: transparent; border: none; outline: none;
            }}
            QListWidget::item {{
                background: {row_bg}; border-radius: 10px; margin: 3px 0;
            }}
            QListWidget::item:hover    {{ background: {row_hov}; }}
            QListWidget::item:selected {{ background: {row_hov}; }}
            QPushButton {{
                background: {btn_bg}; color: {t['text']};
                border: 1px solid {btn_brd}; border-radius: 9px;
                padding: 8px 18px; font-size: 10pt;
            }}
            QPushButton:hover {{ background: {row_hov}; }}
        """)

    # ── Interface ──────────────────────────────────────────────────────────
    def _setup_ui(self):
        t   = T()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 20)
        lay.setSpacing(14)

        title = QLabel("Où sont vos photos ?")
        title.setStyleSheet(
            f"font-size: 16pt; font-weight: bold; color: {t['a1']};")
        subtitle = QLabel(
            f"Parcourez {self._device} et choisissez le dossier à importer.")
        subtitle.setStyleSheet(f"font-size: 10pt; color: {t['dim']};")
        lay.addWidget(title)
        lay.addWidget(subtitle)

        # Fil d'Ariane + retour
        crumb_row = QHBoxLayout()
        crumb_row.setSpacing(8)
        self._btn_back = QPushButton("‹  Retour")
        self._btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_back.clicked.connect(self._go_up)
        crumb_row.addWidget(self._btn_back)
        self._crumb_lbl = QLabel("")
        self._crumb_lbl.setStyleSheet(
            f"font-size: 10pt; font-weight: bold; color: {t['text']};")
        crumb_row.addWidget(self._crumb_lbl)
        crumb_row.addStretch()
        lay.addLayout(crumb_row)

        # Liste des sous-dossiers
        self._list = QListWidget()
        self._list.setSpacing(0)
        self._list.setCursor(Qt.CursorShape.PointingHandCursor)
        self._list.itemClicked.connect(self._on_item)
        lay.addWidget(self._list, 1)

        self._empty_lbl = QLabel("")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(f"font-size: 10pt; color: {t['dim']};")
        lay.addWidget(self._empty_lbl)

        # Pied : contenu du dossier courant + validation
        foot = QHBoxLayout()
        foot.setSpacing(10)
        self._info_lbl = QLabel("")
        self._info_lbl.setStyleSheet(f"font-size: 10pt; color: {t['text']};")
        foot.addWidget(self._info_lbl)
        foot.addStretch()
        btn_cancel = QPushButton("Annuler")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        foot.addWidget(btn_cancel)
        self._btn_ok = GradientButton("Choisir ce dossier")
        self._btn_ok.setMinimumWidth(190)
        self._btn_ok.clicked.connect(self._accept_current)
        foot.addWidget(self._btn_ok)
        lay.addLayout(foot)

    # ── Navigation ─────────────────────────────────────────────────────────
    def _load(self, parts: list[str]):
        self._parts = list(parts)
        self._list.clear()
        self._empty_lbl.setText("⏳  Lecture du téléphone…")
        self._info_lbl.setText("")
        self._btn_back.setEnabled(len(self._parts) > 1)
        self._crumb_lbl.setText("📱  " + (_mtp_path_label(self._parts)
                                          or self._device))
        if self._worker is not None and self._worker.isRunning():
            self._worker.terminate()
        self._worker = _MtpBrowseWorker(self._parts)
        self._worker.result.connect(self._on_loaded)
        self._worker.start()

    def _on_loaded(self, parts: list, children: list, media: int):
        if list(parts) != self._parts:
            return
        self._media = media
        self._list.clear()
        for child in sorted(children, key=lambda c: c['name'].lower()):
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 48))
            item.setData(Qt.ItemDataRole.UserRole, child['parts'])
            self._list.addItem(item)
            self._list.setItemWidget(
                item, _MtpFolderRow(child['name'], child['items']))
        if children:
            self._empty_lbl.setText("")
            self._empty_lbl.setVisible(False)
        else:
            self._empty_lbl.setVisible(True)
            self._empty_lbl.setText("Ce dossier ne contient pas de sous-dossier.")
        noun = "photo/vidéo" if media == 1 else "photos/vidéos"
        self._info_lbl.setText(
            f"📷  {media} {noun} dans ce dossier" if media
            else "Aucune photo directement dans ce dossier")

    def _on_item(self, item):
        parts = item.data(Qt.ItemDataRole.UserRole)
        if parts:
            self._load(list(parts))

    def _go_up(self):
        if len(self._parts) > 1:
            self._load(self._parts[:-1])

    def _accept_current(self):
        self._chosen = list(self._parts)
        self.accept()

    def chosen_path(self) -> list[str] | None:
        return self._chosen

    def closeEvent(self, e):
        if self._worker is not None and self._worker.isRunning():
            self._worker.terminate()
        super().closeEvent(e)


# ── MTP Count Worker ────────────────────────────────────────────────────────

class _MtpCountWorker(QThread):
    result  = pyqtSignal(int)
    partial = pyqtSignal(int)
    names   = pyqtSignal(list)  # noms des fichiers trouvés

    def __init__(self, parts: list[str] | None = None):
        super().__init__()
        self._parts = list(parts or [])
        self._stop  = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                found = _mtp_media_names(self._parts,
                                         stop=lambda: self._stop,
                                         on_progress=self.partial.emit)
                log.debug("_MtpCountWorker : %d fichiers dans %s",
                          len(found), "/".join(self._parts[1:]))
                self.names.emit(found)
                self.result.emit(len(found))
            finally:
                pythoncom.CoUninitialize()
        except Exception:
            log.exception("_MtpCountWorker exception")
            self.names.emit([])
            self.result.emit(0)


# ── USB Action Button ──────────────────────────────────────────────────────

class _UsbActionButton(QWidget):
    clicked = pyqtSignal()

    # Rôle → couleurs. Tout vient du thème : une seule teinte d'accent,
    # le rouge réservé à l'action destructrice, le neutre pour le reste.
    ROLE_PRIMARY = 'primary'
    ROLE_WARNING = 'warning'
    ROLE_DANGER  = 'danger'
    ROLE_NEUTRAL = 'neutral'

    def __init__(self, emoji: str, label: str, desc: str,
                 role: str = 'primary', parent=None):
        super().__init__(parent)
        self._emoji  = emoji
        self._label  = label
        self._desc   = desc
        self._role   = role
        self._count  = ""     # pastille « 653 fichiers »
        self._hov    = 0.0
        self._enabled = True
        self._active  = False
        self._pls     = 0.0
        self._pls_fwd = True
        self.setFixedHeight(172)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._anim = QPropertyAnimation(self, b"_h", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._pulse_anim = QPropertyAnimation(self, b"_pulse_prop", self)
        self._pulse_anim.setDuration(800)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.finished.connect(self._on_pulse_done)
        theme_sig.changed.connect(self.update)

    @property
    def _colors(self) -> tuple[str, str]:
        """(teinte principale, teinte secondaire) selon le rôle et le thème."""
        t = T()
        if self._role == self.ROLE_DANGER:
            return (t['err'], t['err'])
        if self._role == self.ROLE_WARNING:
            return (t['warn'], t['warn'])
        if self._role == self.ROLE_NEUTRAL:
            return (t['dim'], t['dim'])
        return (t['a1'], t['a2'])

    @property
    def _border_alpha(self) -> int:
        return {'primary': 150, 'warning': 120,
                'danger': 120, 'neutral': 80}.get(self._role, 130)

    def _draw_icon(self, p: QPainter, r: QRectF, color: QColor):
        """Pictogramme simple, tracé au trait dans la couleur du bouton."""
        pen = QPen(color, 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        x, y, w, h = r.left(), r.top(), r.width(), r.height()
        cx = x + w / 2
        if self._role == self.ROLE_WARNING:
            # Boîte de rangement avec flèche entrante
            p.drawRoundedRect(QRectF(x + 3, y + h * 0.45, w - 6, h * 0.5), 3, 3)
            p.drawLine(int(x + 3), int(y + h * 0.62), int(x + w - 3), int(y + h * 0.62))
            p.drawLine(int(cx), int(y + 2), int(cx), int(y + h * 0.38))
            p.drawLine(int(cx - 5), int(y + h * 0.22), int(cx), int(y + h * 0.38))
            p.drawLine(int(cx + 5), int(y + h * 0.22), int(cx), int(y + h * 0.38))
        elif self._role == self.ROLE_DANGER:
            # Corbeille
            p.drawLine(int(x + 4), int(y + 8), int(x + w - 4), int(y + 8))
            p.drawLine(int(cx - 4), int(y + 5), int(cx + 4), int(y + 5))
            body = QRectF(x + 7, y + 8, w - 14, h - 12)
            p.drawRoundedRect(body, 3, 3)
            p.drawLine(int(cx - 3), int(y + 13), int(cx - 3), int(y + h - 8))
            p.drawLine(int(cx + 3), int(y + 13), int(cx + 3), int(y + h - 8))
        elif self._role == self.ROLE_NEUTRAL:
            # Œil (aperçu)
            path = QPainterPath()
            path.moveTo(x + 2, y + h / 2)
            path.quadTo(cx, y + 3, x + w - 2, y + h / 2)
            path.quadTo(cx, y + h - 3, x + 2, y + h / 2)
            p.drawPath(path)
            p.drawEllipse(QRectF(cx - 4, y + h / 2 - 4, 8, 8))
        else:
            # Flèche vers un bac (copie sur le disque)
            p.drawLine(int(cx), int(y + 3), int(cx), int(y + h - 12))
            p.drawLine(int(cx - 6), int(y + h - 18), int(cx), int(y + h - 12))
            p.drawLine(int(cx + 6), int(y + h - 18), int(cx), int(y + h - 12))
            p.drawLine(int(x + 4), int(y + h - 6), int(x + w - 4), int(y + h - 6))
            p.drawLine(int(x + 4), int(y + h - 10), int(x + 4), int(y + h - 6))
            p.drawLine(int(x + w - 4), int(y + h - 10), int(x + w - 4), int(y + h - 6))

    @pyqtProperty(float)
    def _h(self):
        return self._hov

    @_h.setter
    def _h(self, v):
        self._hov = v
        self.update()

    @pyqtProperty(float)
    def _pulse_prop(self):
        return self._pls

    @_pulse_prop.setter
    def _pulse_prop(self, v: float):
        self._pls = v
        self.update()

    def setEnabled(self, v: bool):
        self._enabled = v
        self.setCursor(Qt.CursorShape.PointingHandCursor if v
                       else Qt.CursorShape.ArrowCursor)
        self.update()

    def setCountText(self, text: str):
        """Pastille affichée au centre du bouton (nombre de fichiers traités)."""
        if text != self._count:
            self._count = text
            self.update()

    def setActive(self, v: bool):
        self._active = v
        if v:
            self._pls = 0.0
            self._pls_fwd = True
            self._pulse_anim.setStartValue(0.0)
            self._pulse_anim.setEndValue(1.0)
            self._pulse_anim.start()
        else:
            self._pulse_anim.stop()
            self._pls = 0.0
        self.update()

    def _on_pulse_done(self):
        if not self._active:
            return
        self._pls_fwd = not self._pls_fwd
        if self._pls_fwd:
            self._pulse_anim.setStartValue(0.0)
            self._pulse_anim.setEndValue(1.0)
        else:
            self._pulse_anim.setStartValue(1.0)
            self._pulse_anim.setEndValue(0.0)
        self._pulse_anim.start()

    def enterEvent(self, _):
        if self._enabled:
            self._anim.stop()
            self._anim.setStartValue(self._hov)
            self._anim.setEndValue(1.0)
            self._anim.start()

    def leaveEvent(self, _):
        self._anim.stop()
        self._anim.setStartValue(self._hov)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def mousePressEvent(self, e):
        if self._enabled and e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(4, 4, -4, -4)

        # Background card
        t = T()
        eff   = 1.0 if self._active else self._hov
        alpha = int(30 + eff * 40)
        light = sum(t['bg'][0]) / 3 > 128
        base  = QColor(0, 0, 0, alpha) if light else QColor(255, 255, 255, alpha)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(base)
        p.drawRoundedRect(r, 16, 16)

        # Gradient border
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(self._colors[0]))
        g.setColorAt(1, QColor(self._colors[1]))
        border_color = QColor(self._colors[0])
        border_color.setAlpha(min(255, int(self._border_alpha + eff * 105)))
        p.setPen(QPen(border_color, 1.2 + eff * 0.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 15, 15)

        # Glow on hover / active
        if eff > 0.05:
            glow = QRadialGradient(r.center(), r.width() * 0.6)
            gc = QColor(self._colors[0])
            gc.setAlpha(int(eff * 35))
            glow.setColorAt(0, gc)
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(glow)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 16, 16)

        # Pulsing glow when active
        if self._active and self._pls > 0.0:
            pg = QRadialGradient(r.center(), r.width() * 0.65)
            pgc = QColor(self._colors[0])
            pgc.setAlpha(int(self._pls * 55))
            pg.setColorAt(0, pgc)
            pg.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(pg)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 16, 16)

        if not self._enabled and not self._active:
            p.setOpacity(0.35)

        # Icône vectorielle, teintée comme le bouton (pas d'emoji multicolore)
        icon_color = QColor(t['text'] if self._role == self.ROLE_NEUTRAL
                            else self._colors[0])
        self._draw_icon(p, QRectF(r.center().x() - 16, r.top() + 14, 32, 32),
                        icon_color)

        # Label
        lf = QFont("Segoe UI", 11, QFont.Weight.Bold)
        p.setFont(lf)
        gc2 = QColor(t['text'] if self._role == self.ROLE_NEUTRAL
                     else self._colors[0])
        gc2.setAlpha(255)
        p.setPen(gc2)
        label_r = QRectF(r.left(), r.top() + 54, r.width(), 24)
        p.drawText(label_r, Qt.AlignmentFlag.AlignHCenter, self._label)

        # Pastille compteur
        if self._count:
            cf = QFont("Segoe UI", 11, QFont.Weight.Bold)
            p.setFont(cf)
            fm = QFontMetrics(cf)
            tw = fm.horizontalAdvance(self._count)
            ch = 26
            chip = QRectF(r.center().x() - tw / 2 - 12, r.top() + 82,
                          tw + 24, ch)
            chip_bg = QColor(self._colors[0])
            chip_bg.setAlpha(46 if self._enabled or self._active else 26)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(chip_bg)
            p.drawRoundedRect(chip, ch / 2, ch / 2)
            chip_brd = QColor(self._colors[0])
            chip_brd.setAlpha(120)
            p.setPen(QPen(chip_brd, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(chip, ch / 2, ch / 2)
            p.setPen(QColor(t['text'] if self._role == self.ROLE_NEUTRAL
                            else self._colors[0]))
            p.drawText(chip, Qt.AlignmentFlag.AlignCenter, self._count)

        # Description
        df = QFont("Segoe UI", 8)
        p.setFont(df)
        desc_col = QColor(t['text'])
        desc_col.setAlpha(165)
        p.setPen(desc_col)
        desc_top = 114 if self._count else 84
        desc_r = QRectF(r.left() + 8, r.top() + desc_top, r.width() - 16, 50)
        p.drawText(desc_r,
                   Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                   self._desc)


# ── Bandeau de fin d'import ─────────────────────────────────────────────────

class _DoneBanner(QWidget):
    """Bandeau « fin de niveau » : gros titre qui pop, stats, bouton d'accès.

    Rend la fin d'import impossible à rater, avec le bouton « Ouvrir le
    dossier » en action principale.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedHeight(152)   # jamais écrasé ni étiré par la mise en page
        self._pop   = 0.0
        self._title = ""
        self._stats = ""
        self._color = "#000000"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 86, 24, 20)
        lay.setSpacing(0)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_open = GradientButton("📂   Ouvrir le dossier des photos")
        self.btn_open.setFixedHeight(46)
        self.btn_open.setMinimumWidth(340)
        btn_row.addWidget(self.btn_open)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        self._anim = QPropertyAnimation(self, b"_pop_prop", self)
        self._anim.setDuration(750)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        theme_sig.changed.connect(self.update)

    @pyqtProperty(float)
    def _pop_prop(self):
        return self._pop

    @_pop_prop.setter
    def _pop_prop(self, v: float):
        self._pop = v
        self.update()

    def show_result(self, title: str, stats: str, color: str, show_open: bool):
        self._title, self._stats, self._color = title, stats, color
        self.btn_open.setVisible(show_open)
        self.setVisible(True)
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def paintEvent(self, _):
        if not self._title:
            return
        t = T()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        pop  = max(0.0, self._pop)          # OutBack dépasse légèrement 1.0
        vis  = max(0.0, min(pop, 1.0))      # alpha plafonné

        # Fond teinté + bordure de la couleur du résultat
        bg = QColor(self._color)
        bg.setAlpha(int(30 * vis))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(r, 16, 16)
        brd = QColor(self._color)
        brd.setAlpha(int(170 * vis))
        p.setPen(QPen(brd, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, 16, 16)

        # Halo derrière le titre
        if vis > 0.1:
            glow = QRadialGradient(r.center().x(), r.top() + 30, r.width() * 0.35)
            gc = QColor(self._color)
            gc.setAlpha(int(30 * vis))
            glow.setColorAt(0, gc)
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(glow)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 16, 16)

        # Titre qui « pop » (la taille suit l'animation)
        f = QFont("Segoe UI", max(1, int(9 + 13 * pop)), QFont.Weight.Bold)
        p.setFont(f)
        tc = QColor(self._color)
        tc.setAlpha(int(255 * vis))
        p.setPen(tc)
        p.drawText(QRectF(r.left(), r.top() + 10, r.width(), 44),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                   self._title)

        # Ligne de stats
        sf = QFont("Segoe UI", 10)
        p.setFont(sf)
        sc = QColor(t['text'])
        sc.setAlpha(int(230 * vis))
        p.setPen(sc)
        p.drawText(QRectF(r.left(), r.top() + 56, r.width(), 24),
                   Qt.AlignmentFlag.AlignHCenter, self._stats)


# ── USB Import View ────────────────────────────────────────────────────────

class UsbImportView(QWidget):
    options_requested  = pyqtSignal()
    import_finished    = pyqtSignal()

    _SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    _USB_ALL_LABEL = "Tous les dossiers"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._worker: UsbCopyWorker | MtpCopyWorker | None = None
        self._dcim        = ""
        self._drive       = ""
        self._source      = 'usb'  # 'usb' ou 'mtp'
        self._file_count   = 0
        self._file_names: list[str] = []
        self._path_parts: list[str] = []   # dossier choisi sur le téléphone
        self._usb_subdir   = ""
        self._path_worker: _MtpDefaultPathWorker | None = None
        self._sib_worker:  _MtpBrowseWorker | None = None
        self._scanning     = False
        self._scan_partial = 0
        self._usb_bytes_done = 0
        self._last_mode    = ""
        self._active_btn: _UsbActionButton | None = None
        self._spin_i = 0
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(80)
        self._spin_timer.timeout.connect(self._tick_spinner)
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 24, 32, 24)
        lay.setSpacing(18)

        # ── En-tête : appareil source ────────────────────────────────────────
        self._info_card = QWidget()
        self._info_card.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        info_lay = QHBoxLayout(self._info_card)
        info_lay.setContentsMargins(20, 14, 20, 6)
        self._lbl_spinner = QLabel("🔌")
        self._lbl_spinner.setStyleSheet("font-size: 12pt;")
        self._lbl_spinner.setFixedWidth(26)
        self._lbl_drive = QLabel()
        self._lbl_drive.setStyleSheet("font-size: 13pt; font-weight: bold;")
        info_lay.addWidget(self._lbl_spinner)
        info_lay.addSpacing(10)
        info_lay.addWidget(self._lbl_drive)
        info_lay.addStretch()
        btn_about = SmallButton("ℹ  À propos")
        btn_about.setFixedWidth(110)
        btn_about.clicked.connect(lambda: UsbAboutDialog(self).exec())
        info_lay.addWidget(btn_about)
        btn_opt = SmallButton("⚙  Options")
        btn_opt.setFixedWidth(110)
        btn_opt.clicked.connect(self.options_requested)
        info_lay.addWidget(btn_opt)
        lay.addWidget(self._info_card)

        # ── Bloc « source » : d'où viennent les photos ────────────────────────
        # Ligne 1 : le dossier + le nombre de fichiers qu'il contient.
        # Ligne 2 : le filtre de date, aligné sous le dossier car il affine
        #           exactement la même chose.
        self._subdir_row = QWidget()
        self._subdir_row.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        src_lay = QGridLayout(self._subdir_row)
        src_lay.setContentsMargins(20, 0, 20, 0)
        src_lay.setHorizontalSpacing(12)
        src_lay.setVerticalSpacing(10)

        self._subdir_lbl = QLabel("Dossier")
        self._subdir_lbl.setStyleSheet("font-size: 10pt;")
        self._select = PopupSelect()
        self._select.setMinimumWidth(280)
        self._select.selected.connect(self._on_source_selected)
        self._select.browse_requested.connect(self._open_browser)
        self._lbl_count = QLabel()
        self._lbl_count.setStyleSheet("font-size: 10pt;")

        self._subdir_box = QWidget()   # libellé + sélecteur (masquable)
        self._subdir_box.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        sub_lay = QHBoxLayout(self._subdir_box)
        sub_lay.setContentsMargins(0, 0, 0, 0)
        sub_lay.setSpacing(12)
        sub_lay.addWidget(self._subdir_lbl)
        sub_lay.addWidget(self._select)

        src_lay.addWidget(self._subdir_box, 0, 0)
        src_lay.addWidget(self._lbl_count,  0, 1)
        src_lay.setColumnStretch(2, 1)

        # Filtre par date (MTP uniquement), sous le sélecteur
        self._date_row = QWidget()
        self._date_row.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        date_lay = QHBoxLayout(self._date_row)
        date_lay.setContentsMargins(0, 0, 0, 0)
        date_lay.setSpacing(10)
        self._date_cb = QCheckBox("Seulement les photos prises depuis le")
        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDate(QDate.currentDate().addDays(-30))
        self._date_edit.setDisplayFormat("dd/MM/yyyy")
        self._date_edit.setFixedWidth(135)
        self._date_edit.setEnabled(False)
        self._date_cb.toggled.connect(self._date_edit.setEnabled)
        self._date_cb.toggled.connect(lambda _: self._update_counts_ui())
        self._date_edit.dateChanged.connect(lambda _: self._update_counts_ui())
        date_lay.addWidget(self._date_cb)
        date_lay.addWidget(self._date_edit)
        date_lay.addStretch()
        self._date_row.setVisible(False)
        src_lay.addWidget(self._date_row, 1, 0, 1, 3)

        self._subdir_row.setVisible(False)
        lay.addWidget(self._subdir_row)

        # 3 action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        self._btn_copy = _UsbActionButton(
            "📋", "Copier",
            "Copie les fichiers\nsur le disque dur\n(source inchangée)",
            _UsbActionButton.ROLE_PRIMARY
        )
        self._btn_copy_move = _UsbActionButton(
            "📦", "Copier + Déplacer",
            "Copie, puis range les fichiers\nde la source dans DCIM/_old",
            _UsbActionButton.ROLE_WARNING
        )
        self._btn_copy_del = _UsbActionButton(
            "🗑", "Copier + Supprimer",
            "Copie puis supprime\nles fichiers\nde la source",
            _UsbActionButton.ROLE_DANGER
        )
        self._btn_dry = _UsbActionButton(
            "🔬", "Simulation",
            "Simule la copie\nsans toucher\naux fichiers",
            _UsbActionButton.ROLE_NEUTRAL
        )

        self._btn_copy.clicked.connect(
            lambda: self._start(UsbCopyWorker.MODE_COPY))
        self._btn_copy_move.clicked.connect(
            lambda: self._start(UsbCopyWorker.MODE_COPY_MOVE))
        self._btn_copy_del.clicked.connect(
            lambda: self._start(UsbCopyWorker.MODE_COPY_DELETE))
        self._btn_dry.clicked.connect(
            lambda: self._start(UsbCopyWorker.MODE_DRY_RUN))

        btn_row.addWidget(self._btn_copy)
        btn_row.addWidget(self._btn_copy_move)
        btn_row.addWidget(self._btn_copy_del)
        btn_row.addWidget(self._btn_dry)
        lay.addLayout(btn_row)

        # Progress + log (masqués au départ)
        self._progress_area = QWidget()
        self._progress_area.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._progress_area.setVisible(False)
        prog_lay = QVBoxLayout(self._progress_area)
        prog_lay.setContentsMargins(0, 0, 0, 0)
        prog_lay.setSpacing(8)

        self._action_lbl = QLabel("")
        self._action_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._action_lbl.setStyleSheet("font-size: 11pt; font-weight: bold;")
        prog_lay.addWidget(self._action_lbl)

        self._batch_lbl = QLabel("")
        self._batch_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._batch_lbl.setStyleSheet("font-size: 9pt;")
        prog_lay.addWidget(self._batch_lbl)

        self._prog_lbl = QLabel("0 / 0")
        self._prog_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prog_lay.addWidget(self._prog_lbl)

        self._prog_bar = QWidget()
        self._prog_bar.setFixedHeight(8)
        self._prog_bar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._prog_bar_inner = QWidget(self._prog_bar)
        self._prog_bar_inner.setFixedHeight(8)
        prog_lay.addWidget(self._prog_bar)

        self._log_list = QListWidget()
        # Compressible : c'est lui qui cède la place quand la fenêtre est
        # basse (il défile), pour ne jamais écraser le bandeau ni déborder.
        self._log_list.setMinimumHeight(90)
        self._log_list.setMaximumHeight(200)
        self._log_list.setIconSize(QSize(48, 48))
        prog_lay.addWidget(self._log_list)

        # Bandeau de fin, en tête de la zone de progression
        self._done_banner = _DoneBanner()
        self._done_banner.setVisible(False)
        self._done_banner.btn_open.clicked.connect(
            lambda: os.startfile(get_usb_target()))
        prog_lay.insertWidget(0, self._done_banner)

        stop_row = QHBoxLayout()
        stop_row.addStretch()
        self._btn_stop = DangerButton("⏹  Arrêter")
        self._btn_stop.setMinimumWidth(170)
        self._btn_stop.clicked.connect(self._stop_worker)
        stop_row.addWidget(self._btn_stop)
        stop_row.addStretch()
        prog_lay.addLayout(stop_row)

        lay.addWidget(self._progress_area)
        lay.addStretch()

        self._refresh_log_style()
        theme_sig.changed.connect(self._refresh_log_style)

    def refresh_usb(self, drive: str, dcim: str):
        log.debug("refresh_usb drive=%s dcim=%s", drive, dcim)
        self._source = 'usb'
        self._drive  = drive
        self._dcim   = dcim
        self._date_row.setVisible(False)
        t = T()
        self._lbl_spinner.setText("🔌")
        self._lbl_drive.setText(drive.rstrip("\\"))
        self._lbl_drive.setStyleSheet(
            f"font-size: 13pt; font-weight: bold; color: {t['a1']};")
        self._subdir_row.setVisible(True)
        self._btn_copy_move.setVisible(True)   # USB : toujours disponible
        self._begin_scan()
        self._spin_i = 0
        self._spin_timer.start()
        self._progress_area.setVisible(False)
        self._set_buttons_enabled(True)
        self._refresh_log_style()

        # Sous-dossiers du DCIM, proposés dans le menu
        try:
            subdirs = sorted(
                d for d in os.listdir(dcim)
                if os.path.isdir(os.path.join(dcim, d))
            )
        except Exception:
            subdirs = []
        self._select.set_browse("")
        if subdirs:
            # « Tous les dossiers » importe l'intégralité du DCIM, sous-dossiers
            # compris — c'est le choix par défaut ; le menu permet de se
            # restreindre à un seul dossier.
            entries = [(self._USB_ALL_LABEL, "")]
            entries += [(d, d) for d in subdirs]
            self._select.set_entries(entries)
            self._select.set_current(self._USB_ALL_LABEL, "")
            self._subdir_box.setVisible(True)
        else:
            self._subdir_box.setVisible(False)

        self._usb_subdir = ""
        self._restart_count_worker(_UsbCountWorker(dcim), get_usb_timeout() * 1000)

    def refresh_mtp(self, device_name: str):
        log.debug("refresh_mtp device=%s", device_name)
        self._source = 'mtp'
        self._drive  = device_name
        self._dcim   = 'MTP'
        self._subdir_row.setVisible(True)
        self._subdir_box.setVisible(True)
        self._date_row.setVisible(True)
        t = T()
        self._lbl_spinner.setText("📱")
        self._lbl_drive.setText(device_name)
        self._lbl_drive.setStyleSheet(
            f"font-size: 13pt; font-weight: bold; color: {t['prio']};")
        self._begin_scan()
        self._spin_i = 0
        self._spin_timer.start()
        self._progress_area.setVisible(False)
        self._set_buttons_enabled(True)
        self._refresh_log_style()
        # « Copier + Déplacer » masqué si ce téléphone est connu pour ne pas
        # savoir déplacer (appris au premier essai) — l'utilisateur a choisi
        # de ne pas voir l'option dans ce cas.
        self._btn_copy_move.setVisible(
            get_mtp_move_support(device_name) != 'no')
        self._select.set_browse("📂   Parcourir le téléphone…")
        self._select.set_entries([])
        self._select.set_current("Recherche du dossier photos…", None)
        # Cherche DCIM/Camera (et ses voisins) en arrière-plan
        if self._path_worker is not None and self._path_worker.isRunning():
            self._path_worker.terminate()
        self._path_worker = _MtpDefaultPathWorker()
        self._path_worker.result.connect(self._on_default_path)
        self._path_worker.start()

    # ── Choix du dossier source ────────────────────────────────────────────
    def _on_default_path(self, parts: list, siblings: list):
        if self._source != 'mtp':
            return
        if not parts:
            self._select.set_current("Aucun dossier photo trouvé", None)
            self._on_count(0)
            return
        self._set_mtp_path(list(parts), siblings)

    def _set_mtp_path(self, parts: list[str], siblings: list | None = None):
        """Applique un dossier téléphone : menu, libellé et comptage."""
        self._path_parts = list(parts)
        if siblings is not None:
            entries = [(s['name'], list(s['parts']))
                       for s in sorted(siblings, key=lambda s: s['name'].lower())]
            self._select.set_entries(entries)
        self._select.set_current(_mtp_path_label(self._path_parts),
                                 self._path_parts)
        self._select.setToolTip(_mtp_path_label(self._path_parts, full=True))
        self._begin_scan()
        self._restart_count_worker(_MtpCountWorker(self._path_parts), 60_000)

    def _open_browser(self):
        """Navigateur visuel des dossiers du téléphone."""
        if self._source != 'mtp':
            return
        start = self._path_parts or [self._drive]
        dlg = MtpFolderDialog(self._drive, start, self)
        if dlg.exec() and dlg.chosen_path():
            parts = dlg.chosen_path()
            log.info("Dossier téléphone choisi : %s", "/".join(parts[1:]))
            self._set_mtp_path(parts)
            # Rafraîchit les dossiers voisins proposés dans le menu
            if self._sib_worker is not None and self._sib_worker.isRunning():
                self._sib_worker.terminate()
            self._sib_worker = _MtpBrowseWorker(parts[:-1])
            self._sib_worker.result.connect(self._on_siblings)
            self._sib_worker.start()

    def _on_siblings(self, parts: list, children: list, _media: int):
        if self._source != 'mtp' or not children:
            return
        entries = [(c['name'], list(c['parts']))
                   for c in sorted(children, key=lambda c: c['name'].lower())]
        self._select.set_entries(entries)
        self._select.set_current(_mtp_path_label(self._path_parts),
                                 self._path_parts)

    def _restart_count_worker(self, worker, timeout_ms: int):
        if hasattr(self, '_count_worker') and self._count_worker.isRunning():
            self._count_worker.terminate()
        self._count_worker = worker
        self._count_worker.partial.connect(self._on_count_partial)
        self._count_worker.names.connect(self._on_count_names)
        self._count_worker.result.connect(self._on_count)
        self._count_worker.start()
        if hasattr(self, '_count_timeout'):
            self._count_timeout.stop()
        self._count_timeout = QTimer(self)
        self._count_timeout.setSingleShot(True)
        self._count_timeout.timeout.connect(self._on_count_timeout)
        self._count_timeout.start(timeout_ms)

    def _on_source_selected(self, data):
        """Entrée choisie dans le menu du sélecteur de dossier."""
        if data is None:
            return
        if self._source == 'mtp':
            self._set_mtp_path(list(data))
        elif self._source == 'usb':
            subdir    = str(data)
            scan_path = (os.path.join(self._dcim, subdir)
                         if subdir else self._dcim)
            if os.path.isdir(scan_path):
                log.debug("Source USB choisie : %s",
                          subdir or "tous les dossiers")
                self._usb_subdir = subdir
                self._begin_scan()
                self._restart_count_worker(_UsbCountWorker(scan_path),
                                           get_usb_timeout() * 1000)

    def _tick_spinner(self):
        t = T()
        char = self._SPINNER[self._spin_i % len(self._SPINNER)]
        self._lbl_spinner.setText(char)
        self._lbl_spinner.setStyleSheet(f"font-size: 12pt; color: {t['a1']};")
        if self._scanning:
            n    = self._scan_partial
            noun = "trouvé" if n <= 1 else "trouvés"
            self._lbl_count.setText(f"{char}  Analyse… {n} {noun}")
            self._lbl_count.setStyleSheet(self._count_pill_css(scanning=True))
        self._spin_i += 1

    def _on_count_timeout(self):
        """Appelé si le scan USB n'a pas répondu en 10 secondes."""
        log.warning("Timeout scan USB — DCIM inaccessible ou vide")
        if hasattr(self, '_count_worker'):
            self._count_worker.stop()
        self._on_count(0)

    def _on_count_partial(self, count: int):
        self._scan_partial = count

    def _on_count_names(self, names: list):
        self._file_names = list(names)

    def _begin_scan(self):
        """Réinitialise l'affichage des compteurs avant un nouveau scan."""
        self._scanning     = True
        self._scan_partial = 0
        self._file_count   = 0
        self._file_names   = []
        self._lbl_count.setText("⏳  Analyse en cours…")
        self._lbl_count.setStyleSheet(self._count_pill_css(scanning=True))
        for btn in (self._btn_copy, self._btn_copy_move,
                    self._btn_copy_del, self._btn_dry):
            btn.setCountText("…")
        self._spin_timer.start()

    def _count_pill_css(self, scanning: bool = False) -> str:
        t = T()
        r, g, b = t['panel'][:3]
        light = (r + g + b) / 3 > 128
        if scanning:
            bg  = "rgba(0,0,0,10)" if light else "rgba(255,255,255,16)"
            col = t['dim']
        else:
            bg  = "rgba(0,0,0,16)" if light else "rgba(255,255,255,24)"
            col = t['text']
        return (f"font-size: 10pt; font-weight: bold; color: {col};"
                f" background: {bg}; border-radius: 11px; padding: 4px 12px;")

    def _current_date_from(self) -> datetime | None:
        """Date plancher active (filtre MTP), sinon None."""
        if (self._source == 'mtp' and self._date_row.isVisible()
                and self._date_cb.isChecked()):
            qd = self._date_edit.date()
            return datetime(qd.year(), qd.month(), qd.day())
        return None

    def _pending_count(self) -> int:
        """Nombre de fichiers que les actions vont réellement traiter."""
        date_from = self._current_date_from()
        if not date_from or not self._file_names:
            return self._file_count
        return _filter_names_from_date(self._file_names, date_from)

    def _update_counts_ui(self):
        """Rafraîchit la pastille de total et les compteurs des 3 boutons."""
        if self._scanning or not hasattr(self, '_btn_copy'):
            return
        total   = self._file_count
        pending = self._pending_count()
        noun    = "fichier" if total == 1 else "fichiers"
        if total == 0:
            txt = "Aucun fichier photo/vidéo"
        elif pending != total:
            date_txt = self._date_edit.date().toString("dd/MM/yyyy")
            txt = (f"{total} {noun} · {pending} depuis le {date_txt}")
        else:
            txt = f"{total} {noun} photos/vidéos"
        self._lbl_count.setText(txt)
        self._lbl_count.setStyleSheet(self._count_pill_css())
        btn_txt = ("aucun fichier" if pending == 0
                   else f"{pending} fichier" if pending == 1
                   else f"{pending} fichiers")
        busy = self._worker is not None and self._worker.isRunning()
        for btn in (self._btn_copy, self._btn_copy_move,
                    self._btn_copy_del, self._btn_dry):
            btn.setCountText(btn_txt)
            btn.setEnabled(pending > 0 and not busy)

    def _rescan_source(self):
        """Relance le comptage (après une suppression, le total a changé)."""
        if self._source == 'mtp':
            if not self._path_parts:
                return
            self._begin_scan()
            self._restart_count_worker(_MtpCountWorker(self._path_parts), 60_000)
        elif self._source == 'usb' and self._dcim:
            scan_path = (os.path.join(self._dcim, self._usb_subdir)
                         if self._usb_subdir else self._dcim)
            if os.path.isdir(scan_path):
                self._begin_scan()
                self._restart_count_worker(_UsbCountWorker(scan_path),
                                           get_usb_timeout() * 1000)

    def _on_count(self, count: int):
        if hasattr(self, '_count_timeout'):
            self._count_timeout.stop()
        self._scanning = False
        self._spin_timer.stop()
        self._lbl_spinner.setText("📱" if self._source == 'mtp' else "🔌")
        self._lbl_spinner.setStyleSheet("font-size: 12pt;")
        self._file_count = count
        self._update_counts_ui()

    def is_importing(self) -> bool:
        return (self._source == 'mtp' and
                self._worker is not None and
                self._worker.isRunning())

    def notify_mtp_disconnected(self):
        t = T()
        self._action_lbl.setText("⚠  Téléphone déconnecté — import interrompu")
        self._action_lbl.setStyleSheet(
            f"font-size: 10pt; font-weight: bold; color: {t['err']};")

    def _refresh_log_style(self):
        t = T()
        r, g, b = t['panel'][:3]
        light = (r + g + b) / 3 > 128
        el_bg  = "rgba(0,0,0,8)"  if light else "rgba(255,255,255,12)"
        el_brd = "rgba(0,0,0,14)" if light else "rgba(255,255,255,22)"
        # For combos: solid background so text is always readable
        combo_bg  = "rgba(255,255,255,220)" if light else "rgba(40,40,60,220)"
        combo_brd = "rgba(0,0,0,40)"        if light else "rgba(255,255,255,40)"
        self._log_list.setStyleSheet(
            f"QListWidget {{ background: {el_bg}; color: {t['text']};"
            f" border: 1px solid {el_brd}; border-radius: 8px; padding: 4px; }}"
            f"QListWidget::item {{ padding: 2px 4px; }}")
        self._prog_lbl.setStyleSheet(f"color: {t['dim']}; font-size: 10pt;")
        self._subdir_lbl.setStyleSheet(f"font-size: 10pt; color: {t['dim']};")
        self._lbl_count.setStyleSheet(self._count_pill_css(scanning=self._scanning))
        combo_css = (
            f"background: {combo_bg}; color: {t['text']};"
            f" border: 1px solid {combo_brd}; border-radius: 9px;"
            f" padding: 6px 10px; font-size: 10pt;")
        self._date_edit.setStyleSheet(
            f"QDateEdit {{ {combo_css} }}"
            f"QDateEdit:disabled {{ color: {t['dim']}; }}"
            f"QDateEdit::drop-down {{ border: none; width: 18px; }}"
        )
        self._date_cb.setStyleSheet(
            f"QCheckBox {{ font-size: 10pt; color: {t['text']}; }}"
            "QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; }"
            "QCheckBox::indicator:unchecked { background: rgba(255,255,255,230);"
            " border: 2px solid rgba(160,160,160,200); }"
            f"QCheckBox::indicator:checked {{ background: {t['a1']};"
            f" border: 2px solid {t['a1']}; }}"
        )

    def _set_buttons_enabled(self, enabled: bool):
        if (enabled and not self._scanning
                and self._file_count == 0):
            enabled = False
        for btn in (self._btn_copy, self._btn_copy_move,
                    self._btn_copy_del, self._btn_dry):
            btn.setEnabled(enabled)

    def _start(self, mode: str):
        if not self._dcim:
            log.warning("_start appelé sans source définie")
            return
        if mode == UsbCopyWorker.MODE_COPY_DELETE:
            n    = self._pending_count()
            noun = "fichier" if n == 1 else "fichiers"
            dlg  = QMessageBox(self)
            dlg.setWindowTitle("Confirmer la suppression")
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setText(f"Supprimer {n} {noun} de la source après copie ?")
            dlg.setInformativeText(
                "Les fichiers seront d'abord copiés sur le disque dur, "
                "puis supprimés définitivement de la source.\n"
                "Cette action est irréversible.")
            dlg.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            dlg.button(QMessageBox.StandardButton.Yes).setText("Oui")
            dlg.button(QMessageBox.StandardButton.No).setText("Non")
            dlg.setDefaultButton(QMessageBox.StandardButton.No)
            if dlg.exec() != QMessageBox.StandardButton.Yes:
                return
        self._last_mode = mode
        log.info("Import démarré — source=%s mode=%s target=%s",
                 self._source, mode, get_usb_target())
        self._progress_area.setVisible(True)
        self._btn_stop.setVisible(True)
        self._btn_stop.setText("⏹  Arrêter")
        self._btn_stop.setEnabled(True)
        self._done_banner.setVisible(False)
        self._log_list.clear()
        self._prog_lbl.setText("Démarrage…")
        self._set_buttons_enabled(False)
        mode_to_btn = {
            UsbCopyWorker.MODE_COPY:        self._btn_copy,
            UsbCopyWorker.MODE_COPY_MOVE:   self._btn_copy_move,
            UsbCopyWorker.MODE_COPY_DELETE: self._btn_copy_del,
            UsbCopyWorker.MODE_DRY_RUN:     self._btn_dry,
        }
        if self._active_btn:
            self._active_btn.setActive(False)
        self._active_btn = mode_to_btn.get(mode)
        if self._active_btn:
            self._active_btn.setActive(True)
        mode_labels = {
            UsbCopyWorker.MODE_COPY:        "📋  Copier en cours…",
            UsbCopyWorker.MODE_COPY_MOVE:   "📦  Copier + Déplacer en cours…",
            UsbCopyWorker.MODE_COPY_DELETE: "🗑  Copier + Supprimer en cours…",
            UsbCopyWorker.MODE_DRY_RUN:     "🔬  Simulation en cours…",
        }
        t = T()
        self._action_lbl.setText(mode_labels.get(mode, ""))
        self._action_lbl.setStyleSheet(
            f"font-size: 11pt; font-weight: bold; color: {t['a1']};")

        if self._source == 'mtp':
            self._worker = MtpCopyWorker(
                get_usb_target(), mode, self._path_parts,
                self._current_date_from(), get_exif())
            self._worker.log_thumb.connect(self._on_log_thumb)
            self._worker.batch_info.connect(self._on_batch_info)
            self._worker.ask_slow_move.connect(self._on_ask_slow_move)
        else:
            exif_cmd = get_exif()
            if not _check_exiftool(exif_cmd):
                dlg = _ExiftoolDownloadDialog(self)
                dlg.installed.connect(lambda _: self._start(mode))
                dlg.exec()
                self._set_buttons_enabled(True)
                self._progress_area.setVisible(False)
                self._btn_stop.setVisible(False)
                if self._active_btn:
                    self._active_btn.setActive(False)
                    self._active_btn = None
                return
            selected = self._usb_subdir if self._subdir_box.isVisible() else ""
            usb_src  = (os.path.join(self._dcim, selected)
                        if selected and os.path.isdir(os.path.join(self._dcim, selected))
                        else self._dcim)
            self._worker = UsbCopyWorker(
                usb_src, get_usb_target(), mode, exif_cmd,
                dcim_root=self._dcim)
            self._worker.batch_info.connect(self._on_batch_info)
            self._worker.log_thumb.connect(self._on_log_thumb)
            self._worker.progress.connect(self._on_progress_usb)
        self._worker.log_entry.connect(self._on_log)
        if self._source == 'mtp':
            self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._batch_lbl.setText("")
        self._worker.start()

    def _on_ask_slow_move(self, n: int):
        """Le téléphone refuse le déplacement direct : continuer (lent) ?"""
        worker = self._worker
        if worker is None:
            return
        noun = "fichier" if n == 1 else "fichiers"
        dlg  = QMessageBox(self)
        dlg.setWindowTitle("Rangement lent")
        dlg.setIcon(QMessageBox.Icon.Warning)
        dlg.setText("Ce téléphone ne permet pas de déplacer ses fichiers "
                    "directement.")
        dlg.setInformativeText(
            f"L'application peut quand même ranger les {n} {noun} dans "
            "DCIM/_old en les renvoyant depuis le PC, mais cela peut "
            "prendre du temps. Gardez l'écran du téléphone déverrouillé "
            "pendant l'opération.\n\n"
            "•  Continuer : rangement lent, avec progression et temps "
            "restant.\n"
            "•  Arrêter : vos photos sont déjà copiées sur le PC ; rien "
            "n'est modifié sur le téléphone (à vous d'y faire le ménage).")
        btn_go   = dlg.addButton("Continuer (lent)",
                                 QMessageBox.ButtonRole.AcceptRole)
        btn_stop = dlg.addButton("Arrêter là",
                                 QMessageBox.ButtonRole.RejectRole)
        dlg.setDefaultButton(btn_stop)
        dlg.exec()
        worker.reply_slow_move(dlg.clickedButton() is btn_go)

    def _stop_worker(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._btn_stop.setText("⏳  Arrêt en cours…")
            self._btn_stop.setEnabled(False)
            self._batch_lbl.setText(
                "Arrêt demandé — fin de l'opération en cours…")

    def _on_log(self, kind: str, msg: str):
        t = T()
        colors = {'move': t['ok'], 'skip': t['dim'],
                  'error': t['err'], 'new': t['a1']}
        color = colors.get(kind, t['text'])
        if kind == 'move':
            fname = msg.split('  →  ')[0].strip().removeprefix('[Simulation] ')
            ext   = Path(fname).suffix.lower()
            icon  = '🎬' if ext in VIDEO_EXT else '📷'
        else:
            icon = {'skip': '–', 'error': '✗', 'new': '＋'}.get(kind, '·')
        from PyQt6.QtWidgets import QListWidgetItem
        item = QListWidgetItem(f"{icon}  {msg}")
        item.setForeground(QColor(color))
        self._log_list.addItem(item)
        self._log_list.scrollToBottom()

    def _on_log_thumb(self, kind: str, msg: str, fpath: str):
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtGui import QImageReader, QIcon
        t     = T()
        color = {'move': t['ok'], 'skip': t['dim'],
                 'error': t['err'], 'new': t['a1']}.get(kind, t['text'])
        icon_char = {'move': '🖼', 'skip': '–', 'error': '✗', 'new': '＋'}.get(kind, '·')
        item = QListWidgetItem(f"{icon_char}  {msg}")
        item.setForeground(QColor(color))
        if fpath:
            reader = QImageReader(fpath)
            reader.setScaledSize(QSize(48, 48))
            img = reader.read()
            if not img.isNull():
                item.setIcon(QIcon(QPixmap.fromImage(img)))
                item.setSizeHint(QSize(0, 56))
        self._log_list.addItem(item)
        self._log_list.scrollToBottom()

    def _on_batch_info(self, info: str):
        t = T()
        self._batch_lbl.setText(info)
        self._batch_lbl.setStyleSheet(f"font-size: 9pt; color: {t['dim']};")

    def _on_progress(self, cur: int, total: int):
        self._prog_lbl.setText(f"{cur} / {total}")
        if total > 0:
            self._update_prog_bar(cur, total)

    def _on_progress_usb(self, done_bytes: int, total_bytes: int):
        self._usb_bytes_done = done_bytes
        label = f"{_fmt_bytes(done_bytes)} / {_fmt_bytes(total_bytes)}"
        self._prog_lbl.setText(label)
        if total_bytes > 0:
            self._update_prog_bar(done_bytes, total_bytes)

    def _update_prog_bar(self, cur: int, total: int):
        w = max(0, int(self._prog_bar.width() * cur / total))
        self._prog_bar_inner.setFixedWidth(w)
        t = T()
        self._prog_bar_inner.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {t['a1']}, stop:1 {t['a2']});"
            f"border-radius: 4px;")
        self._prog_bar.setStyleSheet(
            "background: rgba(128,128,128,30); border-radius: 4px;")

    def _on_done(self, copied: int, skipped: int, errors: int, elapsed: float):
        if elapsed >= 60:
            m, s = int(elapsed // 60), int(elapsed % 60)
            dur_str = f"{m} min {s:02d}"
        else:
            dur_str = f"{elapsed:.0f} s"
        bytes_str = (f"  ·  {_fmt_bytes(self._usb_bytes_done)}"
                     if self._source == 'usb' and self._usb_bytes_done > 0 else "")
        self._prog_lbl.setText("")
        self._batch_lbl.setText("")

        # Bandeau de résultat, bien visible
        t   = T()
        sim = self._last_mode == UsbCopyWorker.MODE_DRY_RUN
        stopped = self._worker is not None and getattr(self._worker, '_stop', False)
        if stopped:
            title, color = "⏹  Import interrompu", t['warn']
        elif errors > 0:
            noun_e = "erreur" if errors == 1 else "erreurs"
            title, color = f"Import terminé — {errors} {noun_e}", t['warn']
        elif sim:
            title, color = "✓  Simulation terminée", t['a1']
        elif copied == 0:
            title, color = "✓  Rien de nouveau à importer", t['a1']
        else:
            title, color = "🎉  Import terminé !", t['ok']
        if sim:
            stats = f"{skipped} fichiers analysés  ·  {dur_str}"
        else:
            noun = "photo/vidéo importée" if copied == 1 else "photos/vidéos importées"
            stats = f"{copied} {noun}"
            if skipped:
                stats += f"  ·  {skipped} déjà présentes"
            if errors:
                stats += f"  ·  {errors} en erreur"
            stats += f"  ·  {dur_str}{bytes_str}"
        self._done_banner.show_result(title, stats, color,
                                      show_open=copied > 0 and not sim)

        self._set_buttons_enabled(True)
        self._btn_stop.setVisible(False)
        if self._active_btn:
            self._active_btn.setActive(False)
            self._active_btn = None
        self._action_lbl.setText("")

        # Les fichiers ont été supprimés ou déplacés : le total a changé
        if self._last_mode in (UsbCopyWorker.MODE_COPY_DELETE,
                               UsbCopyWorker.MODE_COPY_MOVE):
            self._rescan_source()
        if (self._source == 'mtp'
                and get_mtp_move_support(self._drive) == 'no'):
            self._btn_copy_move.setVisible(False)

        # Avertissement si erreurs en mode COPY_DELETE (fichiers en erreur non supprimés)
        if errors > 0 and self._last_mode == UsbCopyWorker.MODE_COPY_DELETE:
            from PyQt6.QtWidgets import QListWidgetItem
            t    = T()
            noun = "fichier" if errors == 1 else "fichiers"
            warn = QListWidgetItem(
                f"⚠  {errors} {noun} en erreur n'ont PAS été supprimés de la source.")
            warn.setForeground(QColor(t['warn']))
            self._log_list.addItem(warn)
            self._log_list.scrollToBottom()

        self.import_finished.emit()
        self._prog_bar_inner.setFixedWidth(self._prog_bar.width())

        # Notification sonore + visuelle
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONINFORMATION)
        except Exception:
            pass
        try:
            QApplication.alert(self.window(), 0)
        except Exception:
            pass

        # Sauvegarde du log MTP et nettoyage des anciens logs
        if self._source == 'mtp':
            self._save_mtp_log()

    def _save_mtp_log(self):
        try:
            import time as _time
            log_dir = Path(__file__).parent / "log"
            log_dir.mkdir(exist_ok=True)
            fname = log_dir / f"mtp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            lines = []
            for i in range(self._log_list.count()):
                item = self._log_list.item(i)
                if item:
                    lines.append(item.text())
            fname.write_text("\n".join(lines), encoding="utf-8")
            # Supprime les logs MTP de plus de 30 jours
            cutoff = _time.time() - 30 * 86400
            for f in log_dir.glob("mtp_*.log"):
                try:
                    if f.stat().st_mtime < cutoff:
                        f.unlink()
                except Exception:
                    pass
        except Exception:
            pass


# ── About Dialog ───────────────────────────────────────────────────────────

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("À propos")
        self.setMinimumWidth(480)
        self.setMaximumWidth(560)
        self._build_style()
        self._setup_ui()
        theme_sig.changed.connect(self._build_style)

    def _build_style(self):
        t = T()
        r, g, b = t['panel'][:3]
        self.setStyleSheet(f"""
            QDialog  {{ background: rgb({r},{g},{b}); }}
            QLabel   {{ color: {t['text']}; background: transparent; }}
            QPushButton {{
                background: rgba(255,255,255,18); color: {t['text']};
                border: 1px solid rgba(255,255,255,28); border-radius: 8px; padding: 6px 20px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,30); }}
        """)
        if hasattr(self, '_body'):
            self._body.setStyleSheet(
                f"color: {t['text']}; background: transparent; font-size: 10pt;"
                f" line-height: 1.6;")

    def _setup_ui(self):
        t   = T()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 24)
        lay.setSpacing(16)

        # Title row
        title_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(create_app_icon().pixmap(48, 48))
        title_row.addWidget(icon_lbl)
        title_row.addSpacing(12)
        v = QVBoxLayout()
        name_lbl = QLabel(APP_NAME)
        name_lbl.setStyleSheet(
            f"font-size: 18pt; font-weight: bold; color: {t['a1']}; background: transparent;")
        ver_lbl  = QLabel(f"Version {VERSION}  ·  {CREATED}")
        ver_lbl.setStyleSheet(f"color: {t['dim']}; font-size: 9pt; background: transparent;")
        v.addWidget(name_lbl); v.addWidget(ver_lbl)
        title_row.addLayout(v)
        title_row.addStretch()
        lay.addLayout(title_row)

        # Separator
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: rgba(255,255,255,20);")
        lay.addWidget(sep)

        # Body
        self._body = QLabel(
            "<p>DCIM Sorter trie automatiquement vos photos et vidéos dans des "
            "sous-dossiers par <b>jour</b>, en lisant les données <b>EXIF</b> "
            "(date de prise de vue réelle).</p>"
            "<p><b>Fonctionnalités :</b></p>"
            "<ul>"
            "<li>Lecture EXIF via <b>ExifTool</b> pour une date précise</li>"
            "<li>Prise en charge des photos <b>RAW</b> (ARW, CR2, CR3…) et vidéos</li>"
            "<li>Sous-dossiers prioritaires configurables (ex : <i>_Priority</i>)</li>"
            "<li>Barre de progression animée en temps réel</li>"
            "<li>40 thèmes visuels</li>"
            "<li>Interface 4K / HiDPI</li>"
            "</ul>"
            "<p><b>Formats supportés :</b> "
            "JPG · PNG · ARW · CR2 · CR3 · MP4 · MOV</p>"
        )
        self._body.setWordWrap(True)
        self._body.setTextFormat(Qt.TextFormat.RichText)
        self._body.setStyleSheet(
            f"color: {t['text']}; background: transparent; font-size: 10pt;")
        lay.addWidget(self._body)

        # Close button
        close_row = QHBoxLayout()
        close_row.addStretch()
        b_close = QPushButton("Fermer")
        b_close.clicked.connect(self.accept)
        close_row.addWidget(b_close)
        lay.addLayout(close_row)


# ── USB About Dialog ───────────────────────────────────────────────────────

class UsbAboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("À propos — Import USB")
        self.setMinimumWidth(480)
        self.setMaximumWidth(560)
        self._build_style()
        self._setup_ui()
        theme_sig.changed.connect(self._build_style)

    def _build_style(self):
        t = T()
        r, g, b = t['panel'][:3]
        light = (r + g + b) / 3 > 128
        btn_bg  = "rgba(0,0,0,10)"  if light else "rgba(255,255,255,18)"
        btn_brd = "rgba(0,0,0,16)"  if light else "rgba(255,255,255,28)"
        btn_hov = "rgba(0,0,0,20)"  if light else "rgba(255,255,255,30)"
        self.setStyleSheet(f"""
            QDialog  {{ background: rgb({r},{g},{b}); }}
            QLabel   {{ color: {t['text']}; background: transparent; }}
            QPushButton {{
                background: {btn_bg}; color: {t['text']};
                border: 1px solid {btn_brd}; border-radius: 8px; padding: 6px 20px;
            }}
            QPushButton:hover {{ background: {btn_hov}; }}
        """)

    def _setup_ui(self):
        t   = T()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 24)
        lay.setSpacing(16)

        # Titre
        title_row = QHBoxLayout()
        icon_lbl = QLabel("🔌")
        icon_lbl.setStyleSheet("font-size: 32pt; background: transparent;")
        title_row.addWidget(icon_lbl)
        title_row.addSpacing(12)
        v = QVBoxLayout()
        name_lbl = QLabel("Import USB — DCIM")
        name_lbl.setStyleSheet(
            f"font-size: 16pt; font-weight: bold; color: {t['a1']}; background: transparent;")
        ver_lbl = QLabel(f"DCIM Sorter  ·  Version {VERSION}")
        ver_lbl.setStyleSheet(f"color: {t['dim']}; font-size: 9pt; background: transparent;")
        v.addWidget(name_lbl); v.addWidget(ver_lbl)
        title_row.addLayout(v)
        title_row.addStretch()
        lay.addLayout(title_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: rgba(128,128,128,40);")
        lay.addWidget(sep)

        body = QLabel(
            "<p>Cette section permet d'<b>importer les photos et vidéos</b> depuis "
            "une clé USB (ou carte SD via lecteur) qui contient un dossier "
            "<b>DCIM</b> — le dossier standard des appareils photo.</p>"
            "<p><b>Trois modes disponibles :</b></p>"
            "<ul>"
            "<li><b>📋 Copier</b> — copie les fichiers vers le disque dur, "
            "la clé USB reste inchangée</li>"
            "<li><b>🗑 Copier + Supprimer</b> — copie puis efface les fichiers "
            "de la clé (libère l'espace). Suppression uniquement si aucune erreur.</li>"
            "<li><b>🔬 Simulation</b> — simule la copie sans toucher aux fichiers, "
            "pour vérifier ce qui serait importé</li>"
            "</ul>"
            "<p><b>Structure créée automatiquement :</b><br/>"
            "<code>destination / année / to_sort / mois / jour</code><br/>"
            "Exemple : <code>E:\\Photos\\2026\\to_sort\\03\\27\\IMG_1234.JPG</code></p>"
            "<p><b>Date utilisée :</b> données EXIF (date de prise de vue réelle) "
            "via ExifTool, sinon date de création du fichier.</p>"
            "<p><b>Doublons :</b> si un fichier du même nom existe déjà, "
            "un suffixe <code>_2</code>, <code>_3</code>… est ajouté automatiquement.</p>"
        )
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setStyleSheet(
            f"color: {t['text']}; background: transparent; font-size: 10pt;")
        lay.addWidget(body)

        close_row = QHBoxLayout()
        close_row.addStretch()
        b_close = QPushButton("Fermer")
        b_close.clicked.connect(self.accept)
        close_row.addWidget(b_close)
        lay.addLayout(close_row)


# ── Options Dialog ─────────────────────────────────────────────────────────

class OptionsDialog(QDialog):
    def __init__(self, parent=None, initial_tab: int = 0):
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setMinimumWidth(520)
        self._orig_theme  = get_theme()
        self._initial_tab = initial_tab
        self._build_style()
        self._setup_ui()
        theme_sig.changed.connect(self._build_style)

    def _build_style(self):
        t = T()
        r, g, b = t['panel'][:3]
        light  = (r + g + b) / 3 > 128
        el_bg  = "rgba(0,0,0,8)"    if light else "rgba(255,255,255,18)"
        el_brd = "rgba(0,0,0,14)"   if light else "rgba(255,255,255,28)"
        el_hov = "rgba(0,0,0,16)"   if light else "rgba(255,255,255,30)"
        self.setStyleSheet(f"""
            QDialog   {{ background: rgb({r},{g},{b}); }}
            QLabel    {{ color: {t['text']}; background: transparent; }}
            QLineEdit {{
                background: {el_bg}; color: {t['text']};
                border: 1px solid {el_brd}; border-radius: 8px; padding: 6px 12px;
            }}
            QLineEdit:focus {{ border-color: {t['a1']}; }}
            QComboBox {{
                background: {el_bg}; color: {t['text']};
                border: 1px solid {el_brd}; border-radius: 8px; padding: 6px 12px;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background: rgb({r},{g},{b}); color: {t['text']};
                selection-background-color: {t['a1']}; selection-color: #000;
                border: 1px solid {el_brd};
            }}
            QPushButton {{
                background: {el_bg}; color: {t['text']};
                border: 1px solid {el_brd}; border-radius: 8px; padding: 6px 8px;
            }}
            QPushButton:hover {{ background: {el_hov}; }}
            QPushButton#btn_ok {{
                background: {t['a1']}; color: #000; font-weight: bold; border: none;
            }}
            QPushButton#btn_ok:hover {{ background: {t['a2']}; color: #fff; }}
            QTabWidget::pane {{
                border: 1px solid {el_brd}; border-radius: 8px;
                background: transparent;
            }}
            QTabBar::tab {{
                background: {el_bg}; color: {t['dim']};
                border: 1px solid {el_brd}; border-bottom: none;
                border-radius: 6px 6px 0 0;
                padding: 6px 18px; margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background: {t['a1']}; color: #000; font-weight: bold;
                border-color: {t['a1']};
            }}
            QTabBar::tab:hover:!selected {{ background: {el_hov}; color: {t['text']}; }}
        """)

    def _setup_ui(self):
        t   = T()
        light = (t['panel'][0] + t['panel'][1] + t['panel'][2]) / 3 > 128
        el_bg  = "rgba(0,0,0,8)"  if light else "rgba(255,255,255,18)"
        el_brd = "rgba(0,0,0,14)" if light else "rgba(255,255,255,28)"

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        title = QLabel("Options")
        title.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {t['a1']};")
        lay.addWidget(title)

        # ── Tab widget ────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        lay.addWidget(self._tabs)

        # ── Tab 0 : Général ───────────────────────────────────────────────
        gen = QWidget(); gen.setStyleSheet("background: transparent;")
        g   = QVBoxLayout(gen); g.setContentsMargins(16, 16, 16, 8); g.setSpacing(10)

        g.addWidget(QLabel("Dossier racine des photos :"))
        r_row = QHBoxLayout()
        self._root_edit = QLineEdit(get_root())
        r_row.addWidget(self._root_edit)
        b_root = QPushButton("📁"); b_root.setFixedWidth(36)
        b_root.clicked.connect(self._pick_root)
        r_row.addWidget(b_root)
        g.addLayout(r_row)

        g.addWidget(QLabel("Sous-dossiers prioritaires :"))
        self._prios_list = QListWidget()
        self._prios_list.setFixedHeight(80)
        self._prios_list.setStyleSheet(
            f"QListWidget {{ background: {el_bg}; color: {t['text']};"
            f" border: 1px solid {el_brd}; border-radius: 8px; padding: 4px; }}"
            f"QListWidget::item:selected {{ background: {t['a1']}; color: #000; border-radius: 4px; }}")
        for name in get_prios():
            self._prios_list.addItem(name)
        g.addWidget(self._prios_list)
        prio_row = QHBoxLayout()
        self._prio_new = QLineEdit()
        self._prio_new.setPlaceholderText("Nom du sous-dossier…")
        prio_row.addWidget(self._prio_new)
        b_prio_add = QPushButton("Ajouter"); b_prio_add.setFixedWidth(96)
        b_prio_add.clicked.connect(self._add_prio)
        b_prio_del = QPushButton("Supprimer"); b_prio_del.setFixedWidth(96)
        b_prio_del.clicked.connect(self._del_prio)
        prio_row.addWidget(b_prio_add); prio_row.addWidget(b_prio_del)
        g.addLayout(prio_row)

        g.addWidget(QLabel("ExifTool :"))
        e_row = QHBoxLayout()
        self._exif_edit = QLineEdit(get_exif())
        e_row.addWidget(self._exif_edit)
        b_exif = QPushButton("📁"); b_exif.setFixedWidth(36)
        b_exif.clicked.connect(self._pick_exif)
        e_row.addWidget(b_exif)
        b_path = QPushButton("PATH"); b_path.setFixedWidth(52)
        b_path.clicked.connect(lambda: self._exif_edit.setText("exiftool.exe"))
        e_row.addWidget(b_path)
        g.addLayout(e_row)
        exif_hint = QLabel("Laisser « exiftool.exe » pour utiliser la version du PATH")
        exif_hint.setStyleSheet(f"color: {t['dim']}; font-size: 9pt;")
        g.addWidget(exif_hint)

        g.addWidget(QLabel("Formats de fichiers :"))
        self._fmt_list = QListWidget()
        self._fmt_list.setFixedHeight(72)
        self._fmt_list.setStyleSheet(
            f"QListWidget {{ background: {el_bg}; color: {t['text']};"
            f" border: 1px solid {el_brd}; border-radius: 8px; padding: 4px; }}"
            f"QListWidget::item:selected {{ background: {t['a1']}; color: #000; border-radius: 4px; }}")
        self._default_fmt_names = set()
        for ext in sorted(PHOTO_EXT | VIDEO_EXT):
            name = ext.lstrip('.')
            self._fmt_list.addItem(f"🔒 {name}")
            self._default_fmt_names.add(f"🔒 {name}")
        for ext in get_extra_formats():
            self._fmt_list.addItem(ext.lstrip('.'))
        g.addWidget(self._fmt_list)
        fmt_row = QHBoxLayout()
        self._fmt_new = QLineEdit()
        self._fmt_new.setPlaceholderText("Extension (ex: dng, heic, nef…)")
        fmt_row.addWidget(self._fmt_new)
        b_fmt_add = QPushButton("Ajouter"); b_fmt_add.setFixedWidth(96)
        b_fmt_add.clicked.connect(self._add_fmt)
        b_fmt_del = QPushButton("Supprimer"); b_fmt_del.setFixedWidth(96)
        b_fmt_del.clicked.connect(self._del_fmt)
        fmt_row.addWidget(b_fmt_add); fmt_row.addWidget(b_fmt_del)
        g.addLayout(fmt_row)
        fmt_hint = QLabel("Les formats 🔒 sont intégrés et ne peuvent pas être supprimés.")
        fmt_hint.setStyleSheet(f"color: {t['dim']}; font-size: 9pt;")
        g.addWidget(fmt_hint)

        g.addWidget(QLabel("Thème :"))
        self._combo = QComboBox()
        for key, th in THEMES.items():
            pix = QPixmap(44, 16)
            pix.fill(Qt.GlobalColor.transparent)
            pp  = QPainter(pix)
            pp.setRenderHint(QPainter.RenderHint.Antialiasing)
            gg = QLinearGradient(0, 0, 44, 0)
            gg.setColorAt(0, QColor(th['a1'])); gg.setColorAt(1, QColor(th['a2']))
            pp.setBrush(QBrush(gg)); pp.setPen(Qt.PenStyle.NoPen)
            pp.drawRoundedRect(0, 0, 44, 16, 8, 8)
            pp.end()
            self._combo.addItem(QIcon(pix), th['name'], key)
        cur_key = get_theme()
        idx = list(THEMES.keys()).index(cur_key) if cur_key in THEMES else 0
        self._combo.setCurrentIndex(idx)
        self._combo.currentIndexChanged.connect(self._preview_theme)
        theme_row = QHBoxLayout()
        b_prev_t = QPushButton("◀"); b_prev_t.setFixedWidth(32)
        b_prev_t.setToolTip("Thème précédent")
        b_prev_t.clicked.connect(lambda: self._combo.setCurrentIndex(
            (self._combo.currentIndex() - 1) % self._combo.count()))
        b_next_t = QPushButton("▶"); b_next_t.setFixedWidth(32)
        b_next_t.setToolTip("Thème suivant")
        b_next_t.clicked.connect(lambda: self._combo.setCurrentIndex(
            (self._combo.currentIndex() + 1) % self._combo.count()))
        theme_row.addWidget(b_prev_t)
        theme_row.addWidget(self._combo, 1)
        theme_row.addWidget(b_next_t)
        g.addLayout(theme_row)
        g.addStretch()

        self._tabs.addTab(gen, "⚙  Général")

        # ── Tab 1 : Import USB ─────────────────────────────────────────────
        usb_tab = QWidget(); usb_tab.setStyleSheet("background: transparent;")
        u = QVBoxLayout(usb_tab); u.setContentsMargins(16, 16, 16, 8); u.setSpacing(10)

        u.addWidget(QLabel("Dossier de destination :"))
        usb_row = QHBoxLayout()
        self._usb_edit = QLineEdit(get_usb_target())
        usb_row.addWidget(self._usb_edit)
        b_usb = QPushButton("📁"); b_usb.setFixedWidth(36)
        b_usb.clicked.connect(self._pick_usb)
        usb_row.addWidget(b_usb)
        u.addLayout(usb_row)
        usb_hint = QLabel(
            "Structure créée automatiquement :\n"
            "destination / année / to_sort / mois / jour")
        usb_hint.setStyleSheet(f"color: {t['dim']}; font-size: 9pt;")
        u.addWidget(usb_hint)

        u.addSpacing(8)
        timeout_row = QHBoxLayout()
        timeout_lbl = QLabel("Timeout scan source (s) :")
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 120)
        self._timeout_spin.setSuffix(" s")
        self._timeout_spin.setValue(get_usb_timeout())
        self._timeout_spin.setFixedWidth(80)
        timeout_row.addWidget(timeout_lbl)
        timeout_row.addWidget(self._timeout_spin)
        timeout_row.addStretch()
        u.addLayout(timeout_row)

        u.addSpacing(8)
        workers_row = QHBoxLayout()
        workers_lbl = QLabel("Threads de copie parallèle :")
        self._workers_spin = QSpinBox()
        self._workers_spin.setRange(1, 32)
        self._workers_spin.setValue(get_usb_workers())
        self._workers_spin.setFixedWidth(80)
        workers_row.addWidget(workers_lbl)
        workers_row.addWidget(self._workers_spin)
        workers_row.addStretch()
        u.addLayout(workers_row)
        workers_hint = QLabel(
            f"Valeur recommandée sur cette machine : {DEFAULT_USB_WORKERS}.\n"
            "Réduire à 1–2 sur une machine peu puissante ou avec un disque dur rotatif.")
        workers_hint.setStyleSheet(f"color: {t['dim']}; font-size: 9pt;")
        u.addWidget(workers_hint)
        u.addStretch()

        self._tabs.addTab(usb_tab, "🔌  Import USB")

        self._tabs.setCurrentIndex(self._initial_tab)

        # ── Boutons OK / Annuler ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        b_cancel = QPushButton("Annuler"); b_cancel.clicked.connect(self._cancel)
        b_ok     = QPushButton("Enregistrer"); b_ok.setObjectName("btn_ok")
        b_ok.clicked.connect(self._save)
        btn_row.addWidget(b_cancel); btn_row.addWidget(b_ok)
        lay.addLayout(btn_row)

    def _pick_root(self):
        p = QFileDialog.getExistingDirectory(self, "Dossier racine", get_root())
        if p: self._root_edit.setText(p)

    def _pick_usb(self):
        p = QFileDialog.getExistingDirectory(self, "Destination import USB", get_usb_target())
        if p: self._usb_edit.setText(p)

    def _add_fmt(self):
        raw  = self._fmt_new.text().strip().lstrip('.').lower()
        if not raw:
            return
        existing = {self._fmt_list.item(i).text() for i in range(self._fmt_list.count())}
        if raw not in existing and f"🔒 {raw}" not in existing:
            self._fmt_list.addItem(raw)
        self._fmt_new.clear()

    def _del_fmt(self):
        for item in self._fmt_list.selectedItems():
            if item.text() not in self._default_fmt_names:
                self._fmt_list.takeItem(self._fmt_list.row(item))

    def _add_prio(self):
        name = self._prio_new.text().strip()
        if name and not any(
                self._prios_list.item(i).text() == name
                for i in range(self._prios_list.count())):
            self._prios_list.addItem(name)
        self._prio_new.clear()

    def _del_prio(self):
        for item in self._prios_list.selectedItems():
            self._prios_list.takeItem(self._prios_list.row(item))

    def _pick_exif(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner ExifTool", "", "Exécutables (*.exe);;Tous (*.*)")
        if p: self._exif_edit.setText(p)

    def _preview_theme(self, idx: int):
        key = self._combo.itemData(idx)
        apply_theme(key)

    def _save(self):
        set_root(self._root_edit.text())
        set_usb_target(self._usb_edit.text())
        set_usb_timeout(self._timeout_spin.value())
        set_usb_workers(self._workers_spin.value())
        set_prios([self._prios_list.item(i).text()
                  for i in range(self._prios_list.count())])
        set_exif(self._exif_edit.text())
        set_extra_formats([
            self._fmt_list.item(i).text()
            for i in range(self._fmt_list.count())
            if self._fmt_list.item(i).text() not in self._default_fmt_names
        ])
        apply_theme(self._combo.currentData())
        self.accept()

    def _cancel(self):
        apply_theme(self._orig_theme)
        self.reject()


# ── Custom Title Bar ───────────────────────────────────────────────────────

class _WinCtrlBtn(QWidget):
    clicked = pyqtSignal()

    def __init__(self, symbol: str, ckey: str, parent=None):
        super().__init__(parent)
        self._symbol = symbol
        self._ckey   = ckey
        self._hov    = 0.0
        self.setFixedSize(38, 46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._anim = QPropertyAnimation(self, b"_h", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def _h(self): return self._hov

    @_h.setter
    def _h(self, v):
        self._hov = v
        self.update()

    def enterEvent(self, _):
        self._anim.stop()
        self._anim.setStartValue(self._hov)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def leaveEvent(self, _):
        self._anim.stop()
        self._anim.setStartValue(self._hov)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _):
        t   = T()
        col = QColor(t.get(self._ckey, '#ffffff'))
        p   = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._hov > 0.01:
            bg = QColor(col)
            bg.setAlpha(int(self._hov * 200))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRect(QRectF(0, 0, self.width(), self.height()))

        # Symbol color: white on dark bg when hovered, theme color otherwise
        sym_col = QColor(0, 0, 0) if self._hov > 0.5 else col
        sym_col.setAlpha(int(80 + self._hov * 175 + (1 - self._hov) * 80))
        f = QFont("Segoe UI", 11, QFont.Weight.Bold if self._ckey == 'err' else QFont.Weight.Normal)
        p.setFont(f)
        p.setPen(sym_col)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._symbol)


class TitleBar(QWidget):
    def __init__(self, win: QWidget, title: str):
        super().__init__(win)
        self._win       = win
        self._drag_pos  = None
        self._maximized = False
        self.setFixedHeight(46)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 0, 0)
        lay.setSpacing(0)

        self._title_lbl = QLabel(title)
        lay.addWidget(self._title_lbl)
        self._refresh_title_style()
        theme_sig.changed.connect(self._refresh_title_style)
        lay.addStretch()

        self._btn_min = _WinCtrlBtn("─", 'warn', self)
        self._btn_max = _WinCtrlBtn("□", 'a1',   self)
        self._btn_cls = _WinCtrlBtn("✕", 'err',  self)
        self._btn_min.clicked.connect(win.showMinimized)
        self._btn_max.clicked.connect(self._toggle_max)
        self._btn_cls.clicked.connect(win.close)
        lay.addWidget(self._btn_min)
        lay.addWidget(self._btn_max)
        lay.addWidget(self._btn_cls)

    def _refresh_title_style(self):
        t = T()
        c = QColor(t['text'])
        c.setAlpha(215)
        self._title_lbl.setStyleSheet(
            f"color: rgba({c.red()},{c.green()},{c.blue()},{c.alpha()});"
            " font-size: 11pt; font-weight: 600;"
            " letter-spacing: 0.3px; background: transparent;")

    def _toggle_max(self):
        if self._maximized: self._win.showNormal()
        else:               self._win.showMaximized()
        self._maximized = not self._maximized

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self._win.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, e):
        self._toggle_max()

    def paintEvent(self, _):
        t = T()
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(*t['panel']))
        p.setPen(QColor(*t['border']))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


# ── Main Window ────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(820, 580)
        self.resize(1200, 800)
        self.setWindowIcon(create_app_icon())

        self._bg_phase = 0.0
        self._bg_timer = QTimer(self)
        self._bg_timer.timeout.connect(self._tick_bg)
        self._bg_timer.start(33)

        self._setup_ui()
        self._center()

        QTimer.singleShot(600, self._check_exiftool)
        self._folder_view.start_scan()

        # Polling USB toutes les 2 secondes
        self._usb_timer = QTimer(self)
        self._usb_timer.timeout.connect(self._poll_usb)
        self._usb_timer.start(2000)
        self._usb_state: tuple[str, str] | None = None
        self._mtp_state: str | None = None
        self._mtp_poll_counter   = 0
        self._mtp_scan_worker: object | None = None
        self._mtp_disconnected_during_import = False
        QTimer.singleShot(200, self._poll_usb)
        # Premier scan téléphone immédiat (sinon ~10 s d'attente au démarrage)
        QTimer.singleShot(400, self._launch_mtp_scan)

    def _tick_bg(self):
        self._bg_phase = (self._bg_phase + 0.0018) % 1.0
        self.update()

    def _center(self):
        sg = QApplication.primaryScreen().geometry()
        self.move((sg.width() - self.width()) // 2,
                  (sg.height() - self.height()) // 2)

    def _check_exiftool(self):
        if not find_exiftool():
            reply = QMessageBox.question(
                self, "ExifTool introuvable",
                "ExifTool n'a pas été trouvé dans le PATH.\n"
                "Voulez-vous sélectionner son emplacement maintenant ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                p, _ = QFileDialog.getOpenFileName(
                    self, "Sélectionner exiftool.exe", "",
                    "Exécutables (*.exe);;Tous (*.*)")
                if p:
                    set_exif(p)

    def _setup_ui(self):
        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)

        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._titlebar = TitleBar(self, WINDOW_TITLE)
        lay.addWidget(self._titlebar)

        # ── Tab bar ──────────────────────────────────────────────────────
        tab_row = QHBoxLayout()
        tab_row.setContentsMargins(16, 6, 16, 0)
        tab_row.setSpacing(8)

        self._tab_sort_btn = _TabButton("📂  Trier par date")
        self._tab_usb_btn  = _TabButton("💾  Carte SD")
        self._tab_usb_btn.setVisible(False)
        self._tab_mtp_btn  = _TabButton("📱  Téléphone")
        self._tab_mtp_btn.setVisible(False)

        self._tab_sort_btn.clicked.connect(lambda: self._switch_tab(0))
        self._tab_usb_btn.clicked.connect(lambda: self._switch_tab(1))
        self._tab_mtp_btn.clicked.connect(lambda: self._switch_tab(2))

        tab_row.addWidget(self._tab_sort_btn)
        tab_row.addWidget(self._tab_usb_btn)
        tab_row.addWidget(self._tab_mtp_btn)
        tab_row.addSpacing(8)
        # Tant qu'aucun appareil n'est branché : onglet fantôme animé, à
        # l'endroit où l'onglet de l'appareil apparaîtra.
        self._ghost_tab = _GhostTab()
        self._ghost_tab.setVisible(False)
        tab_row.addWidget(self._ghost_tab)
        tab_row.addStretch()
        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(400)
        self._scan_timer.timeout.connect(self._tick_scan_indicator)
        self._scan_timer.start()
        lay.addLayout(tab_row)

        # ── Outer stack (tab pages) ───────────────────────────────────────
        self._outer_stack = FadeStack()

        # Tab 0 : vue tri par date (stack interne existant)
        self._stack         = FadeStack()
        self._folder_view   = FolderListView()
        self._process_view  = ProcessView()
        self._summary_view  = SummaryView()
        self._stack.addWidget(self._folder_view)   # 0
        self._stack.addWidget(self._process_view)  # 1
        self._stack.addWidget(self._summary_view)  # 2
        self._outer_stack.addWidget(self._stack)   # tab 0

        # Tab 1 : import USB
        self._usb_view = UsbImportView()
        self._outer_stack.addWidget(self._usb_view)  # tab 1
        self._mtp_view = UsbImportView()
        self._outer_stack.addWidget(self._mtp_view)  # tab 2

        lay.addWidget(self._outer_stack)

        self._switch_tab(0)

        # Resize grip
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 3, 3)
        grip_row.addStretch()
        grip = QSizeGrip(central)
        grip.setStyleSheet("QSizeGrip { background: transparent; }")
        grip_row.addWidget(grip)
        lay.addLayout(grip_row)

        self._folder_view.folder_selected.connect(self._do_organise)
        self._folder_view.browse_requested.connect(self._browse)
        self._folder_view.options_opened.connect(self._open_options)
        self._usb_view.options_requested.connect(lambda: self._open_options(tab=1))
        self._mtp_view.options_requested.connect(lambda: self._open_options(tab=1))
        self._mtp_view.import_finished.connect(self._on_import_finished)
        self._folder_view.about_opened.connect(self._open_about)
        self._process_view.done.connect(self._show_summary)
        self._summary_view.back.connect(self._back_to_list)

    def _on_import_finished(self):
        if self._mtp_disconnected_during_import:
            self._mtp_disconnected_during_import = False
            if self._mtp_state is None:
                self._tab_mtp_btn.setVisible(False)
                if self._outer_stack.currentIndex() == 2:
                    self._switch_tab(1 if self._usb_state else 0)

    def _switch_tab(self, idx: int):
        self._outer_stack.switch_to(idx)
        self._tab_sort_btn.set_active(idx == 0)
        self._tab_usb_btn.set_active(idx == 1)
        self._tab_mtp_btn.set_active(idx == 2)

    def _tick_scan_indicator(self):
        if self._tab_mtp_btn.isVisible():
            self._ghost_tab.stop()
            return
        self._ghost_tab.set_text(
            "Recherche d'un téléphone…" if self._tab_usb_btn.isVisible()
            else "Recherche d'une carte SD ou d'un téléphone…")
        self._ghost_tab.start()

    def _poll_usb(self):
        try:
            result = find_usb_dcim()
            if result != self._usb_state:
                self._usb_state = result
                log.info("État USB changé : %s", result)
                if result:
                    drive, dcim = result
                    self._tab_usb_btn.setText(
                        f"💾  Carte SD ({result[0].rstrip(chr(92))})")
                    self._tab_usb_btn.setVisible(True)
                    self._usb_view.refresh_usb(drive, dcim)
                else:
                    self._tab_usb_btn.setVisible(False)
                    if self._outer_stack.currentIndex() == 1:
                        self._switch_tab(2 if self._mtp_state else 0)
        except Exception:
            log.exception("_poll_usb exception")

        # Polling MTP toutes les ~10 secondes (5 x 2s)
        self._mtp_poll_counter = (self._mtp_poll_counter + 1) % 5
        if self._mtp_poll_counter == 0:
            self._launch_mtp_scan()

    def _launch_mtp_scan(self):
        if self._mtp_scan_worker is None or not self._mtp_scan_worker.isRunning():
            self._mtp_scan_worker = _MtpScanWorker()
            self._mtp_scan_worker.found.connect(self._on_mtp_found)
            self._mtp_scan_worker.not_found.connect(self._on_mtp_not_found)
            self._mtp_scan_worker.start()

    def _on_mtp_found(self, device_name: str):
        if self._mtp_state != device_name:
            self._mtp_state = device_name
            log.info("Téléphone MTP détecté : %s", device_name)
            self._tab_mtp_btn.setText(f"📱  {device_name[:20]}")
            self._tab_mtp_btn.setVisible(True)
            self._mtp_view.refresh_mtp(device_name)

    def _on_mtp_not_found(self):
        if self._mtp_state is not None:
            self._mtp_state = None
            log.info("Téléphone MTP déconnecté")
            if self._mtp_view.is_importing():
                self._mtp_disconnected_during_import = True
                self._mtp_view.notify_mtp_disconnected()
            else:
                self._tab_mtp_btn.setVisible(False)
                if self._outer_stack.currentIndex() == 2:
                    self._switch_tab(1 if self._usb_state else 0)

    def _do_organise(self, data: dict):
        self._stack.switch_to(1)
        self._process_view.start(data)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier racine", get_root())
        if path:
            self._folder_view.start_scan(root=path)

    def _open_options(self, tab: int = 0):
        dlg = OptionsDialog(self, initial_tab=tab)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._folder_view.start_scan()

    def _open_about(self):
        AboutDialog(self).exec()

    def _show_summary(self, moved: int, skipped: int, errors: int, elapsed: float):
        self._stack.switch_to(2)
        self._summary_view.show_results(moved, skipped, errors, elapsed)

    def _back_to_list(self):
        self._stack.switch_to(0)
        self._folder_view.start_scan()

    def paintEvent(self, _):
        t  = T()
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r  = self.rect()
        ph = self._bg_phase

        # Animated gradient background
        c1   = QColor(*t['bg'][0])
        c2   = QColor(*t['bg'][1])
        angle = ph * math.tau
        gx1  = r.width()  * (0.30 + 0.14 * math.sin(angle))
        gy1  = r.height() * (0.20 + 0.09 * math.cos(angle * 0.7))
        gx2  = r.width()  * (0.70 + 0.10 * math.cos(angle * 1.3))
        gy2  = r.height() * (0.80 + 0.09 * math.sin(angle * 0.9))

        grad = QLinearGradient(gx1, gy1, gx2, gy2)
        grad.setColorAt(0, c1); grad.setColorAt(1, c2)

        clip = QPainterPath()
        clip.addRoundedRect(QRectF(r), 12, 12)
        p.setClipPath(clip)
        p.fillRect(r, grad)

        # Ambient glow orbs
        for ox, oy, orb_r, oc in t.get('orbs', []):
            cx = int(r.width() * ox)
            cy = int(r.height() * oy)
            rg = QRadialGradient(cx, cy, orb_r)
            rg.setColorAt(0, QColor(*oc))
            rg.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(r, rg)

        # Window border
        p.setClipping(False)
        p.setPen(QPen(QColor(*t['border']), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(r).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)


# ── Entry Point ────────────────────────────────────────────────────────────

def main():
    def _excepthook(exc_type, exc_value, exc_tb):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log.critical("Exception non interceptée :\n%s", msg)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    apply_theme()
    app.setWindowIcon(create_app_icon())

    log.info("QApplication créée, lancement de MainWindow")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
