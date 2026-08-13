"""高レベル API 名前空間。

ここにあるのは「よく使う 332 分の数十本」に読みやすい名前を付けただけのもの。
定義されていないエンドポイントは ``client.raw.<name>()`` で全部叩ける。
"""

from .auth import Auth
from .chat import Chat
from .coin import Coin
from .creator import Creator
from .lorebooks import Lorebooks
from .plots import Plots
from .rooms import Rooms
from .users import Users
from .zeta_pass import ZetaPass

__all__ = [
    "Auth",
    "Chat",
    "Coin",
    "Creator",
    "Lorebooks",
    "Plots",
    "Rooms",
    "Users",
    "ZetaPass",
]
