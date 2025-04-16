import sqlite3
import re
import requests
import time
import sys
import asyncio
from telegram import Update, ForceReply
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from datetime import datetime, timedelta

DB_NAME = "price_tracker.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    error INT DEFAULT 0,
                    html_page TEXT,
                    reg_exp TEXT,
                    currency TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id INTEGER UNIQUE,
                    item_id INTEGER,
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(item_id) REFERENCES items(item_id),
                    PRIMARY KEY(user_id, item_id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    price_history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER,
                    price REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(item_id) REFERENCES items(item_id)
                )
            """)
            self.conn.execute(
                "INSERT OR IGNORE INTO items (name, error, html_page, reg_exp, currency) VALUES (?, ?, ?, ?, ?)",
                ("USD", 0, "https://cbr.ru/currency_base/daily/",
                 "<td[^>]*>\s*USD\s*</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>([\d,]+)</td>", "руб.")
            )
            self.conn.execute(
                "INSERT OR IGNORE INTO items (name, error, html_page, reg_exp, currency) VALUES (?, ?, ?, ?, ?)",
                ("EUR", 0, "https://cbr.ru/currency_base/daily/",
                 "<td[^>]*>\s*EUR\s*</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>([\d,]+)</td>", "руб.")
            )
            self.conn.execute(
                "INSERT OR IGNORE INTO items (name, error, html_page, reg_exp, currency) VALUES (?, ?, ?, ?, ?)",
                ("BRENT", 0, "https://www.rbc.ru/quote/ticker/181206",
                 "<span class=\"chart__info__sum\">[\s\S]*?([\d\s]+,\d+)", "USD.")
            )
            

    def add_user(self, user_id, username):
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )

    def add_subscription(self, user_id, item_id):
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO subscriptions (user_id, item_id) VALUES (?, ?)",
                (user_id, item_id)
            )

    def add_price(self, item_id, price):
        with self.conn:
            self.conn.execute(
                "INSERT INTO price_history (item_id, price) VALUES (?, ?)",
                (item_id, price)
            )

    def get_price_history(self, item_id, days):
        if days < 1:
            days = 7 
        current_date = datetime.now()
        result_date = current_date - timedelta(days=days)
        sql_date = result_date.strftime("%Y-%m-%d %H:%M:%S")
        with self.conn:
            cursor = self.conn.execute("""
                SELECT price, timestamp 
                FROM price_history 
                WHERE item_id = ? 
                AND timestamp BETWEEN datetime(?) AND datetime('now') 
            """, (item_id, sql_date))
            return cursor.fetchall()

    def get_user_subscription(self, user_id):
        with self.conn:
            cursor = self.conn.execute(
                "SELECT item_id FROM subscriptions WHERE user_id = ?",
                (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def set_error(self, item_id):
        with self.conn:
            self.conn.execute(
                "UPDATE items SET error = TRUE WHERE item_id = (?)",
                (item_id,)
            )

    def get_prices(self):
        with self.conn:
            cursor = self.conn.execute("""
                SELECT item_id, html_page, reg_exp, error
                FROM items
            """)
            return cursor.fetchall()
    
    def get_items(self):
        with self.conn:
            cursor = self.conn.execute("""
                SELECT item_id, name FROM items
            """)
            return cursor.fetchall()

    def get_item_id(self, name):
        with self.conn:
            cursor = self.conn.execute(
                "SELECT item_id FROM items WHERE name = ?",
            (name,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_currency(self, item_id):
        with self.conn:
            cursor = self.conn.execute(
                "SELECT currency FROM items WHERE item_id = ?",
            (item_id,))
            return cursor.fetchone()

    def delete_subs_for_user(self, user_id):
        with self.conn:
            self.conn.execute(
            "DELETE FROM subscriptions WHERE user_id = ?",
            (user_id,)
        )

    def get_all_subscriptions(self):
        with self.conn:
            cursor = self.conn.execute("SELECT user_id, item_id FROM subscriptions")
            return cursor.fetchall()

    def get_latest_price(self, item_id):
        with self.conn:
            cursor = self.conn.execute("""
                SELECT price 
                FROM price_history 
                WHERE item_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (item_id,))
            result = cursor.fetchone()
            return result[0] if result else None

class PageParser:
    def __init__(self, updatetime):
        self.updatetime = updatetime

    def getValueFromWeb(self, page, regexp):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win32; x32) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(page, headers=headers)
        response.raise_for_status()
        html = response.text
        pattern = re.compile(regexp)
        match = pattern.findall(html)
        s=str()
        if match:
            for i in match:
                for j in i:
                    v = j.replace(',', '.')
                    v = v.replace(' ', '')
                    s += v
            value = float(s)
            return value

    def run(self, db):
        while True:
            prs = db.get_prices()
            for p in prs:
                idd, html, re, er = p
                try:
                    if er == 0:
                        price = self.getValueFromWeb(html, re)
                        if price is not None:
                            db.add_price(idd, price)
                        else:
                            db.set_error(idd)
                except Exception as e:
                    print(f'Ошибка: {e}')
                    db.set_error(idd)
            time.sleep(self.updatetime)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or user.first_name)
    await update.message.reply_text(
        rf"Привет, {user.first_name}! Используй /help для просмотра доступных команд.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""Доступные команды:
    /sub - подписаться на отслеживание цены предмета, или сменить подписку;
    /unsub - отказатьсяч от подписки;
    /list - список предметов, на отслеживание цены которых можно подписаться;
    /hist - показать историю изменения цен.""")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог прерван")
    context.user_data.clear()
    return ConversationHandler.END

DAYZ = range(1)
async def show_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите число дней:")
    return DAYZ

async def show_command2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["days"] = update.message.text
    user = update.effective_user
    item_id = db.get_user_subscription(user.id)
    if not item_id:
        await update.message.reply_text("У вас нет активной подписки!")
        return ConversationHandler.END
    try:
        days = int(context.user_data["days"])
        history = db.get_price_history(item_id, days)
    except ValueError:
        await update.message.reply_text("Некорректный формат числа дней!")
        return ConversationHandler.END
    abc = process_prices(history)
    a=str()
    if(len(abc) < 0):
        a = "За этот период нет отслеживаемых изменений"
    for i in abc:
        a += f"Цена товара на момент {i[1]}: {i[0]} руб.\n"
    await update.message.reply_text(a)
    return ConversationHandler.END

async def unsub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.delete_subs_for_user(user.id)
    await update.message.reply_text("Подписка удалена")
    return ConversationHandler.END

SUB = range(1)
async def sub_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название предмета:")
    return SUB

async def sub_command2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sub"] = update.message.text
    user = update.effective_user
    db.delete_subs_for_user(user.id)
    item_id = db.get_item_id(context.user_data["sub"])
    label=str()
    if item_id != None:
        db.add_subscription(user.id, item_id)
        label = "Подписка добавлена"
    else:
        label = "Такого предмета нет"
    await update.message.reply_text(label)
    return ConversationHandler.END

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = db.get_items()
    item_names = str()
    for n in items:
        item_names += n[1] + "\n"
    await update.message.reply_text("Список предметов:\n" + item_names)

async def send_price_updates(context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data['db']
    subscriptions = db.get_all_subscriptions()
    for user_id, item_id in subscriptions:
        price = db.get_latest_price(item_id)
        cur = db.get_currency(item_id)
        if price is not None:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Текущая цена товара: {price} {cur[0]}"
                )
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")

def process_prices(data):
    n = len(data)
    if n < 10:
        return data
    indices = [round(i * (n - 1) / 9) for i in range(10)]
    result = [data[i] for i in indices]
    return result

async def main(token):
    application = ApplicationBuilder().token(token).build()
    application.bot_data['db'] = db
    application.job_queue.run_repeating(send_price_updates, interval=3600, first=1)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("unsub", unsub_command))
    application.add_handler(CommandHandler("help", help_command))
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("hist", show_command)],
        states={
            DAYZ: [MessageHandler(filters.TEXT, show_command2)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    conv_handler2 = ConversationHandler(
        entry_points=[CommandHandler("sub", sub_command)],
        states={
            SUB: [MessageHandler(filters.TEXT, sub_command2)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(conv_handler)
    application.add_handler(conv_handler2)
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, pp.run, db)

if __name__ == "__main__":
    token = sys.argv[1]
    db = Database()
    pp = PageParser(30)
    
    try:
        asyncio.run(main(token))
    except KeyboardInterrupt:
        print("Приложение остановлено")