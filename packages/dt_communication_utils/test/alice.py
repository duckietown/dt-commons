import time
import logging

from dt_communication_utils import DTCommunicationGroup

agent_name = 'Alice'

pub_group = DTCommunicationGroup('a', loglevel=logging.DEBUG, port=7667)

# sub_group = DTCommunicationGroup('b', loglevel=logging.DEBUG)
#
#
# def _cb(_, msg):
#     print(f'{agent_name} received: ' + str(msg))
#
# sub = sub_group.Subscriber('/topic', _cb)

pub = pub_group.Publisher('/topic')

time.sleep(1)
print('Publishing...')
pub.publish(bytes(f"Hello from {agent_name}!", 'utf-8'))

print('Exiting...')
pub_group.shutdown()
