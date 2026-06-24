export interface Transaction {
    id: number | null;       // stored-row id; null for a fresh /analyze response
    date: string;
    description: string;
    merchant: string;
    amount: number;          // original, signed; negative = spend
    category: string | null;
    reimbursed: number;      // confirmed offset applied to this spend (>= 0)
}

export interface CategorySummary {
    category: string;
    total: number;
    count: number;
}

export interface MerchantSummary {
    merchant: string;
    total: number;
    count: number;
}

export interface AnalysisResult {
    id: number | null;       // stored statement id (null for a raw /analyze)
    bank: string;
    period_start: string;
    period_end: string;
    total_spend: number;
    transactions: Transaction[];
    by_category: CategorySummary[];
    top_merchants: MerchantSummary[];
}

export interface StatementSummary {
    id: number;
    bank: string;
    period_start: string;
    period_end: string;
    uploaded_at: string;
    transaction_count: number;
    total_spend: number;
}

export interface ReimbursementSuggestion {
    transfer: Transaction;
    candidates: Transaction[];
}

// { category: { "2026-03": 180.5, "2026-04": 166.83 } }
export type Trends = Record<string, Record<string, number>>;

export const CATEGORIES = [
    "Food", "Groceries", "Transport", "Shopping", "Subscriptions",
    "Bills & Utilities", "Health", "Entertainment", "Travel", 
    "Investments", "Transfers", "Income", "Other",
] as const;

export const EXCLUDED_CATEGORIES = new Set(["Income", "Transfers", "Investments" ]);
