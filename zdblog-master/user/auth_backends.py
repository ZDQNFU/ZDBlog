"""自定义认证后端：保持 MySQL 时代「用户名不区分大小写」的登录行为。

迁移到 PostgreSQL 之前，库里用的是 MySQL 的 utf8mb4_general_ci 排序规则，
字符串比较默认忽略大小写：用户名存成 'ZDQNFU'，用 'zdqnfu' 也能登录。
PostgreSQL 默认是精确匹配，同样的登录会直接失败。

Django 自带的 ModelBackend 走 get_by_natural_key()，那是精确匹配，
所以只能在认证后端这一层改，改调用点是绕不过去的。
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class CaseInsensitiveModelBackend(ModelBackend):
    """按用户名查找时忽略大小写，其余行为与 ModelBackend 完全一致。"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        lookup = {f'{User.USERNAME_FIELD}__iexact': username}
        try:
            user = User._default_manager.get(**lookup)
        except User.DoesNotExist:
            # 与 ModelBackend 一致：用户不存在时也跑一次哈希，
            # 免得用响应时间差异就能枚举出哪些用户名已被注册。
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # 正常不该发生——注册时的唯一性校验同样已改成不区分大小写。
            # 万一是迁移带过来的历史数据，取最早的账号，至少不要抛 500。
            user = User._default_manager.filter(**lookup).order_by('pk').first()

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
