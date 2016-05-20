from websocket_server import WebsocketServer
from influxdb import InfluxDBClient
from time import sleep

import Pyro4

influx_client = InfluxDBClient('localhost', 8086, 'root', 'root', 'example')

api_server = Pyro4.Proxy("PYRONAME:apiserver")

batch_number = 0

def send_messages(client, server):

	global batch_number

	session_id = api_server.get_session_id()
	
	if session_id is not None:

		query_string = """ SELECT value FROM "error_rate" WHERE "session_id" = '{session_id}' AND time >= now() - 1s AND time <= now() """.format(session_id=session_id)

		result = influx_client.query(query_string)

		if "counter" not in client:
			batch_number = 0

		for items in result:
			for item in items:
				server.send_message_to_all("Batch Number => " + str(batch_number))
				server.send_message_to_all("Error Rate => " + str(item['value']))
				batch_number += 1
				sleep(0.01)

	else:
		server.send_message_to_all("Session expired..!")

def receive_messages(client, server, message):
	client['counter'] = message
	send_messages(client, server)

server = WebsocketServer(8080, host='0.0.0.0')
server.set_fn_new_client(send_messages)
server.set_fn_message_received(receive_messages)
server.run_forever()