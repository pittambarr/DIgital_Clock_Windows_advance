import sys
import os
import json
from datetime import datetime
import pytz
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QFontDialog, QSlider, QVBoxLayout,
    QPushButton, QColorDialog, QDialog, QLabel
)
from PyQt5.QtGui import QFont, QPainter, QColor, QPixmap
from PyQt5.QtCore import Qt, QTimer, QPoint

apikey = "ec3c4ad34aa898da907fae6ea5e7a23f"
SETTINGS_FILE = "clocksettings.json"
try:
# Get user's city
    ip_data = requests.get("https://api.ipify.org?format=json").json()
    ip = ip_data["ip"]
    location_data = requests.get(f"http://ip-api.com/json/{ip}").json()
    usr = location_data["city"]
except Exception as e:
    e


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.clock = parent
        self.setWindowTitle("Clock Settings")
        self.setFixedSize(300, 300)

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

        color_btn = QPushButton("Choose Color")
        color_btn.clicked.connect(self.choose_color)
        layout.addWidget(color_btn)

        btn_sv = QPushButton("Save Settings")
        btn_sv.clicked.connect(self.clock.save_settings)
        layout.addWidget(btn_sv)

        self.setLayout(layout)

    def choose_font(self):
        font, ok = QFontDialog.getFont(QFont(self.clock.font_family, self.clock.time_size), self)
        if ok:
            self.clock.font_family = font.family()
            self.clock.time_size = font.pointSize()
            self.size_slider.setValue(self.clock.time_size)
            self.clock.update()

    def change_time_size(self, value):
        self.clock.time_size = value
        self.clock.update()

    def change_date_size(self, value):
        self.clock.date_size = value
        self.clock.update()

    def choose_color(self):
        color = QColorDialog.getColor(self.clock.color, self)
        if color.isValid():
            self.clock.color = color
            self.clock.update()


class TransparentClock(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(600, 600)

        self.font_family = "DS-Digital"
        self.time_size = 60
        self.date_size = 30
        self.color = QColor("white")
        self.is_24_hour = True
        self.drag_position = QPoint()
        self.timezone = "Asia/Kolkata"

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
                f"https://api.openweathermap.org/data/2.5/weather?q={usr}&appid={apikey}&units=metric"
            )
            if response.ok:
                self.weather_data = response.json()
                icon_code = self.weather_data["weather"][0]["icon"]
                icon_url = f"http://openweathermap.org/img/wn/{icon_code}@2x.png"
                icon_response = requests.get(icon_url)
                if icon_response.ok:
                    self.weather_icon = QPixmap()
                    self.weather_icon.loadFromData(icon_response.content)
        except:
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
            weather_text = f"  {temp}°C"
        except:
            weather_text = "Weather unavailable"

        shadow_offset = 1
        shadow_color = QColor(0, 0, 0, 50)

        # Time
        painter.setFont(QFont(self.font_family, self.time_size))
        time_rect = self.rect().adjusted(0, 0, 0, -50)
        painter.setPen(shadow_color)
        painter.drawText(time_rect.translated(shadow_offset, shadow_offset), Qt.AlignCenter, time_str)
        painter.setPen(self.color)
        painter.drawText(time_rect, Qt.AlignCenter, time_str)

        # Date
        painter.setFont(QFont(self.font_family, self.date_size))
        date_rect = self.rect().adjusted(0, 50, 0, 0)
        painter.setPen(shadow_color)
        painter.drawText(date_rect.translated(shadow_offset, shadow_offset), Qt.AlignCenter, date_str)
        painter.setPen(self.color)
        painter.drawText(date_rect, Qt.AlignCenter, date_str)

        # Weather Text
        painter.setFont(QFont(self.font_family, 16))
        weather_rect = self.rect().adjusted(0, 120, 0, 0)
        painter.setPen(shadow_color)
        painter.drawText(weather_rect.translated(shadow_offset, shadow_offset), Qt.AlignCenter, weather_text)
        painter.setPen(self.color)
        painter.drawText(weather_rect, Qt.AlignCenter, weather_text)

        # Weather Icon
        if self.weather_icon:
            icon_size = 50
            x = self.width() // 2-100
            y = 335
            painter.drawPixmap(x, y, icon_size, icon_size, self.weather_icon)

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
            "time_size": self.time_size,
            "date_size": self.date_size,
            "color": self.color.name(),
            "timezone": self.timezone
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    self.font_family = settings.get("font_family", self.font_family)
                    self.time_size = settings.get("time_size", self.time_size)
                    self.date_size = settings.get("date_size", self.date_size)
                    self.color = QColor(settings.get("color", self.color.name()))
                    self.timezone = settings.get("timezone", self.timezone)
            except:
                pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    clock = TransparentClock()
    clock.show()
    sys.exit(app.exec_())
