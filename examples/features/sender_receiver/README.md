# Sender-Receiver Example

This project focuses on sender-receiver communication between two atomic SWCs.

It highlights:

- a sender-receiver interface with one data element
- a publisher SWC that writes the value on a timing event
- a consumer SWC that reads the same signal with explicit, implicit, and queued receiver semantics
- a simple system composition that wires the sender to all three receiver ports

Entry point: `examples/features/sender_receiver/autosar.project.yaml`
