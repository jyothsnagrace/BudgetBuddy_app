-- BudgetBuddy Database Schema
-- Supabase PostgreSQL
-- Run this script in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLE: users
-- ============================================
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  username TEXT UNIQUE NOT NULL,
  display_name TEXT,
  selected_pet TEXT DEFAULT 'penguin' CHECK (selected_pet IN ('penguin', 'dragon', 'capybara', 'cat')),
  friendship_level INTEGER DEFAULT 1 CHECK (friendship_level BETWEEN 1 AND 10),
  last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT username_length CHECK (char_length(username) >= 3 AND char_length(username) <= 30)
);

-- Index for fast username lookups
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_last_activity ON users(last_activity);

-- ============================================
-- TABLE: expenses
-- ============================================
CREATE TABLE IF NOT EXISTS expenses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  amount DECIMAL(10, 2) NOT NULL CHECK (amount >= 0),
  category TEXT NOT NULL,
  description TEXT,
  expense_date DATE NOT NULL DEFAULT CURRENT_DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  metadata JSONB DEFAULT '{}',
  
  CONSTRAINT category_valid CHECK (category IN (
    'Food', 
    'Transportation', 
    'Entertainment', 
    'Shopping', 
    'Bills', 
    'Healthcare', 
    'Education', 
    'Other'
  ))
);

-- Indexes for fast queries
CREATE INDEX idx_expenses_user_id ON expenses(user_id);
CREATE INDEX idx_expenses_date ON expenses(expense_date DESC);
CREATE INDEX idx_expenses_category ON expenses(category);
CREATE INDEX idx_expenses_user_date ON expenses(user_id, expense_date DESC);

-- ============================================
-- TABLE: budgets
-- ============================================
CREATE TABLE IF NOT EXISTS budgets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  monthly_limit DECIMAL(10, 2) NOT NULL CHECK (monthly_limit > 0),
  category TEXT,
  month DATE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT category_or_total CHECK (
    category IS NULL OR 
    category IN ('Food', 'Transportation', 'Entertainment', 'Shopping', 'Bills', 'Healthcare', 'Education', 'Other')
  ),
  
  -- Unique constraint: one budget per user per month per category
  UNIQUE(user_id, month, category)
);

-- Indexes
CREATE INDEX idx_budgets_user_id ON budgets(user_id);
CREATE INDEX idx_budgets_month ON budgets(month DESC);
CREATE INDEX idx_budgets_user_month ON budgets(user_id, month DESC);

-- ============================================
-- TABLE: calendar_entries
-- ============================================
CREATE TABLE IF NOT EXISTS calendar_entries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expense_id UUID NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
  display_date DATE NOT NULL,
  label TEXT NOT NULL,
  category TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  UNIQUE(expense_id)
);

-- Indexes
CREATE INDEX idx_calendar_user_id ON calendar_entries(user_id);
CREATE INDEX idx_calendar_date ON calendar_entries(display_date);
CREATE INDEX idx_calendar_user_date ON calendar_entries(user_id, display_date);

-- ============================================
-- TABLE: chat_history (for chatbot context)
-- ============================================
CREATE TABLE IF NOT EXISTS chat_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  message TEXT NOT NULL,
  sender TEXT NOT NULL CHECK (sender IN ('user', 'assistant')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'
);

-- Index for retrieving recent chats
CREATE INDEX idx_chat_user_id ON chat_history(user_id);
CREATE INDEX idx_chat_created_at ON chat_history(created_at DESC);
CREATE INDEX idx_chat_user_recent ON chat_history(user_id, created_at DESC);

-- ============================================
-- TABLE: api_cache (for cost-of-living data)
-- ============================================
CREATE TABLE IF NOT EXISTS api_cache (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  cache_key TEXT UNIQUE NOT NULL,
  cache_value JSONB NOT NULL,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for cache lookups
CREATE INDEX idx_api_cache_key ON api_cache(cache_key);
CREATE INDEX idx_api_cache_expires ON api_cache(expires_at);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Function: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update updated_at for expenses
CREATE TRIGGER trigger_expenses_updated_at
    BEFORE UPDATE ON expenses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Auto-update updated_at for budgets
CREATE TRIGGER trigger_budgets_updated_at
    BEFORE UPDATE ON budgets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function: Auto-create calendar entry when expense is added
CREATE OR REPLACE FUNCTION create_calendar_entry()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO calendar_entries (user_id, expense_id, display_date, label, category)
    VALUES (
        NEW.user_id,
        NEW.id,
        NEW.expense_date,
        COALESCE(NEW.description, NEW.category),
        NEW.category
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-create calendar entry
CREATE TRIGGER trigger_create_calendar_entry
    AFTER INSERT ON expenses
    FOR EACH ROW
    EXECUTE FUNCTION create_calendar_entry();

-- ============================================
-- VIEWS
-- ============================================

-- View: Monthly spending summary
CREATE OR REPLACE VIEW monthly_spending_summary AS
SELECT 
    user_id,
    DATE_TRUNC('month', expense_date) as month,
    category,
    SUM(amount) as total_amount,
    COUNT(*) as transaction_count,
    AVG(amount) as avg_amount
FROM expenses
GROUP BY user_id, DATE_TRUNC('month', expense_date), category;

-- View: Budget vs actual comparison
CREATE OR REPLACE VIEW budget_comparison AS
SELECT 
    b.user_id,
    b.month,
    b.category,
    b.monthly_limit as budget,
    COALESCE(SUM(e.amount), 0) as actual_spent,
    b.monthly_limit - COALESCE(SUM(e.amount), 0) as remaining,
    CASE 
        WHEN COALESCE(SUM(e.amount), 0) > b.monthly_limit THEN 'over'
        WHEN COALESCE(SUM(e.amount), 0) > b.monthly_limit * 0.8 THEN 'warning'
        ELSE 'safe'
    END as status
FROM budgets b
LEFT JOIN expenses e ON 
    b.user_id = e.user_id 
    AND b.category = e.category 
    AND DATE_TRUNC('month', e.expense_date) = b.month
GROUP BY b.user_id, b.month, b.category, b.monthly_limit;

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own data
CREATE POLICY users_select_own ON users
    FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY expenses_select_own ON expenses
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY expenses_insert_own ON expenses
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY expenses_update_own ON expenses
    FOR UPDATE
    USING (user_id = auth.uid());

CREATE POLICY expenses_delete_own ON expenses
    FOR DELETE
    USING (user_id = auth.uid());

-- Similar policies for other tables
CREATE POLICY budgets_all_own ON budgets
    FOR ALL
    USING (user_id = auth.uid());

CREATE POLICY calendar_all_own ON calendar_entries
    FOR ALL
    USING (user_id = auth.uid());

CREATE POLICY chat_all_own ON chat_history
    FOR ALL
    USING (user_id = auth.uid());

-- ============================================
-- SAMPLE DATA (for testing)
-- ============================================

-- Insert sample user
INSERT INTO users (username, display_name, selected_pet)
VALUES ('demo_user', 'Demo User', 'penguin')
ON CONFLICT (username) DO NOTHING;

-- Insert sample expenses
DO $$
DECLARE
    demo_user_id UUID;
BEGIN
    SELECT id INTO demo_user_id FROM users WHERE username = 'demo_user';
    
    IF demo_user_id IS NOT NULL THEN
        INSERT INTO expenses (user_id, amount, category, description, expense_date)
        VALUES 
            (demo_user_id, 15.50, 'Food', 'Lunch at Chipotle', CURRENT_DATE),
            (demo_user_id, 45.00, 'Transportation', 'Uber to airport', CURRENT_DATE - 1),
            (demo_user_id, 120.00, 'Entertainment', 'Concert tickets', CURRENT_DATE - 2),
            (demo_user_id, 89.99, 'Shopping', 'New shoes', CURRENT_DATE - 3)
        ON CONFLICT DO NOTHING;
        
        INSERT INTO budgets (user_id, monthly_limit, category, month)
        VALUES 
            (demo_user_id, 500.00, 'Food', DATE_TRUNC('month', CURRENT_DATE)),
            (demo_user_id, 200.00, 'Transportation', DATE_TRUNC('month', CURRENT_DATE)),
            (demo_user_id, 150.00, 'Entertainment', DATE_TRUNC('month', CURRENT_DATE))
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

-- ============================================
-- CLEANUP FUNCTION (optional)
-- ============================================

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM api_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- You can run this periodically or set up a cron job in Supabase

COMMENT ON TABLE users IS 'User accounts with username-only authentication';
COMMENT ON TABLE expenses IS 'User expenses with category and metadata';
COMMENT ON TABLE budgets IS 'Monthly budget limits per category';
COMMENT ON TABLE calendar_entries IS 'Calendar view entries linked to expenses';
COMMENT ON TABLE chat_history IS 'Chatbot conversation history';
COMMENT ON TABLE api_cache IS 'Cache for external API responses (cost of living, etc.)';
