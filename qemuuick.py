import sys
import subprocess
import os
import threading
import base64
from io import BytesIO
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QComboBox, QPushButton, QVBoxLayout,
    QHBoxLayout, QMessageBox, QRadioButton, QButtonGroup, QFileDialog, QMainWindow, QMenuBar, QAction, QSplashScreen
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap


class QemuLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.qemu_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qemu')
        self.required_binaries = ['qemu-system-x86_64.exe', 'qemu-system-i386.exe']
        if not self.check_qemu():
            QMessageBox.critical(self, 'QEMU Missing', 'The QEMU directory or required binaries are missing. Please download QEMU.')
            sys.exit()
        self.initUI()

    def initUI(self):
        # Set window properties
        self.setWindowTitle('quemuuick - qemu quick - qemumuckuki!')
        self.resize(400, 400)
        self.center()

        # Create menubar
        menubar = self.menuBar()
        
        # File menu with Exit option
        file_menu = menubar.addMenu('File')
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu with About option
        help_menu = menubar.addMenu('Help')
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        # Create central widget and layout
        widget = QWidget()
        layout = QVBoxLayout()

        # System selection
        system_label = QLabel('Select System:')
        self.system_combo = QComboBox(self)
        self.system_combo.addItems([
            'x86_64', 'i386', 'arm', 'aarch64', 'mips', 'ppc', 'sparc', 'riscv64'
        ])
        layout.addWidget(system_label)
        layout.addWidget(self.system_combo)

        # ISO Path
        iso_label = QLabel('ISO Path:')
        self.iso_input = QLineEdit(self)
        iso_browse_button = QPushButton('Browse', self)
        iso_browse_button.clicked.connect(self.browse_iso)
        iso_layout = QHBoxLayout()
        iso_layout.addWidget(self.iso_input)
        iso_layout.addWidget(iso_browse_button)
        layout.addWidget(iso_label)
        layout.addLayout(iso_layout)

        # Memory selection with radio buttons
        mem_label = QLabel('Select Memory:')
        layout.addWidget(mem_label)

        self.mem_group = QButtonGroup(self)
        self.mem_1gb = QRadioButton('1024 MB (1 GB)')
        self.mem_2gb = QRadioButton('2048 MB (2 GB)')
        self.mem_4gb = QRadioButton('4096 MB (4 GB)')
        self.mem_custom = QRadioButton('Custom (MB)')

        self.mem_group.addButton(self.mem_1gb)
        self.mem_group.addButton(self.mem_2gb)
        self.mem_group.addButton(self.mem_4gb)
        self.mem_group.addButton(self.mem_custom)

        # Custom memory input
        self.custom_mem_input = QLineEdit(self)
        self.custom_mem_input.setPlaceholderText('Enter custom size in MB')
        self.custom_mem_input.setDisabled(True)

        # Radio button change event
        self.mem_custom.toggled.connect(self.toggle_custom_mem_input)

        # Add radio buttons to layout
        mem_layout = QVBoxLayout()
        mem_layout.addWidget(self.mem_1gb)
        mem_layout.addWidget(self.mem_2gb)
        mem_layout.addWidget(self.mem_4gb)
        mem_layout.addWidget(self.mem_custom)
        mem_layout.addWidget(self.custom_mem_input)
        layout.addLayout(mem_layout)

        # Error label to show feedback for incorrect memory values
        self.error_label = QLabel('')
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        # Custom switches input
        custom_switch_label = QLabel('Custom QEMU Switches:')
        layout.addWidget(custom_switch_label)

        self.custom_switch_input = QLineEdit(self)
        self.custom_switch_input.setPlaceholderText('e.g., -cpu host -enable-kvm')
        layout.addWidget(self.custom_switch_input)

        # Create Start and Exit buttons
        button_layout = QHBoxLayout()
        start_button = QPushButton('Start VM', self)
        exit_button = QPushButton('Exit', self)
        start_button.clicked.connect(self.start_vm)
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(start_button)
        button_layout.addWidget(exit_button)

        layout.addLayout(button_layout)

        # Set the central widget
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def check_qemu(self):
        """Check if the QEMU directory and required binaries exist."""
        if not os.path.exists(self.qemu_dir):
            return False

        for binary in self.required_binaries:
            if not os.path.exists(os.path.join(self.qemu_dir, binary)):
                return False

        return True

    def center(self):
        screen = QApplication.desktop().screenGeometry()
        window_size = self.geometry()
        x = (screen.width() - window_size.width()) // 2
        y = (screen.height() - window_size.height()) // 2
        self.move(x, y)

    def toggle_custom_mem_input(self):
        """Enable or disable the custom memory input depending on the selected radio button."""
        if self.mem_custom.isChecked():
            self.custom_mem_input.setDisabled(False)
        else:
            self.custom_mem_input.setDisabled(True)

    def browse_iso(self):
        """Open a file dialog to allow the user to select an ISO file."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select ISO File", "", "ISO Files (*.iso);;All Files (*)", options=options)
        if file_path:
            self.iso_input.setText(file_path)

    def start_vm(self):
        # Retrieve selected system
        system = self.system_combo.currentText()

        # Retrieve ISO path
        iso_path = self.iso_input.text()

        # Determine memory size
        if self.mem_1gb.isChecked():
            ram = 1024
        elif self.mem_2gb.isChecked():
            ram = 2048
        elif self.mem_4gb.isChecked():
            ram = 4096
        elif self.mem_custom.isChecked():
            try:
                ram = int(self.custom_mem_input.text())  # Expect input in MB
                if ram < 128:
                    raise ValueError('Too low memory value.')
            except ValueError:
                self.error_label.setText('Please enter a valid memory size in MB (minimum 128 MB).')
                return
        else:
            self.error_label.setText('Please select a memory size.')
            return

        if not iso_path:
            self.error_label.setText('Please select an ISO path.')
            return

        # Get custom QEMU switches
        custom_switches = self.custom_switch_input.text()

        # Clear error label after all checks pass
        self.error_label.setText('')

        # Determine the QEMU executable based on system selection
        qemu_exe = os.path.join(self.qemu_dir, f'qemu-system-{system}.exe')

        # QEMU base command
        command = [
            qemu_exe,
            '-m', str(ram),
            '-cdrom', iso_path,
            '-boot', 'd'
        ]

        # Add custom switches (if any)
        if custom_switches:
            command += custom_switches.split()

        # Run QEMU in a separate thread
        threading.Thread(target=self.run_qemu, args=(command,)).start()

    def run_qemu(self, command):
        """Runs the QEMU command in a separate thread."""
        try:
            # Launch the VM using subprocess
            subprocess.run(command)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to start VM: {str(e)}')

    def show_about_dialog(self):
        """Show the About dialog."""
        QMessageBox.about(self, 'About', 'v69.4.20\nwww.onlyfans.com/StringyLinguini')

BASE64_IMAGE = """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AAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLiA0h8+YPEIECBAgAABAgQIKP12gAABAgQIECBAgEC4gNIfPmDxCBAgQIAAAQIECCj9doAAAQIECBAgQIBAuIDSHz5g8QgQIECAAAECBAgo/XaAAAECBAgQIECAQLhAU/r/OcnYDc8pHgECBAgQIECAAIHWClTP7vS26qostlZAcAIECBAgQIAAAQLBAlVdtqtvPul9XerSC84pGgECBAgQIECAAIHWCuyV/ufLvSfjUpZaqyA4AQIECBAgQIAAgWSBqgyqZ8u9tbqUfnJO2QgQIECAAAECBAi0VaBTymb1dKX3sBqX+21FkJsAAQIECBAgQIBAtEBdPlf6oycsHAECBAgQIECAQNsF6k55VL1YudXfHY/W2o4hPwECBAgQIECAAIFEgbrq3Ku2+kvd93aGzWf1+0OAAAECBAgQIECAQJhAZ2H+ZtVk8gVdYZMVhwABAgQIECBAgMB/BYY/3Rj8eK/0+9hOO0GAAAECBAgQIEAgT6D55J6PNga390q/T/DJG7BEBAgQIECAAAECBJo38d54PFjdK/3ezGshCBAgQIAAAQIECOQJzHWu3P3g8V/X90p/8+fZnd5WXZXFvKgSESBAgAABAgQIEGilwPDlQvfmzfXN4evS74hPKxdBaAIECBAgQIAAgVCBSdFf/8nG4G4T73Xp//tvf7XU2d19EppZLAIECBAgQIAAAQKtEpge7fmf0t/8iyM+rdoDYQkQIECAAAECBHIFXh/tOVT6HfHJnbpkBAgQIECAAAEC7RHYf7TnUOl/3v94cbzz3VZ7OCQlQIAAAQIECBAgkCcwnpu7/bM//mVzmuz1mf7pD7650/tsctL/07zoEhEgQIAAAQIECBDIFzh4l//Qnf7mB+725y+ChAQIECBAgAABArkCB+/yv7H0Nz98ttxbq0vp51JIRoAAAQIECBAgQCBP4E13+Y8s/e725y2ARAQIECBAgAABAvkCb7rLf2Tpd7c/fyEkJECAAAECBAgQyBI46i7/saV/q7/UfW9n2HySTzeLQxoCBAgQIECAAAECcQLDurp6+8YXXw7elOzQp/fsf9CLlVv93fFoLY5EIAIECBAgQIAAAQJBAldKZ/XDja8eHRXp2NLf/JI39QZtgygECBAgQIAAAQJxAscd65mGfWvpd8wnbi8EIkCAAAECBAgQyBE49ljPiUt/80DHfHK2QhICBAgQIECAAIEcgbcd65mp9DcP9k29OcshCQECBAgQIECAwP+/QN0pj248HqyeJMlbj/fsv4jifxJSjyFAgAABAgQIECBwwQJ1+fzl9e7qzfXN4UmeaabS31zw+XLvybiUpZNc3GMIECBAgAABAgQIEDhngaoMXl7r3j5p4W+efebSv/fG3m+HT0pdeuf88l2OAAECBAgQIECAAIFjBKq6bH9/vfuLWQr/qUp/80uKv10kQIAAAQIECBAgcMkCkzv8nWvzdz9a//P2rM88853+6RM0xX9+Z7jmqM+s5B5PgAABAgQIECBAYDaBTimb3y107856h3/6LKcu/dMLeHPvbAPzaAIECBAgQIAAAQKzCDRfvvX9QvfeaQt/81xnLv3NRZ6u9B5W43J/lhfvsQQIECBAgAABAgQIHC/QfCznq/e7D85S+M+t9DcX+sfyL++PyvihwREgQIAAAQIECBAgcGaB4eSLtx58uPHVozNf6bzu9E9fSHPO/0c7w8/qUvrn8eJcgwABAgQIECBAgEDbBJrz+2Vh/t5p3rB7lNW5HO85eHF3/du2mvISIECAAAECBAicg8C53t3f/3oupPQ3T7D3sZ7/Gj6cvGvg03MAcAkCBAgQIECAAAECsQIXcXf/Ukr/9EmefvLrXjV+9XvlP3ZHBSNAgAABAgQIEDilQFP2R9XV1RtffDk45SVO9GsXdqf/4LMr/yeahwcRIECAAAECBAi0QOCyyv6U8tJKvzv/LdheEQkQIECAAAECBI4TGE7K9+a4uvrgou/sH3wRl17697+AFyu3+ruj0e8c/fFfBwECBAgQIECAQKjAXtEfzc39YXd+YXDWz9s/rdE7Lf2H/geg1L3OePybcSlLpw3k9wgQIECAAAECBAi8Q4Hh5OjOYNQpg6vlyp/+/f71zXdV9Pcb/GBK/8HBPO9/vDj69uVSVZXFajz++eSFdsdV6U6++bdbT/6ePL75xx8CBAgQIECAAAEClykwrOoynHxT7rDT/F3KcNwp26Xu/K2UK4NX165t/xBK/kGQ/wDifhaxBRrXOQAAAABJRU5ErkJggg==
"""

# Main application with splash screen
#def main():
#    app = QApplication(sys.argv)
#    
#    # Load the splash screen image
#    splash_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'splash_image.png')
#    splash_pix = QPixmap(splash_image_path)
#    
#    # Create the splash screen
#    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
#    splash.show()
#    
#    # Wait for 3 seconds and then load the main window
#   QTimer.singleShot(3000, splash.close)  # Display splash screen for 3 seconds
#   
#    launcher = QemuLauncher()
#   launcher.show()
#
#    sys.exit(app.exec_())

def main():
    app = QApplication(sys.argv)

    # Decode the Base64 image and convert it to QPixmap
    image_data = base64.b64decode(BASE64_IMAGE)
    pixmap = QPixmap()
    pixmap.loadFromData(image_data)

    # Create the splash screen
    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    splash.show()

    # Wait for 3 seconds and then load the main window
    QTimer.singleShot(3000, splash.close)  # Display splash screen for 3 seconds
    
    launcher = QemuLauncher()
    launcher.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
