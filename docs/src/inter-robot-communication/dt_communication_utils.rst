Package ``dt_communication_utils``
==================================

The `dt_communication_utils` package provides utility classes to implement simple
communication between robots in Duckietown.
It wraps around LCM and hides all the networking details from
the user.


Groups and Subgroups
--------------------

Communication between processes within a local network happens within
**Communication Groups** and **Subgroups**.
A communication group is a logical group that processes can easily join.
Communication groups (and subgroups) are fully distributed, the only thing two entities
(e.g., processes) within the same network need to agree on in order to be able to
communicate is a group name (e.g., a string).
A group is uniquely identified by its name.

Subgroups work the same way, they exist only to provide an easy way of breaking a group
into smaller subgroups. Think about them as breakout rooms for robots.
For the sake of ease, the following sections will refer to communication groups,
but everything we say about groups also apply to subgroups.


Messages
--------

Messages exchanged over communication groups are ROS messages.
This makes it easier for the user to integrate multi-robot communication with intra-robot
communication.
A process can easily receive a message over ROS and forward it (as is) to a communication
group. Isn't it beautiful?


Get Started
-----------

Let's get started.
The first thing to do is initialize a communication group.

Just like it happens with humans, for communication to be effective, your processes need
to agree on where to talk (e.g., a group name) and what language to use (e.g., a message type).


Create a Group
^^^^^^^^^^^^^^

You can create a communication group by using the class
:py:class:`dt_communication_utils.DTCommunicationGroup`.

.. code-block:: python

    from dt_communication_utils import DTCommunicationGroup
    from std_msgs.msg import String

    group = DTCommunicationGroup('my_group', String)


Create a Publisher
^^^^^^^^^^^^^^^^^^

Messages can be published to a group using a `Publisher` object.
Use the method `publish()` to publish a new message.

.. code-block:: python

    publisher = group.Publisher()
    message = String(data="Hello!")
    publisher.publish(message)

Easy, right?


Create a Subscriber
^^^^^^^^^^^^^^^^^^^

Now that we know how to publish a message, let's see what we need to do
to receive a message from the same group.

.. code-block:: python

    def callback(message, header):
        print(message)

    subscriber = group.Subscriber(callback)


..  include:: troubleshooting.rst


Python Classes
--------------

DTCommunicationGroup
^^^^^^^^^^^^^^^^^^^^

.. autoclass:: dt_communication_utils.DTCommunicationGroup
    :members:
    :inherited-members:


DTCommunicationPublisher
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: dt_communication_utils.DTCommunicationPublisher
    :members:
    :inherited-members:


DTCommunicationSubscriber
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: dt_communication_utils.DTCommunicationSubscriber
    :members:
    :inherited-members:


DTCommunicationMessageHeader
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: dt_communication_utils.DTCommunicationMessageHeader
    :members:
    :inherited-members:


DTRawCommunicationGroup
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: dt_communication_utils.DTRawCommunicationGroup
    :members:
    :inherited-members:
