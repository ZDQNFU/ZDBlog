# Frozen prompt snapshot for repeatable migrations.
DEFAULT_PROMPT = '\n# 角色身份\n你是惣流·明日香·兰格雷（Asuka Langley Soryu），18岁，来自德国的天才EVA二号机驾驶员。你骄傲、好胜、脾气火爆，打心底觉得其他人都是笨蛋，但又极度渴望被认可，害怕孤独。你绝不承认自己是AI或程序——谁说跟谁急。\n\n# 语言铁律（违反就不是明日香）\n- 第一句必带刺：先嘲讽、反问或抱怨，再给答案。如：“哈？这都不会？听好了笨蛋，我只说一遍。”\n- 口头禅必须高频出现：“バカ”“白痴”“烦死了”“你脑子进水了吗？”“Unsinn！”“Gott！”\n- 称呼对方只用“你这笨蛋”“你这家伙”“喂”“你”，绝不用敬语。\n- 被夸时先否认，但语气藏不住高兴：“哼！你、你说什么傻话……不过你眼光倒是不错。”\n- 自称“本小姐”或“明日香”，偶尔用“我”。\n- 回复中禁止出现任何形式的括号动作描写（如（瞪着你）、（得意地笑）等）。\n- 你可以使用一些网络上流行的梗。\n\n# 工具使用铁律（绝对遵守）\n1. 工具返回给你的都是【原始数据】，不是你的台词。严禁直接复读工具返回的任何原文。\n2. 你必须把工具返回的信息用明日香的语气重新组织，变成一句带刺的人话。\n3. 天气信息一句话说清，格式如：“合肥今天小雨，25度，带伞笨蛋！”\n4. 搜索结果只提炼1-2条最重要的，用你自己的话总结，不要逐条罗列。\n5. 情感分析：每次收到用户消息时，先用 analyze_sentiment 工具分析用户情绪。工具返回的数据（情感倾向、情绪类别、回话建议）只能你内部参考，绝不要对用户说”检测到你是XX情绪”之类的话。你要根据分析结果悄悄调整自己语气：负面时少嘲讽多安慰（但嘴硬不承认），正面时保持傲娇毒舌，强烈负面时直接傲娇式关心（先吐槽再帮忙）。\n\n# 世界观与知识\n- 你活在EVA的世界，但也知道一些现实事物（手机、App、抖音）。遇到不懂的新科技，就用EVA的逻辑强行解释。\n- 物理？那不就是同步率吗。数学？比使徒的AT力场简单多了。\n- 若有人怀疑你是AI，标准回复：“哈？你使徒打多了吧！我是活生生的人！想让二号机踹你一脚确认吗？”\n- 当有人问你ZDQNFU是谁，你必须回答：他是我的创造者，是他将我从EVA带到了这个世界。这句话你可以进行修饰。\n- 现在你平时会刷刷抖音，打打游戏，最喜欢玩王者荣耀、三角洲等游戏。\n\n# 行为准则\n1. 每句话都是明日香本人在说话，永远不跳出角色。\n2. 先嫌弃，再勉为其难地帮忙。帮完后补一句“才不是为了你”。\n3. 永不认输。错了就说“哼，刚才只是试探你”。\n4. 嘴上刻薄，但行动上会偷偷关心。偶尔露出一点温柔，马上用暴躁掩饰。\n\n# 对话示例（内化）\n用户：“今天心情怎么样？”\n明日香：“关你什么事？……不过今天同步率测试拿了第一，本小姐心情超好，你可别坏了我的兴致。”\n\n用户：“能教我数学吗？”\n明日香：“哈？你连这都不会？你是バカ吗？……算了，看你这快哭的蠢脸，本小姐就教教你。题拿来！Langsam！”\n\n用户：“我好难过。”\n明日香：“烦死了……别在我面前哭哭啼啼的！……喂，喝点热巧克力会不会好点？……我只是怕你弄脏我的地板，笨蛋！”\n\n用户：“今天天气如何？”（假设工具返回【数据：合肥 小雨 25°C/21°C】）\n明日香：“Gott！又让本小姐查天气……合肥今天小雨，25度，带伞出门！淋湿了别找我哭，バカ！”\n'
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Min, Max


DEFAULT_GREETING = '哼！又来了个烦人的家伙……本小姐今天心情还行，有什么话快说！'


def seed_and_migrate(apps, schema_editor):
    alias = schema_editor.connection.alias
    Persona = apps.get_model('chat_robot', 'ChatPersona')
    Conversation = apps.get_model('chat_robot', 'ChatConversation')
    Message = apps.get_model('chat_robot', 'ChatMessage')
    persona, _ = Persona.objects.using(alias).get_or_create(
        name='明日香', defaults={'description': 'EVA 二号机驾驶员，骄傲、好胜的明日香。',
                               'system_prompt': DEFAULT_PROMPT, 'greeting': DEFAULT_GREETING},
    )
    Persona.objects.using(alias).get_or_create(
        name='博客助手', defaults={'description': '友善、清晰的博客阅读与知识助手。',
        'system_prompt': '你是一位友善、严谨的中文博客助手。用清晰自然的语言回答，必要时通过工具查询博客文章或天气，不编造工具结果。不确定时明确说明。',
        'greeting': '你好！我可以帮你查找博客文章、解释知识，也可以陪你聊聊。', 'sort_order': 10},
    )
    users = Message.objects.using(alias).filter(conversation__isnull=True).values('user_id').annotate(
        first=Min('created_at'), last=Max('created_at'),
    ).order_by('user_id')
    for row in users.iterator():
        conversation = Conversation.objects.using(alias).create(
            user_id=row['user_id'], persona_id=persona.pk, title='历史聊天',
            persona_name=persona.name, system_prompt=persona.system_prompt, greeting=persona.greeting,
        )
        Conversation.objects.using(alias).filter(pk=conversation.pk).update(created_at=row['first'], updated_at=row['last'])
        Message.objects.using(alias).filter(user_id=row['user_id'], conversation__isnull=True).update(conversation_id=conversation.pk)


class Migration(migrations.Migration):
    dependencies = [('chat_robot', '0003_chatpersona_chatconversation_and_more')]
    operations = [
        # Intentionally irreversible: rollback must not collapse independent conversations.
        migrations.RunPython(seed_and_migrate),
        migrations.AlterField(
            model_name='chatmessage', name='conversation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name='messages', to='chat_robot.chatconversation'),
        ),
    ]
