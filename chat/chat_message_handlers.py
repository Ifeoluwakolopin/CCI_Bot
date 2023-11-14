from datetime import datetime
from bot import db, config
from bot.commands import unknown
from bot.helpers import find_text_for_callback
from bot.database import add_topic_to_db
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import CallbackContext
from bot.keyboards import categories_keyboard


def counseling(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["counseling_start"],
        reply_markup=InlineKeyboardMarkup(categories_keyboard, resize_keyboard=True),
    )


def handle_counseling(update, context):
    chat_id = update.effective_chat.id
    topic = find_text_for_callback(update.callback_query).lower()
    topic_from_db = db.counseling_topics.find_one({"topic": topic})

    if topic_from_db:
        faqs = topic_from_db["faqs"]

        buttons = [
            [
                InlineKeyboardButton(
                    str(faqs[idx]["id"]),
                    callback_data="faq=" + topic + "=" + str(faqs[idx]["id"]) + "=5",
                )
                for idx in range(0, 5)
            ],
            [
                InlineKeyboardButton(
                    "View More Questions",
                    callback_data="faq=" + topic + "=" + str(5) + "=more",
                )
            ],
        ]

        questions = "\n\n".join(
            ["{0}. {1}".format(faq["id"], faq["q"]) for faq in faqs[0:5]]
        )

        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counseling_topic_reply"].format(
                topic.capitalize(), questions
            ),
            reply_markup=InlineKeyboardMarkup(buttons, resize_keyboard=True),
        )
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counseling_topic_not_found"],
            reply_markup=InlineKeyboardMarkup(
                categories_keyboard, resize_keyboard=True
            ),
        )
    # adds topic to database
    add_topic_to_db(topic)
    ask_question_or_request_counselor(update, context)


def ask_question_or_request_counselor(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["add_question_or_request_counselor"],
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Ask a question", callback_data="qa_or_c=" + str(0)
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Speak to a Counselor", callback_data="qa_or_c=" + str(1)
                    )
                ],
            ],
            resize_keyboard=True,
        ),
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
    q = update.callback_query.data
    q_head = q.split("=")
    topic = q_head[1]
    response = db.counseling_topics.find_one({"topic": topic})

    if q_head[-1] == "more":
        last_idx = int(q_head[-2])

        faqs = db.counseling_topics.find_one({"topic": topic})["faqs"]
        try:
            buttons = [
                [
                    InlineKeyboardButton(
                        str(faqs[idx]["id"]),
                        callback_data="faq="
                        + topic
                        + "="
                        + str(faqs[idx]["id"])
                        + "="
                        + str(last_idx + 5),
                    )
                    for idx in range(last_idx, last_idx + 5)
                ],
                [
                    InlineKeyboardButton(
                        "View More Questions",
                        callback_data="faq="
                        + topic
                        + "="
                        + str(last_idx + 5)
                        + "=more",
                    )
                ],
            ]

            questions = "\n\n".join(
                [
                    "{0}. {1}".format(faq["id"], faq["q"])
                    for faq in faqs[last_idx : last_idx + 5]
                ]
            )
        except:
            l = len(faqs)
            buttons = [
                [
                    InlineKeyboardButton(
                        str(faqs[idx]["id"]),
                        callback_data="faq="
                        + topic
                        + "="
                        + str(faqs[idx]["id"])
                        + "="
                        + str(last_idx + 5),
                    )
                    for idx in range(last_idx, l - 1)
                ]
            ]
            questions = "\n\n".join(
                [
                    "{0}. {1}".format(faq["id"], faq["q"])
                    for faq in faqs[last_idx : len(faqs) - 1]
                ]
            )

        if len(buttons[0]) == 0:
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["counseling_topic_reply_end"].format(
                    topic.capitalize()
                ),
            )
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["counseling_topic_reply"].format(
                    topic.capitalize(), questions
                ),
                reply_markup=InlineKeyboardMarkup(buttons, resize_keyboard=True),
            )
    else:
        answer = response["faqs"][int(q_head[2]) - 1]["a"].strip()
        buttons = [
            [
                InlineKeyboardButton(
                    "View More Questions",
                    callback_data="faq=" + q_head[1] + "=" + str(q_head[-1]) + "=more",
                )
            ]
        ]
        context.bot.send_message(
            chat_id=chat_id,
            text=answer,
            reply_markup=InlineKeyboardMarkup(buttons, resize_keyboard=True),
        )


def get_topics_from_db():
    topics = db.counseling_topics.find()
    return [topic["topic"] for topic in topics]


def handle_ask_question(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text.strip().lower()

    db.new_questions.insert_one({"chat_id": chat_id, "question": message})
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["ask_question_success"]
    )
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


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
