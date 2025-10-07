import configs
from typing import cast


from stem import Signal
from stem.control import Controller
from stem.process import launch_tor_with_config

import asyncio
import shutil
from contextlib import asynccontextmanager
from typing import Optional

import aiohttp
from aiohttp_socks import ProxyConnector


class Connector:
    def __init__(self) -> None:
        self.default_port = configs.TOR_SOCKS_DEFAULT
        self.default_control_port = configs.TOR_SOCKS_DEFAULT # int
        self.control_password = configs.TOR_CONTROL_PASSWORD
        self.controller = None


    def connect(self):
        self._controller = Controller.from_port(port=str(self.default_control_port))
        
        if self.control_password :
            self._controller.authenticate(password=self.control_password)
        else:
            self._controller.authenticate()

    def newnym(self):

        if self._controller is None:
            raise RuntimeError("Controller not Connected !")
        
        self._controller.signal(Signal.NEWNYM) # avoid error everything is normal

    def get_version(self):
        return self._controller.get_version() if self._controller else None
    

class TorProcessManager:

    def __init__(self, socks_port=configs.TOR_SOCKS_DEFAULT, control_port=configs.TOR_SOCKS_CONTROL_DEFAULT, tor_binary: Optional[str]=None):
        self.socks_port = socks_port
        self.control_port = control_port
        self.tor_binary = tor_binary or shutil.which("tor")  # sys tor
        self.process = None


    def can_launch(self) -> bool:
        return self.tor_binary is not None
    
    def launch(self):

        if not self.can_launch():
            raise RuntimeError("No tor binary available to launch !")
        
        config = {
            "SocksPort": str(self.socks_port),
            "ControlPort": str(self.control_port)
        }
        tor_cmd = cast(str, self.tor_binary)
        self.process = launch_tor_with_config(config=config, take_ownership=True, tor_cmd=tor_cmd)

        return self.process
    
    def kill(self):
        if self.process:  
            self.process.kill()
            self.process = None


@asynccontextmanager
async def tor_session(socks_host=configs.SOCKS_HOST, socks_port=configs.TOR_SOCKS_DEFAULT, launch_tor_if_missing=False,
                      control_port=configs.TOR_SOCKS_CONTROL_DEFAULT, control_password=configs.TOR_CONTROL_PASSWORD):

    """
    Async context that yields an aiohttp.ClientSession routed via Tor.
    If launch_tor_if_missing==True, will attempt to launch tor process (requires tor binary).
    """

    connector = ProxyConnector.from_url(f"socks5h://{socks_host}:{socks_port}")
    session = aiohttp.ClientSession(connector=connector, trust_env=False)

    tor_proc_mgr = None
    controller = None

    try:
        # try to connect to control port (non-blocking attempt)
        try:
            controller = Controller.from_port(port=str(control_port))
            controller.authenticate(password=control_password) if control_password else controller.authenticate()
        except Exception:
            controller = None

        # Optionally start tor if no controller and launch requested
        if controller is None and launch_tor_if_missing:
            tor_proc_mgr = TorProcessManager(socks_port=socks_port, control_port=control_port)
            if tor_proc_mgr.can_launch():
                tor_proc_mgr.launch()
                # wait a bit for tor to boot
                await asyncio.sleep(4)
                controller = Controller.from_port(port=str(control_port))
                controller.authenticate(password=control_password) if control_password else controller.authenticate()

        yield session, controller

    finally:
        await session.close()
        if tor_proc_mgr:
            tor_proc_mgr.kill()