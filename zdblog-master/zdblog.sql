#创建数据库
CREATE DATABASE zdblog CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库（请提前创建好 zdblog）
USE zdblog;

-- ----------------------------
-- 1. 分类表
-- ----------------------------
CREATE TABLE `article_category` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID v7 主键',
    `name` VARCHAR(50) NOT NULL COMMENT '分类名',
    `created_by_id` BIGINT NULL COMMENT '创建人ID',
    `updated_by_id` BIGINT NULL COMMENT '最后修改人ID',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '最后修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_category_name` (`name`),
    KEY `idx_category_created_by` (`created_by_id`),
    KEY `idx_category_updated_by` (`updated_by_id`),
    CONSTRAINT `fk_category_created_by` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_category_updated_by` FOREIGN KEY (`updated_by_id`) REFERENCES `auth_user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章分类';

-- ----------------------------
-- 2. 标签表
-- ----------------------------
CREATE TABLE `article_tag` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID v7 主键',
    `name` VARCHAR(50) NOT NULL COMMENT '标签名',
    `color` VARCHAR(7) NOT NULL DEFAULT '#3b82f6' COMMENT '标签颜色（十六进制）',
    `created_by_id` BIGINT NULL COMMENT '创建人ID',
    `updated_by_id` BIGINT NULL COMMENT '最后修改人ID',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '最后修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_tag_name` (`name`),
    KEY `idx_tag_created_by` (`created_by_id`),
    KEY `idx_tag_updated_by` (`updated_by_id`),
    CONSTRAINT `fk_tag_created_by` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_tag_updated_by` FOREIGN KEY (`updated_by_id`) REFERENCES `auth_user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章标签';

-- ----------------------------
-- 3. 文章表
-- ----------------------------
CREATE TABLE `article` (
    `id` CHAR(36) NOT NULL COMMENT 'UUID v7 主键',
    `title` VARCHAR(200) NOT NULL COMMENT '文章标题',
    `slug` VARCHAR(50) NOT NULL COMMENT 'URL 别名',
    `summary` VARCHAR(300) NOT NULL DEFAULT '' COMMENT '文章摘要',
    `content_md` LONGTEXT NOT NULL COMMENT 'Markdown 内容',
    `content_html` LONGTEXT NOT NULL DEFAULT '' COMMENT 'HTML 内容',
    `cover` VARCHAR(200) NOT NULL DEFAULT '' COMMENT '封面图 URL',
    `status` VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT '状态：draft/published/private',
    `view_count` INTEGER NOT NULL DEFAULT 0 COMMENT '阅读数',
    `like_count` INTEGER NOT NULL DEFAULT 0 COMMENT '点赞数',
    `comment_count` INTEGER NOT NULL DEFAULT 0 COMMENT '评论数',
    `author_id` BIGINT NULL COMMENT '作者ID',
    `category_id` CHAR(36) NULL COMMENT '分类ID（UUID）',
    `published_at` DATETIME(6) NULL COMMENT '发布时间',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '最后修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_article_slug` (`slug`),
    KEY `idx_article_status` (`status`),
    KEY `idx_article_author` (`author_id`),
    KEY `idx_article_category` (`category_id`),
    KEY `idx_article_published_at` (`published_at`),
    CONSTRAINT `fk_article_author` FOREIGN KEY (`author_id`) REFERENCES `auth_user` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_article_category` FOREIGN KEY (`category_id`) REFERENCES `article_category` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章';
