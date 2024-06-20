import zmq

context = zmq.Context()

# Receiving socket
rx = context.socket(zmq.SUB)
rx.bind("tcp://*:5555")
rx.setsockopt_string(zmq.SUBSCRIBE, "")

# Sending socket
tx = context.socket(zmq.PUB)
tx.bind("tcp://*:5556")

zmq.proxy(rx, tx)
