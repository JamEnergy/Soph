import re
class Reactor:
    def __init__(self, server_opts):
        self.server_opts = server_opts
        self.server_regs = {}
        for id, o in self.server_opts.items():
            regs = o.get("reactRegs", [])
            self.server_regs[id] = [re.compile(r) for r in regs]


    async def react(self, message, client):
        try:
            lowerMsg = message.content.lower().strip()
            sid = message.server.id
            for r in self.server_regs[sid]:
                if r.match(lowerMsg):
                    for resp in self.server_opts[sid]["reactResp"]:
                        await client.add_reaction(message, resp)
                    break
        except Exception as e:
            pass
        return None