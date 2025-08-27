import sys
import os
import geocoder
import json
from datetime import datetime
import pytz
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QFontDialog, QSlider, QVBoxLayout,
    QPushButton, QColorDialog, QDialog,QComboBox, QLabel,
)
from PyQt5.QtGui import QFont, QPainter, QColor, QPixmap
from PyQt5.QtCore import Qt, QTimer, QPoint

apikey = os.getenv("OWM_API_KEY", "ec3c4ad34aa898da907fae6ea5e7a23f")
SETTINGS_FILE = "clocksettings.json"


def get_city():
    try:
        ip_data = requests.get("https://api.ipify.org?format=json", timeout=5).json()
        ip = ip_data["ip"]
        g = geocoder.ip(ip)
        return g.city
    except:
        return "Delhi"  # fallback city


def get_shadow_color_based_on_font(font_color):
    r, g, b, _ = font_color.getRgb()
    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    if brightness > 128:
        return QColor(0, 0, 0, 150)  # dark shadow
    else:
        return QColor(255, 255, 255, 150)  # light shadow


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.clock = parent
        self.setWindowTitle("Clock Settings")
        self.setFixedSize(300, 400)

        layout = QVBoxLayout()

        font_btn = QPushButton("Choose Font")
        font_btn.clicked.connect(self.choose_font)
        layout.addWidget(font_btn)

        layout.addWidget(QLabel("Time Font Size"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(40)
        self.size_slider.setMaximum(90)
        self.size_slider.setValue(self.clock.time_size)
        self.size_slider.valueChanged.connect(self.change_time_size)
        layout.addWidget(self.size_slider)

        layout.addWidget(QLabel("Date Font Size"))
        self.date_slider = QSlider(Qt.Horizontal)
        self.date_slider.setMinimum(10)
        self.date_slider.setMaximum(60)
        self.date_slider.setValue(self.clock.date_size)
        self.date_slider.valueChanged.connect(self.change_date_size)
        layout.addWidget(self.date_slider)

        layout.addWidget(QLabel("Line Spacing"))
        self.spacing_slider = QSlider(Qt.Horizontal)
        self.spacing_slider.setMinimum(0)
        self.spacing_slider.setMaximum(20)
        self.spacing_slider.setValue(self.clock.line_spacing)
        self.spacing_slider.valueChanged.connect(self.change_spacing)
        layout.addWidget(self.spacing_slider)

        color_btn = QPushButton("Choose Color")
        color_btn.clicked.connect(self.choose_color)
        layout.addWidget(color_btn)

        layout.addWidget(QLabel("Timezone"))
        self.tz_combo = QComboBox()
        self.tz_combo.addItems(pytz.all_timezones)
        self.tz_combo.setCurrentText(self.clock.timezone)
        self.tz_combo.currentTextChanged.connect(self.change_timezone)
        layout.addWidget(self.tz_combo)

        shadow_btn = QPushButton("Toggle Shadow")
        shadow_btn.clicked.connect(self.toggle_shadow)
        layout.addWidget(shadow_btn)

        btn_sv = QPushButton("Save Settings")
        btn_sv.clicked.connect(self.clock.save_settings)
        layout.addWidget(btn_sv)

        self.setLayout(layout)

    def choose_font(self):
        font, ok = QFontDialog.getFont(QFont(self.clock.font_family, self.clock.time_size), self)
        if ok:
            self.clock.font_family = font.family()
            self.clock.time_size = font.pointSize()
            self.clock.font_is_bold = font.bold()
            self.clock.font_is_italic = font.italic()
            self.size_slider.setValue(self.clock.time_size)
            self.clock.update()

    def change_time_size(self, value):
        self.clock.time_size = value
        self.clock.update()

    def change_date_size(self, value):
        self.clock.date_size = value
        self.clock.update()

    def change_spacing(self, value):
        self.clock.line_spacing = value
        self.clock.update()


    def choose_color(self):
        color = QColorDialog.getColor(self.clock.color, self)
        if color.isValid():
            self.clock.color = color
            self.clock.update()
    def change_timezone(self, tz):
        self.clock.timezone = tz
        self.clock.update()

    def toggle_shadow(self):
        self.clock.shadow_enabled = not self.clock.shadow_enabled
        self.clock.update()


class TransparentClock(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(600, 600)
        # Place window at top-right corner by default
        screen = QApplication.primaryScreen().availableGeometry()
        window_size = self.frameGeometry()
        x = screen.right() - window_size.width() + 100   # 110px margin
        y = screen.top() -50                          # -50px margin from top
        self.move(x, y)


        self.font_family = "DS-Digital"
        self.font_is_bold = False
        self.font_is_italic = False
        self.time_size = 60
        self.date_size = 30
        self.line_spacing = 2
        self.color = QColor("white")
        self.is_24_hour = True
        self.drag_position = QPoint()
        self.timezone = "Asia/Kolkata"
        self.city = get_city()

        self.shadow_enabled = True  # 🔹 shadow toggle flag

        self.weather_data = {}
        self.weather_icon = None

        self.load_settings()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

        self.fetch_weather()
        self.weather_timer = QTimer()
        self.weather_timer.timeout.connect(self.fetch_weather)
        self.weather_timer.start(15 * 60 * 1000)

    def fetch_weather(self):
        try:
            response = requests.get(
                f"https://api.openweathermap.org/data/2.5/weather?q={self.city}&appid={apikey}&units=metric",
                timeout=5
            )
            if response.ok:
                self.weather_data = response.json()
                icon_code = self.weather_data["weather"][0]["icon"]
                icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"
                icon_response = requests.get(icon_url, timeout=5)
                if icon_response.ok:
                    self.weather_icon = QPixmap()
                    self.weather_icon.loadFromData(icon_response.content)
        except Exception as e:
            print("Weather fetch failed:", e)
            self.weather_data = {}
            self.weather_icon = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        now = datetime.now(pytz.timezone(self.timezone))
        time_str = now.strftime("%H:%M:%S") if self.is_24_hour else now.strftime("%I:%M:%S %p")
        date_str = now.strftime("%a, %d %b %y")

        try:
            temp = self.weather_data["main"]["temp"]
            weather_text = f"{temp}°C"
        except:
            weather_text = "Weather unavailable"

        spacing = self.line_spacing
        center_x = self.rect().center().x()
        current_y = 30

        shadow_color = get_shadow_color_based_on_font(self.color)
        shadow_offset_x, shadow_offset_y = 1, 1

        # TIME
        time_font = QFont(self.font_family, self.time_size)
        time_font.setBold(self.font_is_bold)
        time_font.setItalic(self.font_is_italic)
        painter.setFont(time_font)
        time_metrics = painter.fontMetrics()
        time_width = time_metrics.horizontalAdvance(time_str)
        time_height = time_metrics.ascent()

        if self.shadow_enabled:
            painter.setPen(shadow_color)
            painter.drawText(center_x - time_width // 2 + shadow_offset_x, current_y + time_height + shadow_offset_y, time_str)
        painter.setPen(self.color)
        painter.drawText(center_x - time_width // 2, current_y + time_height, time_str)
        current_y += time_height + spacing

        # DATE
        date_font = QFont(self.font_family, self.date_size)
        date_font.setBold(self.font_is_bold)
        date_font.setItalic(self.font_is_italic)
        painter.setFont(date_font)
        date_metrics = painter.fontMetrics()
        date_width = date_metrics.horizontalAdvance(date_str)
        date_height = date_metrics.ascent()

        if self.shadow_enabled:
            painter.setPen(shadow_color)
            painter.drawText(center_x - date_width // 2 + shadow_offset_x, current_y + date_height + shadow_offset_y, date_str)
        painter.setPen(self.color)
        painter.drawText(center_x - date_width // 2, current_y + date_height, date_str)
        current_y += date_height + spacing

        # WEATHER
        weather_font = QFont(self.font_family, 16)
        weather_font.setBold(self.font_is_bold)
        weather_font.setItalic(self.font_is_italic)
        painter.setFont(weather_font)
        weather_metrics = painter.fontMetrics()
        weather_width = weather_metrics.horizontalAdvance(weather_text)
        weather_height = weather_metrics.ascent()

        if self.shadow_enabled:
            painter.setPen(shadow_color)
            painter.drawText(center_x - weather_width // 2 + shadow_offset_x, current_y + weather_height + shadow_offset_y, weather_text)
        painter.setPen(self.color)
        painter.drawText(center_x - weather_width // 2, current_y + weather_height, weather_text)
        current_y += weather_height + spacing

        # ICON
        if self.weather_icon:
            icon_size = 50
            painter.drawPixmap(center_x - icon_size // 2, current_y, icon_size, icon_size, self.weather_icon)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self.open_settings()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)

    def mouseDoubleClickEvent(self, event):
        self.is_24_hour = not self.is_24_hour
        self.update()

    def open_settings(self):
        SettingsDialog(self).exec_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def save_settings(self):
        settings = {
            "font_family": self.font_family,
            "font_is_bold": self.font_is_bold,
            "font_is_italic": self.font_is_italic,
            "time_size": self.time_size,
            "date_size": self.date_size,
            "color": self.color.name(),
            "timezone": self.timezone,
            "line_spacing": self.line_spacing,
            "shadow_enabled": self.shadow_enabled
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    self.font_family = settings.get("font_family", "DS-Digital")
                    self.font_is_bold = settings.get("font_is_bold", False)
                    self.font_is_italic = settings.get("font_is_italic", False)
                    self.time_size = settings.get("time_size", 60)
                    self.date_size = settings.get("date_size", 30)
                    self.color = QColor(settings.get("color", "white"))
                    self.timezone = settings.get("timezone", "Asia/Kolkata")
                    self.line_spacing = settings.get("line_spacing", 2)
                    self.shadow_enabled = settings.get("shadow_enabled", True)
            except Exception as e:
                print("Failed to load settings:", e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    clock = TransparentClock()
    clock.show()
    sys.exit(app.exec_())
