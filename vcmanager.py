from zthon import zedub
from zthon.core.managers import edit_delete, edit_or_reply
from zthon.helpers.utils import mentionuser
from telethon import functions
from telethon.errors import ChatAdminRequiredError, UserAlreadyInvitedError
from telethon.tl.types import Channel, Chat, User


async def get_group_call(chat):
    if isinstance(chat, Channel):
        result = await zedub(functions.channels.GetFullChannelRequest(channel=chat))
    elif isinstance(chat, Chat):
        result = await zedub(functions.messages.GetFullChatRequest(chat_id=chat.id))
    return result.full_chat.call


async def chat_vc_checker(event, chat, edits=True):
    if isinstance(chat, User):
        await edit_delete(event, "**لايمكنك تشغيل الاغاني في المكالمات الخاصه**")
        return None
    result = await get_group_call(chat)
    if not result:
        if edits:
            await edit_delete(event, "** لا توجد مكالمة صوتية في هذه الدردشه**")
        return None
    return result


async def parse_entity(entity):
    if entity.isnumeric():
        entity = int(entity)
    return await zedub.get_entity(entity)


@zedub.zed_cmd(pattern="افتح الكول")
async def start_vc(event):
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat, False)
    if gc_call:
        return await edit_delete(
            event, "**- المكالمة الصوتية بالفعل مشغلة بهذه الدردشة**"
        )
    try:
        await zedub(
            functions.phone.CreateGroupCallRequest(
                peer=vc_chat,
                title="سورس كرستين",
            )
        )
        await edit_delete(event, "**- تم بنجاح تشغيل المكالمة الصوتية**")
    except ChatAdminRequiredError:
        await edit_delete(event, "**- يجب ان تكون ادمن لتشغيل المكالمة هنا**", time=20)


@zedub.zed_cmd(pattern="اقفل الكول")
async def end_vc(event):
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat)
    if not gc_call:
        return
    try:
        await zedub(functions.phone.DiscardGroupCallRequest(call=gc_call))
        await edit_delete(event, "**- تم بنجاح انهاء المكالمة الصوتية**")
    except ChatAdminRequiredError:
        await edit_delete(
            event, "**- يجب ان تكون مشرف لأنهاء المكالمة الصوتية**", time=20
        )


@zedub.zed_cmd(pattern="دعوة ?(.*)?")
async def inv_vc(event):
    users = event.pattern_match.group(1)
    reply = await event.get_reply_message()
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat)
    if not gc_call:
        return
    if not users:
        if not reply:
            return await edit_delete(
                "**- يجب عليك الرد على المستخدم او وضع معرفه مع الامر**"
            )
        users = reply.from_id
    await edit_or_reply(event, "**- تم بنجاح دعوة المستخدم**")
    entities = str(users).split(" ")
    user_list = []
    for entity in entities:
        cc = await parse_entity(entity)
        if isinstance(cc, User):
            user_list.append(cc)
    try:
        await zedub(
            functions.phone.InviteToGroupCallRequest(call=gc_call, users=user_list)
        )
        await edit_delete(event, "**- تم بنجاح دعوة المستخدمين**")
    except UserAlreadyInvitedError:
        return await edit_delete(event, "- تم دعوة المستخدم بالاصل", time=20)


@zedub.zed_cmd(pattern="مين في الكول")
async def info_vc(event):
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat)
    if not gc_call:
        return
    await edit_or_reply(event, "**- جار جلب معلومات المكالمة انتظر قليلا**")
    call_details = await zedub(
        functions.phone.GetGroupCallRequest(call=gc_call, limit=1)
    )
    grp_call = "**معلومات مكالمة المجموعة**\n\n"
    grp_call += f"**العنوان :** {call_details.call.title}\n"
    grp_call += f"**عدد المشاركين :** {call_details.call.participants_count}\n\n"

    if call_details.call.participants_count > 0:
        grp_call += "**المشاركون**\n"
        for user in call_details.users:
            nam = f"{user.first_name or ''} {user.last_name or ''}"
            grp_call += f"  ● {mentionuser(nam,user.id)} - `{user.id}`\n"
    await edit_or_reply(event, grp_call)


@zedub.zed_cmd(pattern="عنوان?(.*)?")
async def title_vc(event):
    title = event.pattern_match.group(1)
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat)
    if not gc_call:
        return
    if not title:
        return await edit_delete("**- يجب عليك كتابة العنوان مع الامر**")
    await zedub(functions.phone.EditGroupCallTitleRequest(call=gc_call, title=title))
    await edit_delete(event, f"- تم بنجاح تغيير اسم المكالمة الى **{title}**")


@zedub.zed_cmd(
    pattern="اسكت ([\s\S]*)",
    command=("اسكت", plugin_category),
    info={
        "header": "To mute users on Voice Chat.",
        "description": "To mute a stream on Voice Chat",
        "usage": [
            "{tr}vcmute < userid/username or reply to user >",
        ],
        "examples": [
            "{tr}vcmute @angelpro",
            "{tr}vcmute userid1 userid2",
        ],
    },
)
async def mute_vc(event):
    "To mute users in vc."
    cmd = event.pattern_match.group(1)
    users = event.pattern_match.group(2)
    reply = await event.get_reply_message()
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat)
    if not gc_call:
        return
    check = "Unmute" if cmd else "Mute"
    if not users:
        if not reply:
            return await edit_delete(f"Whom Should i {check}")
        users = reply.from_id
    await edit_or_reply(event, f"{check[:-1]}ing User in Group Call")
    entities = str(users).split(" ")
    user_list = []
    for entity in entities:
        cc = await parse_entity(entity)
        if isinstance(cc, User):
            user_list.append(cc)

    for user in user_list:
        await zedub(
            functions.phone.EditGroupCallParticipantRequest(
                call=gc_call,
                participant=user,
                muted=bool(not cmd),
            )
        )
    await edit_delete(event, f"{check}d users in Group Call")


@zedub.zed_cmd(
    command=("اتكلم", plugin_category),
    info={
        "header": "To unmute users on Voice Chat.",
        "description": "To unmute a stream on Voice Chat",
        "usage": [
            "{tr}vcunmute < userid/username or reply to user>",
        ],
        "examples": [
            "{tr}vcunmute @angelpro",
            "{tr}vcunmute userid1 userid2",
        ],
    },
)
async def unmute_vc(event):
    "To unmute users in vc."
