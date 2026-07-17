from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})
    captcha_key = serializers.CharField()
    captcha_answer = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError(_('用户名或密码错误'))
            if not user.is_active:
                raise serializers.ValidationError(_('该用户已被禁用'))
            if not user.is_staff and not user.is_superuser:
                raise serializers.ValidationError(_('该账号没有后台管理权限'))
            attrs['user'] = user
        else:
            raise serializers.ValidationError(_('请输入用户名和密码'))
        return attrs


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined', 'is_superuser', 'is_staff']


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_superuser', 'is_staff',
                  'is_active', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_superuser',
                  'is_staff', 'is_active', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_('该邮箱已被注册'))
        return value


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=2, max_length=30)
    password = serializers.CharField(min_length=6, style={'input_type': 'password'})
    email = serializers.EmailField()
    verification_code = serializers.CharField()
    verification_key = serializers.CharField()

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(_('用户名已存在'))
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_('该邮箱已被注册'))
        return value

    def validate(self, attrs):
        from .email_verification import verify_code
        if not verify_code(attrs['verification_key'], attrs['verification_code']):
            raise serializers.ValidationError({'verification_code': ['验证码错误或已过期']})
        return attrs

    def create_user(self):
        return User.objects.create_user(
            username=self.validated_data['username'],
            password=self.validated_data['password'],
            email=self.validated_data['email'],
            is_superuser=False,
            is_staff=False,
        )
