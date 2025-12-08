from asyncio import get_event_loop, AbstractEventLoop
import socket
from TISControlProtocol.Protocols.udp.PacketProtocol import PacketProtocol

loop = get_event_loop()


async def setup_udp_protocol(
    sock: socket, loop: AbstractEventLoop, udp_ip, udp_port, hass
) -> tuple[socket.socket, PacketProtocol]:
    # Server mode: Listen for incoming packets on specified port
    # Remove remote_addr to allow receiving from ANY source
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: PacketProtocol(sock, udp_ip, udp_port, hass),
        local_addr=("0.0.0.0", udp_port),  # Bind to port for receiving
        allow_broadcast=True,
        reuse_port=True,  # Allow multiple processes to bind same port
    )
    return transport, protocol
