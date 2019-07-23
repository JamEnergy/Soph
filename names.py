import discord
from typing import *
import os
import json


class NameManagerBundle(object):
    """
        I adore Penny
        because she's adorable
        and cute and fun
        and knows how to talk about pretty much anything I give a shit about
        from programming to linguistics to anime to games
    """

    def __init__(self, client:discord.Client, init_all=False):
        self._client = client  # type:discord.Client
        self._mgrs = {}  # type:Dict[str, "NameManager"]

    def get(self, server:discord.Server):
        if server.id not in self._mgrs:
            self._mgrs[server.id] = NameManager(self._client, server)

        return self._mgrs[server.id]


class NameManager(object):
    """
        Manages names for a single server
    """
    def __init__(self, client:discord.Client, server:discord.Server):
        self._aliases = {}
        self._uid_to_name = {}  # type:Dict[Str,Str] uid -> desired name
        self._name_to_uid = {}  # type:Dict[Str,Str] name -> uid
        self._client = client  # type:discord.Client
        self._server = server  # type:discord.Server
        self._alias_path = os.path.join("data", self._server.id, "aliases")

        self._name_to_uid = self.load_aliases()

        for member in server.members:  # type:discord.Member
            self._uid_to_name[member.id] = member.display_name
            self._name_to_uid[member.display_name] = member.id
            self._name_to_uid[member.name] = member.id

    def set_alias(self, uid, new_alias):
        aliases = self.load_aliases()
        aliases[new_alias] = uid
        with open(self._alias_path, "w") as of:
            json.dump(aliases, of, indent=4)

    def load_aliases(self):
        """
        file of name->uid
        :return:
        """

        try:
            with open(self._alias_path) as inf:
                return json.load(inf)
        except IOError:
            return {}

    #def get_name(self, uid):
    #    return self._uid_to_name.get(uid, "?")

    async def get_name(self, uid):
        if uid in self._uid_to_name:
            return self._uid_to_name[uid]
        try:
            info = await self._client.get_user_info(uid)
            if info:
                name = getattr(info, "display_name", None) or getattr(info, "name", "[unknown]")
                self._uid_to_name[uid] = name
                self._name_to_uid[name] = uid
                return name
        except:
            pass  # probably wasn't a user

        return None

