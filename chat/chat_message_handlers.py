from datetime import datetime
from bot import db, config
from bot.keyboards import ask_question_or_counseling_keyboard
from bot.helpers import (
    find_text_for_callback,
    create_buttons_from_data,
    handle_view_more,
)
from bot.database import (
    add_topic_to_db,
    get_all_counseling_topics,
    set_user_last_command,
)
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import CallbackContext


def counseling(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    counseling_topics = get_all_counseling_topics()
    categories_keyboard = create_buttons_from_data(counseling_topics, "counsel", 5, 1)
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["counseling_start"],
        reply_markup=categories_keyboard,
    )


def handle_counseling(update, context):
    chat_id = update.effective_chat.id
    topic = find_text_for_callback(update.callback_query).lower()
    topic_from_db = db.counseling_topics.find_one({"topic": topic})

    questions = topic_from_db["faqs"]

    ids = [faq["id"] for faq in questions]
    topic_callback_info = f"faq={topic}"
    row, cols = 1, 5

    # Create buttons using the sliced FAQs
    buttons = create_buttons_from_data(ids, topic_callback_info, row, cols)

    num_questions = row * cols

    # Slicing the FAQs to match the number of buttons
    displayed_faqs = questions[:num_questions]

    # Format the questions for display
    questions = "\n\n".join(
        ["{0}. {1}".format(faq["id"], faq["q"]) for faq in displayed_faqs]
    )

    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["counseling_topic_reply"].format(
            topic.capitalize(), questions
        ),
        reply_markup=buttons,
    )

    # Add topic to database and ask question or request counselor
    add_topic_to_db(topic)
    ask_question_or_request_counselor(update, context)


def ask_question_or_request_counselor(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["add_question_or_request_counselor"],
        reply_markup=ask_question_or_counseling_keyboard,
    )


def handle_ask_question_or_request_counselor(update, context):
    chat_id = update.effective_chat.id
    user_request = find_text_for_callback(update.callback_query).lower()

    print(user_request)

    if user_request == "speak to a counselor":
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counselor_request_yes"],
        )
        db.users.update_one(
            {"chat_id": chat_id}, {"$set": {"last_command": "counselor_request_yes"}}
        )
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["ask_question"],
        )
        db.users.update_one(
            {"chat_id": chat_id}, {"$set": {"last_command": "ask_counseling_question"}}
        )


def handle_counselor_request_yes(update, context):
    chat_id = update.effective_chat.id
    message = update.message
    try:
        contact_info = message.text.split("\n")
        name = contact_info[0].strip()
        email = contact_info[1].strip()  # regex email validation
        phone = contact_info[2].strip()  # regex validate phone number
        message_id = message.message_id

        # temporarily add request to db queue
        add_request_to_queue(
            {
                "created": datetime.now(),
                "chat_id": chat_id,
                "name": name,
                "email": email,
                "phone": phone,
                "request_message_id": message_id,
                "note": None,
            }
        )

        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counselor_request_contact_info_confirm"].format(
                name, email, phone
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Yes, this is correct",
                            callback_data="cr=yes=" + str(message_id),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "No, I want to make a change",
                            callback_data="cr=no=" + str(message_id),
                        )
                    ],
                ],
                resize_keyboard=True,
            ),
        )
    except:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counselor_request_invalid_info"]
        )
        db.users.update_one(
            {"chat_id": chat_id}, {"$set": {"last_command": "counselor_request_yes"}}
        )


def handle_get_faq_callback(update, context):
    chat_id = update.effective_chat.id
    question_id = find_text_for_callback(update.callback_query).lower()
    q_head = update.callback_query.data.split("=")
    topic = q_head[1]
    response = db.counseling_topics.find_one({"topic": topic})

    if q_head[2] == "more":
        last_idx = int(q_head[-1])
        questions = response["faqs"]

        row, cols = 1, 5

        num_questions = min(last_idx + row * cols, len(questions))

        # Slicing the FAQs to match the number of buttons
        displayed_faqs = questions[last_idx:num_questions]

        ids = [faq["id"] for faq in questions]
        updated_buttons = handle_view_more(
            update.callback_query, ids, f"faq={topic}", row, cols
        )
        # Format the questions for display
        questions = "\n\n".join(
            ["{0}. {1}".format(faq["id"], faq["q"]) for faq in displayed_faqs]
        )

        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counseling_topic_reply"].format(
                topic.capitalize(), questions
            ),
            reply_markup=updated_buttons,
        )

        if num_questions == len(questions):
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["counseling_topic_reply_end"],
                reply_markup=ask_question_or_counseling_keyboard,
            )
    else:
        answer = response["faqs"][int(question_id) - 1]["a"].strip()
        context.bot.send_message(
            chat_id=chat_id,
            text=answer,
        )


def handle_ask_question(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text.strip().lower()

    db.new_questions.insert_one({"chat_id": chat_id, "question": message})
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["ask_question_success"]
    )
    set_user_last_command(chat_id, None)


def add_request_to_queue(counseling_request: dict):
    db.counseling_requests.insert_one(
        {
            "created": counseling_request["created"],
            "name": counseling_request["name"],
            "email": counseling_request["email"],
            "phone": counseling_request["phone"],
            "chat_id": counseling_request["chat_id"],
            "request_message_id": counseling_request["request_message_id"],
            "active": False,
            "note": counseling_request["note"],
            "status": "pending",
            "counselor_chat_id": None,
        }
    )
