Introduction
============

Duckietown employs ROS (Robot Operating System) as its main intra-device communication
framework. Given the dependency on a predefined (always reachable) ROS Master node, ROS
does not fit the needs of a fully-distributed multi-robot communication infrastructure.
For this reason, Duckietown employs LCM (Lightweight Communications and Marshalling).
LCM is a library that provides a fully-distributed communication framework for processes
within a local network. While ROS transports data using the TCP protocol, LCM uses UDP
Multicast.
