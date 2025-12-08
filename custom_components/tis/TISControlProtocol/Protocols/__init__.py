from asyncio import get_event_loop, AbstractEventLoop
import socket
from TISControlProtocol.Protocols.udp.PacketProtocol import PacketProtocol

loop = get_event_loop()


async def setup_udp_protocol(
    sock: socket, loop: AbstractEventLoop, udp_ip, udp_port, hass
) -> tuple[socket.socket, PacketProtocol]:
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: PacketProtocol(sock, udp_ip, udp_port, hass),
        remote_addr=(udp_ip, udp_port),
        # Don't bind to specific port - let OS assign random port for sending
        # local_addr=("0.0.0.0", udp_port),  # This was causing "Address in use"
        allow_broadcast=True,
        reuse_port=False,  # Changed from True - we don't need to share port
    )
    return transport, protocol
