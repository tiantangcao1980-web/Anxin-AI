-- AI法务智能体系统 - 数据库初始化脚本

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ==================== 组织与用户 ====================

-- 组织表
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    logo_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP WITH TIME ZONE,
    login_attempts INTEGER DEFAULT 0,
    password_changed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==================== 案件管理 ====================

-- 案件表
CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    case_number VARCHAR(50) UNIQUE,
    case_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'medium',
    description TEXT,
    assignee_id UUID REFERENCES users(id) ON DELETE SET NULL,
    parties JSONB DEFAULT '{}',
    ai_analysis JSONB DEFAULT '{}',
    risk_score FLOAT,
    deadline TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 案件事件/时间线
CREATE TABLE IF NOT EXISTS case_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_data JSONB DEFAULT '{}',
    event_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==================== 文档管理 ====================

-- 文档表
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    case_id UUID REFERENCES cases(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    doc_type VARCHAR(50),
    description TEXT,
    file_path TEXT NOT NULL,
    file_size BIGINT DEFAULT 0,
    mime_type VARCHAR(100),
    file_hash VARCHAR(64),
    version INTEGER DEFAULT 1,
    is_latest BOOLEAN DEFAULT true,
    ai_summary TEXT,
    ai_analysis JSONB DEFAULT '{}',
    extracted_text TEXT,
    tags JSONB DEFAULT '[]',
    doc_metadata JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 文档版本表
CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT DEFAULT 0,
    file_hash VARCHAR(64),
    change_summary TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==================== 合同管理 ====================

-- 合同表
CREATE TABLE IF NOT EXISTS contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    contract_number VARCHAR(50) UNIQUE,
    contract_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    party_a JSONB DEFAULT '{}',
    party_b JSONB DEFAULT '{}',
    other_parties JSONB DEFAULT '[]',
    amount FLOAT,
    currency VARCHAR(10) DEFAULT 'CNY',
    sign_date DATE,
    effective_date DATE,
    expiry_date DATE,
    risk_level VARCHAR(20),
    risk_score FLOAT,
    review_summary TEXT,
    key_terms JSONB DEFAULT '{}',
    review_result JSONB DEFAULT '{}',
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 合同条款表
CREATE TABLE IF NOT EXISTS contract_clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE,
    clause_number VARCHAR(50) NOT NULL,
    clause_type VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    content TEXT NOT NULL,
    is_standard BOOLEAN DEFAULT true,
    risk_level VARCHAR(20),
    analysis JSONB DEFAULT '{}',
    suggestions JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 合同风险点
CREATE TABLE IF NOT EXISTS contract_risks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE,
    risk_type VARCHAR(100) NOT NULL,
    risk_level VARCHAR(20) DEFAULT 'medium',
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    related_clause VARCHAR(50),
    original_text TEXT,
    suggestion TEXT,
    suggested_text TEXT,
    is_resolved BOOLEAN DEFAULT false,
    resolution_note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==================== AI对话 ====================

-- 对话会话表
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    case_id UUID REFERENCES cases(id) ON DELETE SET NULL,
    title VARCHAR(255),
    summary TEXT,
    context JSONB DEFAULT '{}',
    message_count INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 对话消息表
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    agent_name VARCHAR(100),
    reasoning TEXT,
    citations JSONB DEFAULT '[]',
    actions JSONB DEFAULT '[]',
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    rating INTEGER,
    feedback TEXT,
    msg_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==================== 知识库 ====================

-- 知识库表
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    knowledge_type VARCHAR(50) DEFAULT 'other',
    doc_count INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 0,
    vector_collection VARCHAR(100),
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-large',
    embedding_dimensions INTEGER DEFAULT 3072,
    is_public BOOLEAN DEFAULT false,
    config JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 知识库文档表
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id UUID REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    source VARCHAR(255),
    source_url VARCHAR(500),
    content TEXT NOT NULL,
    summary TEXT,
    is_processed BOOLEAN DEFAULT false,
    chunk_count INTEGER DEFAULT 0,
    extra_metadata JSONB DEFAULT '{}',
    tags JSONB DEFAULT '[]',
    law_category VARCHAR(100),
    effective_date VARCHAR(50),
    issuing_authority VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==================== 舆情监控 ====================

-- 舆情报告表
CREATE TABLE IF NOT EXISTS due_diligence_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    unified_code VARCHAR(50),
    report_type VARCHAR(50) DEFAULT 'standard',
    risk_score DECIMAL(5, 2),
    risk_level VARCHAR(20),
    report_data JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'completed',
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==================== 索引 ====================

-- 用户索引
CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 案件索引
CREATE INDEX IF NOT EXISTS idx_cases_org_id ON cases(org_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_assignee_id ON cases(assignee_id);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases(created_at DESC);

-- 文档索引
CREATE INDEX IF NOT EXISTS idx_documents_org_id ON documents(org_id);
CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_documents_name ON documents USING gin(name gin_trgm_ops);

-- 对话索引
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);

-- 知识库索引
CREATE INDEX IF NOT EXISTS idx_knowledge_bases_org_id ON knowledge_bases(org_id);

-- ==================== 初始数据 ====================

-- 创建默认组织
INSERT INTO organizations (id, name, description)
VALUES ('00000000-0000-0000-0000-000000000001', '安心法务', 'AI法务系统默认组织')
ON CONFLICT (id) DO NOTHING;

-- 创建默认知识库
INSERT INTO knowledge_bases (id, org_id, name, description, knowledge_type)
VALUES 
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', '法律法规库', '中国法律法规汇编', 'law'),
    ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', '司法判例库', '裁判文书网判例', 'case'),
    ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001', '合同模板库', '标准合同模板', 'template')
ON CONFLICT (id) DO NOTHING;
