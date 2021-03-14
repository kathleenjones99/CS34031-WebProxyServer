from datetime import datetime

class Request:

    def __init__(self, request_data):
        self.request_data = request_data
        self.cached = False
        self.blocked = False
        self.https = False
        self.start_date = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")     # date & time accessed
        self.start_timestamp = datetime.now().microsecond                   # start timer when object created
        self.end_timestamp = self.start_timestamp                           # initialise endtime for timer
        self.duration = 0

        # basic parsing of request
        first_line = str(request_data).split("\n")[0]
        command = first_line.split(" ")[0]

        if "CONNECT" in command.upper():
            self.https = True

        url = first_line.split(" ")[1]
        self.host = self.extract_host(url)

    def extract_host(self, url):
        ## further parsing of request
        ## use data in request line to determine if http or https & find host
        temp = self.request_data.decode().split("\r\n")
        host_i = 0
        i = 0
        for string in temp:
            if string[: 4] == "Host":
                host_i = i
            i = i + 1
        destination_host = temp[host_i][6:]             # if http this is fine

        if self.https:                                       # if https we need to chop port number from the end
            port_position = destination_host.find(":")  # trim port number to extract host url
            if port_position != -1:
                host_position = port_position
                temp = destination_host[:host_position]
                destination_host = temp

        return destination_host

    def end_request(self):
        self.end_timestamp = datetime.now().microsecond
        self.duration = abs(self.end_timestamp - self.start_timestamp)

