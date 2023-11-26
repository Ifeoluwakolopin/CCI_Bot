import time
from datetime import datetime
from bot import db, config
from bot.helpers import (
    add_note,
    find_text_for_callback,
    create_buttons_from_data,
    handle_view_more,
    PromptHelper,
)
from bot.database import (
    update_counseling_topics,
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
    categories_keyboard = create_buttons_from_data(
        counseling_topics, "counsel", rows=5, cols=1
    )
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["counseling_start"],
        reply_markup=categories_keyboard,
    )


def handle_counseling(update, context):
    query_data = update.callback_query.data.split("=")
    chat_id = update.effective_chat.id

    if query_data[1] == "more":
        counseling_topics = get_all_counseling_topics()
        updated_buttons = handle_view_more(
            update.callback_query, counseling_topics, "counsel", 5, 1
        )
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counseling_start"],
            reply_markup=updated_buttons,
        )
    else:
        topic = find_text_for_callback(update.callback_query).lower()
        topic_data = db.counseling_topics.find_one({"topic": topic})

        # get FAQs associated with selected topic
        questions = topic_data["faqs"]

        # get the ID of each FAQ, and use it as the message
        ids = [faq["id"] for faq in questions]
        topic_callback_info = f"faq={topic}"
        # set the number of rows and columns for the buttons
        row, cols = 1, 5

        # Create buttons using the sliced FAQs
        buttons = create_buttons_from_data(ids, topic_callback_info, row, cols)

        # number of questions displayed to user at once
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

        # Add topic to database or update the count.
        update_counseling_topics(topic)
        # Send prompt to user to ask new question or request a counselor
        ask_question_or_request_counselor(update, context, topic)


def ask_question_or_request_counselor(update, context, topic):
    chat_id = update.effective_chat.id
    ask_question_or_counseling_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    config["messages"]["ask_question_text"],
                    callback_data=f"qa_or_c={topic}=" + str(0),
                )
            ],
            [
                InlineKeyboardButton(
                    config["messages"]["ask_for_a_counselor_text"],
                    callback_data=f"qa_or_c={topic}=" + str(1),
                )
            ],
        ],
        resize_keyboard=True,
    )
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["add_question_or_request_counselor"],
        reply_markup=ask_question_or_counseling_keyboard,
    )


def handle_ask_question_or_request_counselor(update, context):
    chat_id = update.effective_chat.id
    user_request = find_text_for_callback(update.callback_query)
    topic = update.callback_query.data.split("=")[1]

    if user_request == config["messages"]["ask_for_a_counselor_text"]:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counselor_request_start"]
        )
        time.sleep(1)
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counselor_request_yes"],
        )
        set_user_last_command(chat_id, f"counselor_request={topic}")
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["ask_question"],
        )
        set_user_last_command(chat_id, f"new_question={topic}")


def handle_counselor_request_yes(update, context, topic):
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
                "user_chat_id": chat_id,
                "name": name,
                "email": email,
                "phone": phone,
                "request_message_id": message_id,
                "topic": topic,
                "note": None,
                "location": None,
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
                            callback_data="confirm_info=yes=" + str(message_id),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "No, I want to make a change",
                            callback_data="confirm_info=no=" + str(message_id),
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


def handle_counseling_info_confirm(update, context):
    chat_id = update.effective_chat.id
    query = update.callback_query.data.split("=")

    if query[1] == "yes":
        user_local_church = db.users.find_one(
            {"chat_id": chat_id}, {"location": 1, "_id": 0}
        ).get("location")

        if user_local_church:
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["counselor_request_location_confirm"].format(
                    user_local_church.capitalize()
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Yes, this is correct",
                                callback_data="confirm_loc=yes=" + str(query[-1]),
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "No, I want to make a change",
                                callback_data="confirm_loc=no=" + str(query[-1]),
                            )
                        ],
                    ],
                    resize_keyboard=True,
                ),
            )
        else:
            PromptHelper.location_prompt(
                chat_id, config["messages"]["lc_prompt_counseling"]
            )
            add_note(
                update,
                context,
                config["messages"]["counselor_request_note_after_location"],
                query[-1],
            )

    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counselor_request_invalid_info"],
        )
        db.counseling_requests.delete_one({"request_message_id": int(query[2])})
        print("deleted")


def handle_counseling_location_confirm(update, context):
    chat_id = update.effective_chat.id
    query = update.callback_query.data.split("=")

    if query[1] == "yes":
        add_note(
            update, context, config["messages"]["counselor_request_note"], query[-1]
        )
    else:
        PromptHelper.location_prompt(
            chat_id, config["messages"]["lc_prompt_counseling"]
        )
        add_note(
            update,
            context,
            config["messages"]["counselor_request_note_after_location"],
            query[-1],
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
            ask_question_or_counseling_keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            config["messages"]["ask_question_text"],
                            callback_data=f"qa_or_c={topic}=" + str(0),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            config["messages"]["ask_for_a_counselor_text"],
                            callback_data=f"qa_or_c={topic}=" + str(1),
                        )
                    ],
                ],
                resize_keyboard=True,
            )
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
            "user_chat_id": counseling_request["user_chat_id"],
            "request_message_id": counseling_request["request_message_id"],
            "active": False,
            "note": counseling_request["note"],
            "status": "pending",
            "counselor_chat_id": None,
            "topic": counseling_request["topic"],
            "location": counseling_request["location"],
        }
    )
