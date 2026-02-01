import os
import sys
import json
import ctypes
import logging
import threading
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from PIL import ImageGrab, Image, ImageDraw
import subprocess
from pathlib import Path
import time
import io

# ============================================
# НАСТРОЙКИ БОТА
# ============================================
# Вставьте сюда ваш Telegram Bot Token
BOT_TOKEN = "ВАШ_TELEGRAM_BOT_TOKEN_ЗДЕСЬ"

# ID администратора (автоматически заполнится при первом запуске)
# Можно изменить вручную если нужно
ADMIN_ID = None
# ============================================

APPDATA_PATH = os.path.join(os.getenv('APPDATA'), 'tgtoolspanel')
os.makedirs(APPDATA_PATH, exist_ok=True)

LOG_FILE = os.path.join(APPDATA_PATH, 'tgtoolspanel.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
    ]
)

class TGToolsPanelBot:
    def __init__(self):
        self.hide_console()
        
        self.token = BOT_TOKEN
        self.admin_id = ADMIN_ID
            
        if not self.token or self.token == "ВАШ_TELEGRAM_BOT_TOKEN_ЗДЕСЬ":
            logging.error("BOT_TOKEN не установлен в bot.py")
            sys.exit(1)
            
        self.admin_file = os.path.join(APPDATA_PATH, 'admin.json')
        
        if self.admin_id is None:
            self.admin_id = self.load_admin_id()
        
        self.shutdown_timer = None
        
        self.waiting_for_minutes = False
        self.waiting_for_file_path = False
        self.waiting_for_process_name = False
        self.waiting_for_clipboard_text = False
        self.waiting_for_mouse_step = False
        self.waiting_for_program_path = False
        self.waiting_for_notification_text = False
        
        self.mouse_step = 100
        
        self.bot = telebot.TeleBot(self.token)
        self.setup_handlers()
        
        self.create_keyboards()
        
        self.send_startup_notification()
        
    def hide_console(self):
        try:
            kernel32 = ctypes.WinDLL('kernel32')
            user32 = ctypes.WinDLL('user32')
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                user32.ShowWindow(hwnd, 0)
        except:
            pass
            
    def create_keyboards(self):
        # Главное меню (ReplyKeyboardMarkup)
        self.main_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        self.main_menu.add(
            KeyboardButton("📸 Быстрый скриншот"),
            KeyboardButton("⚡ Питание ПК"),
            KeyboardButton("📁 Файлы"),
            KeyboardButton("⚙️ Процессы"),
            KeyboardButton("🖱️ Взаимодействие")
        )
        
        # Меню управления питанием
        self.power_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        self.power_menu.add(KeyboardButton("⏺️ Выключить ПК"))
        self.power_menu.add(
            KeyboardButton("🔄 Перезагрузить ПК"),
            KeyboardButton("💤 Отправить в сон")
        )
        self.power_menu.add(KeyboardButton("⏰ Отложить выключение"))
        self.power_menu.add(KeyboardButton("🔙 Назад в главное меню"))
        
        # Меню файлов
        self.files_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        self.files_menu.add(
            KeyboardButton("📤 Отправить на ПК"),
            KeyboardButton("📥 Загрузить с ПК")
        )
        self.files_menu.add(KeyboardButton("🔙 Назад в главное меню"))
        
        # Меню процессов
        self.processes_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        self.processes_menu.add(KeyboardButton("✅ Запустить процесс"))
        self.processes_menu.add(KeyboardButton("❌ Завершить процесс"))
        self.processes_menu.add(KeyboardButton("🔙 Назад в главное меню"))
        
        # Меню взаимодействия
        self.interaction_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        self.interaction_menu.add(
            KeyboardButton("📋 Буфер обмена"),
            KeyboardButton("🔔 Уведомление"),
            KeyboardButton("🖱️ Управление мышью"),
            KeyboardButton("⌨️ Комбинации клавиш")
        )
        self.interaction_menu.add(KeyboardButton("🔙 Назад в главное меню"))
        
        # Меню управления мышью (джойстик)
        self.mouse_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        self.mouse_menu.add(
            KeyboardButton("🖱️ ЛКМ"),
            KeyboardButton("⬆️ ВВЕРХ"),
            KeyboardButton("🖱️ ПКМ")
        )
        self.mouse_menu.add(
            KeyboardButton("⬅️ ВЛЕВО"),
            KeyboardButton("➡️ ВПРАВО")
        )
        self.mouse_menu.add(
            KeyboardButton("🚪 ВЫХОД"),
            KeyboardButton("⬇️ ВНИЗ"),
            KeyboardButton("📏 РАЗМЕР")
        )
        
        # Меню комбинаций клавиш
        self.hotkeys_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        self.hotkeys_menu.add(
            KeyboardButton("ALT+TAB"),
            KeyboardButton("CTRL+C"),
            KeyboardButton("CTRL+V"),
            KeyboardButton("CTRL+SHIFT+ESC"),
            KeyboardButton("SHIFT+TAB")
        )
        self.hotkeys_menu.add(KeyboardButton("🔙 Назад в меню взаимодействия"))
        
    def load_admin_id(self):
        """Загружает ID администратора из файла в AppData"""
        try:
            if os.path.exists(self.admin_file):
                with open(self.admin_file, 'r') as f:
                    data = json.load(f)
                    return data.get('admin_id')
        except:
            pass
        return None
        
    def save_admin_id(self, admin_id):
        """Сохраняет ID администратора в файл в AppData"""
        try:
            with open(self.admin_file, 'w') as f:
                json.dump({'admin_id': admin_id}, f)
            
            return True
        except Exception as e:
            logging.error(f"Ошибка сохранения admin_id: {e}")
            return False
            
    def send_welcome_message(self, chat_id):
        welcome_text = """
👋🏻 *Добро пожаловать в TGtoolspanel v0.1*

⚙️ *Управляйте вашим ПК с помощью телеграм в любом месте!*

👨‍💻 *dev by kondensator666*

💻 *GitHub* https://github.com/kondensator666

        """
        self.bot.send_message(chat_id, welcome_text, parse_mode='Markdown')
        
    def setup_handlers(self):
        
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            if self.admin_id is None:
                self.admin_id = message.from_user.id
                self.save_admin_id(self.admin_id)
                
                reply = "✅ *Вы назначены администратором этого бота!*\n\n"
                self.bot.send_message(message.chat.id, reply, parse_mode='Markdown')
                self.send_welcome_message(message.chat.id)
                self.bot.send_message(message.chat.id, "👇 *Используйте меню для управления:*", 
                                     reply_markup=self.main_menu, parse_mode='Markdown')
            elif message.from_user.id == self.admin_id:
                self.bot.send_message(message.chat.id, "🔄 *Бот уже запущен и готов к работе!*", 
                                     reply_markup=self.main_menu, parse_mode='Markdown')
            else:
                self.bot.send_message(message.chat.id, "⛔ *Доступ запрещен.*\nВы не администратор.")
        
        @self.bot.message_handler(commands=['stopoff'])
        def handle_stopoff(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            if self.shutdown_timer and self.shutdown_timer.is_alive():
                self.shutdown_timer.cancel()
                self.shutdown_timer = None
                self.bot.send_message(message.chat.id, "✅ *Отложенное выключение отменено!*", 
                                     parse_mode='Markdown')
            else:
                self.bot.send_message(message.chat.id, "ℹ️ *Нет активных отложенных выключений.*", 
                                     parse_mode='Markdown')
                
        @self.bot.message_handler(func=lambda message: message.text == "📸 Быстрый скриншот")
        def handle_screenshot(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            msg = self.bot.send_message(message.chat.id, "📸 *Делаю скриншот...*", 
                                       parse_mode='Markdown')
            self.send_screenshot_with_cursor(message.chat.id, "📸 *Скриншот экрана*")
            self.bot.delete_message(message.chat.id, msg.message_id)
            
        @self.bot.message_handler(func=lambda message: message.text == "⚡ Питание ПК")
        def handle_power_menu(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, "⚡ *Управление питанием ПК:*\nВыберите действие:", 
                                 reply_markup=self.power_menu, parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "📁 Файлы")
        def handle_files_menu(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, "📁 *Работа с файлами:*\nВыберите действие:", 
                                 reply_markup=self.files_menu, parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "⚙️ Процессы")
        def handle_processes_menu(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, "⚙️ *Управление процессами:*\nВыберите действие:", 
                                 reply_markup=self.processes_menu, parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "🖱️ Взаимодействие")
        def handle_interaction_menu(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, "🖱️ *Взаимодействие с ПК:*\nВыберите действие:", 
                                 reply_markup=self.interaction_menu, parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "🔙 Назад в главное меню")
        def handle_back_to_main(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.reset_waiting_states()
            self.bot.send_message(message.chat.id, "🔙 *Возврат в главное меню:*", 
                                 reply_markup=self.main_menu, parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "🔙 Назад в меню взаимодействия")
        def handle_back_to_interaction(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.reset_waiting_states()
            self.bot.send_message(message.chat.id, "🔙 *Возврат в меню взаимодействия:*", 
                                 reply_markup=self.interaction_menu, parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "⏺️ Выключить ПК")
        def handle_shutdown(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, "⏺️ *Выключаю ПК...*", parse_mode='Markdown')
            self.shutdown_pc()
            
        @self.bot.message_handler(func=lambda message: message.text == "🔄 Перезагрузить ПК")
        def handle_reboot(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, "🔄 *Перезагружаю ПК...*", parse_mode='Markdown')
            self.reboot_pc()
            
        @self.bot.message_handler(func=lambda message: message.text == "💤 Отправить в сон")
        def handle_sleep(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, "💤 *Отправляю ПК в спящий режим...*", parse_mode='Markdown')
            self.sleep_pc()
            
        @self.bot.message_handler(func=lambda message: message.text == "⏰ Отложить выключение")
        def handle_delayed_shutdown(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.waiting_for_minutes = True
            self.bot.send_message(message.chat.id, 
                                 "⏰ *Через какое время выключить ПК?*\nВведите число в минутах:",
                                 parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "❌ Завершить процесс")
        def handle_kill_process(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.waiting_for_process_name = True
            self.bot.send_message(message.chat.id, 
                                 "❌ *Введите название процесса который хотите завершить*\nПример: `chrome.exe`",
                                 parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "✅ Запустить процесс")
        def handle_start_program(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.waiting_for_program_path = True
            self.bot.send_message(message.chat.id, 
                                 "🚀 *Введите полный путь до программы или файла который хотите запустить*\nПример: `C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe`",
                                 parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "🔔 Уведомление")
        def handle_notification(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.waiting_for_notification_text = True
            self.bot.send_message(message.chat.id, 
                                 "🔔 *Введите текст уведомления, которое появится на ПК*",
                                 parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "📋 Буфер обмена")
        def handle_clipboard(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.waiting_for_clipboard_text = True
            self.bot.send_message(message.chat.id, 
                                 "📋 *Отправьте текст, который вы хотите скопировать в буфер обмена ПК*",
                                 parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "🖱️ Управление мышью")
        def handle_mouse_control(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, 
                                 f"🖱️ *Управление мышью:*\nТекущий шаг: `{self.mouse_step}` пикселей\nИспользуйте меню:",
                                 parse_mode='Markdown',
                                 reply_markup=self.mouse_menu)
            
        @self.bot.message_handler(func=lambda message: message.text == "⌨️ Комбинации клавиш")
        def handle_hotkeys(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, 
                                 "⌨️ *Комбинации клавиш:*\nВыберите комбинацию:",
                                 parse_mode='Markdown',
                                 reply_markup=self.hotkeys_menu)
            
        @self.bot.message_handler(func=lambda message: message.text == "📤 Отправить на ПК")
        def handle_send_to_pc(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, 
                                 "📤 *Отправьте файл, который будет сохранен на рабочий стол ПК*",
                                 parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "📥 Загрузить с ПК")
        def handle_get_from_pc(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.waiting_for_file_path = True
            self.bot.send_message(message.chat.id, 
                                 "📥 *Укажите полный путь до файла, который хотите загрузить*\nПример: `C:\\Program Files\\file.txt`",
                                 parse_mode='Markdown')
            
        # Обработчики управления мышью
        @self.bot.message_handler(func=lambda message: message.text == "⬆️ ВВЕРХ")
        def handle_mouse_up(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.move_mouse(0, -self.mouse_step, message.chat.id, "⬆️ *Мышь перемещена вверх*")
            
        @self.bot.message_handler(func=lambda message: message.text == "⬇️ ВНИЗ")
        def handle_mouse_down(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.move_mouse(0, self.mouse_step, message.chat.id, "⬇️ *Мышь перемещена вниз*")
            
        @self.bot.message_handler(func=lambda message: message.text == "⬅️ ВЛЕВО")
        def handle_mouse_left(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.move_mouse(-self.mouse_step, 0, message.chat.id, "⬅️ *Мышь перемещена влево*")
            
        @self.bot.message_handler(func=lambda message: message.text == "➡️ ВПРАВО")
        def handle_mouse_right(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.move_mouse(self.mouse_step, 0, message.chat.id, "➡️ *Мышь перемещена вправо*")
            
        @self.bot.message_handler(func=lambda message: message.text == "🖱️ ЛКМ")
        def handle_left_click(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.mouse_click('left', message.chat.id, "🖱️ *Выполнен левый клик*")
            
        @self.bot.message_handler(func=lambda message: message.text == "🖱️ ПКМ")
        def handle_right_click(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.mouse_click('right', message.chat.id, "🖱️ *Выполнен правый клик*")
            
        @self.bot.message_handler(func=lambda message: message.text == "🚪 ВЫХОД")
        def handle_mouse_exit(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.bot.send_message(message.chat.id, "🚪 *Возврат в меню взаимодействия*",
                                 reply_markup=self.interaction_menu, parse_mode='Markdown')
            
        @self.bot.message_handler(func=lambda message: message.text == "📏 РАЗМЕР")
        def handle_mouse_size(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.waiting_for_mouse_step = True
            self.bot.send_message(message.chat.id, 
                                 f"📏 *Введите новый размер шага мыши в пикселях*\nТекущий шаг: `{self.mouse_step}`",
                                 parse_mode='Markdown')
            
        # Обработчики комбинаций клавиш
        @self.bot.message_handler(func=lambda message: message.text == "ALT+TAB")
        def handle_alt_tab(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.send_hotkey(['alt', 'tab'], message.chat.id, "🔀 *Выполнена комбинация ALT+TAB*")
            
        @self.bot.message_handler(func=lambda message: message.text == "CTRL+C")
        def handle_ctrl_c(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.send_hotkey(['ctrl', 'c'], message.chat.id, "📋 *Выполнена комбинация CTRL+C*")
            
        @self.bot.message_handler(func=lambda message: message.text == "CTRL+V")
        def handle_ctrl_v(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.send_hotkey(['ctrl', 'v'], message.chat.id, "📋 *Выполнена комбинация CTRL+V*")
            
        @self.bot.message_handler(func=lambda message: message.text == "CTRL+SHIFT+ESC")
        def handle_ctrl_shift_esc(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.send_hotkey(['ctrl', 'shift', 'esc'], message.chat.id, "⚙️ *Выполнена комбинация CTRL+SHIFT+ESC*")
            
        @self.bot.message_handler(func=lambda message: message.text == "SHIFT+TAB")
        def handle_shift_tab(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            self.send_hotkey(['shift', 'tab'], message.chat.id, "🔙 *Выполнена комбинация SHIFT+TAB*")
            
        @self.bot.message_handler(func=lambda message: self.waiting_for_minutes)
        def handle_minutes_input(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                self.waiting_for_minutes = False
                return
                
            try:
                minutes = int(message.text.strip())
                if minutes <= 0:
                    self.bot.send_message(message.chat.id, "❌ *Введите положительное число минут!*", 
                                         parse_mode='Markdown')
                    return
                    
                if self.shutdown_timer and self.shutdown_timer.is_alive():
                    self.shutdown_timer.cancel()
                
                seconds = minutes * 60
                self.shutdown_timer = threading.Timer(seconds, self.shutdown_pc)
                self.shutdown_timer.start()
                
                self.waiting_for_minutes = False
                
                self.bot.send_message(message.chat.id, 
                                     f"✅ *Выключение ПК запланировано через {minutes} минут!*\nДля отменя введите `/stopoff`",
                                     parse_mode='Markdown',
                                     reply_markup=self.power_menu)
                
            except ValueError:
                self.bot.send_message(message.chat.id, "❌ *Пожалуйста, введите число!*", 
                                     parse_mode='Markdown')
                
        @self.bot.message_handler(func=lambda message: self.waiting_for_file_path)
        def handle_file_path_input(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                self.waiting_for_file_path = False
                return
                
            file_path = message.text.strip()
            
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as file:
                        file_name = os.path.basename(file_path)
                        
                        if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                            self.bot.send_photo(message.chat.id, file, caption=f"📁 *{file_name}*", 
                                              parse_mode='Markdown')
                        elif file_name.lower().endswith(('.txt', '.log', '.ini', '.cfg', '.json', '.xml')):
                            self.bot.send_document(message.chat.id, file, caption=f"📄 *{file_name}*", 
                                                 parse_mode='Markdown')
                        elif file_name.lower().endswith(('.mp3', '.wav', '.ogg')):
                            self.bot.send_audio(message.chat.id, file, caption=f"🎵 *{file_name}*", 
                                              parse_mode='Markdown')
                        elif file_name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                            self.bot.send_video(message.chat.id, file, caption=f"🎬 *{file_name}*", 
                                              parse_mode='Markdown')
                        else:
                            self.bot.send_document(message.chat.id, file, caption=f"📎 *{file_name}*", 
                                                 parse_mode='Markdown')
                    
                    self.waiting_for_file_path = False
                    self.bot.send_message(message.chat.id, "✅ *Файл успешно загружен!*", 
                                         parse_mode='Markdown', reply_markup=self.files_menu)
                else:
                    self.bot.send_message(message.chat.id, "❌ *Файл не найден! Проверьте путь.*", 
                                         parse_mode='Markdown')
                    
            except Exception as e:
                logging.error(f"Ошибка при загрузке файла: {e}")
                self.bot.send_message(message.chat.id, "❌ *Ошибка при загрузке файла!*", 
                                     parse_mode='Markdown')
                self.waiting_for_file_path = False
                
        @self.bot.message_handler(func=lambda message: self.waiting_for_process_name)
        def handle_process_name_input(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                self.waiting_for_process_name = False
                return
                
            process_name = message.text.strip()
            
            try:
                import psutil
                
                killed = False
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'].lower() == process_name.lower():
                            proc.kill()
                            killed = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                
                if killed:
                    self.bot.send_message(message.chat.id, f"✅ *Процесс {process_name} успешно завершен!*", 
                                         parse_mode='Markdown', reply_markup=self.processes_menu)
                else:
                    self.bot.send_message(message.chat.id, f"❌ *Процесс {process_name} не найден или не может быть завершен!*", 
                                         parse_mode='Markdown')
                
                self.waiting_for_process_name = False
                
            except ImportError:
                self.bot.send_message(message.chat.id, "❌ *Библиотека psutil не установлена!*", 
                                     parse_mode='Markdown')
                self.waiting_for_process_name = False
            except Exception as e:
                logging.error(f"Ошибка при завершении процесса: {e}")
                self.bot.send_message(message.chat.id, "❌ *Ошибка при завершении процесса!*", 
                                     parse_mode='Markdown')
                self.waiting_for_process_name = False
        
        @self.bot.message_handler(func=lambda message: self.waiting_for_program_path)
        def handle_program_path_input(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                self.waiting_for_program_path = False
                return
                
            program_path = message.text.strip()
            
            try:
                if os.path.exists(program_path):
                    os.startfile(program_path)
                    
                    self.waiting_for_program_path = False
                    self.bot.send_message(message.chat.id, 
                                         f"✅ *Программа успешно запущена:*\n`{program_path}`",
                                         parse_mode='Markdown',
                                         reply_markup=self.processes_menu)
                else:
                    try:
                        subprocess.Popen(program_path, shell=True)
                        
                        self.waiting_for_program_path = False
                        self.bot.send_message(message.chat.id, 
                                             f"✅ *Команда выполнена:*\n`{program_path}`",
                                             parse_mode='Markdown',
                                             reply_markup=self.processes_menu)
                    except:
                        self.bot.send_message(message.chat.id, "❌ *Файл не найден и не удалось выполнить команду! Проверьте путь.*", 
                                             parse_mode='Markdown')
                    
            except Exception as e:
                logging.error(f"Ошибка при запуске программы: {e}")
                self.bot.send_message(message.chat.id, "❌ *Ошибка при запуске программы!*", 
                                     parse_mode='Markdown')
                self.waiting_for_program_path = False
        
        @self.bot.message_handler(func=lambda message: self.waiting_for_notification_text)
        def handle_notification_input(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                self.waiting_for_notification_text = False
                return
                
            notification_text = message.text.strip()
            
            try:
                MessageBox = ctypes.windll.user32.MessageBoxW
                result = MessageBox(None, notification_text, "Уведомление от TGtoolspanel", 0x00000040 | 0x00000000)  # 0x40 = MB_ICONINFORMATION
                
                self.waiting_for_notification_text = False
                self.bot.send_message(message.chat.id, 
                                     f"✅ *Уведомление отправлено на ПК:*\n```\n{notification_text}\n```",
                                     parse_mode='Markdown',
                                     reply_markup=self.interaction_menu)
                
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления: {e}")
                self.bot.send_message(message.chat.id, "❌ *Ошибка при отправке уведомления на ПК!*", 
                                     parse_mode='Markdown')
                self.waiting_for_notification_text = False
        
        @self.bot.message_handler(func=lambda message: self.waiting_for_clipboard_text)
        def handle_clipboard_input(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                self.waiting_for_clipboard_text = False
                return
                
            text = message.text.strip()
            
            try:
                import pyperclip
                pyperclip.copy(text)
                
                self.waiting_for_clipboard_text = False
                self.bot.send_message(message.chat.id, 
                                     f"✅ *Текст скопирован в буфер обмена:*\n```\n{text}\n```",
                                     parse_mode='Markdown',
                                     reply_markup=self.interaction_menu)
                
            except ImportError:
                self.bot.send_message(message.chat.id, "❌ *Библиотека pyperclip не установлена!*", 
                                     parse_mode='Markdown')
                self.waiting_for_clipboard_text = False
            except Exception as e:
                logging.error(f"Ошибка при копировании в буфер обмена: {e}")
                self.bot.send_message(message.chat.id, "❌ *Ошибка при копировании в буфер обмена!*", 
                                     parse_mode='Markdown')
                self.waiting_for_clipboard_text = False
                
        @self.bot.message_handler(func=lambda message: self.waiting_for_mouse_step)
        def handle_mouse_step_input(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                self.waiting_for_mouse_step = False
                return
                
            try:
                step = int(message.text.strip())
                if step <= 0 or step > 1000:
                    self.bot.send_message(message.chat.id, "❌ *Введите число от 1 до 1000!*", 
                                         parse_mode='Markdown')
                    return
                
                self.mouse_step = step
                self.waiting_for_mouse_step = False
                
                self.bot.send_message(message.chat.id, 
                                     f"✅ *Шаг мыши изменен на {step} пикселей*",
                                     parse_mode='Markdown',
                                     reply_markup=self.mouse_menu)
                
            except ValueError:
                self.bot.send_message(message.chat.id, "❌ *Пожалуйста, введите число!*", 
                                     parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Ошибка при изменении шага мыши: {e}")
                self.bot.send_message(message.chat.id, "❌ *Ошибка при изменении шага мыши!*", 
                                     parse_mode='Markdown')
                self.waiting_for_mouse_step = False
                
        @self.bot.message_handler(content_types=['document', 'photo', 'audio', 'video'])
        def handle_file(message):
            if message.from_user.id != self.admin_id:
                self.bot.send_message(message.chat.id, "⛔ Доступ запрещен")
                return
                
            try:
                desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
                
                if message.document:
                    file_info = self.bot.get_file(message.document.file_id)
                    file_name = message.document.file_name
                elif message.photo:
                    file_info = self.bot.get_file(message.photo[-1].file_id)
                    file_name = f"photo_{int(time.time())}.jpg"
                elif message.audio:
                    file_info = self.bot.get_file(message.audio.file_id)
                    file_name = message.audio.file_name or f"audio_{int(time.time())}.mp3"
                elif message.video:
                    file_info = self.bot.get_file(message.video.file_id)
                    file_name = message.video.file_name or f"video_{int(time.time())}.mp4"
                else:
                    self.bot.send_message(message.chat.id, "❌ *Тип файла не поддерживается!*", 
                                         parse_mode='Markdown')
                    return
                
                downloaded_file = self.bot.download_file(file_info.file_path)
                
                save_path = os.path.join(desktop_path, file_name)
                
                if os.path.exists(save_path):
                    name, ext = os.path.splitext(file_name)
                    file_name = f"{name}_{int(time.time())}{ext}"
                    save_path = os.path.join(desktop_path, file_name)
                
                with open(save_path, 'wb') as new_file:
                    new_file.write(downloaded_file)
                
                self.bot.send_message(message.chat.id, 
                                     f"✅ *Файл сохранен на рабочий стол:*\n`{file_name}`",
                                     parse_mode='Markdown',
                                     reply_markup=self.files_menu)
                
            except Exception as e:
                logging.error(f"Ошибка при сохранении файла: {e}")
                self.bot.send_message(message.chat.id, "❌ *Ошибка при сохранении файла!*", 
                                     parse_mode='Markdown')
                
    def reset_waiting_states(self):
        """Сбрасывает все состояния ожидания ввода"""
        self.waiting_for_minutes = False
        self.waiting_for_file_path = False
        self.waiting_for_process_name = False
        self.waiting_for_clipboard_text = False
        self.waiting_for_mouse_step = False
        self.waiting_for_program_path = False
        self.waiting_for_notification_text = False
        
    def send_startup_notification(self):
        """Отправляет уведомление о включении ПК"""
        if self.admin_id:
            try:
                self.bot.send_message(self.admin_id, "🖥️ *ПК Включен*", 
                                     parse_mode='Markdown')
            except:
                pass
    
    def send_screenshot_with_cursor(self, chat_id, caption=None):
        """Делает скриншот с нарисованным курсором как в примере"""
        try:
            screenshot = ImageGrab.grab()
            
            import pyautogui
            mouse_x, mouse_y = pyautogui.position()
            
            draw = ImageDraw.Draw(screenshot)
            cursor_radius = 5  # Размер курсора
            
            draw.ellipse(
                [(mouse_x - cursor_radius, mouse_y - cursor_radius),
                 (mouse_x + cursor_radius, mouse_y + cursor_radius)],
                outline='white',
                width=2
            )
            
            draw.ellipse(
                [(mouse_x - cursor_radius + 2, mouse_y - cursor_radius + 2),
                 (mouse_x + cursor_radius - 2, mouse_y + cursor_radius - 2)],
                fill='red'
            )
            
            img_byte_arr = io.BytesIO()
            
            screenshot.save(img_byte_arr, format='JPEG', quality=90, optimize=True)
            img_byte_arr.seek(0)
            
            if caption:
                self.bot.send_photo(chat_id, img_byte_arr, caption=caption, parse_mode='Markdown')
            else:
                self.bot.send_photo(chat_id, img_byte_arr, caption="📸 *Скриншот экрана*", parse_mode='Markdown')
                
        except Exception as e:
            logging.error(f"Ошибка при создании скриншота: {e}")
            self.bot.send_message(chat_id, "❌ *Компьютер заблокирован или ошибка при создании скриншота*", 
                                 parse_mode='Markdown')
            
    def shutdown_pc(self):
        """Выключает компьютер"""
        try:
            subprocess.run(["shutdown", "/s", "/f", "/t", "0"], shell=True)
        except:
            os.system("shutdown /s /f /t 0")
            
    def reboot_pc(self):
        """Перезагружает компьютер"""
        try:
            subprocess.run(["shutdown", "/r", "/f", "/t", "0"], shell=True)
        except:
            os.system("shutdown /r /f /t 0")
            
    def sleep_pc(self):
        """Отправляет компьютер в спящий режим"""
        try:
            import ctypes
            ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
        except:
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            
    def move_mouse(self, x, y, chat_id, action_message):
        """Перемещает мышь и отправляет скриншот"""
        try:
            import pyautogui
            
            pyautogui.moveRel(x, y, duration=0.1)
            
            self.send_screenshot_with_cursor(chat_id, action_message)
            
        except ImportError:
            self.bot.send_message(chat_id, "❌ *Библиотека pyautogui не установлена!*", 
                                 parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Ошибка при перемещении мыши: {e}")
            self.bot.send_message(chat_id, "❌ *Ошибка при перемещении мыши!*", 
                                 parse_mode='Markdown')
            
    def mouse_click(self, button, chat_id, action_message):
        """Выполняет клик мыши и отправляет скриншот"""
        try:
            import pyautogui
            
            pyautogui.click(button=button)
            
            self.send_screenshot_with_cursor(chat_id, action_message)
            
        except ImportError:
            self.bot.send_message(chat_id, "❌ *Библиотека pyautogui не установлена!*", 
                                 parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Ошибка при клике мыши: {e}")
            self.bot.send_message(chat_id, "❌ *Ошибка при клике мыши!*", 
                                 parse_mode='Markdown')
            
    def send_hotkey(self, keys, chat_id, action_message):
        """Отправляет комбинацию клавиш"""
        try:
            from pynput.keyboard import Controller, Key
            
            keyboard = Controller()
            
            key_map = {
                'ctrl': Key.ctrl,
                'alt': Key.alt,
                'shift': Key.shift,
                'esc': Key.esc,
                'tab': Key.tab,
                'c': 'c',
                'v': 'v'
            }
            
            pynput_keys = []
            for key in keys:
                if key.lower() in key_map:
                    pynput_keys.append(key_map[key.lower()])
                else:
                    pynput_keys.append(key)
            
            for key in pynput_keys:
                keyboard.press(key)
            
            time.sleep(0.1)
            
            for key in reversed(pynput_keys):
                keyboard.release(key)
            
            self.bot.send_message(chat_id, action_message, parse_mode='Markdown')
            
        except ImportError:
            try:
                import pyautogui
                
                pyautogui.hotkey(*keys)
                self.bot.send_message(chat_id, action_message, parse_mode='Markdown')
                
            except Exception as e:
                logging.error(f"Ошибка при отправке комбинации клавиш: {e}")
                self.bot.send_message(chat_id, "❌ *Ошибка при отправке комбинации клавиш!*", 
                                     parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Ошибка при отправке комбинации клавиш: {e}")
            self.bot.send_message(chat_id, "❌ *Ошибка при отправке комбинации клавиш!*", 
                                 parse_mode='Markdown')
            
    def run(self):
        """Запускает бота"""
        logging.info("TGtoolspanel запущен")
        try:
            self.bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            logging.error(f"Ошибка в работе бота: {e}")

if __name__ == "__main__":
    bot = TGToolsPanelBot()
    bot.run()