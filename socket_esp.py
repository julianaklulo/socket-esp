import machine
import utime
import json


class ESP():
    def __init__(self):
        self._uart = machine.UART(0, baudrate=115200, rxbuf=10000)
        self._tcp_open = False

    def read_line(self, ignore_empty=True, timeout=2000):
        """Read one line of data from ESP module."""
        response = b""
        try:
            limit = utime.ticks_ms() + timeout
            while utime.ticks_ms() < limit:
                if self._uart.any():
                    received = self._uart.read(1)
                    if received == b'\r':  # ignore \r
                        continue
                    if received == b'\n':
                        if response != b"" or not ignore_empty:
                            break
                    else:
                        response = response + received
            print(f"LINE: {response.decode()}")
            return response.decode()
        except Exception as e:
            return ""

    def send_command(self, command, timeout=2000):
        """
        Send an AT command to ESP module.
        Returns the reponse for the command, ignoring the echo."""
        self._uart.write(f"{command}\r\n")
        print(f"COMMAND: {command}")
        self.read_line(timeout=timeout) # echo
        return self.read_line(timeout=timeout)

    def check_ESP(self):
        """Test communication with ESP module."""
        return self.send_command("AT") == "OK"

    def connect_to_wifi(self, ssid, password):
        """Connect to WiFi using SSID and password provided."""
        if not self.send_command("AT+CWMODE=1") == "OK":
            print("Failed to configure Station mode")
            return False

        if not self.send_command(f'AT+CWJAP="{ssid}","{password}"', timeout=10000) == "WIFI DISCONNECT":
            print("Unexpected response")
            return False

        if not self.read_line(timeout=10000) == "WIFI CONNECTED":
            print("Error connecting to AP")
            return False

        if not self.read_line(timeout=10000) == "WIFI GOT IP":
            print("Error getting an IP")
            return False

        return self.read_line() == "OK"

    def create_tcp_connection(self, host, port=80):
        """Create a TCP connection to a host and port."""
        if self.send_command(f'AT+CIPSTART="TCP","{host}",{port}', timeout=10000) == "CONNECT":
            if self.read_line() == "OK":
                return True
        print("Error creating TCP connection")
        return False
        
    def open_tcp_connection(self, host, port=80):
        """
        Open a TCP connection to a host and port.
        If a connection is already open, it will be closed first.
        """
        if self._tcp_open:
            self.close_tcp_connection()
        self._tcp_open = self.create_tcp_connection(host, port)
        if not self._tcp_open:
            print("Error opening TCP connection")
        return self._tcp_open            

    def close_tcp_connection(self):
        """Close the TCP connection."""
        if self._tcp_open:
            if self.send_command("AT+CIPCLOSE", timeout=10000) == "CLOSED":
                if self.read_line() == "OK":
                    self._tcp_open = False
                    return True
                print("Error closing TCP connection")
                return False
        return False
        
    def send_data(self, data):
        """Send data over the TCP connection."""
        if self.send_command(f'AT+CIPSEND={len(data)}', timeout=10000) == "OK":
            self._uart.write(data)
            while True:
                response = self.read_line(timeout=10000)
                if response == "SEND OK":
                    return True
                if response == "SEND FAIL":
                    break
                if response == "ERROR":
                    break
            print("Error sending data")
            return False

    def make_http_request(self, host, path, port=80, return_header=False, parse_json=False):
        """Make an HTTP request to a host and path."""
        if not self.open_tcp_connection(host, port):
            return False
    
        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\n\r\n"
        
        if self.send_data(request):
            response = self.read_http_response(return_header=return_header, parse_json=parse_json)
            self.close_tcp_connection()
            return response
        return False

    def read_http_response(self, timeout=10000, return_header=False, parse_json=False):
        """
        Read an HTTP response and returns the header and body.
        If `return_header` is True, the header will be returned as a string.
        If `json` is True, the body will be returned as a JSON object.
        """
        self.read_line(ignore_empty=False, timeout=timeout)
        
        header = []
        while True:
            line = self.read_line(ignore_empty=False, timeout=timeout)
            if line == "":
                break
            header.append(line)
        header = " ".join(header)
    
        body = []
        while True:
            line = self.read_line(ignore_empty=False, timeout=500)
            body.append(line.strip())
            if line == "":
                break
        body = " ".join(body)

        if parse_json:
            body = json.loads(body)
        
        response = {"body": body}
        
        if return_header:
            response["header"] = header

        return response

