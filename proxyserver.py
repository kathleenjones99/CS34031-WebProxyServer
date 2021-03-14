from proxy_request import Request       # custom proxy request class
import socket
import sys
import time
from threading import Thread

# relevant constants #
MAX_BACKLOG = 50                # maximum number of unaccepted connections to be in the backlog at a time, how many
BUFFER = 4096                   # maximum amount of data to be received at once, 4096 is a relatively small power of 2 (realistic value)
DEFAULT_PORT = 8080             # default client port 8080
HTTP_PORT = 80                  # server port for http connections
HTTPS_PORT = 443                # server port for https connections

# global variables #
# list for blocked URLs that can be updated dynamically
blockedURLs= ["www.facebook.com", "www.twitter.com"]
# local cache is a dict with key:value pairs. key is url, value is the response to be sent to client
cache = {}

def main():
    try:
        while True:
            ## enter control menu
            print("Hello, welcome to the proxy menu!\n")
            user_input = input("Please enter 'S' to start connection, 'B' to block/unblock URLs, or 'Q' to quit & close.\n").lower()
            if user_input == "s":
                ## user wants to connect
                while True:
                    try:
                        print("Do you wish to connect using default port 8080?\n")
                        port_yn_input = input("Enter Y or N").lower()
                        if port_yn_input == "y":
                            establish_connection(DEFAULT_PORT)
                        if port_yn_input == "n":
                            user_port = input("Please enter a port number:\n")
                            establish_connection(user_port)
                        # call connection subroutine
                    except socket.error:
                        print("Port error encountered. Please try again!")
                        pass
                    except ValueError:
                        print("Incorrect input entered. Please try again!")
            elif user_input == "b":
                ## user wants to block/unblock URLs
                while True:
                    # implement blocking sequence
                    print("URLs currently blocked: \n")
                    ## print list of currently blocked URLs
                    for i in blockedURLs:
                        print(i)
                    user_block_input = input("Enter 'B' to block a new URL or 'U' to unblock one listed above.\n"
                                             "Enter 'R' to return to the main menu.\n")
                    if user_block_input == "b":
                        url = input("Please enter the URL you wish to block:\n")
                        # call block subroutine
                        block(url)
                    elif user_block_input == "u":
                        url = input("Please enter the URL you wish to unblock:\n")
                        # call unblock subroutine
                        unblock(url)
                    elif user_block_input == "r":
                        print("Returning to main menu...\n")
                        break
                    else:
                        print("Incorrect input entered, please try again!\n")
            elif user_input == "q":
                ## user wants to quit & close
                print("Exiting ...\n")
                sys.exit()
            else:
                print("Incorrect input entered, please try again!")
    except Exception:
        pass

def establish_connection(listening_port):
    print("connect method")
    try:
        # establish TCP connection
        # AF_INET for IPv4 & SOCK_STREAM for TCP
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # bind client socket to 8080 by default, or other user defined port if this option selected in menu
        client_socket.bind(("", listening_port))
        # begin listening
        client_socket.listen(MAX_BACKLOG)
        print("Server successfully started on port", listening_port)
    except socket.error as err:
        print(err)
    except Exception:
        print("Connection Error on ", listening_port)

    # accept connection from client and spin up threads for each request
    while True:
        try:
            conn, addr = client_socket.accept()
            print("Client connection initiated...")
            thread = Thread(target = threaded_proxy, args = (conn, ))
            thread.daemon = True
            thread.start()

        except socket.error as err:
            print("Socket error in thread - ", err)
        except Exception as err:
            print("Error - ", err)

def threaded_proxy(conn):
    try:
        # create request object to represent each request that comes to proxy
        request_data = conn.recv(BUFFER)
        request = Request(request_data)

        # check if url is blocked
        if request.host in blockedURLs:
            request.blocked = True

        # check if request is cached
        if request.host in  cache:
            request.cached = True

        ## check if url is blocked
        if request.blocked:
            ## if url is blocked, log and exit
            print("Requested URL: ", url, " is blocked.")
            # determine request type for log
            if request.https:
                request_type = "https"
            else:
                request_type = "http"
            # log request
            print("Request rejected: request_type=,", request_type,"destination_host=", request.host)
            print("Exiting...")
            conn.close()        # close client connection
            sys.exit()          # exit program
        else:
            ## if url is ok, check if the request is https or not
            print("URL allowed, proceeding...")
            if request.https:
                ## forward request straight on to server as caching not possible for https
                print("https forwarding... = ", request_data)
                https_forward(conn, request)
                #log request
                print("Request fulfilled: request_type=https, destination_host=", request.host, " duration = ", request.duration)
            else:
                if request.cached:
                    ## retrieve cached version
                    print("Requested page available in local cache - request retrieved from cache.")
                    conn.sendall(cache[request.host])
                    #log request & duration for efficiency data
                    print("Request fulfilled from cache: request_type=http, destination_host=", request.host, " duration = ", request.duration)
                else:
                    ## no cached version available, forward request to port 80
                    print("Requested page not in cache - forward request to browser.")
                    http_forward(conn, request)
                    #log request  & duration for efficiency data
                    print("Request fulfilled: request_type=http, destination_host=", request.host, " duration = ", request.duration)
                    #print(request)

    except Exception as err:
        print("Other error= ", err)

def http_forward(conn, request):
    try:
        destination_port = HTTP_PORT        # http=80
        destination_host = request.host

        # create http server socket
        http_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        http_socket.connect((destination_host, destination_port))
        # forward request to server
        http_socket.sendall(request.request_data)

        # instantiate bytearray to later take response data for cache
        cache_data = bytearray()

        # http connection success - print destination_host to log
        print("[http] host: ", destination_host)

        # server responds to proxy, send response back to client
        while True:
            response = http_socket.recv(BUFFER)  # take in response from server
            if len(response)>0:
                conn.sendall(response)           # send response back to browser
                cache_data.extend(response)      # fully formatted response to be stored as cache data, ready to be retransmitted on command
            else:
                # no response, end connection
                break
        cache[request.host] = cache_data  # cache response in cache dict, url as key
        print(request.host, "  now cached")
        print("Closing connections...")
        request.end_request()       # stops request timer
        http_socket.close()         # close server socket connection
        conn.close()                # close client connection

    except Exception as err:
        print("http connection error - ", err)
        conn.close()

def https_forward(conn, request):
    try:
        # set parameters from request object
        destination_port = HTTPS_PORT
        destination_host = request.host

        # create server socket and connect
        https_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        https_socket.connect((destination_host, destination_port))
        # send https accept message to initiate
        response =  "HTTP/1.0 200 Connection Established\r\n"
        response += "proxy-agent: pyx\r\n\r\n"
        # client send
        conn.sendall(response.encode())

        #https server connection success - print destination host to log
        print("[https] host: ", destination_host)

        #for https we must continuously relay information in both directions - contain both in separate try/except blocks
        # client2server relay
        while True:
            try:
                client_data = conn.recv(BUFFER) # receive data from client
                https_socket.sendall(client_data)  # send data to server
            except socket.error:
                pass
            # server2client relay
            try:
                server_data = https_socket.recv(BUFFER) # receive data from server
                conn.sendall(server_data)                  # send data back to client (browser)
            except socket.error:
                pass

    except socket.error as err:
        print(err)
        time.sleep(2)
    except Exception:
        print("https connection error")

    https_socket.close()
    conn.close()

def block(url):
    print("Blocking: ", url)
    try:
        # add supplied url to blocked list
        blockedURLs.add(url)
        print(url, " successfully blocked. Returning to block menu.\n")
    except Exception:
        print(error)

def unblock(url):
    print("Unblocking: ", url)
    try:
        # remove supplied url from blocked list
        blockedURLs.remove(url)
        print(url, " successfully unblocked. Returning to block menu.\n")
    except ValueError:
        print("URL specified was not on blocked URL list.\nReturning to block menu\n")

if __name__ == '__main__':
    main()


