import telebot
import threading
import time
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# നിന്റെ പുതിയ ബോട്ട് ടോക്കൺ ഇവിടെ കൃത്യമായി ആഡ് ചെയ്തിട്ടുണ്ട്
API_TOKEN = '8605216441:AAFt8SWetFc5NiA5TAUk7qHYv9PtB2c9PA4'
bot = telebot.TeleBot(API_TOKEN)

# Render വെബ് സർവീസിന് വേണ്ടിയുള്ള ഹെൽത്ത് ചെക്ക് സെർവർ (Uptime സെറ്റിങ്സ്)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_health_server, daemon=True).start()

# ചാറ്റ് സ്റ്റാറ്റസ് ട്രാക്ക് ചെയ്യാനുള്ളവ
unlocked_users = set()        # ചാറ്റ് അൺലോക്ക് ആയവരുടെ ലിസ്റ്റ്
link_creators = {}            # ഏത് ലിങ്ക് ആര് ഉണ്ടാക്കി എന്ന് സൂക്ഷിക്കാൻ
last_warning_id = None

# 30 സെക്കൻഡിന് ശേഷം ബോട്ടിന്റെ വാണിംഗ് മെസ്സേജ് ഡിലീറ്റ് ചെയ്യാനുള്ള ഫങ്ക്ഷൻ
def delete_warning_after_time(chat_id, message_id):
    time.sleep(30)
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

# 1. പുതിയൊരാൾ ജോയിൻ ചെയ്യുമ്പോൾ ഉള്ള സിസ്റ്റം മെസ്സേജ് ഡിലീറ്റ് ചെയ്യലും റെഫറൽ ചെക്കിംഗും
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    try:
        # സിസ്റ്റം മെസ്സേജ് അപ്പോൾ തന്നെ കളയുന്നു
        bot.delete_message(message.chat.id, message.message_id)
        
        # ഗ്രൂപ്പിൽ കയറിയ പുതിയ ആൾ വന്നത് ആരുടെ ലിങ്ക് വഴിയാണെന്ന് നോക്കുന്നു
        for member in message.new_chat_members:
            if message.invite_link and message.invite_link.invite_link in link_creators:
                referrer_id = link_creators[message.invite_link.invite_link]
                # റെഫർ ചെയ്ത ആളുടെ ചാറ്റ് അൺലോക്ക് ചെയ്യുന്നു!
                unlocked_users.add(referrer_id)
                print(f"User {referrer_id} റെഫർ ചെയ്ത ആൾ ജോയിൻ ചെയ്തു! ചാറ്റ് അൺലോക്ക് ആയി.")
    except Exception as e:
        print(f"New member error: {e}")

# 2. മെസ്സേജ് ലോക്കിങ് സിസ്റ്റം
@bot.message_handler(func=lambda message: True)
def lock_and_check(message):
    global last_warning_id
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # യൂസർ ഇതുവരെ ആരെയും ജോയിൻ ചെയ്യിപ്പിച്ചിട്ടില്ലെങ്കിൽ (Locked അവസ്ഥയിൽ)
    if user_id not in unlocked_users:
        try:
            # അയാൾ ഗ്രൂപ്പിൽ ഇടുന്ന എന്ത് മെസ്സേജും അപ്പോൾ തന്നെ ഡിലീറ്റ് ചെയ്യുന്നു
            bot.delete_message(chat_id, message.message_id)
            
            # ബോട്ടിന്റെ പഴയ വാണിംഗ് ഉണ്ടെങ്കിൽ കളയുന്നു
            if last_warning_id:
                try:
                    bot.delete_message(chat_id, last_warning_id)
                except Exception:
                    pass
            
            # ഈ യൂസർക്ക് വേണ്ടി മാത്രം പ്രൈവറ്റ് ഗ്രൂപ്പിന്റെ ഒരു യുണീക് ഇൻവൈറ്റ് ലിങ്ക് ഉണ്ടാക്കുന്നു
            invite_link_obj = bot.create_chat_invite_link(chat_id, member_limit=1)
            unique_link = invite_link_obj.invite_link
            
            # ഈ ലിങ്ക് ട്രാക്ക് ചെയ്യാൻ സൂക്ഷിക്കുന്നു
            link_creators[unique_link] = user_id
            
            user_mention = f"[{message.from_user.first_name}](tg://user?id={user_id})"
            
            # നീ ആവശ്യപ്പെട്ട ഇംഗ്ലീഷ് മെസ്സേജ്
            warning_text = f"Hey {user_mention}, you need to share this group link with at least 1 person and they must join for you to unlock messaging here!"
            
            # ഷെയർ ചെയ്യാനുള്ള ഇൻലൈൻ ബട്ടൺ
            markup = InlineKeyboardMarkup()
            share_button = InlineKeyboardButton(text="📢 Share Link", url=f"https://t.me/share/url?url={unique_link}")
            markup.add(share_button)
            
            sent_msg = bot.send_message(chat_id, warning_text, parse_mode='Markdown', reply_markup=markup)
            last_warning_id = sent_msg.message_id
            
            # ബോട്ടിന്റെ വാണിംഗ് മെസ്സേജ് 30 സെക്കൻഡിൽ ഡിലീറ്റ് ചെയ്യും
            threading.Thread(target=delete_warning_after_time, args=(chat_id, sent_msg.message_id)).start()
        except Exception as e:
            print(f"Lock system error: {e}")
        return
        
    # യൂസർ അൺലോക്ക് ആയിക്കഴിഞ്ഞാൽ അയാൾ അയക്കുന്ന മെസ്സേജുകൾ നോർമൽ ആയി ഗ്രൂപ്പിൽ വരും
    print(f"User {user_id} അൺലോക്ക് ആയ ആളാണ്, മെസ്സേജ് അനുവദിച്ചു.")

bot.infinity_polling()
