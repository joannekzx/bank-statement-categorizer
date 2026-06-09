export interface Transaction {
    data: string;
    description: string;
    merchant: string;
    amount: number;
    category: string | null;
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

export interface AnalystResult {
    bank: string;
    period_start: string;
    period_end: string;
    total_spend: number;
    transactions: Transaction[];
    by_category: CategorySummary[];
    top_merchants: MerchantSummary[];
}

export const CATEGORIES = [
    "Food", "Groceries", "Transport", "Shopping", "Subscriptions",
    "Bills & Utilities", "Health", "Entertainment", "Travel", 
    "Investments", "Transfers", "Income", "Other",
] as const;

export const EXCLUDED_CATEGORIES = new Set(["Income", "Transfers", "Investments" ]);
