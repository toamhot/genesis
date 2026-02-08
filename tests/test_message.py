"""Tests for the message system."""

from genesis.core.message import Message, MessageType


def test_message_creation():
    msg = Message(sender="alice", recipient="bob", content="Hello", msg_type=MessageType.TASK)
    assert msg.sender == "alice"
    assert msg.recipient == "bob"
    assert msg.content == "Hello"
    assert msg.msg_type == MessageType.TASK
    assert msg.id  # auto-generated
    assert msg.parent_id is None


def test_message_reply():
    original = Message(sender="alice", recipient="bob", content="Question?", msg_type=MessageType.QUESTION)
    reply = original.reply(sender="bob", content="Answer!")

    assert reply.sender == "bob"
    assert reply.recipient == "alice"
    assert reply.content == "Answer!"
    assert reply.msg_type == MessageType.ANSWER
    assert reply.parent_id == original.id


def test_message_str():
    msg = Message(sender="a", recipient="b", content="test", msg_type=MessageType.STATUS)
    assert "[status]" in str(msg)
    assert "a -> b" in str(msg)
