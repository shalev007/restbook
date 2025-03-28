from typing import Optional
import aiohttp
from aiohttp import ClientTimeout

class AioSessionCache:
    def __init__(self):
        self.client_session: Optional[aiohttp.ClientSession] = None

    async def get_session(self, timeout: int) -> aiohttp.ClientSession:
        if self.client_session is None or self.client_session.closed:
            self.client_session = aiohttp.ClientSession(timeout=ClientTimeout(total=timeout))
        return self.client_session
    
    async def close(self):
        if self.client_session:
            await self.client_session.close()
            self.client_session = None
