import numpy as np
import sys

from websocket_server import WebsocketServer
from scipy.io.wavfile import write
from pydub.playback import play
from pydub import AudioSegment
from IPython import embed

from data_iterators.audio_server_2 import AudioServer2

audio_server = AudioServer2({})

def send_messages(client, server):
	server.send_message_to_all("Ready to receive messages...")

def receive_messages(client, server, message):
	print "Message Received!"
	audio_as_array = np.frombuffer(message, 'f4')
	spectrum = audio_server.build_spect_frames(audio_as_array)
	#send_messages(client, server)

def play_audio(signal):
	print "Playing audio..."
	audio_segment = AudioSegment(
    signal.tobytes(), 
    frame_rate=44100,
    sample_width=4, 
    channels=1
	)
	play(audio_segment)

server = WebsocketServer(8087, host='0.0.0.0')
server.set_fn_new_client(send_messages)
server.set_fn_message_received(receive_messages)
server.run_forever()