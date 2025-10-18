import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.notifier import Notifier


class TestNotifier:
    """Тесты для Notifier - управление уведомлениями."""

    @pytest.fixture
    def mock_bot(self):
        """Фикстура для создания мок-бота."""
        bot = AsyncMock()
        bot.send_message = AsyncMock()
        return bot

    @pytest.fixture
    def mock_settings(self):
        """Фикстура для создания мок-настроек."""
        settings = MagicMock()
        settings.ADMIN_CHAT_ID = "123456"
        settings.logger = MagicMock()
        return settings

    @pytest.fixture
    def notifier(self, mock_bot, mock_settings):
        """Фикстура для создания Notifier."""
        notifier = Notifier(mock_bot)
        notifier._settings = mock_settings
        notifier._logger = mock_settings.logger
        return notifier

    @pytest.mark.asyncio
    async def test_send_message_success(self, notifier, mock_bot):
        """Тест успешной отправки сообщения."""
        chat_id = 123456
        text = "Тестовое сообщение"
        mock_message = MagicMock()
        mock_bot.send_message.return_value = mock_message
        
        result = await notifier.send_message(chat_id, text)
        
        mock_bot.send_message.assert_called_once_with(chat_id=chat_id, text=text)
        assert result == mock_message

    @pytest.mark.asyncio
    async def test_send_message_bot_none(self, notifier):
        """Тест отправки сообщения при отсутствующем боте."""
        notifier._bot = None
        chat_id = 123456
        text = "Тестовое сообщение"
        
        result = await notifier.send_message(chat_id, text)
        
        notifier._logger.error.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_send_message_telegram_error(self, notifier, mock_bot):
        """Тест обработки ошибки Telegram при отправке сообщения."""
        chat_id = 123456
        text = "Тестовое сообщение"
        mock_bot.send_message.side_effect = Exception("Telegram Error")
        
        result = await notifier.send_message(chat_id, text)
        
        mock_bot.send_message.assert_called_once_with(chat_id=chat_id, text=text)
        notifier._logger.warning.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_send_message_with_kwargs(self, notifier, mock_bot):
        """Тест отправки сообщения с дополнительными параметрами."""
        chat_id = 123456
        text = "Тестовое сообщение"
        reply_markup = MagicMock()
        parse_mode = "Markdown"
        mock_message = MagicMock()
        mock_bot.send_message.return_value = mock_message
        
        result = await notifier.send_message(
            chat_id, text, 
            reply_markup=reply_markup, 
            parse_mode=parse_mode
        )
        
        mock_bot.send_message.assert_called_once_with(
            chat_id=chat_id, 
            text=text, 
            reply_markup=reply_markup, 
            parse_mode=parse_mode
        )
        assert result == mock_message

    @pytest.mark.asyncio
    async def test_send_admin_notification_success(self, notifier, mock_bot):
        """Тест успешной отправки админ-уведомления."""
        text = "Админ-уведомление"
        mock_message = MagicMock()
        mock_message.message_id = 789
        mock_bot.send_message.return_value = mock_message
        
        result = await notifier.send_admin_notification(text)
        
        # Проверяем, что сообщение было отправлено в админский чат
        mock_bot.send_message.assert_called_once_with(
            chat_id=123456, 
            text=text
        )
        assert result == mock_message
        notifier._logger.info.assert_called()  # Проверяем, что были логи

    @pytest.mark.asyncio
    async def test_send_admin_notification_no_admin_chat_id(self, notifier, mock_bot, mock_settings):
        """Тест отправки админ-уведомления без настроенного ADMIN_CHAT_ID."""
        mock_settings.ADMIN_CHAT_ID = None
        notifier._settings = mock_settings
        text = "Админ-уведомление"
        
        result = await notifier.send_admin_notification(text)
        
        notifier._logger.error.assert_called_once()
        mock_bot.send_message.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_send_admin_notification_invalid_chat_id(self, notifier, mock_bot, mock_settings):
        """Тест отправки админ-уведомления с некорректным ADMIN_CHAT_ID."""
        mock_settings.ADMIN_CHAT_ID = "invalid_id"
        notifier._settings = mock_settings
        text = "Админ-уведомление"
        
        result = await notifier.send_admin_notification(text)
        
        notifier._logger.error.assert_called_once()
        mock_bot.send_message.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_send_admin_notification_send_message_fails(self, notifier, mock_bot):
        """Тест отправки админ-уведомления при ошибке в send_message."""
        text = "Админ-уведомление"
        mock_bot.send_message.return_value = None  # Имитируем неудачу
        
        result = await notifier.send_admin_notification(text)
        
        mock_bot.send_message.assert_called_once_with(chat_id=123456, text=text)
        notifier._logger.error.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_send_admin_notification_with_kwargs(self, notifier, mock_bot):
        """Тест отправки админ-уведомления с дополнительными параметрами."""
        text = "Админ-уведомление"
        reply_markup = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 789
        mock_bot.send_message.return_value = mock_message
        
        result = await notifier.send_admin_notification(
            text, 
            reply_markup=reply_markup
        )
        
        mock_bot.send_message.assert_called_once_with(
            chat_id=123456, 
            text=text, 
            reply_markup=reply_markup
        )
        assert result == mock_message

    def test_notifier_initialization(self, mock_bot):
        """Тест инициализации Notifier."""
        notifier = Notifier(mock_bot)
        
        assert notifier._bot == mock_bot
        assert notifier._settings is not None
        assert notifier._logger is not None

    @pytest.mark.asyncio
    async def test_send_admin_notification_with_special_characters(self, notifier, mock_bot):
        """Тест отправки админ-уведомления со специальными символами."""
        text = "Тест с кириллицей и символами: @#$%^&*()_+{}|:<>?[]\\;\",./~`"
        mock_message = MagicMock()
        mock_message.message_id = 789
        mock_bot.send_message.return_value = mock_message
        
        result = await notifier.send_admin_notification(text)
        
        mock_bot.send_message.assert_called_once_with(
            chat_id=123456, 
            text=text
        )
        assert result == mock_message

    @pytest.mark.asyncio
    async def test_send_admin_notification_empty_text(self, notifier, mock_bot):
        """Тест отправки админ-уведомления с пустым текстом."""
        text = ""
        mock_message = MagicMock()
        mock_message.message_id = 789
        mock_bot.send_message.return_value = mock_message
        
        result = await notifier.send_admin_notification(text)
        
        mock_bot.send_message.assert_called_once_with(
            chat_id=123456, 
            text=text
        )
        assert result == mock_message