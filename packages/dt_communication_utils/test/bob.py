import time
import logging

from dt_communication_utils import DTCommunicationGroup

agent_name = 'Bob'

# pub_group = DTCommunicationGroup('b', loglevel=logging.DEBUG)

sub_group = DTCommunicationGroup('a', loglevel=logging.DEBUG)


def _cb(_, msg):
    print(f'{agent_name} received: ' + str(msg))


# pub = pub_group.Publisher('/topic')

print('Subscribing...')
sub = sub_group.Subscriber('/topic', _cb)

# time.sleep(1)
# print('Publishing...')
# pub.publish(bytes(f"Hello from {agent_name}!", 'utf-8'))

time.sleep(1)

print('Exiting...')
sub_group.shutdown()
