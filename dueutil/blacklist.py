from typing import Set
from . import dbconn

class BlacklistedUser:
    """
    A class to handle the blacklisted users

    Attributes:
        id (int): The user's ID
        reason (str): The reason for the blacklist
    """
    def __init__(self, id: int, reason: str):
        self.id = id
        self.reason = reason

    def __str__(self):
        return f"{self.id} - {self.reason}"

    def __repr__(self):
        return f"{self.id} - {self.reason}"
    
    def __hash__(self) -> int:
        return hash(self.id)

blacklist: Set[BlacklistedUser] = set()

def add(id: int, reason: str) -> None:
    """
    Add a user to the blacklist
    """
    dbconn.blacklist_member(id, reason)
    blacklist.add(BlacklistedUser(id, reason))


def remove(id: int) -> None:
    """
    Remove a user from the blacklist
    """
    dbconn.unblacklist_member(id)
    blacklist.remove(find(id))


def find(id: int) -> BlacklistedUser or None:
    """
    Find a user in the blacklist
    """
    for user in blacklist:
        if user.id == id:
            return user
    return None


def exists(id: int) -> bool:
    """
    Find a user in the blacklist
    """
    for user in blacklist:
        if user.id == id:
            return True
    return False


def __load() -> None:
    """
    Load the blacklist from the database
    """
    for cursor in dbconn.get_blacklist():
        add(cursor["_id"], cursor["reason"])


__load()