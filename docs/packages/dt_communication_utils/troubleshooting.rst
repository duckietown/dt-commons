Troubleshooting
---------------

I don't receive messages
^^^^^^^^^^^^^^^^^^^^^^^^

For UDP Multicast (UDPm) to work properly, the kernel of your Operating System has to have a route
for UDPm traffic. This means that a network interface has to be identified as the gateway for
such traffic. When no explicit route exists, the default gateway is selected.

This can result in missing messages on computers where multiple network interfaces exist.
For example, if you have a computer with two interfaces, say ``eth0`` connected to a WAN and
``eth1`` connected to a LAN, your default gateway will (most likely) be ``eth0``,
because it is the one with access to the internet.

If you create a Communication Group on such computer, the UDPm traffic will enter/leave
your computer through the interface ``eth0``. This means that any message incoming from a
device within your LAN will not be received, and similarly, no messages leaving your computer
will ever reach any device on your LAN.

This can be fixed by explicitly telling your kernel which interface should be responsible
for Duckietown UDPm traffic. You can do so by running the command,

..  code-block:: bash

    sudo route add -net 239.255.0.0 netmask 255.255.240.0 dev DEVICE

where you replace ``DEVICE`` with the network interface your LAN is connected to (e.g., ``eth1``
in the example above).

.. note::
    UDPm networks can take IP addresses from the range ``224/4``, which means any IP address
    between ``224.0.0.0`` and ``239.255.255.255``. Duckietown spans communication groups
    across the range ``239.255.0/20`` hence the route above only routes Duckietown UDPm traffic.