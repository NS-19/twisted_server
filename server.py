from twisted.internet import reactor, protocol
from twisted.internet.protocol import ServerFactory as ServFactory, connectionDone
from twisted.internet.endpoints import TCP4ServerEndpoint
import json

class Server(protocol.Protocol):
    def __init__(self, clients: dict, my_id):
        """
        Initialize the Server instance.

        :param clients: A dictionary of connected clients, where the key is the client ID and the value is the client instance
        :type clients: dict
        :param my_id: The ID of the client connected to this instance of the Server
        :type my_id: int
        """
        self.my_id = my_id
        self.clients = clients
        self.another_client = None

    def connectionMade(self):
        """
        Called when a client connects to the server.
        Adds the client instance to the dictionary of connected clients.
        """
        self.clients[self.my_id] = self

    
    def __encode_json(**kwargs):
        """
        Encode keyword arguments as a JSON string.

        :param kwargs: The keyword arguments to encode
        :type kwargs: dict
        :return: The encoded JSON string
        :rtype: str
        """
        return json.dumps(kwargs)

    def send_message(self, **kwargs):
        """
        Send a message to the client.

        :param kwargs: The keyword arguments to send as the message, including the "where" keyword argument to specify the client to send to
        :type kwargs: dict
        """
        if kwargs.get('where'):
            where = kwargs['where']
            del kwargs['where']
            where.transport.write(self.__encode_json(**kwargs).encode("utf-8"))
        else:
            self.transport.write(self.__encode_json(**kwargs).encode("utf-8"))

    def dataReceived(self, data):
        """
        Called when data is received from the client.
        Parses the data as a JSON string and processes it accordingly.

        :param data: The data received from the client
        :type data: bytes
        """
        try:
            data = json.loads(data.decode("utf-8"))
            print("Received message from client: ", data["value"])
        except UnicodeDecodeError:
            self.send_message(value="The given message can't be decoded, use utf-8", type='error')
            return
        except json.JSONDecodeError:
            self.send_message(value="The given message can't be decoded, use json", type='error')
            return

        if not data.get('type') or not data.get('value'):
            self.send_message(value=f"Error in data", type='error')
            return

        if data['type'] == "user_choose":
            try:
                another_client = int(data['value'])
                if another_client in self.clients.keys():
                    self.another_client = another_client
                else:
                    raise KeyError

            except ValueError:
                self.send_message(value="Error: id ; Write another ID", type='error')
            except KeyError:
                self.send_message(value="Error : No client ", type='error')
            else:
                self.send_message(value=f"Talk to {self.another_client}", type='user_chosen')

        elif data['type'] == "new_message":
            if not self.another_client:
                self.send_message(value=f"No client available", type='error')

            try:
                self.send_message(value=data['value'], where=self.clients[self.another_client], type='new_message')
            except KeyError:
                self.send_message(value="Client Error : Try a new Client", type='error')
                self.another_client = None

    def connectionLost(self, reason=connectionDone):
        """
        Called when the connection with the client is lost
        """
        self.disconnect()
 
    def disconnect(self):
        del self.clients[self.my_id]


class ServerFactory(ServFactory):
    """
    Factory for creating server instances
    """
    def __init__(self):
        self.clients = {}  # dictionary to store connected clients
        self.last_id = 0  # integer to assign unique IDs to clients

    def buildProtocol(self, addr):
        """
        Build a new instance of the Server class for each client connection
        :param addr: address information of the client
        :return: Server instance
        """
        self.last_id += 1  # assign a new unique ID to the client
        return Server(self.clients, self.last_id)


if __name__ == '__main__':
    # Create an instance of TCP4ServerEndpoint that listens on port 12345
    endpoint = TCP4ServerEndpoint(reactor, 12345)

    # Set the endpoint to use the ServerFactory to create new instances of the Server class
    endpoint.listen(ServerFactory())

    # Start the reactor event loop
    reactor.run()
