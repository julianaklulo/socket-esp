from esp import ESP

esp = ESP("ssid", "password")

class ESPSocket:
    _timeout = 10000

    def __init__(self):
        self._esp = esp
        self._connected = False

    def socket(self):
        return self

    def getaddrinfo(self, host, port):
        return [(0, 0, 0, 0, (host, port))]

    def settimeout(self, timeout):
        self._timeout = timeout

    def connect(self, host, port):
        self._connected = self._esp.open_tcp_connection(host, port)
        return self._connected

    def send(self, data):
        if self_connected:
            if self._esp.send_data(data):
                return len(data)
        return 0

    def recv(self, length):
        if self._connected:
            return self._esp.read_bytes(length)
        return b""

    def close(self):
        self._esp.close_tcp_connection()
        self._connected = False
