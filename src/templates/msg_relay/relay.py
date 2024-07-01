import logging
import signal
import sys

import zmq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - Relay - %(message)s')

context = zmq.Context()

frontend = context.socket(zmq.SUB)
frontend.bind("tcp://*:5555")
frontend.setsockopt_string(zmq.SUBSCRIBE, "")

backend = context.socket(zmq.PUB)
backend.bind("tcp://*:5556")


# Handle signals
def signal_handler(sig, _frame):
    """Handle shutdown signal events from the operating system."""
    logging.info('Interrupt signal received: {} ({})'.format(sig, signal.Signals(sig).name))
    logging.info('Stopping')
    shutdown()
    sys.exit(0)


def shutdown():
    """Cleanly shutdown the relay server."""
    frontend.close()
    backend.close()
    context.term()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    logging.info("Starting")

    while True:
        try:
            message = frontend.recv_string()
            logging.info(f"Message: {message}")
            backend.send_string(message)
        except zmq.ZMQError as e:
            logging.error(f"ZMQError: {e}")
            break

except Exception as e:
    logging.error(f"Interrupted: {e}")
finally:
    shutdown()
