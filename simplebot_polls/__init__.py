import os
import time

import simplebot
from deltachat import Chat, Contact, Message
from pkg_resources import DistributionNotFound, get_distribution
from simplebot import DeltaBot
from simplebot.bot import Replies
from sqlalchemy.exc import NoResultFound

from .orm import Option, Poll, Vote, init, session_scope
from .templates import template

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0.dev0-unknown"
BARS = ["🟩", "🟥", "🟦", "🟪", "🟧", "🟨", "🟫", "⬛"]


@simplebot.hookimpl
def deltabot_start(bot: DeltaBot) -> None:
    path = os.path.join(os.path.dirname(bot.account.db_path), __name__)
    if not os.path.exists(path):
        os.makedirs(path)
    path = os.path.join(path, "sqlite.db")
    init(f"sqlite:///{path}")


@simplebot.command
def poll_new(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Create a new public poll.

    Example:
    /poll_new Do you like polls?
    yes
    no
    maybe
    """
    lines = []
    for ln in payload.split("\n"):
        ln = ln.strip()
        if ln:
            lines.append(ln)

    if len(lines) < 3:
        replies.add(text="❌ Invalid poll, at least two options needed")
        return

    question = lines.pop(0)

    poll = Poll(addr=message.get_sender_contact().addr, question=question)
    for i, opt in enumerate(lines, 1):
        poll.options.append(Option(id=i, text=opt))
    with session_scope() as session:
        session.add(poll)
        session.flush()
        text, html = _format_poll(bot, poll)
    replies.add(text=text, html=html)


@simplebot.command
def poll_get(bot: DeltaBot, args: str, message: Message, replies: Replies) -> None:
    """Get poll with given id."""
    if args:
        try:
            with session_scope() as session:
                text, html = _format_poll(
                    bot, session.query(Poll).filter_by(id=int(args[0])).one()
                )
            replies.add(text=text, html=html)
        except NoResultFound:
            replies.add(text="❌ Invalid poll", quote=message)
    else:
        replies.add(text="❌ Invalid poll", quote=message)


@simplebot.command
def poll_status(bot: DeltaBot, args: str, message: Message, replies: Replies) -> None:
    """Get poll status."""
    addr = message.get_sender_contact().addr
    if args:
        try:
            with session_scope() as session:
                poll = session.query(Poll).filter_by(id=int(args[0])).one()
                is_admin = addr == poll.addr
                voted = is_admin or addr in [v.addr for v in poll.votes]
                if voted:
                    text, html = _format_poll(bot, poll, voted=True, is_admin=is_admin)
                else:
                    text = "❌ You can't see poll status until you vote"
                    html = None
            replies.add(text=text, html=html, chat=message.get_sender_chat())
        except NoResultFound:
            replies.add(
                text="❌ Invalid poll", quote=message, chat=message.get_sender_chat()
            )
    else:
        replies.add(
            text="❌ Invalid poll", quote=message, chat=message.get_sender_chat()
        )


@simplebot.command
def poll_settings(args: str, message: Message, replies: Replies) -> None:
    """Get poll's advanced settings."""
    if args:
        try:
            with session_scope() as session:
                poll = (
                    session.query(Poll)
                    .filter_by(id=int(args[0]), addr=message.get_sender_contact().addr)
                    .one()
                )
                text = "📊 /poll_get_{0}\n{1}\n\n🛑 /poll_end_{0}".format(
                    poll.id, poll.question
                )
            replies.add(text=text, chat=message.get_sender_chat())
        except NoResultFound:
            replies.add(
                text="❌ Invalid poll", quote=message, chat=message.get_sender_chat()
            )
    else:
        replies.add(
            text="❌ Invalid poll", quote=message, chat=message.get_sender_chat()
        )


@simplebot.command
def poll_list(message: Message, replies: Replies) -> None:
    """Show your public polls."""
    with session_scope() as session:
        text = ""
        for poll in (
            session.query(Poll).filter_by(addr=message.get_sender_contact().addr).all()
        ):
            if len(poll.question) > 100:
                q = poll.question[:100] + "..."
            else:
                q = poll.question
            text += "📊 /poll_get_{} {}\n\n".format(poll.id, q)
    replies.add(text=text or "❌ Empty list", chat=message.get_sender_chat())


@simplebot.command
def poll_end(bot: DeltaBot, args: str, message: Message, replies: Replies) -> None:
    """Close the poll with the given id."""
    if args:
        addr = message.get_sender_contact().addr
        try:
            with session_scope() as session:
                poll = session.query(Poll).filter_by(id=int(args[0]), addr=addr).one()
                text, html = _format_poll(bot, poll, closed=True)
                addresses = set(vote.addr for vote in poll.votes)
                session.delete(poll)
            addresses.add(addr)
            for addr in addresses:
                contact = bot.get_contact(addr)
                if not contact.is_blocked():
                    replies.add(text=text, html=html, chat=bot.get_chat(contact))
        except NoResultFound:
            replies.add(
                text="❌ Invalid poll", quote=message, chat=message.get_sender_chat()
            )
    else:
        replies.add(
            text="❌ Invalid poll", quote=message, chat=message.get_sender_chat()
        )


@simplebot.command
def vote(bot: DeltaBot, args: str, message: Message, replies: Replies) -> None:
    """Vote in polls."""
    if len(args) == 2:
        option_id = int(args[1])
        addr = message.get_sender_contact().addr
        try:
            with session_scope() as session:
                poll = session.query(Poll).filter_by(id=int(args[0])).one()
                if addr in [v.addr for v in poll.votes]:
                    text, html = "❌ You already voted", None
                elif option_id not in [o.id for o in poll.options]:
                    text, html = "❌ Invalid option number", None
                else:
                    poll.votes.append(Vote(addr=addr, value=option_id))
                    is_admin = addr == poll.addr
                    text, html = _format_poll(bot, poll, voted=True, is_admin=is_admin)
            replies.add(text=text, html=html, chat=message.get_sender_chat())
        except NoResultFound:
            replies.add(
                text="❌ Invalid poll", quote=message, chat=message.get_sender_chat()
            )
    else:
        replies.add(
            text="❌ Invalid poll", quote=message, chat=message.get_sender_chat()
        )


def _format_poll(
    bot: DeltaBot,
    poll,
    voted: bool = False,
    closed: bool = False,
    is_admin: bool = False,
) -> tuple:
    if closed:
        text = "📊 POLL RESULTS - {}".format(poll.question)
    else:
        text = "📊 POLL - {}".format(poll.question)
    vcount = len(poll.votes)

    html = template.render(
        poll=poll,
        bot_addr=bot.self_contact.addr,
        closed=closed,
        voted=voted,
        is_admin=is_admin,
        vcount=vcount,
        percent=lambda opt: vcount
        and len([v for v in poll.votes if v.value == opt.id]) / vcount,
        BARS=BARS,
    )
    return text, html
