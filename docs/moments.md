# 动态

## 功能

- 后台「动态管理」：发布、编辑、隐藏和删除纯文字动态，最多 500 字，空白内容不可提交。
- 管理权限沿用网站已有权限：仅 staff 或超级管理员可以管理动态，访客不可发布。
- 前台 `/moments`：按发布时间倒序分页展示公开动态，保留换行，采用普通文本渲染，无图片、Markdown 或评论。
- 桌面和手机导航均新增「动态」，沿用全站昼夜背景。
- 游客可点赞及取消点赞，不需要登录。同一浏览器共用签名 HttpOnly Cookie，数据库对每条动态及访客标识摘要建立唯一约束。
- 点赞 POST 与 DELETE 均为幂等操作，数量由点赞记录统计，避免重复累加。操作使用事务及动态行锁；点赞接口每 IP 每分钟最多 30 次操作。
- Cookie 有效期一年；清理 Cookie、使用无痕模式或更换浏览器会被视为新的访客。这是轻量的浏览器去重，不是实名投票或严格防刷系统。
- 隐藏动态不进入公开列表，隐藏或已删除的动态无法点赞。删除动态会级联删除点赞记录。

## 部署

```sh
cd zdblog-master
python manage.py migrate
```

迁移 `moment.0001_initial` 创建 `moment` 和 `moment_like` 表，无额外服务或依赖。本次已应用至本地数据库，部署其他环境时仍需执行迁移。项目已有 Docker 后端启动脚本会自动执行 `migrate --noinput`。

## 接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/moments/c/list/?page=1&page_size=10` | 公开动态及当前浏览器点赞状态 |
| POST / DELETE | `/api/moments/c/{id}/like/` | 点赞 / 取消点赞 |
| GET / POST | `/api/moments/s/moments/` | 后台列表 / 创建 |
| GET / PATCH / DELETE | `/api/moments/s/moments/{id}/` | 后台详情 / 修改 / 删除 |

后台列表支持 `search` 和 `is_published=true/false` 筛选；分页每页最多 50 条。后台写入仅接受内容与公开状态，发布时间、发布人和点赞数由服务端维护。
