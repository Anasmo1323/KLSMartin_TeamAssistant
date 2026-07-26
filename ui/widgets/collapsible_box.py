from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QToolButton, QScrollArea, 
                             QSizePolicy, QFrame)
from PyQt6.QtCore import Qt, QParallelAnimationGroup, QPropertyAnimation, QAbstractAnimation

class CollapsibleBox(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)

        self.toggle_button = QToolButton(
            text=title, checkable=True, checked=True
        )
        self.toggle_button.setStyleSheet("""
            QToolButton {
                border: 1px solid #C4C4C3;
                border-radius: 4px;
                background-color: #f0f0f0;
                padding: 6px;
                font-weight: normal;
                text-align: left;
            }
            QToolButton:checked {
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
        """)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)

        self.toggle_animation = QParallelAnimationGroup(self)

        self.content_area = QScrollArea(maximumHeight=0, minimumHeight=0)
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.content_area.setFrameShape(QFrame.Shape.NoFrame)
        self.content_area.setWidgetResizable(True)
        self.content_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #C4C4C3;
                border-top: none;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_area)

        self.toggle_animation.addAnimation(QPropertyAnimation(self, b"minimumHeight"))
        self.toggle_animation.addAnimation(QPropertyAnimation(self, b"maximumHeight"))
        self.toggle_animation.addAnimation(QPropertyAnimation(self.content_area, b"maximumHeight"))

    def on_pressed(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(
            Qt.ArrowType.DownArrow if not checked else Qt.ArrowType.RightArrow
        )
        self.toggle_animation.setDirection(
            QAbstractAnimation.Direction.Forward if not checked else QAbstractAnimation.Direction.Backward
        )
        self.toggle_animation.start()

    def setContentLayout(self, layout):
        lay = self.content_area.layout()
        del lay
        widget = QWidget()
        widget.setLayout(layout)
        self.content_area.setWidget(widget)
        
        collapsed_height = self.sizeHint().height() - self.content_area.maximumHeight()
        content_height = layout.sizeHint().height() + 20
        
        for i in range(self.toggle_animation.animationCount()):
            animation = self.toggle_animation.animationAt(i)
            animation.setDuration(300)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = self.toggle_animation.animationAt(self.toggle_animation.animationCount() - 1)
        content_animation.setDuration(300)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)
        
        self.toggle_button.setChecked(True)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
        self.content_area.setMaximumHeight(content_height)
        
    def set_highlight(self, active: bool):
        if active:
            self.toggle_button.setStyleSheet("""
                QToolButton {
                    border: 1px solid #005A9E;
                    border-radius: 4px;
                    background-color: #E6F2FA;
                    color: #005A9E;
                    padding: 6px;
                    font-weight: bold;
                    text-align: left;
                }
                QToolButton:checked {
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                }
            """)
        else:
            self.toggle_button.setStyleSheet("""
                QToolButton {
                    border: 1px solid #C4C4C3;
                    border-radius: 4px;
                    background-color: #f0f0f0;
                    color: black;
                    padding: 6px;
                    font-weight: normal;
                    text-align: left;
                }
                QToolButton:checked {
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                }
            """)
