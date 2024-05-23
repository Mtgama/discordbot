import discord
import asyncio
import os
import subprocess
from PyQt5 import QtCore
from discord.ext import commands
from ctypes import cast, POINTER
import threading
from PyQt5.QtGui import QIcon
import ctypes
from pydub import AudioSegment
from discord.ext import commands
import sounddevice as sd
import numpy as np
import time
import pyautogui
import cv2
import traceback
import logging
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pyaudio
import wave
import pygame
from pygame import mixer
from PIL import Image
import keyboard
from PyQt5 import QtWidgets, QtCore
from win10toast import ToastNotifier

class DiscordBotThread(QtCore.QThread):
    connection_changed = QtCore.pyqtSignal(bool)
    message_received = QtCore.pyqtSignal(str)
    playback_canceled = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.connected = False
        self.monitoring_face = True
        self.monitoring_mouse = False
        self.monitoring_keyboard = False
        self.playback_canceled.connect(self.cancel_playback)
        self.commands = {
            'shutdown': 'Shutdown the system. Usage: shutdown <time> or shutdown now.',
            'photo': 'Take a photo using the webcam.',
            'screenshot': 'Take a screenshot of the screen.',
            'screenrecord': 'Record the screen for approximately 5 seconds.',
            'lock': 'Lock the system.',
            'cmd': 'Execute a command from the command prompt (cmd). Usage: cmd <command>',
            'recordvoice': 'Record surrounding sound for approximately 5 seconds.',
            'play': 'Play music or video. Usage: play <filename>',
            'mouse monitor': 'send mouse location',
            'mouse cancel': 'cancel detect mouse position',
            'keyboard monitor': 'send key clicked',
            'face_rec': 'Detect human faces in an image.',
            'alert': 'Play a loud alert sound.',
            'ls': 'List files and directories in the current directory.',
            'pwd': 'Display the absolute path of the current working directory.',
            'cd': 'Change the current working directory. Usage: cd <directory>',
            'sound':'mute and unmuted volume',
            'volume x' : 'change volume x%',
            'record_video' : 'record video from webcam, 7 secend'
        }
        self.toaster = ToastNotifier()
        self.alert_sound_file = 'alert.mp3'  # Path to the alert sound file

        # Load token from file if it exists
        self.token_file = 'token.txt'
        self.token = self.load_token()

    def load_token(self):
        token = ''
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as file:
                token = file.read().strip()
        return token
    

    async def monitor_mouse_position(self, message):
        # Send initial message to start mouse monitoring
        await message.channel.send("Starting mouse monitoring. Type 'mouse cancel' to stop.")

        # Set monitoring flag to True
        self.monitoring_mouse = True

        # Loop until monitoring is stopped
        while self.monitoring_mouse:
            # Check if the command "mouse cancel" has been received
            if not self.monitoring_mouse:
                await message.channel.send("Mouse monitoring canceled.")
                break

            # Get the current mouse position
            mouse_position = pyautogui.position()

            # Send the mouse position to Discord
            await message.channel.send(f"Mouse Position: {mouse_position}")

            # Wait for 5 seconds before sending the next update
            await asyncio.sleep(5)

    async def monitor_keyboard_input(self, message):
        # Send initial message to start keyboard monitoring
        await message.channel.send("Starting keyboard monitoring. Type 'keyboard cancel' to stop.")

        # Set monitoring flag to True
        self.monitoring_keyboard = True

        # Loop until monitoring is stopped
        while self.monitoring_keyboard:
            # Check if the command "keyboard cancel" has been received
            if not self.monitoring_keyboard:
                await message.channel.send("Keyboard monitoring canceled.")
                break

            # Get the latest keyboard event
            event = keyboard.read_event()

            # Send the keyboard event to Discord
            await message.channel.send(f"Keyboard Input: {event.name}")

    async def handle_command(self, message):
        if message.content.startswith('mouse'):
            if message.content == 'mouse':
                await message.channel.send("Please specify a command: 'mouse monitor' or 'mouse cancel'")
            elif message.content.startswith('mouse monitor'):
                # Start monitoring mouse position
                await self.monitor_mouse_position(message)
            elif message.content == 'mouse cancel':
                # Stop monitoring mouse position
                self.monitoring_mouse = False
            else:
                await message.channel.send("Invalid command. Type 'mouse monitor' to start monitoring or 'mouse cancel' to stop.")
        elif message.content.startswith('keyboard'):
            if message.content == 'keyboard':
                await message.channel.send("Please specify a command: 'keyboard monitor' or 'keyboard cancel'")
            elif message.content.startswith('keyboard monitor'):
                # Start monitoring keyboard input
                await self.monitor_keyboard_input(message)
            elif message.content == 'keyboard cancel':
                # Stop monitoring keyboard input
                self.monitoring_keyboard = False
            else:
                await message.channel.send("Invalid command. Type 'keyboard monitor' to start monitoring or 'keyboard cancel' to stop.")
        elif message.content.startswith('ls'):
            # List files and directories in the current directory
            file_list = os.listdir('.')
            await message.channel.send("Contents of current directory:\n" + "\n".join(file_list))
        elif message.content.startswith('alert'):
            import vlc
            p = vlc.MediaPlayer("alert.mp3")
            p.play()
        elif message.content.startswith('sound'):
            try:
        # Initialize COM
                ctypes.windll.ole32.CoInitialize(None)

                # Get the speakers and activate the volume interface
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))

                # Check if the volume is muted and toggle the mute state
                muted = volume.GetMute()
                if muted:
                    volume.SetMute(0, None)
                    await message.channel.send("Unmuted")
                else:
                    volume.SetMute(1, None)
                    await message.channel.send("Muted")

            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")

            finally:
                # Uninitialize COM
                ctypes.windll.ole32.CoUninitialize()
        elif message.content.startswith('volume'):
            try:
        # Extract the target volume percentage from the message content
                parts = message.content.split()
                if len(parts) == 2:
                    target_volume = int(parts[1])
                    if target_volume < 0 or target_volume > 100:
                        raise ValueError("Volume percentage must be between 0 and 100.")
                else:
                    raise ValueError("Invalid command format. Usage: volume <percentage>")

                # Initialize COM
                ctypes.windll.ole32.CoInitialize(None)

                # Get the speakers and activate the volume interface
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))

                # Calculate the volume level from the percentage
                new_volume_level = target_volume / 100.0

                # Set the new volume level
                volume.SetMasterVolumeLevelScalar(new_volume_level, None)

                # Send a message confirming the volume change
                await message.channel.send(f"Volume set to {target_volume}%.")

            except ValueError as ve:
                await message.channel.send(str(ve))

            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")

            finally:
                # Uninitialize COM
                ctypes.windll.ole32.CoUninitialize()

        


        elif message.content.startswith('notouch'):
            try:
                # Send warning alert
                await message.channel.send("Warning: Any mouse movement or key press will be detected!")

                # Function to check for mouse movement or key press
                # Function to check for mouse movement or key press
                async def check_for_activity():
                    while True:
                        if pyautogui.onScreen(0, 0):  # Check if mouse is on the screen
                            await message.channel.send("Mouse movement detected!")
                            break
                        if keyboard.is_pressed():  # Check if any key is pressed
                            await message.channel.send("Key press detected!")
                            break


                # Start a thread to check for activity
                activity_thread = threading.Thread(target=check_for_activity)
                activity_thread.start()

                # Take screenshot
                screenshot = pyautogui.screenshot()
                screenshot.save('screenshot.png')

                # Record video from webcam for 7 seconds
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    raise Exception("Failed to open webcam.")

                # Define the codec and create VideoWriter object
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))

                # Record video for 7 seconds
                start_time = time.time()
                while time.time() - start_time < 7:
                    ret, frame = cap.read()
                    if ret:
                        # Write the frame to the output video file
                        out.write(frame)
                    else:
                        break

                # Release the webcam and video writer
                cap.release()
                out.release()

                # Send the screenshot and recorded video to Discord
                await message.channel.send("Screenshot:")
                await message.channel.send(file=discord.File('screenshot.png'))
                await message.channel.send("Recorded Video:")
                await message.channel.send(file=discord.File('output.avi'))

            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")

        

        

        elif message.content.startswith('record_video'):
            try:
                # Record video from webcam for 7 seconds
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    await message.channel.send("Failed to open webcam.")
                    return

                # Define the codec and create VideoWriter object
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))

                # Record video for 7 seconds
                start_time = time.time()
                while time.time() - start_time < 7:
                    ret, frame = cap.read()
                    if ret:
                        # Write the frame to the output video file
                        out.write(frame)
                    else:
                        break

                # Release the webcam and video writer
                cap.release()
                out.release()

                # Send the recorded video to Discord
                await message.channel.send("Recording complete. Sending video...")
                await message.channel.send(file=discord.File('output.avi'))

                # Delay for 1 minute
                await asyncio.sleep(60)

                # Delete the video file
                os.remove('output.avi')

            except Exception as e:
                await message.channel.send(f"An error occurred: {str(e)}")


                


            
        elif message.content.startswith('pwd'):
            # Display the absolute path of the current working directory
            current_dir = os.getcwd()
            await message.channel.send(f"Current directory: {current_dir}")
        elif message.content.startswith('cd'):
            # Change the current working directory
            try:
                command_parts = message.content.split()
                if len(command_parts) == 2:
                    target_dir = command_parts[1]
                    os.chdir(target_dir)
                    await message.channel.send(f"Changed directory to: {os.getcwd()}")
                else:
                    await message.channel.send("Usage: cd <directory>")
            except Exception as e:
                await message.channel.send(f"Error: {str(e)}")

    async def face_rec(self, message):
        # Initialize the webcam
        cap = cv2.VideoCapture(0)

        # Start capturing images until a face is detected or the command is canceled
        while True:
            # Check if the command "face_rec cancel" has been received
            if not self.monitoring_face:
                await message.channel.send("Face recognition canceled.")
                break

            # Capture photo using webcam
            ret, frame = cap.read()

            # Detect faces in the captured frame
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            # If faces are detected, send the images to Discord with a 2-second interval
            if len(faces) > 0:
                for (x, y, w, h) in faces:
                    # Draw rectangles around the faces
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

                # Save the image
                cv2.imwrite('detected_faces.jpg', frame)

                # Send the image to Discord
                await message.channel.send("Human face detected!")
                await message.channel.send(file=discord.File('detected_faces.jpg'))

                # Remove the temporary image file
                os.remove('detected_faces.jpg')

                # Wait for 2 seconds before capturing the next image
                await asyncio.sleep(2)

            # Release the webcam if the command is canceled
            if not self.monitoring_face:
                cap.release()
                break

        # Release the webcam when face recognition is done or canceled
        cap.release()

    async def record_voice(self, message):
        # Parameters for audio recording
        duration = 5  # Duration of recording in seconds
        fs = 44100  # Sample rate
        channels = 1  # Mono channel

        try:
            print("Recording voice...")
            # Start recording
            recorded_audio = sd.rec(int(duration * fs), samplerate=fs, channels=channels, dtype='int16')
            sd.wait()  # Wait for recording to complete
            print("Recording complete.")

            # Save recorded audio to a WAV file
            with wave.open("output.wav", 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(fs)
                wf.writeframes(recorded_audio.tobytes())

            # Send the WAV file to Discord
            await message.channel.send(file=discord.File("output.wav"))

        except Exception as e:
            await message.channel.send(f"An error occurred: {str(e)}")

    async def delete_temp_file(self):
        await asyncio.sleep(5)
        os.remove('output.wav')

    def play_media(self, filename):
        if filename.endswith(('.mp3', '.wav')):
            mixer.init()
            mixer.music.load(filename)
            mixer.music.play()
            while mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        elif filename.endswith(('.mp4', '.avi')):
            subprocess.Popen(['start', '', filename], shell=True)

    async def cancel_playback(self, message):
        # Stop the playback of music or video
        # You need to implement the logic to stop the playback here
        # For example, if you're using pygame.mixer, you can use pygame.mixer.music.stop()
        # Example:
        pygame.mixer.music.stop()
        await message.channel.send('Playback canceled.')

    def run(self):
        intents = discord.Intents.default()

        client = commands.Bot(command_prefix='!', intents=intents)

        @client.event
        async def on_ready():
            print('Logged in as {0.user}'.format(client))
            # Set the connection status to True when bot is ready
            self.connected = True
            self.connection_changed.emit(True)
            self.toaster.show_toast("Discord Bot", "Connected to Discord", duration=5)

        @client.event
        async def on_disconnect():
            print('Disconnected from Discord')
            self.toaster.show_toast("Discord Bot", "Disconnected from Discord", duration=5)

        @client.event
        async def on_message(message):
            if message.author == client.user:
                return

            if message.content.startswith('shutdown'):
                command_parts = message.content.split(' ')
                if len(command_parts) == 2:  # Check if the command has 2 parts
                    if command_parts[1] == 'now':
                        await message.channel.send('Shutting down immediately...')
                        os.system('shutdown /s /t 0')  # Shutdown the system immediately
                        return
                    else:
                        try:
                            time = int(command_parts[1])
                            await message.channel.send(f'System will shutdown in {time} seconds.')
                            await asyncio.sleep(time)
                            await message.channel.send('Shutting down...')
                            os.system(f'shutdown /s /t {time}')  # Shutdown the system after specified time
                            return
                        except ValueError:
                            await message.channel.send('Invalid time provided.')

            elif message.content.startswith('photo'):
                # Capture photo using webcam
                cap = cv2.VideoCapture(0)
                ret, frame = cap.read()
                cap.release()

                # Save photo temporarily
                cv2.imwrite('temp_photo.jpg', frame)

                # Send photo to Discord
                await message.channel.send(file=discord.File('temp_photo.jpg'))

                # Delete temporary photo file
                os.remove('temp_photo.jpg')

            elif message.content.startswith('screenshot'):
                # Capture screenshot
                screenshot = pyautogui.screenshot()

                # Save screenshot temporarily
                screenshot.save('screenshot.png')

                # Send screenshot to Discord
                await message.channel.send(file=discord.File('screenshot.png'))

                # Delete temporary screenshot file
                os.remove('screenshot.png')
            elif message.content.startswith('face_rec'):
                await self.face_rec(message)
            elif message.content.startswith('screenrecord'):

                # Record screen for approximately 5 seconds
                frames = []
                for _ in range(5 * 10):  # Approximately 5 seconds at 10 frames per second
                    frame = pyautogui.screenshot()
                    frames.append(frame)

                    # Sleep for 0.1 second (10 frames per second)
                    await asyncio.sleep(0.1)

                # Save frames as a GIF
                frames[0].save('screenrecord.gif', format='GIF', append_images=frames[1:], save_all=True, duration=100, loop=0)

                # Send screen recording to Discord
                await message.channel.send(file=discord.File('screenrecord.gif'))

                # Delete temporary screen recording file
                os.remove('screenrecord.gif')

            elif message.content.startswith('lock'):
                # Lock the system using ctypes and Windows API
                ctypes.windll.user32.LockWorkStation()
                await message.channel.send('System locked.')

            elif message.content.startswith('cmd'):
                # Execute command from cmd
                cmd_command = message.content[len('cmd')+1:]  # Remove the 'cmd ' prefix
                try:
                    cmd_output = subprocess.check_output(cmd_command, shell=True, stderr=subprocess.STDOUT, timeout=10)
                    await message.channel.send(f'```{cmd_output.decode("utf-8")}```')
                except subprocess.CalledProcessError as e:
                    await message.channel.send(f'Command failed with error: {e}')
                except subprocess.TimeoutExpired:
                    await message.channel.send('Command execution timed out.')

            elif message.content.startswith('recordvoice'):
                await self.record_voice(message)
                await message.channel.send('Recording voice...')
            elif message.content.startswith('play cancel'):
                pygame.mixer.music.stop()
                await message.channel.send('Playback canceled.')
                
                
            elif message.content.startswith('play'):
                command_parts = message.content.split(' ')
                if len(command_parts) == 2:
                    filename = command_parts[1]
                    if os.path.exists(filename):
                        self.play_media(filename)
                    else:
                        await message.channel.send('File not found.')
            elif message.content.startswith('help'):
                # Display all available commands
                response = "Available commands:\n"
                for command, description in self.commands.items():
                    response += f"{command}: {description}\n"
                await message.channel.send(response)
            await self.handle_command(message)

        logging.basicConfig(filename='discord_bot.log', level=logging.ERROR)

        try:
            client.run(self.token)
        except discord.errors.LoginFailure:
            # Log the error instead of displaying a message box
            pyautogui.alert('Token invalid: Token not Validity!')


class DiscordBotGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Discord Bot GUI")

        layout = QtWidgets.QVBoxLayout()

        # Bot Token Entry
        token_label = QtWidgets.QLabel("Bot Token:")
        self.token_entry = QtWidgets.QLineEdit()
        layout.addWidget(token_label)
        layout.addWidget(self.token_entry)

        # Start Bot Button
        self.start_button = QtWidgets.QPushButton("Start Bot")
        self.start_button.clicked.connect(self.start_bot)
        layout.addWidget(self.start_button)

        # Connection Status
        self.connection_label = QtWidgets.QLabel("Connection Status: Not Connected")
        layout.addWidget(self.connection_label)

        # Status Indicator
        self.status_indicator = QtWidgets.QLabel()
        self.status_indicator.setFixedSize(20, 20)
        self.status_indicator.setStyleSheet("background-color: red; border-radius: 10px;")
        layout.addWidget(self.status_indicator)
        self.marker = QtWidgets.QLabel()
        self.marker.setText('PowerBy:Medofile\nwww.Medofile.ir\n GitHub:Mtgama')
        layout.addWidget(self.marker)
        self.setLayout(layout)

        # Create a system tray icon
        self.tray_icon = QtWidgets.QSystemTrayIcon(QIcon("discordroboticon.jpg"), self)
        self.tray_icon.setToolTip("Discord Bot")
        self.tray_icon.activated.connect(self.tray_icon_clicked)
        self.tray_icon.setContextMenu(self.create_tray_menu())
        self.tray_icon.show()
        try:
            # Load token automatically
            self.token_entry.setText(self.load_token())
        except:
            QtWidgets.QMessageBox(self,'token invalid','Token not valid!')

    def load_token(self):
        token = ''
        if os.path.exists('token.txt'):
            with open('token.txt', 'r') as file:
                token = file.read().strip()
        return token

    def start_bot(self):
        token = self.token_entry.text()
        if not token:
            QtWidgets.QMessageBox.critical(self, "Error", "Please enter the bot token.")
            return

        # Set the connection status to "Connecting" when starting the bot
        self.connection_label.setText("Connection Status: Connecting...")
        self.connection_label.repaint()  # Force repaint to update the label immediately
        try:
            self.bot_thread = DiscordBotThread()
            self.bot_thread.token = token
            self.bot_thread.connection_changed.connect(self.update_connection_status)  # Connect signal
            self.bot_thread.start()
        except:
            QtWidgets.QMessageBox.critical(self, "Error", "Invalid token.")

    def update_connection_status(self, connected):
        if connected:
            self.connection_label.setText("Connection Status: Connected")
            self.status_indicator.setStyleSheet("background-color: green; border-radius: 10px;")
        else:
            self.connection_label.setText("Connection Status: Not Connected")
            self.status_indicator.setStyleSheet("background-color: red; border-radius: 10px;")

    # Override the close event to hide the window instead of closing it
    def closeEvent(self, event):
        event.ignore()  # Ignore the close event
        self.hide()  # Hide the window instead of closing it

    def tray_icon_clicked(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            # Show the window when the tray icon is clicked
            self.show()

    def create_tray_menu(self):
        menu = QtWidgets.QMenu()
        close_action = menu.addAction("Close App")
        close_action.triggered.connect(self.close_app)
        return menu

    def close_app(self):
        # Close the application
        QtWidgets.qApp.quit()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    gui = DiscordBotGUI()
    gui.show()
    sys.exit(app.exec_())
