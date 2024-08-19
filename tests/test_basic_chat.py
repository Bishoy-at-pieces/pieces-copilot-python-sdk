import pytest
from unittest.mock import Mock, patch, call
from typing import Literal, Optional, List, TYPE_CHECKING
from abc import ABC, abstractmethod
from pieces_os_client import (
    ApiClient,
    Application,
    Configuration,
    ConversationApi,
    ConversationMessageApi,
    ConversationMessagesApi,
    ConversationsApi,
    QGPTApi,
    UserApi,
    FormatApi,
    ConnectorApi,
    SeededConnectorConnection,
    SeededTrackedApplication,
    AssetApi,
    AssetsApi,
    FragmentMetadata,
    ModelsApi,
    AnnotationApi
)
from typing import Optional,Dict
import platform
import atexit
import sys
import importlib.util
import queue
from typing import Dict, List, Union, Callable, TYPE_CHECKING
from pieces_os_client import Conversation, StreamedIdentifiers, Asset
from abc import ABC, abstractmethod
import threading
from pieces_copilot_sdk.copilot import Copilot
from pieces_copilot_sdk.basic_identifier.asset import BasicAsset
from pieces_copilot_sdk.streamed_identifiers.assets_snapshot import AssetSnapshot
from websockets import *
from pieces_copilot_sdk.client import PiecesClient
from pieces_copilot_sdk.basic_identifier.basic import Basic
from pieces_copilot_sdk.basic_identifier.message import BasicMessage
from pieces_copilot_sdk.basic_identifier.chat import BasicChat
from pieces_copilot_sdk.streamed_identifiers._streamed_identifiers import StreamedIdentifiersCache
from pieces_copilot_sdk.streamed_identifiers.conversations_snapshot import ConversationsSnapshot

class TestBasicChat:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_conversation = Mock(id="test_id", messages=Mock(indices={}), annotations=None)
        self.mock_conversation.name = "Test Conversation"
        ConversationsSnapshot.identifiers_snapshot = {"test_id": self.mock_conversation}
        ConversationsSnapshot.pieces_client = Mock()

    def test_init_valid_id(self):
        chat = BasicChat("test_id")
        assert chat.id == "test_id"
        assert chat.name == "Test Conversation"

    def test_init_invalid_id(self):
        with pytest.raises(ValueError, match="Conversation not found"):
            BasicChat("invalid_id")

    def test_name_property(self):
        chat = BasicChat("test_id")
        assert chat.name == "Test Conversation"

        chat.name = "New Name"
        assert chat.name == "New Name"
        ConversationsSnapshot.pieces_client.conversation_api.conversation_update.assert_called_once()

    def test_name_property_default(self):
        self.mock_conversation.name = None
        chat = BasicChat("test_id")
        assert chat.name == "New Conversation"

    @patch.object(BasicMessage, '__init__', return_value=None)
    @patch.object(BasicChat, '_get_message')
    def test_messages(self, mock_get_message, mock_basic_message_init):
        ConversationsSnapshot.identifiers_snapshot["test_id"].messages.indices = {
            "msg1": 0,
            "msg2": 1,
            "msg3": -1  # Deleted message
        }

        # Mock the _get_message method to return a Mock object
        mock_get_message.side_effect = lambda message_id: Mock(id=message_id)

        chat = BasicChat("test_id")
        messages = chat.messages()

        assert len(messages) == 2
        assert all(isinstance(msg, BasicMessage) for msg in messages)

        # Check that BasicMessage.__init__ was called twice
        assert mock_basic_message_init.call_count == 2

        # Check that _get_message was called with the correct message IDs
        mock_get_message.assert_has_calls([
            call("msg1"),
            call("msg2")
        ], any_order=True)

        # Check that BasicMessage.__init__ was called with the results of _get_message
        for call_args in mock_basic_message_init.call_args_list:
            assert isinstance(call_args[0][0], Mock)
            assert call_args[0][0].id in ["msg1", "msg2"]

    def test_annotations_property(self):
        mock_annotations = Mock(iterable=["annotation1", "annotation2"])
        ConversationsSnapshot.identifiers_snapshot["test_id"].annotations = mock_annotations
        
        chat = BasicChat("test_id")
        assert chat.annotations == ["annotation1", "annotation2"]

    def test_annotations_property_none(self):
        ConversationsSnapshot.identifiers_snapshot["test_id"].annotations = None
        
        chat = BasicChat("test_id")
        assert chat.annotations is None
