-- =========================================================================
--  Community Agent Project - Complete Database Schema DDL (PostgreSQL)
-- =========================================================================

-- ---------------------------------------------------------
-- 1. 创建会话表 sessions
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,                                      -- 会话自增主键 ID
    user_id VARCHAR(255) NOT NULL,                              -- 关联的用户 ID
    title VARCHAR(255) DEFAULT '新对话',                        -- 会话标题，默认为 "新对话"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 创建时间（含时区）
);

-- 创建 sessions 表的性能优化索引
CREATE INDEX IF NOT EXISTS ix_sessions_id ON sessions (id);
CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions (user_id);


-- ---------------------------------------------------------
-- 2. 创建消息表 messages
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,                                      -- 消息自增主键 ID
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, -- 外键：关联 sessions(id)，级联删除
    role VARCHAR(100) NOT NULL,                                 -- 消息角色（例如 'user'、'assistant'）
    content TEXT,                                               -- 消息文本内容
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- 创建时间（含时区）
);

-- 创建 messages 表的性能优化索引
CREATE INDEX IF NOT EXISTS ix_messages_id ON messages (id);
CREATE INDEX IF NOT EXISTS ix_messages_session_id ON messages (session_id);
